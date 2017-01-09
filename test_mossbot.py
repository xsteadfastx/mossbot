import pytest

from unittest import mock

import mossbot


@pytest.mark.parametrize('input,expected', [
    ('hello umberto', 'hi umberto'),
    ('hello', 'hi Mr. NoName'),
    ('foo', None),
])
def test_serve(input, expected):

    moss = mossbot.MossBot()

    @moss.route(r'(?P<route>hello)\s?(?P<msg>.*)')
    def servetest(route=None, msg=None):
        if msg:
            name = msg
        else:
            name = 'Mr. NoName'

        return 'hi {}'.format(name)

    assert moss.serve(input) == expected


@pytest.mark.parametrize('input,expected', [
    ('ping foo bar', ('notice', 'Good morning, thats a nice TNETENNBA')),
    ('foo bar ping', None),
])
def test_ping(input, expected):
    assert mossbot.MOSS.serve(input) == expected


@pytest.mark.parametrize('route,html,expected', [
    (
        'http://foo.bar',
        '<title>foobar</title>',
        ('html', '<a href="http://foo.bar">foobar</a>')
    ),
])
@mock.patch('mossbot.requests.get')
def test_url(requests_mock, route, html, expected):
    requests_mock.return_value.text = html

    assert mossbot.MOSS.serve(route) == expected


@mock.patch('mossbot.requests.get')
def test_url_exception(requests_mock):
    requests_mock.return_value.text = 'foobar'

    with pytest.raises(Exception):
        assert mossbot.MOSS.serve('http://foo.bar') == ('skip', None)
