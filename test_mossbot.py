import pytest

import mossbot


@pytest.mark.parametrize('input,expected', [
    ('hello umberto', 'hi umberto'),
    ('hello', 'hi Mr. NoName'),
    ('foo', None),
])
def test_serve(input, expected):

    moss = mossbot.MossBot()

    @moss.route(r'(?P<route>hello)\s?(?P<msg>.*)')
    def servetest(msg=None):
        if msg:
            name = msg
        else:
            name = 'Mr. NoName'

        return 'hi {}'.format(name)

    assert moss.serve(input) == expected


@pytest.mark.parametrize('input,expected', [
    ('ping foo bar', ('text', 'Good morning, thats a nice TNETENNBA')),
    ('foo bar ping', None),
])
def test_ping(input, expected):
    assert mossbot.moss.serve(input) == expected
