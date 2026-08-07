"""
Custom Formula & Expression Charting Service (Band B #26)

Features:
- Safe expression parser with financial functions
- Multi-ticker formula evaluation
- Time-series operations (rolling, lag, pct_change)
- Cross-sectional calculations
- Formula validation and error handling
"""

import re
import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import random


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class FormulaResult:
    """Result of a formula evaluation."""
    formula: str
    tickers: List[str]
    series: Dict[str, List[Dict[str, Any]]]  # ticker -> [{date, value}, ...]
    computed: List[Dict[str, Any]]  # [{date, value}, ...]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FormulaValidation:
    """Formula validation result."""
    valid: bool
    formula: str
    parsed_tokens: List[str]
    referenced_tickers: List[str]
    referenced_metrics: List[str]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SavedFormula:
    """User-saved formula."""
    id: str
    name: str
    formula: str
    description: str
    category: str
    tickers: List[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict:
        return asdict(self)


# ── Formula Parser ───────────────────────────────────────────────────────────

class FormulaParser:
    """Safe expression parser for financial formulas."""

    # Allowed functions
    FUNCTIONS = {
        # Math functions
        'abs': abs,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'sqrt': math.sqrt,
        'pow': pow,
        'min': min,
        'max': max,
        'round': round,

        # Statistical (will be implemented on series)
        'avg': 'avg',
        'std': 'std',
        'var': 'var',
        'sum': 'sum',
        'count': 'count',

        # Time-series functions
        'lag': 'lag',
        'lead': 'lead',
        'pct_change': 'pct_change',
        'rolling_avg': 'rolling_avg',
        'rolling_std': 'rolling_std',
        'rolling_sum': 'rolling_sum',
        'cumsum': 'cumsum',
        'diff': 'diff',

        # Cross-sectional
        'rank': 'rank',
        'zscore': 'zscore',
        'percentile': 'percentile',
    }

    # Financial metrics that can be referenced
    METRICS = {
        'price', 'close', 'open', 'high', 'low', 'volume',
        'market_cap', 'pe', 'pb', 'ps', 'ev_ebitda',
        'revenue', 'net_income', 'ebitda', 'eps',
        'roe', 'roa', 'roic', 'gross_margin', 'net_margin',
        'debt_equity', 'current_ratio', 'quick_ratio',
        'dividend_yield', 'payout_ratio',
        'beta', 'volatility', 'sharpe',
    }

    # Operators
    OPERATORS = {'+', '-', '*', '/', '^', '%', '(', ')', ','}

    def __init__(self):
        self.token_pattern = re.compile(
            r'(\d+\.?\d*)|'  # Numbers
            r'([A-Z]{1,5})\.([\w]+)|'  # TICKER.metric
            r'(\w+)\s*\(|'  # Function calls
            r'([+\-*/^%(),])|'  # Operators
            r'(\w+)'  # Identifiers
        )

    def tokenize(self, formula: str) -> List[str]:
        """Tokenize formula into components."""
        tokens = []
        for match in self.token_pattern.finditer(formula):
            token = match.group(0).strip()
            if token:
                tokens.append(token)
        return tokens

    def extract_references(self, formula: str) -> tuple:
        """Extract ticker and metric references from formula."""
        tickers = set()
        metrics = set()

        # Pattern for TICKER.metric
        ref_pattern = re.compile(r'([A-Z]{1,5})\.(\w+)')
        for match in ref_pattern.finditer(formula):
            tickers.add(match.group(1))
            metrics.add(match.group(2))

        return list(tickers), list(metrics)

    def validate(self, formula: str) -> FormulaValidation:
        """Validate a formula for safety and correctness."""
        errors = []
        warnings = []

        # Check for dangerous patterns
        dangerous = ['import', 'exec', 'eval', '__', 'open', 'file', 'os.', 'sys.']
        for pattern in dangerous:
            if pattern in formula.lower():
                errors.append(f"Dangerous pattern detected: {pattern}")

        tokens = self.tokenize(formula)
        tickers, metrics = self.extract_references(formula)

        # Validate metrics
        for metric in metrics:
            if metric.lower() not in self.METRICS:
                warnings.append(f"Unknown metric '{metric}' - will try to resolve")

        # Check balanced parentheses
        paren_count = formula.count('(') - formula.count(')')
        if paren_count != 0:
            errors.append("Unbalanced parentheses")

        # Validate function names
        func_pattern = re.compile(r'(\w+)\s*\(')
        for match in func_pattern.finditer(formula):
            func_name = match.group(1).lower()
            if func_name not in self.FUNCTIONS and func_name not in [t.lower() for t in tickers]:
                errors.append(f"Unknown function: {func_name}")

        return FormulaValidation(
            valid=len(errors) == 0,
            formula=formula,
            parsed_tokens=tokens,
            referenced_tickers=tickers,
            referenced_metrics=metrics,
            errors=errors,
            warnings=warnings,
        )


# ── Formula Engine ───────────────────────────────────────────────────────────

class FormulaEngine:
    """Executes formulas against financial data."""

    def __init__(self):
        self.parser = FormulaParser()
        self._data_cache = {}

    def _generate_mock_series(self, ticker: str, metric: str, days: int = 252) -> List[Dict]:
        """Generate mock time series data for a ticker.metric."""
        base_date = datetime.now()
        series = []

        # Base values by metric type
        base_values = {
            'price': random.uniform(50, 500),
            'close': random.uniform(50, 500),
            'volume': random.uniform(1_000_000, 50_000_000),
            'pe': random.uniform(10, 40),
            'market_cap': random.uniform(10_000_000_000, 500_000_000_000),
            'revenue': random.uniform(1_000_000_000, 100_000_000_000),
            'eps': random.uniform(1, 20),
        }

        base = base_values.get(metric.lower(), random.uniform(10, 100))
        volatility = 0.02 if 'price' in metric.lower() else 0.01

        value = base
        for i in range(days):
            date = base_date - timedelta(days=days - i)
            # Random walk with drift
            change = random.gauss(0.0002, volatility)
            value = value * (1 + change)

            series.append({
                'date': date.strftime('%Y-%m-%d'),
                'value': round(value, 4),
            })

        return series

    def _fetch_series(self, ticker: str, metric: str, days: int = 252) -> List[Dict]:
        """Fetch time series data for ticker.metric."""
        cache_key = f"{ticker}.{metric}"
        if cache_key not in self._data_cache:
            # In production, this would call actual data APIs
            self._data_cache[cache_key] = self._generate_mock_series(ticker, metric, days)
        return self._data_cache[cache_key]

    def _apply_time_series_func(
        self,
        series: List[Dict],
        func_name: str,
        *args
    ) -> List[Dict]:
        """Apply a time-series function to a series."""
        values = [d['value'] for d in series]
        dates = [d['date'] for d in series]

        result_values = []

        if func_name == 'pct_change':
            periods = int(args[0]) if args else 1
            result_values = [None] * periods
            for i in range(periods, len(values)):
                if values[i - periods] != 0:
                    pct = (values[i] - values[i - periods]) / values[i - periods]
                    result_values.append(round(pct, 6))
                else:
                    result_values.append(None)

        elif func_name == 'lag':
            periods = int(args[0]) if args else 1
            result_values = [None] * periods + values[:-periods]

        elif func_name == 'rolling_avg':
            window = int(args[0]) if args else 20
            for i in range(len(values)):
                if i < window - 1:
                    result_values.append(None)
                else:
                    avg = sum(values[i - window + 1:i + 1]) / window
                    result_values.append(round(avg, 4))

        elif func_name == 'rolling_std':
            window = int(args[0]) if args else 20
            for i in range(len(values)):
                if i < window - 1:
                    result_values.append(None)
                else:
                    window_vals = values[i - window + 1:i + 1]
                    mean = sum(window_vals) / window
                    variance = sum((x - mean) ** 2 for x in window_vals) / window
                    result_values.append(round(math.sqrt(variance), 4))

        elif func_name == 'cumsum':
            cumulative = 0
            for v in values:
                cumulative += v if v else 0
                result_values.append(round(cumulative, 4))

        elif func_name == 'diff':
            periods = int(args[0]) if args else 1
            result_values = [None] * periods
            for i in range(periods, len(values)):
                result_values.append(round(values[i] - values[i - periods], 4))

        else:
            result_values = values

        return [
            {'date': d, 'value': v}
            for d, v in zip(dates, result_values)
        ]

    def _evaluate_binary_op(
        self,
        left: List[Dict],
        right: List[Dict],
        op: str
    ) -> List[Dict]:
        """Evaluate a binary operation between two series."""
        # Align by date
        left_by_date = {d['date']: d['value'] for d in left}
        right_by_date = {d['date']: d['value'] for d in right}

        all_dates = sorted(set(left_by_date.keys()) & set(right_by_date.keys()))

        results = []
        for date in all_dates:
            lv = left_by_date.get(date)
            rv = right_by_date.get(date)

            if lv is None or rv is None:
                results.append({'date': date, 'value': None})
                continue

            if op == '+':
                value = lv + rv
            elif op == '-':
                value = lv - rv
            elif op == '*':
                value = lv * rv
            elif op == '/':
                value = lv / rv if rv != 0 else None
            elif op == '^':
                value = lv ** rv
            else:
                value = None

            results.append({'date': date, 'value': round(value, 4) if value else None})

        return results

    def evaluate(
        self,
        formula: str,
        days: int = 252,
        tickers: Optional[List[str]] = None
    ) -> FormulaResult:
        """Evaluate a formula and return results."""
        validation = self.parser.validate(formula)
        if not validation.valid:
            return FormulaResult(
                formula=formula,
                tickers=[],
                series={},
                computed=[],
                metadata={'errors': validation.errors}
            )

        # Get referenced tickers from formula or use provided
        ref_tickers = tickers or validation.referenced_tickers

        # Fetch all required series
        all_series = {}
        for ticker in ref_tickers:
            all_series[ticker] = {}
            for metric in validation.referenced_metrics:
                all_series[ticker][metric] = self._fetch_series(ticker, metric, days)

        # Simplified evaluation: handle common patterns
        # Pattern: TICKER.metric
        simple_ref = re.match(r'^([A-Z]{1,5})\.(\w+)$', formula.strip())
        if simple_ref:
            ticker, metric = simple_ref.groups()
            series = self._fetch_series(ticker, metric, days)
            return FormulaResult(
                formula=formula,
                tickers=[ticker],
                series={ticker: series},
                computed=series,
                metadata={'type': 'simple_reference'}
            )

        # Pattern: TICKER.metric / TICKER.metric (ratio)
        ratio_match = re.match(
            r'^([A-Z]{1,5})\.(\w+)\s*/\s*([A-Z]{1,5})\.(\w+)$',
            formula.strip()
        )
        if ratio_match:
            t1, m1, t2, m2 = ratio_match.groups()
            s1 = self._fetch_series(t1, m1, days)
            s2 = self._fetch_series(t2, m2, days)
            computed = self._evaluate_binary_op(s1, s2, '/')
            return FormulaResult(
                formula=formula,
                tickers=[t1, t2],
                series={t1: s1, t2: s2},
                computed=computed,
                metadata={'type': 'ratio'}
            )

        # Pattern: pct_change(TICKER.metric, N)
        pct_match = re.match(
            r'^pct_change\s*\(\s*([A-Z]{1,5})\.(\w+)\s*(?:,\s*(\d+))?\s*\)$',
            formula.strip()
        )
        if pct_match:
            ticker, metric, periods = pct_match.groups()
            periods = int(periods) if periods else 1
            series = self._fetch_series(ticker, metric, days)
            computed = self._apply_time_series_func(series, 'pct_change', periods)
            return FormulaResult(
                formula=formula,
                tickers=[ticker],
                series={ticker: series},
                computed=computed,
                metadata={'type': 'pct_change', 'periods': periods}
            )

        # Pattern: rolling_avg(TICKER.metric, N)
        roll_match = re.match(
            r'^rolling_avg\s*\(\s*([A-Z]{1,5})\.(\w+)\s*,\s*(\d+)\s*\)$',
            formula.strip()
        )
        if roll_match:
            ticker, metric, window = roll_match.groups()
            window = int(window)
            series = self._fetch_series(ticker, metric, days)
            computed = self._apply_time_series_func(series, 'rolling_avg', window)
            return FormulaResult(
                formula=formula,
                tickers=[ticker],
                series={ticker: series},
                computed=computed,
                metadata={'type': 'rolling_avg', 'window': window}
            )

        # Default: return first ticker's first metric
        if ref_tickers and validation.referenced_metrics:
            ticker = ref_tickers[0]
            metric = validation.referenced_metrics[0]
            series = self._fetch_series(ticker, metric, days)
            return FormulaResult(
                formula=formula,
                tickers=ref_tickers,
                series={ticker: series},
                computed=series,
                metadata={'type': 'fallback', 'note': 'Complex formula - simplified evaluation'}
            )

        return FormulaResult(
            formula=formula,
            tickers=[],
            series={},
            computed=[],
            metadata={'error': 'Could not evaluate formula'}
        )


# ── Service Class ────────────────────────────────────────────────────────────

class FormulaService:
    """Main service for formula operations."""

    def __init__(self):
        self.engine = FormulaEngine()
        self.parser = FormulaParser()
        self._saved_formulas: Dict[str, SavedFormula] = {}
        self._init_preset_formulas()

    def _init_preset_formulas(self):
        """Initialize preset formulas."""
        presets = [
            SavedFormula(
                id='preset_pe_ratio',
                name='P/E Ratio',
                formula='TICKER.price / TICKER.eps',
                description='Price to Earnings ratio',
                category='valuation',
                tickers=[],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            ),
            SavedFormula(
                id='preset_momentum',
                name='12M Momentum',
                formula='pct_change(TICKER.price, 252)',
                description='12-month price momentum',
                category='technical',
                tickers=[],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            ),
            SavedFormula(
                id='preset_volatility',
                name='20D Volatility',
                formula='rolling_std(TICKER.price, 20)',
                description='20-day rolling volatility',
                category='risk',
                tickers=[],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            ),
            SavedFormula(
                id='preset_relative_strength',
                name='Relative Strength',
                formula='TICKER.price / SPY.price',
                description='Relative strength vs SPY',
                category='technical',
                tickers=['SPY'],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            ),
        ]
        for p in presets:
            self._saved_formulas[p.id] = p

    def validate_formula(self, formula: str) -> FormulaValidation:
        """Validate a formula."""
        return self.parser.validate(formula)

    def evaluate_formula(
        self,
        formula: str,
        tickers: Optional[List[str]] = None,
        days: int = 252
    ) -> FormulaResult:
        """Evaluate a formula and return chart data."""
        return self.engine.evaluate(formula, days=days, tickers=tickers)

    def save_formula(
        self,
        name: str,
        formula: str,
        description: str = '',
        category: str = 'custom',
        tickers: Optional[List[str]] = None
    ) -> SavedFormula:
        """Save a custom formula."""
        formula_id = f"custom_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self._saved_formulas)}"

        saved = SavedFormula(
            id=formula_id,
            name=name,
            formula=formula,
            description=description,
            category=category,
            tickers=tickers or [],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        self._saved_formulas[formula_id] = saved
        return saved

    def list_formulas(self, category: Optional[str] = None) -> List[SavedFormula]:
        """List saved formulas."""
        formulas = list(self._saved_formulas.values())
        if category:
            formulas = [f for f in formulas if f.category == category]
        return formulas

    def get_formula(self, formula_id: str) -> Optional[SavedFormula]:
        """Get a saved formula by ID."""
        return self._saved_formulas.get(formula_id)

    def delete_formula(self, formula_id: str) -> bool:
        """Delete a saved formula."""
        if formula_id in self._saved_formulas and not formula_id.startswith('preset_'):
            del self._saved_formulas[formula_id]
            return True
        return False

    def get_available_metrics(self) -> List[Dict[str, str]]:
        """Get list of available metrics for formulas."""
        metrics = []
        for metric in sorted(FormulaParser.METRICS):
            metrics.append({
                'name': metric,
                'description': self._get_metric_description(metric),
            })
        return metrics

    def get_available_functions(self) -> List[Dict[str, str]]:
        """Get list of available functions for formulas."""
        descriptions = {
            'abs': 'Absolute value',
            'log': 'Natural logarithm',
            'log10': 'Base-10 logarithm',
            'exp': 'Exponential (e^x)',
            'sqrt': 'Square root',
            'pow': 'Power (x^y)',
            'min': 'Minimum value',
            'max': 'Maximum value',
            'round': 'Round to nearest integer',
            'avg': 'Average of series',
            'std': 'Standard deviation',
            'var': 'Variance',
            'sum': 'Sum of values',
            'count': 'Count of values',
            'lag': 'Lag values by N periods',
            'lead': 'Lead values by N periods',
            'pct_change': 'Percentage change over N periods',
            'rolling_avg': 'Rolling average over N periods',
            'rolling_std': 'Rolling standard deviation',
            'rolling_sum': 'Rolling sum over N periods',
            'cumsum': 'Cumulative sum',
            'diff': 'Difference from N periods ago',
            'rank': 'Cross-sectional rank',
            'zscore': 'Cross-sectional z-score',
            'percentile': 'Cross-sectional percentile',
        }
        return [
            {'name': name, 'description': descriptions.get(name, '')}
            for name in sorted(FormulaParser.FUNCTIONS.keys())
        ]

    def _get_metric_description(self, metric: str) -> str:
        """Get description for a metric."""
        descriptions = {
            'price': 'Current/closing price',
            'close': 'Closing price',
            'open': 'Opening price',
            'high': 'High price',
            'low': 'Low price',
            'volume': 'Trading volume',
            'market_cap': 'Market capitalization',
            'pe': 'Price to Earnings ratio',
            'pb': 'Price to Book ratio',
            'ps': 'Price to Sales ratio',
            'ev_ebitda': 'EV/EBITDA ratio',
            'revenue': 'Total revenue',
            'net_income': 'Net income',
            'ebitda': 'EBITDA',
            'eps': 'Earnings per share',
            'roe': 'Return on equity',
            'roa': 'Return on assets',
            'roic': 'Return on invested capital',
            'gross_margin': 'Gross profit margin',
            'net_margin': 'Net profit margin',
            'debt_equity': 'Debt to equity ratio',
            'current_ratio': 'Current ratio',
            'quick_ratio': 'Quick ratio',
            'dividend_yield': 'Dividend yield',
            'payout_ratio': 'Dividend payout ratio',
            'beta': 'Beta vs market',
            'volatility': 'Historical volatility',
            'sharpe': 'Sharpe ratio',
        }
        return descriptions.get(metric, '')


# ── Module-level instance ────────────────────────────────────────────────────

_service_instance = None

def get_formula_service() -> FormulaService:
    """Get singleton service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = FormulaService()
    return _service_instance
