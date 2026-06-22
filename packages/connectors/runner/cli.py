"""CLI entry point for connector runs: python -m runner.cli --connector sec_edgar --source-id 1 --run-id 1"""
import argparse
import importlib
import os
import sys

from runner.run_connector import run

CONNECTORS = {
    # Original 17 gov connectors
    "sec_edgar": ("us.sec.edgar", "SECEDGARConnector"),
    "fec": ("us.fec.fec", "FECConnector"),
    "congress_gov": ("us.congress.congress", "CongressGovConnector"),
    "sam_gov": ("us.sam.sam", "SAMGovConnector"),
    "courtlistener": ("us.courtlistener.courtlistener", "CourtListenerConnector"),
    "usaspending": ("us.usaspending.usaspending", "USASpendingConnector"),
    "ofac": ("us.ofac.ofac", "OFACConnector"),
    "gleif": ("us.gleif.gleif", "GLEIFConnector"),
    "lda_gov": ("us.lda.lda", "LDAConnector"),
    "fara": ("us.fara.fara", "FARAConnector"),
    "govinfo": ("us.govinfo.govinfo", "GovInfoConnector"),
    "federal_register": ("us.federal_register.federal_register", "FederalRegisterConnector"),
    "regulations_gov": ("us.regulations.regulations", "RegulationsGovConnector"),
    "ecfr": ("us.ecfr.ecfr", "ECFRConnector"),
    "reginfo_oira": ("us.reginfo_oira.reginfo_oira", "RegInfoOIRAConnector"),
    "irs_990": ("us.irs990.irs990", "IRS990Connector"),
    "opencorporates": ("us.opencorporates.opencorporates", "OpenCorporatesConnector"),
    # Phase 2 — BEA economic data (#18)
    "bea": ("us.bea.bea", "BEAConnector"),
    # Phase 2 — State registry Tier A bulk
    "state_us_ny": ("us.state_registry.bulk.ny", "NewYorkBulkConnector"),
    "state_us_co": ("us.state_registry.bulk.co", "ColoradoBulkConnector"),
    "state_us_fl": ("us.state_registry.bulk.fl", "FloridaBulkConnector"),
    "state_us_or": ("us.state_registry.bulk.or_", "OregonBulkConnector"),
    # Phase 2 — State registry Tier B API
    "state_us_wa": ("us.state_registry.api.wa", "WashingtonAPIConnector"),
    "state_us_tx": ("us.state_registry.api.tx", "TexasAPIConnector"),
    "state_us_ca": ("us.state_registry.api.ca", "CaliforniaSOSConnector"),
}


def _load_env() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    env_path = os.path.join(root, ".env")
    if os.path.isfile(env_path):
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path)
        except ImportError:
            pass


def main():
    _load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--connector", required=True)
    parser.add_argument("--source-id", type=int, required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--token", default=os.getenv("API_TOKEN"))
    args = parser.parse_args()

    if args.connector not in CONNECTORS:
        print(f"Unknown connector: {args.connector}", file=sys.stderr)
        sys.exit(1)

    mod_path, cls_name = CONNECTORS[args.connector]
    mod = importlib.import_module(mod_path)
    cls = getattr(mod, cls_name)
    connector = cls(creds={})
    metrics = run(connector, args.token, args.source_id, args.run_id)
    print(metrics)


if __name__ == "__main__":
    main()
