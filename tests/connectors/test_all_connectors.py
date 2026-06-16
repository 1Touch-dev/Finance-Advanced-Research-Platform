import importlib
import os

import pytest

os.environ["ENV"] = "test"

CONNECTORS = [
    ("us.sec.edgar", "SECEDGARConnector"),
    ("us.fec.fec", "FECConnector"),
    ("us.congress.congress", "CongressGovConnector"),
    ("us.sam.sam", "SAMGovConnector"),
    ("us.courtlistener.courtlistener", "CourtListenerConnector"),
    ("us.usaspending.usaspending", "USASpendingConnector"),
    ("us.ofac.ofac", "OFACConnector"),
    ("us.gleif.gleif", "GLEIFConnector"),
    ("us.lda.lda", "LDAConnector"),
    ("us.fara.fara", "FARAConnector"),
    ("us.govinfo.govinfo", "GovInfoConnector"),
    ("us.federal_register.federal_register", "FederalRegisterConnector"),
    ("us.regulations.regulations", "RegulationsGovConnector"),
    ("us.ecfr.ecfr", "ECFRConnector"),
    ("us.reginfo_oira.reginfo_oira", "RegInfoOIRAConnector"),
    ("us.irs990.irs990", "IRS990Connector"),
    ("us.opencorporates.opencorporates", "OpenCorporatesConnector"),
]


@pytest.mark.parametrize("mod_path,cls_name", CONNECTORS)
def test_connector_contract_run(mod_path, cls_name):
    mod = importlib.import_module(mod_path)
    cls = getattr(mod, cls_name)
    c = cls(creds={})
    m = c.run()
    assert m["seen"] >= 1
    assert m["errors"] == 0
    assert "checkpoint" in m
