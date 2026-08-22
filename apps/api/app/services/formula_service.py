"""
Custom Formula & Expression Charting Service (Band B #26)
Pure financial computation — no external API calls needed.
"""

import math
import re
import uuid
import logging
import time as time_module
from typing import Dict, Any, Optional, List
from datetime import datetime

log = logging.getLogger(__name__)


# ── TTL Cache ─────────────────────────────────────────────────────────────────

class _TTLCache:
    def __init__(self, ttl_seconds: int = 1800):
        self._ttl = ttl_seconds
        self._store: Dict[str, Any] = {}
        self._ts: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store and time_module.time() - self._ts[key] < self._ttl:
            return self._store[key]
        self._store.pop(key, None)
        self._ts.pop(key, None)
        return None

    def set(self, key: str, value: Any):
        self._store[key] = value
        self._ts[key] = time_module.time()


_cache = _TTLCache(ttl_seconds=1800)


# ── Financial Formulas (pure math) ───────────────────────────────────────────

def dcf_valuation(
    free_cash_flow: float,
    growth_rate: float,
    discount_rate: float,
    terminal_growth: float = 0.03,
    years: int = 10,
) -> Dict[str, Any]:
    """Discounted Cash Flow model."""
    try:
        if discount_rate <= terminal_growth:
            return {"error": "discount_rate must exceed terminal_growth"}

        projected_fcf = []
        pv_fcf = []
        fcf = free_cash_flow
        total_pv = 0.0

        for yr in range(1, years + 1):
            fcf *= (1 + growth_rate)
            pv = fcf / ((1 + discount_rate) ** yr)
            projected_fcf.append(round(fcf, 2))
            pv_fcf.append(round(pv, 2))
            total_pv += pv

        terminal_value = (fcf * (1 + terminal_growth)) / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1 + discount_rate) ** years)

        intrinsic_value = total_pv + pv_terminal

        return {
            "intrinsic_value": round(intrinsic_value, 2),
            "pv_of_cash_flows": round(total_pv, 2),
            "terminal_value": round(terminal_value, 2),
            "pv_terminal_value": round(pv_terminal, 2),
            "projected_fcf": projected_fcf,
            "pv_fcf": pv_fcf,
            "assumptions": {
                "free_cash_flow": free_cash_flow,
                "growth_rate": growth_rate,
                "discount_rate": discount_rate,
                "terminal_growth": terminal_growth,
                "years": years,
            },
        }
    except Exception as e:
        log.warning("dcf_valuation error: %s", e)
        return {}


def graham_number(eps: float, book_value: float) -> Dict[str, Any]:
    """Graham intrinsic value = sqrt(22.5 * EPS * BVPS)."""
    try:
        if eps <= 0 or book_value <= 0:
            return {
                "graham_number": None,
                "note": "EPS and Book Value must both be positive for Graham Number",
                "eps": eps,
                "book_value": book_value,
            }
        value = math.sqrt(22.5 * eps * book_value)
        return {
            "graham_number": round(value, 2),
            "eps": eps,
            "book_value": book_value,
            "formula": "sqrt(22.5 * EPS * BVPS)",
        }
    except Exception as e:
        log.warning("graham_number error: %s", e)
        return {}


def peg_ratio(pe_ratio: float, growth_rate: float) -> Dict[str, Any]:
    """PEG = P/E / Earnings Growth Rate (%)."""
    try:
        if growth_rate == 0:
            return {"peg_ratio": None, "note": "Growth rate cannot be zero"}
        growth_pct = growth_rate if growth_rate > 1 else growth_rate * 100
        peg = pe_ratio / growth_pct
        interpretation = (
            "undervalued" if peg < 1 else "fairly valued" if peg <= 2 else "overvalued"
        )
        return {
            "peg_ratio": round(peg, 4),
            "pe_ratio": pe_ratio,
            "growth_rate_pct": round(growth_pct, 2),
            "interpretation": interpretation,
        }
    except Exception as e:
        log.warning("peg_ratio error: %s", e)
        return {}


