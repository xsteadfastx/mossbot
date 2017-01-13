import pytest


@pytest.fixture
def config():
    return {
        'username': 'foo',
        'password': 'bar',
        'hostname': 'bar.tld',
        'uid': '@foo:bar.tld',
        'giphy_api_key': 'f00b4r',
    }
