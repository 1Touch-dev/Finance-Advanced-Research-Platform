from us.regulations.regulations import RegulationsGovConnector

def test_regulations_sample_run():
    c = RegulationsGovConnector(creds={})
    m = c.run()
    assert m["seen"] >= 1
    assert m["errors"] == 0
