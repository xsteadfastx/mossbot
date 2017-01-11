import pytest


@pytest.fixture
def config():
    return {
        'username': 'foo',
        'password': 'bar',
        'hostname': 'bar.tld',
        'uid': '@foo:bar.tld'
    }
