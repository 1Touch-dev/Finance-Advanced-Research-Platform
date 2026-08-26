import pytest
from us.ofac.ofac import OFACConnector


@pytest.mark.skip(reason="OFAC connector hits external API - run manually")
def test_ofac_sample_run():
    c = OFACConnector(creds={})
    m = c.run()
    assert m["seen"] >= 2
    assert m["errors"] == 0
