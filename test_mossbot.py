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
    giphy_mock.return_value = 'https://foo.tld/bar.gif'
    room_mock = mock.Mock(spec=Room)

    with mock.patch.object(
        mossbot.MatrixHandler,
        'write_media'
    ) as write_media_mock:

        mossbot.MatrixHandler(config).on_message(room_mock, event)

        write_media_mock.assert_called_with(
            'image',
            room_mock,
            'https://foo.tld/bar.gif'
        )

        giphy_mock.assert_called_with(
            'f00b4r',
            'it crowd'
        )


@pytest.mark.parametrize('response,expected', [
    (
        {
            'data': [
                {
                    'images': {
                        'downsized': {
                            'url': 'https://foo.tld/bar.gif?fingerprint=abc'
                        }
                    }
                }
            ]
        },
        'https://foo.tld/bar.gif'
    ),
    (
        {
            'data': [
                {
                    'images': {
                        'downsized': {
                            'url': 'https://foo.tld/bar.gif'
                        }
                    }
                }
            ]
        },
        'https://foo.tld/bar.gif'
    ),
    (
        {},
        None
    ),
    (
        {
            'data': []
        },
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
        'http://api.giphy.com/v1/gifs/search?api_key=f00b4r&q=it+crowd&limit=5'
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

    room_mock.send_html.assert_called_with('Foo Bar')


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


@pytest.mark.parametrize(
    'media_type,url,mime,filename,size_return,media_info',
    [
        (
            'image',
            'https://foo.tld/bar.png',
            'image/png',
            'bar.png',
            {
                'w': 200,
                'h': 100
            },
            {
                'w': 200,
                'h': 100,
                'mimetype': 'image/png'
            },
        ),
        (
            'image',
            'https://foo.tld/bar.png',
            'image/png',
            'bar.png',
            None,
            {
                'mimetype': 'image/png'
            },
        ),
    ]
)
@mock.patch('mossbot.get_image_size')
@mock.patch('mossbot.requests')
def test_write_media(
        requests_mock,
        get_image_size_mock,
        media_type,
        url,
        mime,
        filename,
        size_return,
        media_info,
        config
):
    get_image_size_mock.return_value = size_return

    room_mock = mock.Mock(spec=Room)

    matrix_handler = mossbot.MatrixHandler(config)
    matrix_handler.client = mock.Mock()

    matrix_handler.write_media(
        media_type,
        room_mock,
        url
    )

    get_image_size_mock.assert_called_with(requests_mock.get.return_value.raw)

    matrix_handler.client.upload.assert_called_with(
        requests_mock.get.return_value.raw,
        mime
    )

    room_mock.send_image.assert_called_with(
        matrix_handler.client.upload(),
        filename,
        media_info
    )


@mock.patch('mossbot.logger')
def test_write_media_not_image(logger_mock, config):
    room_mock = mock.Mock(spec=Room)

    matrix_handler = mossbot.MatrixHandler(config)
    matrix_handler.client = mock.Mock()

    assert matrix_handler.write_media(
        'video',
        room_mock,
        'https://foo.tld/bar.png'
    ) is None

    logger_mock.error.assert_called_with(
        '%s as media type is not supported',
        'video'
    )


@mock.patch('mossbot.HTTPResponse')
@mock.patch('mossbot.Image')
def test_get_image_size(image_mock, httpresponse_mock):
    image_mock.open.return_value.size = (200, 100)

    assert mossbot.get_image_size(httpresponse_mock) == {
        'h': 100,
        'w': 200
    }


@mock.patch('mossbot.HTTPResponse')
@mock.patch('mossbot.Image')
@mock.patch('mossbot.logger')
def test_get_image_size_exception(logger_mock, image_mock, httpresponse_mock):
    image_mock.open.side_effect = KeyError('problem')

    assert mossbot.get_image_size(httpresponse_mock) is None

    logger_mock.error.assert_called_with(
        'could not get sizes: %s', "'problem'"
    )
