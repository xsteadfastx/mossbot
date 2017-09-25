# pylint: disable=redefined-builtin,missing-docstring

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
    """test serve function"""

    moss = mossbot.MossBot()

    @moss.route(r'(?P<route>hello)\s?(?P<msg>.*)')
    def servetest(route=None, msg=None):  # pylint: disable=unused-variable
        """servetest function"""
        if msg:
            name = msg
        else:
            name = 'Mr. NoName'

        return 'hi {}'.format(name)

    assert moss.serve({'content': {'body': input}}) == expected


@pytest.mark.parametrize('input,expected', [
    (
        '!ping',
        (
            'notice',
            (
                'Good morning, thats a nice TNETENNBA',
                'Ow. Four! I mean, five! I mean, fire!',
                'Did you see that ludicrous display last night?',
            )
        ),
    )
])
def test_ping(input, expected):
    for _ in range(10):
        response = mossbot.MOSS.serve({'content': {'body': input}})

        assert response[0] == expected[0]
        assert response[1] in expected[1]


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

    assert mossbot.MOSS.serve({'content': {'body': route}}) == expected


@mock.patch('mossbot.requests.get')
def test_url_exception(requests_mock):
    requests_mock.return_value.text = 'foobar'

    with pytest.raises(Exception):
        assert mossbot.MOSS.serve('http://foo.bar') == ('skip', None)


@pytest.mark.parametrize('route,expected', [
    (
        'https://mediarg/thumb/d/d4/Pav_23.jpg/80ieu_Louvre_3.jpg',
        (
            'image',
            'https://mediarg/thumb/d/d4/Pav_23.jpg/80ieu_Louvre_3.jpg'
        )
    )
])
def test_image(route, expected):
    assert mossbot.MOSS.serve({'content': {'body': route}}) == expected


@pytest.mark.parametrize('route,expected', [
    ('!reaction foo bar', ('reaction', 'foo bar'))
])
def test_reaction(route, expected):
    assert mossbot.MOSS.serve({'content': {'body': route}}) == expected


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
def test_on_message_image(moss_mock, config):
    event = {
        'content': {
            'msgtype': 'm.text',
            'body': 'Foo Bar'
        },
        'sender': '@bar:foo.tld'
    }

    msg = mossbot.MSG_RETURN('image', 'http://foo.tld/bar.png')

    moss_mock.serve.return_value = msg
    room_mock = mock.Mock(spec=Room)

    with mock.patch.object(
        mossbot.MatrixHandler,
        'write_media'
    ) as write_media_mock:

        mossbot.MatrixHandler(config).on_message(room_mock, event)

        write_media_mock.assert_called_with(
            'image',
            room_mock,
            'http://foo.tld/bar.png'
        )


@mock.patch('mossbot.get_giphy_reaction_url')
@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_reaction(moss_mock, giphy_mock, config):
    event = {
        'content': {
            'msgtype': 'm.text',
            'body': 'Foo Bar'
        },
        'sender': '@bar:foo.tld'
    }

    msg = mossbot.MSG_RETURN('reaction', 'it crowd')

    moss_mock.serve.return_value = msg
    giphy_mock.return_value = 'https://foo.tld/bar.mp4'
    room_mock = mock.Mock(spec=Room)

    with mock.patch.object(
        mossbot.MatrixHandler,
        'write_media'
    ) as write_media_mock:

        mossbot.MatrixHandler(config).on_message(room_mock, event)

        write_media_mock.assert_called_with(
            'video',
            room_mock,
            'https://foo.tld/bar.mp4'
        )

        giphy_mock.assert_called_with(
            'f00b4r',
            'it crowd'
        )


@pytest.mark.parametrize('response,expected', [
    (
        {
            'data': {
                'image_mp4_url': 'https://foo.tld/bar.mp4'
            }
        },
        'https://foo.tld/bar.mp4'
    ),
    (
        {},
        None
    )
])
@mock.patch('mossbot.requests')
def test_get_giphy_reaction_url(requests_mock, response, expected):
    requests_mock.get.return_value.json.return_value = response

    assert mossbot.get_giphy_reaction_url(
        'f00b4r',
        'it crowd'
    ) == expected

    requests_mock.get.assert_called_with(
        'http://api.giphy.com/v1/gifs/random?api_key=f00b4r&tag=it+crowd'
    )


@mock.patch('mossbot.requests')
def test_get_giphy_reaction_url_exception(requests_mock):
    requests_mock.get.side_effect = Exception

    assert mossbot.get_giphy_reaction_url('f00b4r', 'it crowd') is None


@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_text(moss_mock, config):
    event = {
        'content': {
            'msgtype': 'm.text',
            'body': 'Foo Bar'
        },
        'sender': {'@bar:foo.tld'},
    }

    msg = mossbot.MSG_RETURN(
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

    msg = mossbot.MSG_RETURN(
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

    msg = mossbot.MSG_RETURN(
        'html',
        'Foo Bar'
    )

    moss_mock.serve.return_value = msg

    room_mock = mock.Mock()
    room_mock.room_id = '!foobar:foo.tld'
    room_mock.client.api.get_html_content.return_value = 'HTML'

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

    msg = mossbot.MSG_RETURN(
        'skip',
        None
    )

    moss_mock.serve.return_value = msg
    room_mock = mock.Mock(spec=Room)

    mossbot.MatrixHandler(config).on_message(room_mock, event)

    room_mock.assert_not_called()


@pytest.mark.parametrize('media_type,url,mime,filename', [
    (
        'image',
        'https://foo.tld/bar.png',
        'image/png',
        'bar.png'

    ),
    (
        'video',
        'https://foo.tld/bar.mp4',
        'video/mp4',
        'bar.mp4'
    )
])
@mock.patch('mossbot.requests')
def test_write_media(requests_mock, media_type, url, mime, filename, config):
    room_mock = mock.Mock(spec=Room)

    matrix_handler = mossbot.MatrixHandler(config)
    matrix_handler.client = mock.Mock()

    matrix_handler.write_media(
        media_type,
        room_mock,
        url
    )

    matrix_handler.client.upload.assert_called_with(
        requests_mock.get.return_value.raw,
        mime
    )

    if media_type == 'image':

        room_mock.send_image.assert_called_with(
            matrix_handler.client.upload(),
            filename
        )

    elif media_type == 'video':

        room_mock.send_video.assert_called_with(
            matrix_handler.client.upload(),
            filename
        )

    else:
        assert False
