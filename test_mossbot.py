from unittest import mock

from matrix_client.room import Room

import mossbot

import pytest


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


@pytest.mark.parametrize('route,expected', [
    (
        'https://mediarg/thumb/d/d4/Pav_23.jpg/80ieu_Louvre_3.jpg',
        (
            'html',
            'https://mediarg/thumb/d/d4/Pav_23.jpg/80ieu_Louvre_3.jpg'
        )
    )
])
def test_image(route, expected):
    mossbot.MOSS.serve(route) == expected


@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_nothing(moss_mock, config):
    event = {
        'content': {},
        'sender': {},
    }

    room_mock = mock.Mock(spec=Room)

    mossbot.MatrixHandler(config).on_message(room_mock, event)

    room_mock.assert_not_called()


@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_text(moss_mock, config):
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

    moss_mock.serve.return_value = msg
    room_mock = mock.Mock(spec=Room)

    mossbot.MatrixHandler(config).on_message(room_mock, event)

    room_mock.send_text.assert_called_with('Foo Bar')


@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_notice(moss_mock, config):
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

    moss_mock.serve.return_value = msg
    room_mock = mock.Mock(spec=Room)

    mossbot.MatrixHandler(config).on_message(room_mock, event)

    room_mock.send_notice.assert_called_with('Foo Bar')


@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_html(moss_mock, config):
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

    moss_mock.serve.return_value = msg

    room_mock = mock.Mock()
    room_mock.room_id = '!foobar:foo.tld'
    room_mock.client.api.get_html_body.return_value = 'HTML'

    mossbot.MatrixHandler(config).on_message(room_mock, event)

    room_mock.client.api.send_message_event.assert_called_with(
        '!foobar:foo.tld',
        'm.room.message',
        'HTML'
    )


@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_skip(moss_mock, config):
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

    moss_mock.serve.return_value = msg
    room_mock = mock.Mock(spec=Room)

    mossbot.MatrixHandler(config).on_message(room_mock, event)

    room_mock.assert_not_called()


@mock.patch('mossbot.requests')
def test_write_image(requests_mock, config):
    room_mock = mock.Mock(spec=Room)

    matrix_handler = mossbot.MatrixHandler(config)
    matrix_handler.client = mock.Mock()

    matrix_handler.write_image(
        room_mock,
        'https://foo.tld/bar.png'
    )

    matrix_handler.client.upload.assert_called_with(
        requests_mock.get.return_value.raw,
        'image/png'
    )

    room_mock.send_image.assert_called_with(
        matrix_handler.client.upload(),
        'bar.png'
    )
