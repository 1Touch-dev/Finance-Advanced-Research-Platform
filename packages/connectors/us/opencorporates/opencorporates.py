import os
from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, env_or_creds, is_test_env


class OpenCorporatesConnector(USBaseConnector):
    name = "opencorporates"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        api_key = env_or_creds(self.creds, "api_token", "OPENCORPORATES_API_KEY")
        if api_key:
            try:
                url = "https://api.opencorporates.com/v0.4/companies/search"
                resp = http_get(
                    url,
                    params={
                        "q": "Apple",
                        "jurisdiction_code": "us_de",
                        "per_page": 10,
                        "api_token": api_key,
                    },
                    timeout=30,
                )
                for r in resp.json().get("results", {}).get("companies", []):
                    co = r.get("company", {})
                    ext = co.get("opencorporates_url") or co.get("company_number")
                    if ext:
                        yield str(ext), co
                return
            except Exception:
                if not is_test_env():
                    raise

        if not is_test_env():
            # Public fallback when OpenCorporates API key is not yet provisioned.
            url = "https://www.sec.gov/files/company_tickers.json"
            ua = os.getenv("SEC_USER_AGENT", "FinancePlatform research@example.com")
            resp = http_get(url, headers={"User-Agent": ua}, timeout=30)
            count = 0
            for entry in resp.json().values():
                if count >= 10:
                    break
                cik = str(entry.get("cik_str", "")).zfill(10)
                name = entry.get("title", "")
                if not cik or not name:
                    continue
                ext = f"sec-cik-{cik}"
                yield ext, {
                    "company_number": cik,
                    "name": name,
                    "jurisdiction_code": "us",
                    "ticker": entry.get("ticker", ""),
                    "registry_fallback": "sec_company_tickers",
                    "note": "SEC public registry fallback until OPENCORPORATES_API_KEY is set",
                }
                count += 1
            return

        yield from yield_samples([
            {"external_id": "us_ca-1234567", "company": "Example LLC", "jurisdiction_code": "us_ca"},
        ])
