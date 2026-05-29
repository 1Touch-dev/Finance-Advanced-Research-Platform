from connectors.us.ofac.ofac import OFACConnector

def test_ofac_sample_run():
    c = OFACConnector(creds={})
    m = c.run()
    assert m["seen"] >= 2
    assert m["errors"] == 0
