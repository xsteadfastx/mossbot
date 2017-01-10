import pytest

from unittest import mock

from matrix_client.room import Room

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


@mock.patch('mossbot.MOSS', autospec=True)
@mock.patch('mossbot.config')
def test_on_message_nothing(config_mock, moss_mock):
    event = {
        'content': {},
        'sender': {},
    }

    room_mock = mock.Mock(spec=Room)

    mossbot.on_message(room_mock, event)

    room_mock.assert_not_called()


@mock.patch('mossbot.MOSS', autospec=True)
@mock.patch('mossbot.config')
def test_on_message_text(config_mock, moss_mock):
    event = {
        'content': {
            'msgtype': 'm.text',
            'body': 'Foo Bar'
        },
        'sender': {'@bar:foo.tld'},
    }

    msg = (
        'text',
        'Foo Bar'
    )

    config_mock.UID = '@foo:bar.tld'
    moss_mock.serve.return_value = msg
    room_mock = mock.Mock(spec=Room)

    mossbot.on_message(room_mock, event)

    room_mock.send_text.assert_called_with('Foo Bar')


@mock.patch('mossbot.MOSS', autospec=True)
@mock.patch('mossbot.config')
def test_on_message_notice(config_mock, moss_mock):
    event = {
        'content': {
            'msgtype': 'm.text',
            'body': 'Foo Bar'
        },
        'sender': {'@bar:foo.tld'},
    }

    msg = (
        'notice',
        'Foo Bar'
    )

    config_mock.UID = '@foo:bar.tld'
    moss_mock.serve.return_value = msg
    room_mock = mock.Mock(spec=Room)

    mossbot.on_message(room_mock, event)

    room_mock.send_notice.assert_called_with('Foo Bar')


@mock.patch('mossbot.MOSS', autospec=True)
@mock.patch('mossbot.config')
def test_on_message_html(config_mock, moss_mock):
    event = {
        'content': {
            'msgtype': 'm.text',
            'body': 'Foo Bar'
        },
        'sender': {'@bar:foo.tld'},
    }

    msg = (
        'html',
        'Foo Bar'
    )

    config_mock.UID = '@foo:bar.tld'
    moss_mock.serve.return_value = msg

    room_mock = mock.Mock()
    room_mock.room_id = '!foobar:foo.tld'
    room_mock.client.api.get_html_body.return_value = 'HTML'

    mossbot.on_message(room_mock, event)

    room_mock.client.api.send_message_event.assert_called_with(
        '!foobar:foo.tld',
        'm.room.message',
        'HTML'
    )


@mock.patch('mossbot.MOSS', autospec=True)
@mock.patch('mossbot.config')
def test_on_message_skip(config_mock, moss_mock):
    event = {
        'content': {
            'msgtype': 'm.text',
            'body': 'Foo Bar'
        },
        'sender': {'@bar:foo.tld'},
    }

    msg = (
        'skip',
        None
    )

    config_mock.UID = '@foo:bar.tld'
    moss_mock.serve.return_value = msg
    room_mock = mock.Mock(spec=Room)

    mossbot.on_message(room_mock, event)

    room_mock.assert_not_called()
