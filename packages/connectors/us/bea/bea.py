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

# Sample datasets to seed
BEA_DATASETS = [
    {
        "datasetname": "NIPA",
        "TableName": "T10101",
        "Frequency": "A",
        "Year": "2023",
        "ResultFormat": "JSON",
        "description": "GDP and personal income (Annual)",
    },
    {
        "datasetname": "Regional",
        "TableName": "CAINC1",
        "LineCode": "1",
        "GeoFIPS": "STATE",
        "Year": "2022",
        "ResultFormat": "JSON",
        "description": "State personal income (2022)",
    },
]


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

        for dataset in BEA_DATASETS:
            params = {"UserID": user_id, "method": "GetData", "ResultFormat": "JSON"}
            params.update({k: v for k, v in dataset.items() if k != "description"})

            try:
                resp = http_get(BEA_BASE, params=params, timeout=30)
                data = resp.json()
                result_data = (
                    data.get("BEAAPI", {}).get("Results", {}).get("Data", [])
                    or data.get("Results", {}).get("Data", [])
                )
                if result_data:
                    for i, row in enumerate(result_data[:20]):
                        eid = f"bea_{dataset['datasetname']}_{dataset.get('TableName', '')}_{i}"
                        yield eid, {
                            "dataset": dataset["datasetname"],
                            "table": dataset.get("TableName", ""),
                            "description": dataset["description"],
                            "geo_name": row.get("GeoName", ""),
                            "line_description": row.get("LineDescription", ""),
                            "time_period": row.get("TimePeriod", ""),
                            "data_value": row.get("DataValue", ""),
                            "cl_unit": row.get("CL_Unit", ""),
                            "note": row.get("NoteRef", ""),
                        }
                else:
                    print(f"[bea] No data for dataset={dataset['datasetname']}")
                    yield from _sample_records()
            except Exception as exc:
                print(f"[bea] fetch error: {exc}")
                yield from _sample_records()

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
            "raw": payload,
        }

    def evidence_excerpt(self, payload: Dict[str, Any]) -> str:
        return f"BEA {payload.get('dataset','')}: {payload.get('description','')} | {payload.get('geo_name','')} {payload.get('time_period','')}"[:500]


def _sample_records():
    samples = [
        {
            "dataset": "NIPA", "table": "T10101", "description": "GDP and personal income (Annual)",
            "geo_name": "United States", "line_description": "Gross domestic product",
            "time_period": "2023", "data_value": "27360.0", "cl_unit": "Billions of dollars",
        },
        {
            "dataset": "Regional", "table": "CAINC1", "description": "State personal income (2022)",
            "geo_name": "California", "line_description": "Personal income",
            "time_period": "2022", "data_value": "3027.0", "cl_unit": "Millions of dollars",
        },
        {
            "dataset": "Regional", "table": "CAINC1", "description": "State personal income (2022)",
            "geo_name": "New York", "line_description": "Personal income",
            "time_period": "2022", "data_value": "1987.0", "cl_unit": "Millions of dollars",
        },
        {
            "dataset": "Regional", "table": "CAINC1", "description": "State personal income (2022)",
            "geo_name": "Texas", "line_description": "Personal income",
            "time_period": "2022", "data_value": "1823.0", "cl_unit": "Millions of dollars",
        },
    ]
    for i, s in enumerate(samples):
        yield f"bea_sample_{i}", s
