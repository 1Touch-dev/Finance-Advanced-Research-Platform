"""
BEA (Bureau of Economic Analysis) connector — connector #18.

Fetches U.S. GDP, regional income, and industry data from the BEA API.
Signup: https://apps.bea.gov/API/signup/
Env var: BEA_API_USER_ID (free 36-char UUID from BEA)
"""
import os
from typing import Any, Dict, Iterable, Tuple

from us._common.base_us import USBaseConnector
from us._common.http_helpers import http_get, is_test_env

BEA_BASE = "https://apps.bea.gov/api/data"
BEA_SEED_LIMIT = int(os.getenv("BEA_SEED_LIMIT", "100"))

# Datasets per BEA API user guide (Appendix B NIPA, Appendix N Regional)
BEA_DATASETS = [
    {
        "datasetname": "NIPA",
        "TableName": "T10101",
        "Frequency": "A",
        # NIPA does not accept LAST5; use explicit recent years
        "Year": "2020,2021,2022,2023,2024",
        "ResultFormat": "JSON",
        "description": "Percent change in real GDP (Annual)",
    },
    {
        "datasetname": "Regional",
        "TableName": "SAINC1",
        "LineCode": "1",
        "GeoFips": "STATE",
        "Year": "LAST5",
        "ResultFormat": "JSON",
        "description": "State personal income summary",
    },
    {
        "datasetname": "Regional",
        "TableName": "SAGDP9",
        "LineCode": "1",
        "GeoFips": "STATE",
        "Year": "LAST5",
        "ResultFormat": "JSON",
        "description": "State real GDP",
    },
]


def _bea_results(data: Dict[str, Any]) -> Dict[str, Any]:
    return data.get("BEAAPI", {}).get("Results", {}) or data.get("Results", {}) or {}


def _bea_api_error(data: Dict[str, Any]) -> str | None:
    err = _bea_results(data).get("Error")
    if not err:
        return None
    if isinstance(err, dict):
        return err.get("APIErrorDescription") or str(err)
    return str(err)


class BEAConnector(USBaseConnector):
    name = "bea"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            yield from _sample_records()
            return

        user_id = os.getenv("BEA_API_USER_ID", "")
        if not user_id:
            print("[bea] BEA_API_USER_ID not set — using sample data. Signup: https://apps.bea.gov/API/signup/")
            yield from _sample_records()
            return

        live_count = 0
        api_error: str | None = None

        for dataset in BEA_DATASETS:
            params = {"UserID": user_id, "method": "GetData", "ResultFormat": "JSON"}
            params.update({k: v for k, v in dataset.items() if k != "description"})

            try:
                resp = http_get(BEA_BASE, params=params, timeout=30)
                data = resp.json()
                err = _bea_api_error(data)
                if err:
                    api_error = err
                    print(f"[bea] API error for {dataset['datasetname']}: {err}")
                    continue

                result_data = _bea_results(data).get("Data") or []
                if not result_data:
                    print(f"[bea] No rows for dataset={dataset['datasetname']}")
                    continue

                statistic = _bea_results(data).get("Statistic", "")
                for i, row in enumerate(result_data[:BEA_SEED_LIMIT]):
                    geo = row.get("GeoName", "")
                    period = row.get("TimePeriod", "")
                    line = row.get("LineDescription") or statistic or dataset["description"]
                    eid = f"bea_{dataset['datasetname']}_{dataset.get('TableName', '')}_{geo}_{period}_{i}"
                    live_count += 1
                    yield eid, {
                        "dataset": dataset["datasetname"],
                        "table": dataset.get("TableName", ""),
                        "description": dataset["description"],
                        "geo_name": geo,
                        "line_description": line,
                        "time_period": period,
                        "data_value": row.get("DataValue", ""),
                        "cl_unit": row.get("CL_UNIT") or row.get("CL_Unit", ""),
                        "unit_mult": row.get("UNIT_MULT", ""),
                        "note": row.get("NoteRef", ""),
                        "source_tier": "live",
                    }
            except Exception as exc:
                api_error = str(exc)
                print(f"[bea] fetch error: {exc}")

        if live_count == 0:
            if api_error:
                print(f"[bea] Using sample data — {api_error}")
            else:
                print("[bea] Using sample data — no live rows returned")
            yield from _sample_records(api_error=api_error)

    def normalize(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "external_id": external_id,
            "jurisdiction": "US",
            "source": self.name,
            "dataset": payload.get("dataset"),
            "table": payload.get("table"),
            "description": payload.get("description"),
            "geo_name": payload.get("geo_name"),
            "line_description": payload.get("line_description"),
            "time_period": payload.get("time_period"),
            "data_value": payload.get("data_value"),
            "cl_unit": payload.get("cl_unit"),
            "source_tier": payload.get("source_tier", "live"),
            "note": payload.get("note"),
            "raw": payload,
        }

    def evidence_excerpt(self, payload: Dict[str, Any]) -> str:
        return f"BEA {payload.get('dataset','')}: {payload.get('description','')} | {payload.get('geo_name','')} {payload.get('time_period','')}"[:500]


def _sample_records(api_error: str | None = None):
    note = api_error or "BEA_API_USER_ID not configured"
    samples = [
        {
            "dataset": "NIPA", "table": "T10101", "description": "GDP and personal income (Annual)",
            "geo_name": "United States", "line_description": "Gross domestic product",
            "time_period": "2023", "data_value": "27360.0", "cl_unit": "Billions of dollars",
        },
        {
            "dataset": "Regional", "table": "SAINC1", "description": "State personal income summary",
            "geo_name": "California", "line_description": "Personal income",
            "time_period": "2022", "data_value": "3027.0", "cl_unit": "Millions of dollars",
        },
        {
            "dataset": "Regional", "table": "SAINC1", "description": "State personal income summary",
            "geo_name": "New York", "line_description": "Personal income",
            "time_period": "2022", "data_value": "1987.0", "cl_unit": "Millions of dollars",
        },
        {
            "dataset": "Regional", "table": "SAINC1", "description": "State personal income summary",
            "geo_name": "Texas", "line_description": "Personal income",
            "time_period": "2022", "data_value": "1823.0", "cl_unit": "Millions of dollars",
        },
    ]
    for i, s in enumerate(samples):
        row = {**s, "source_tier": "sample", "note": note}
        yield f"bea_sample_{i}", row
