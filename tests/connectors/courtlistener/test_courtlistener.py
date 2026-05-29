from connectors.us.courtlistener.courtlistener import CourtListenerConnector

def test_courtlistener_sample_run():
    c = CourtListenerConnector(creds={})
    m = c.run()
    assert m["seen"] >= 1
    assert m["errors"] == 0
