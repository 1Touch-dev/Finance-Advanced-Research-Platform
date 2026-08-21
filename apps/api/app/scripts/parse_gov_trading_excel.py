"""
Parse Government Officials Stock Trading Rankings Excel
─────────────────────────────────────────────────────────
Source: docs/US Government Officials — Stock Trading Rankings.xlsx
Data: Capitol Markets, Capitol Trades, Kapitol.ai, Open Cabinet (2013-2026)

Outputs JSON files for:
- Top by Trades (357 officials)
- Top by Volume (241 officials)
- Top by Returns (72 officials)
- Executive Branch (50 officials)
- Notable Cases (20 cases)
- Lobbying Context (43 firms)
- Flat Combined (637 total deduplicated)
"""
import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Any

log = logging.getLogger(__name__)

# Try importing openpyxl, pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    log.warning("pandas not installed - Excel parsing unavailable")

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    log.warning("openpyxl not installed - Excel parsing unavailable")


# Base paths - scripts is in apps/api/app/scripts, so go up 4 levels to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
EXCEL_PATH = PROJECT_ROOT / "docs" / "US Government Officials — Stock Trading Rankings.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "apps" / "api" / "app" / "data" / "gov_trading"


def parse_excel() -> Dict[str, Any]:
    """Parse the Excel file and return all sheets as structured data."""
    if not PANDAS_AVAILABLE or not OPENPYXL_AVAILABLE:
        return {"error": "pandas or openpyxl not installed"}

    if not EXCEL_PATH.exists():
        return {"error": f"Excel file not found at {EXCEL_PATH}"}

    result = {
        "top_by_trades": [],
        "top_by_volume": [],
        "top_by_returns": [],
        "executive_branch": [],
        "notable_cases": [],
        "lobbying_context": [],
        "flat_combined": [],
        "metadata": {
            "source": str(EXCEL_PATH),
            "parsed_at": None,
        }
    }

    try:
        xl = pd.ExcelFile(EXCEL_PATH, engine='openpyxl')
        sheet_names = xl.sheet_names
        log.info(f"Found sheets: {sheet_names}")

        # Map sheet names to our keys (flexible matching)
        sheet_mapping = {}
        for sheet in sheet_names:
            sheet_lower = sheet.lower()
            if "trade" in sheet_lower and "top" in sheet_lower:
                sheet_mapping["top_by_trades"] = sheet
            elif "volume" in sheet_lower:
                sheet_mapping["top_by_volume"] = sheet
            elif "return" in sheet_lower:
                sheet_mapping["top_by_returns"] = sheet
            elif "executive" in sheet_lower:
                sheet_mapping["executive_branch"] = sheet
            elif "notable" in sheet_lower or "case" in sheet_lower:
                sheet_mapping["notable_cases"] = sheet
            elif "lobby" in sheet_lower:
                sheet_mapping["lobbying_context"] = sheet
            elif "flat" in sheet_lower or "combined" in sheet_lower:
                sheet_mapping["flat_combined"] = sheet

        # Parse each mapped sheet - headers are in row 4 (0-indexed)
        for key, sheet_name in sheet_mapping.items():
            try:
                # Read with header at row 4 (skip first 4 rows), skip empty column 0
                df = pd.read_excel(xl, sheet_name=sheet_name, header=4)
                # Drop first column if it's unnamed/empty
                if df.columns[0] in ['Unnamed: 0', None] or str(df.columns[0]).startswith('Unnamed'):
                    df = df.iloc[:, 1:]
                # Clean column names
                df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "").replace("$", "").replace("%", "pct").replace("/", "_") for c in df.columns]
                # Remove rows where all values are NaN
                df = df.dropna(how='all')
                # Convert to list of dicts, handling NaN
                records = df.where(pd.notnull(df), None).to_dict(orient='records')
                result[key] = records
                log.info(f"Parsed {key}: {len(records)} records")
            except Exception as e:
                log.warning(f"Failed to parse sheet {sheet_name}: {e}")

        # If no flat_combined, create from all politician records
        if not result["flat_combined"]:
            seen = set()
            combined = []
            for key in ["top_by_trades", "top_by_volume", "top_by_returns", "executive_branch"]:
                for record in result.get(key, []):
                    name = record.get("name") or record.get("official") or record.get("politician")
                    if name and name not in seen:
                        seen.add(name)
                        combined.append(record)
            result["flat_combined"] = combined
            log.info(f"Created flat_combined from {len(combined)} unique officials")

        from datetime import datetime
        result["metadata"]["parsed_at"] = datetime.now().isoformat()
        result["metadata"]["sheet_names"] = sheet_names
        result["metadata"]["mapped_sheets"] = sheet_mapping

    except Exception as e:
        log.error(f"Excel parse error: {e}")
        result["error"] = str(e)

    return result


