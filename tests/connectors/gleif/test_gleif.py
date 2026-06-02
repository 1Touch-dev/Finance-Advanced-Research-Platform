from us.gleif.gleif import GLEIFConnector

def test_gleif_sample_run():
    c = GLEIFConnector(creds={})
    m = c.run()
    assert m["seen"] >= 1
    assert m["errors"] == 0
