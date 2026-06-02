from us.fara.fara import FARAConnector

def test_fara_sample_run():
    c = FARAConnector(creds={})
    m = c.run()
    assert m["seen"] >= 1
    assert m["errors"] == 0