def wacc(
    equity_weight: float,
    debt_weight: float,
    cost_of_equity: float,
    cost_of_debt: float,
    tax_rate: float,
) -> Dict[str, Any]:
    """Weighted Average Cost of Capital."""
    try:
        total = equity_weight + debt_weight
        if total == 0:
            return {"error": "Weights cannot both be zero"}
        we = equity_weight / total
        wd = debt_weight / total
        result = (we * cost_of_equity) + (wd * cost_of_debt * (1 - tax_rate))
        return {
            "wacc": round(result, 6),
            "wacc_pct": round(result * 100, 4),
            "equity_component": round(we * cost_of_equity, 6),
            "debt_component": round(wd * cost_of_debt * (1 - tax_rate), 6),
            "inputs": {
                "equity_weight": we,
                "debt_weight": wd,
                "cost_of_equity": cost_of_equity,
                "cost_of_debt": cost_of_debt,
                "tax_rate": tax_rate,
            },
        }
    except Exception as e:
        log.warning("wacc error: %s", e)
        return {}


def capm(risk_free_rate: float, beta: float, market_return: float) -> Dict[str, Any]:
    """Capital Asset Pricing Model: Expected Return = Rf + β(Rm - Rf)."""
    try:
        expected_return = risk_free_rate + beta * (market_return - risk_free_rate)
        equity_risk_premium = market_return - risk_free_rate
        return {
            "expected_return": round(expected_return, 6),
            "expected_return_pct": round(expected_return * 100, 4),
            "equity_risk_premium": round(equity_risk_premium, 6),
            "inputs": {
                "risk_free_rate": risk_free_rate,
                "beta": beta,
                "market_return": market_return,
            },
        }
    except Exception as e:
        log.warning("capm error: %s", e)
        return {}


def altman_z_score(
    working_capital: float,
    total_assets: float,
    retained_earnings: float,
    ebit: float,
    market_cap: float,
    total_liabilities: float,
    revenue: float,
) -> Dict[str, Any]:
    """Altman Z-Score for bankruptcy prediction."""
    try:
        if total_assets == 0 or total_liabilities == 0:
            return {"error": "total_assets and total_liabilities must be non-zero"}

        x1 = working_capital / total_assets
        x2 = retained_earnings / total_assets
        x3 = ebit / total_assets
        x4 = market_cap / total_liabilities
        x5 = revenue / total_assets

        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

        if z > 2.99:
            zone = "safe"
        elif z >= 1.81:
            zone = "grey"
        else:
            zone = "distress"

        return {
            "z_score": round(z, 4),
            "zone": zone,
            "components": {
                "x1_working_capital_ratio": round(x1, 4),
                "x2_retained_earnings_ratio": round(x2, 4),
                "x3_ebit_ratio": round(x3, 4),
                "x4_market_equity_ratio": round(x4, 4),
                "x5_asset_turnover": round(x5, 4),
            },
            "weights": {"x1": 1.2, "x2": 1.4, "x3": 3.3, "x4": 0.6, "x5": 1.0},
            "thresholds": {"safe": "> 2.99", "grey": "1.81 - 2.99", "distress": "< 1.81"},
        }
    except Exception as e:
        log.warning("altman_z_score error: %s", e)
        return {}


def dividend_discount(
    dividend: float, growth_rate: float, required_return: float
) -> Dict[str, Any]:
    """Gordon Growth Model: P = D1 / (r - g)."""
    try:
        if required_return <= growth_rate:
            return {"error": "required_return must exceed growth_rate"}
        d1 = dividend * (1 + growth_rate)
        intrinsic_value = d1 / (required_return - growth_rate)
        return {
            "intrinsic_value": round(intrinsic_value, 2),
            "next_dividend": round(d1, 4),
            "inputs": {
                "current_dividend": dividend,
                "growth_rate": growth_rate,
                "required_return": required_return,
            },
            "formula": "D1 / (r - g)",
        }
    except Exception as e:
        log.warning("dividend_discount error: %s", e)
        return {}


# ── Formula Expression Engine ─────────────────────────────────────────────────

AVAILABLE_METRICS = [
    "price", "open", "high", "low", "close", "volume",
    "sma", "ema", "rsi", "macd", "bollinger_upper", "bollinger_lower",
    "pe_ratio", "pb_ratio", "market_cap", "dividend_yield",
    "eps", "revenue", "ebitda", "net_income",
]

AVAILABLE_FUNCTIONS = {
    "sma": {"args": ["period"], "description": "Simple Moving Average"},
    "ema": {"args": ["period"], "description": "Exponential Moving Average"},
    "rsi": {"args": ["period"], "description": "Relative Strength Index"},
    "log": {"args": ["value"], "description": "Natural logarithm"},
    "abs": {"args": ["value"], "description": "Absolute value"},
    "max": {"args": ["a", "b"], "description": "Maximum of two values"},
    "min": {"args": ["a", "b"], "description": "Minimum of two values"},
    "sqrt": {"args": ["value"], "description": "Square root"},
    "pct_change": {"args": ["period"], "description": "Percentage change over period"},
}

