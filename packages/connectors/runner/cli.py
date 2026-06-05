"""CLI entry point for connector runs: python -m runner.cli --connector sec_edgar --source-id 1 --run-id 1"""
import argparse
import importlib
import os
import sys

from runner.run_connector import run

CONNECTORS = {
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
}


def main():
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