def save_parsed_data(data: Dict[str, Any]) -> str:
    """Save parsed data to JSON files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save combined file
    combined_path = OUTPUT_DIR / "gov_trading_rankings.json"
    with open(combined_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    # Save individual files for each category
    for key in ["top_by_trades", "top_by_volume", "top_by_returns",
                "executive_branch", "notable_cases", "lobbying_context", "flat_combined"]:
        if data.get(key):
            path = OUTPUT_DIR / f"{key}.json"
            with open(path, 'w') as f:
                json.dump(data[key], f, indent=2, default=str)

    return str(combined_path)


def load_cached_data() -> Dict[str, Any]:
    """Load previously parsed data from JSON cache."""
    combined_path = OUTPUT_DIR / "gov_trading_rankings.json"
    if combined_path.exists():
        with open(combined_path, 'r') as f:
            return json.load(f)
    return {}


def get_leaderboard_data(category: str = "trades", limit: int = 50) -> List[Dict]:
    """
    Get leaderboard data for a specific category.
    Categories: trades, volume, returns, executive
    """
    data = load_cached_data()
    if not data:
        data = parse_excel()
        if not data.get("error"):
            save_parsed_data(data)

    category_map = {
        "trades": "top_by_trades",
        "volume": "top_by_volume",
        "returns": "top_by_returns",
        "executive": "executive_branch",
    }

    key = category_map.get(category.lower(), "top_by_trades")
    records = data.get(key, [])

    # Normalize records for API response
    normalized = []
    for i, r in enumerate(records[:limit]):
        normalized.append({
            "rank": i + 1,
            "name": r.get("name") or r.get("official") or r.get("politician") or "Unknown",
            "party": r.get("party") or r.get("party_affiliation") or "",
            "chamber": r.get("chamber") or r.get("branch") or "",
            "state": r.get("state") or "",
            "trade_count": _safe_int(r.get("trades") or r.get("trade_count") or r.get("total_trades")),
            "volume_usd": _safe_float(r.get("volume") or r.get("total_volume") or r.get("volume_usd")),
            "return_pct": _safe_float(r.get("return") or r.get("roi") or r.get("return_pct") or r.get("return_%")),
            "vs_sp500": _safe_float(r.get("vs_sp500") or r.get("vs_s&p") or r.get("excess_return")),
            "late_filing_pct": _safe_float(r.get("late_filing") or r.get("late_%") or r.get("late_filing_pct")),
            "data_source": r.get("source") or "Capitol Trades / Kapitol.ai",
        })

    return normalized


def get_notable_cases(limit: int = 20) -> List[Dict]:
    """Get notable insider trading cases."""
    data = load_cached_data()
    if not data:
        data = parse_excel()
        if not data.get("error"):
            save_parsed_data(data)

    cases = data.get("notable_cases", [])
    normalized = []
    for c in cases[:limit]:
        normalized.append({
            "official": c.get("official") or c.get("name") or "",
            "party": c.get("party") or "",
            "incident": c.get("incident") or c.get("description") or c.get("case") or "",
            "date": c.get("date") or c.get("year") or "",
            "outcome": c.get("outcome") or c.get("resolution") or "",
            "profit_loss": c.get("profit") or c.get("gain") or c.get("amount") or "",
            "source": c.get("source") or "Public records",
        })
    return normalized


def get_lobbying_firms(limit: int = 50) -> List[Dict]:
    """Get top lobbying firms with revolving door data."""
    data = load_cached_data()
    if not data:
        data = parse_excel()
        if not data.get("error"):
            save_parsed_data(data)

    firms = data.get("lobbying_context", [])
    normalized = []
    for i, f in enumerate(firms[:limit]):
        normalized.append({
            "rank": i + 1,
            "firm": f.get("firm") or f.get("name") or f.get("lobbying_firm") or "",
            "revenue": _safe_float(f.get("revenue") or f.get("total_revenue")),
            "clients": _safe_int(f.get("clients") or f.get("client_count")),
            "former_officials": _safe_int(f.get("former_officials") or f.get("revolving_door")),
            "top_clients": f.get("top_clients") or "",
        })
    return normalized


def search_politician(name: str) -> Dict:
    """Search for a specific politician across all rankings."""
    data = load_cached_data()
    if not data:
        data = parse_excel()
        if not data.get("error"):
            save_parsed_data(data)

    name_lower = name.lower()
    results = {
        "name": name,
        "found_in": [],
        "rankings": {},
    }

    for category in ["top_by_trades", "top_by_volume", "top_by_returns", "executive_branch"]:
        records = data.get(category, [])
        for i, r in enumerate(records):
            record_name = (r.get("name") or r.get("official") or r.get("politician") or "").lower()
            if name_lower in record_name or record_name in name_lower:
                results["found_in"].append(category)
                results["rankings"][category] = {
                    "rank": i + 1,
                    "data": r,
                }
                break

    return results


def _safe_int(val) -> int:
    """Safely convert to int."""
    if val is None:
        return 0
    try:
        # Handle strings like "23,974" or "$618.9M"
        if isinstance(val, str):
            val = val.replace(",", "").replace("$", "").replace("M", "000000").replace("K", "000")
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _safe_float(val) -> float:
    """Safely convert to float."""
    if val is None:
        return 0.0
    try:
        if isinstance(val, str):
            val = val.replace(",", "").replace("$", "").replace("%", "")
            if "M" in val:
                val = val.replace("M", "")
                return float(val) * 1_000_000
            if "K" in val:
                val = val.replace("K", "")
                return float(val) * 1_000
        return float(val)
    except (ValueError, TypeError):
        return 0.0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Parsing Government Trading Excel...")
    data = parse_excel()
    if data.get("error"):
        print(f"Error: {data['error']}")
    else:
        path = save_parsed_data(data)
        print(f"Saved to: {path}")
        print(f"Top by Trades: {len(data.get('top_by_trades', []))} records")
        print(f"Top by Volume: {len(data.get('top_by_volume', []))} records")
        print(f"Top by Returns: {len(data.get('top_by_returns', []))} records")
        print(f"Executive Branch: {len(data.get('executive_branch', []))} records")
        print(f"Notable Cases: {len(data.get('notable_cases', []))} records")
        print(f"Lobbying Context: {len(data.get('lobbying_context', []))} records")
        print(f"Flat Combined: {len(data.get('flat_combined', []))} unique officials")