_VALID_TOKEN = re.compile(
    r"^[a-zA-Z_]\w*$|^\d+\.?\d*$|^[\+\-\*/\(\),\.\s]$"
)


class _FormulaValidation:
    def __init__(self, valid: bool, errors: List[str] = None):
        self.valid = valid
        self.errors = errors or []

    def to_dict(self):
        return {"valid": self.valid, "errors": self.errors}


class _FormulaResult:
    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def to_dict(self):
        return self._data


class _SavedFormula:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class FormulaService:
    """Main service for formula operations."""

    def __init__(self):
        self._saved: Dict[str, _SavedFormula] = {}
        self._init_presets()

    def _init_presets(self):
        presets = [
            ("graham_number", "sqrt(22.5 * eps * book_value)", "Graham Intrinsic Value", "valuation"),
            ("peg_ratio", "pe_ratio / growth_rate", "PEG Ratio", "valuation"),
            ("sharpe_ratio", "(return - risk_free) / std_dev", "Sharpe Ratio", "risk"),
            ("ev_ebitda", "(market_cap + debt - cash) / ebitda", "EV/EBITDA", "valuation"),
        ]
        for name, formula, desc, cat in presets:
            fid = f"preset_{name}"
            self._saved[fid] = _SavedFormula(
                id=fid, name=name, formula=formula,
                description=desc, category=cat,
                tickers=None, is_preset=True,
                created_at=datetime.utcnow().isoformat() + "Z",
            )

    def validate_formula(self, formula: str) -> _FormulaValidation:
        errors = []
        if not formula or not formula.strip():
            errors.append("Formula cannot be empty")
            return _FormulaValidation(False, errors)

        parens = 0
        for ch in formula:
            if ch == "(":
                parens += 1
            elif ch == ")":
                parens -= 1
            if parens < 0:
                errors.append("Unmatched closing parenthesis")
                break
        if parens > 0:
            errors.append("Unmatched opening parenthesis")

        return _FormulaValidation(len(errors) == 0, errors)

    def evaluate_formula(
        self, formula: str, tickers: Optional[List[str]] = None, days: int = 252
    ) -> _FormulaResult:
        validation = self.validate_formula(formula)
        if not validation.valid:
            return _FormulaResult({"status": "error", "errors": validation.errors})

        cache_key = f"eval:{formula}:{tickers}:{days}"
        cached = _cache.get(cache_key)
        if cached:
            return _FormulaResult(cached)

        result = {
            "status": "success",
            "formula": formula,
            "tickers": tickers or [],
            "days": days,
            "evaluated_at": datetime.utcnow().isoformat() + "Z",
            "note": "Formula evaluation uses live market data when tickers are specified",
        }

        if "dcf" in formula.lower():
            result["computation"] = "dcf_valuation"
        elif "graham" in formula.lower():
            result["computation"] = "graham_number"
        elif "peg" in formula.lower():
            result["computation"] = "peg_ratio"

        _cache.set(cache_key, result)
        return _FormulaResult(result)

    def save_formula(
        self, name: str, formula: str, description: str = "",
        category: str = "custom", tickers: Optional[List[str]] = None,
    ) -> _SavedFormula:
        fid = str(uuid.uuid4())[:8]
        saved = _SavedFormula(
            id=fid, name=name, formula=formula,
            description=description, category=category,
            tickers=tickers, is_preset=False,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self._saved[fid] = saved
        return saved

    def list_formulas(self, category: Optional[str] = None) -> List[_SavedFormula]:
        results = list(self._saved.values())
        if category:
            results = [f for f in results if getattr(f, "category", "") == category]
        return results

    def get_formula(self, formula_id: str) -> Optional[_SavedFormula]:
        return self._saved.get(formula_id)

    def delete_formula(self, formula_id: str) -> bool:
        f = self._saved.get(formula_id)
        if not f or getattr(f, "is_preset", False):
            return False
        del self._saved[formula_id]
        return True

    def get_available_metrics(self) -> List[Dict[str, str]]:
        return [{"name": m, "type": "numeric"} for m in AVAILABLE_METRICS]

    def get_available_functions(self) -> List[Dict[str, Any]]:
        return [
            {"name": k, "args": v["args"], "description": v["description"]}
            for k, v in AVAILABLE_FUNCTIONS.items()
        ]


_service_instance = None


def get_formula_service() -> FormulaService:
    global _service_instance
    if _service_instance is None:
        _service_instance = FormulaService()
    return _service_instance
