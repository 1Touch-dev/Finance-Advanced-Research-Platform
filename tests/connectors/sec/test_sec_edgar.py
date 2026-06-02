from us.sec.edgar import SECEDGARConnector

def test_sec_sample_run():
    c = SECEDGARConnector(creds={})
    m = c.run()
    assert m["seen"] >= 2
    assert m["errors"] == 0
