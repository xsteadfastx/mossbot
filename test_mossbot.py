# pylint: disable=redefined-builtin,missing-docstring

from io import BytesIO
from unittest import mock

import pytest

import mossbot


@pytest.mark.parametrize('input,expected', [
    ('hello umberto', 'hi umberto'),
    ('hello', 'hi Mr. NoName'),
    ('foo', None),
])
def test_serve(input, expected):
    """test serve function"""

    moss = mossbot.MossBot()

    @moss.route(r'(?P<route>hello)\s?(?P<msg>.*)')
    # pylint: disable=unused-variable
    def servetest(route=None, msg=None, event=None):
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


@mock.patch('mossbot.MatrixHandler.store_msg')
@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_nothing(moss_mock, store_msg_mock, matrix_handler, room):
    event = {
        'content': {},
        'sender': {},
    }

    matrix_handler.on_message(room, event)

    room.assert_not_called()

    moss_mock.assert_not_called()

    store_msg_mock.assert_called_with(event)


@mock.patch('mossbot.logger')
@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_no_msg(moss_mock, logger_mock, matrix_handler, room):
    moss_mock.serve.return_value = None

    event = {
        'content': {
            'msgtype': 'm.text',
            'body': 'Foo Bar'
        },
        'sender': '@bar:foo.tld'
    }

    matrix_handler.on_message(room, event)

    logger_mock.debug.assert_called_with('no matching in event')


@mock.patch('mossbot.MatrixHandler.store_msg')
@mock.patch('mossbot.MatrixHandler.write_media')
@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_image(
        moss_mock,
        write_media_mock,
        store_msg_mock,
        matrix_handler,
        room
):
    event = {
        'content': {
            'msgtype': 'm.text',
            'body': 'Foo Bar'
        },
        'sender': '@bar:foo.tld'
    }

    msg = mossbot.MSG_RETURN('image', 'http://foo.tld/bar.png')

    moss_mock.serve.return_value = msg

    matrix_handler.on_message(room, event)

    write_media_mock.assert_called_with(
        'image',
        room,
        'http://foo.tld/bar.png'
    )

    store_msg_mock.assert_called_with(event)


@mock.patch('mossbot.MatrixHandler.store_msg')
@mock.patch('mossbot.MatrixHandler.write_media')
@mock.patch('mossbot.get_giphy_reaction_url')
@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_reaction(
        moss_mock,
        giphy_mock,
        write_media_mock,
        store_msg_mock,
        matrix_handler,
        room
):
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

    matrix_handler.on_message(room, event)

    write_media_mock.assert_called_with(
        'image',
        room,
        'https://foo.tld/bar.gif'
    )

    giphy_mock.assert_called_with(
        'f00b4r',
        'it crowd'
    )

    store_msg_mock.assert_called_with(event)


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
        (
            'http://api.giphy.com/v1/gifs/search'
            '?api_key=f00b4r&q=it+crowd&limit=20'
        )
    )


@mock.patch('mossbot.requests')
def test_get_giphy_reaction_url_exception(requests_mock):
    requests_mock.get.side_effect = Exception

    assert mossbot.get_giphy_reaction_url('f00b4r', 'it crowd') is None


@mock.patch('mossbot.MatrixHandler.store_msg')
@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_text(moss_mock, store_msg_mock, matrix_handler, room):
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

    matrix_handler.on_message(room, event)

    room.send_text.assert_called_with('Foo Bar')

    store_msg_mock.assert_called_with(event)


@mock.patch('mossbot.MatrixHandler.store_msg')
@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_notice(moss_mock, store_msg_mock, matrix_handler, room):
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

    matrix_handler.on_message(room, event)

    room.send_notice.assert_called_with('Foo Bar')

    store_msg_mock.assert_called_with(event)


@mock.patch('mossbot.MatrixHandler.store_msg')
@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_html(moss_mock, store_msg_mock, matrix_handler):
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

    matrix_handler.on_message(room_mock, event)

    room_mock.send_html.assert_called_with('Foo Bar')

    store_msg_mock.assert_called_with(event)


@mock.patch('mossbot.MatrixHandler.store_msg')
@mock.patch('mossbot.MOSS', autospec=True)
def test_on_message_skip(moss_mock, store_msg_mock, matrix_handler, room):
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

    matrix_handler.on_message(room, event)

    room.assert_not_called()

    store_msg_mock.assert_called_with(event)


@pytest.mark.parametrize('image_data', [
    (
        {
            'content-type': 'image/gif',
            'height': 100,
            'width': 200,
            'image': 'gif_image'
        }
    ),
    (
        {
            'height': 100,
            'width': 200,
            'image': 'gif_image'
        }
    ),
])
@mock.patch('mossbot.get_image')
def test_write_media(
        get_image_mock,
        image_data,
        config,
        matrix_handler,
        room,
):
    get_image_mock.return_value = image_data

    matrix_handler.client.upload.return_value = 'succ_uploaded'

    assert matrix_handler.write_media(
        'image',
        room,
        'http://foo.bar/image.gif'
    ) is None

    matrix_handler.client.upload.assert_called_with(
        'gif_image',
        'image/gif'
    )

    room.send_image.assert_called_with(
        'succ_uploaded',
        'image.gif',
        h=100,
        mimetype='image/gif',
        w=200
    )


@mock.patch('mossbot.logger')
@mock.patch('mossbot.get_image')
def test_write_media_no_image_data(
        get_image_mock,
        logger_mock,
        config,
        matrix_handler,
        room
):
    get_image_mock.return_value = None

    assert matrix_handler.write_media(
        'image',
        room,
        'http://foo.bar/image.gif'
    ) is None

    logger_mock.error.assert_called_with('got no image_data')


@mock.patch('mossbot.logger')
def test_write_media_not_image(logger_mock, config, matrix_handler, room):
    assert matrix_handler.write_media(
        'video',
        room,
        'https://foo.tld/bar.png'
    ) is None

    logger_mock.error.assert_called_with(
        '%s as media type is not supported',
        'video'
    )


@mock.patch('mossbot.BytesIO')
@mock.patch('mossbot.logger')
@mock.patch('mossbot.Image')
@mock.patch('mossbot.requests')
def test_get_image_200(
        requests_mock,
        image_mock,
        logger_mock,
        bytesio_mock,
):
    requests_mock.get.return_value.status_code = 200
    requests_mock.get.return_value.content = 'foo'
    requests_mock.get.return_value.headers = {'Content-Type': 'image/gif'}

    gif = BytesIO()
    bytesio_mock.return_value = gif

    image_mock.open.return_value.width = 200
    image_mock.open.return_value.height = 100

    assert mossbot.get_image('http://foo.bar/test.gif') == {
        'content-type': 'image/gif',
        'image': gif,
        'width': 200,
        'height': 100,
    }

    logger_mock.info.assert_called_with(
        'downloading image: %s',
        'http://foo.bar/test.gif'
    )

    requests_mock.get.assert_called_with('http://foo.bar/test.gif')

    bytesio_mock.assert_called_with('foo')


@mock.patch('mossbot.logger')
@mock.patch('mossbot.Image')
@mock.patch('mossbot.requests')
def test_get_image_wrong_status_code(requests_mock, image_mock, logger_mock):
    requests_mock.get.return_value.status_code = 404

    assert mossbot.get_image('http://foo.bar/test.gif') is None

    logger_mock.error.assert_called_with(
        'could not download and analyze img: %s',
        "('wrong status code %s', 404)"
    )


@mock.patch('mossbot.logger')
@mock.patch('mossbot.requests')
def test_get_image_exception(requests_mock, logger_mock):
    requests_mock.get.side_effect = KeyError('problem')

    assert mossbot.get_image('http://foo.bar/test.gif') is None

    logger_mock.error.assert_called_with(
        'could not download and analyze img: %s', "'problem'"
    )


@pytest.mark.parametrize('event,db_prefill,db_all', [
    (
        {
            'content': {
                'msgtype': 'm.text',
                'body': 'Foo Bar'
            },
            'sender': '@bar:foo.tld'
        },
        [],
        [
            {
                'sender': '@bar:foo.tld',
                'body': 'Foo Bar',
            }
        ]
    ),
    (
        {
            'content': {
                'msgtype': 'm.text',
                'body': 'Message 12'
            },
            'sender': '@bar:foo.tld'
        },
        [
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 1',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 2',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 3',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 4',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 5',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 6',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 7',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 8',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 9',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 10',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 11',
            },
        ],
        [
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 3',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 4',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 5',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 6',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 7',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 8',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 9',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 10',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 11',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 12',
            },
        ]

    )
])
def test_store_msg(event, db_prefill, db_all, matrix_handler):
    # prepare db
    for prefill in db_prefill:
        matrix_handler.db.table('msgs').insert(prefill)

    # try to store event
    matrix_handler.store_msg(event)

    assert matrix_handler.db.table('msgs').all() == db_all

    assert len(matrix_handler.db.table('msgs').all()) <= 10


@mock.patch('mossbot.logger')
@mock.patch('mossbot.MatrixHandler.db')
def test_store_msg_exception(db_mock, logger_mock, matrix_handler):
    db_mock.table.side_effect = KeyError('problem')

    event = {
        'content': {
            'msgtype': 'm.text',
            'body': 'Foo Bar'
        },
        'sender': '@bar:foo.tld'
    }

    assert matrix_handler.store_msg(event) is None

    logger_mock.debug.assert_called_with(
        'got event to store: %s',
        str(event)
    )

    logger_mock.exception.assert_called_with('could not store msg')


@pytest.mark.parametrize('event,db_prefill,expected', [
    (
        {
            'content': {
                'msgtype': 'm.text',
                'body': 's/Foo Bar/Zick Zack'
            },
            'sender': '@bar:foo.tld'
        },
        [
            {
                'sender': '@bar:foo.tld',
                'body': 'Message 1',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 'Dies ist ein Foo Bar',
            },
            {
                'sender': '@bar:foo.tld',
                'body': 's/Foo Bar/Zick Zack',
            },
        ],
        mossbot.MSG_RETURN(
            'html',
            '<i><b>@bar:foo.tld</b>: Dies ist ein Zick Zack</i>'
        )
    ),
    (
        {
            'content': {
                'msgtype': 'm.text',
                'body': 's/Foo Bar/Zick Zack'
            },
            'sender': '@bar:foo.tld'
        },
        [
            {
                'sender': '@bar:foo.tld',
                'body': 's/Foo Bar/Zick Zack'
            }
        ],
        mossbot.MSG_RETURN(
            'skip',
            None
        )
    ),
])
@mock.patch('mossbot.get_db')
def test_replace(get_db_mock, db, event, db_prefill, expected):
    # prepare database
    for prefill in db_prefill:
        db.table('msgs').insert(prefill)

    get_db_mock.return_value = db

    assert mossbot.MOSS.serve(event) == expected


@mock.patch('mossbot.logger')
@mock.patch('mossbot.get_db')
def test_replace_exception(get_db_mock, logger_mock):
    get_db_mock.side_effect = KeyError('problem')

    assert mossbot.MOSS.serve(
        {
            'content': {
                'msgtype': 'm.text',
                'body': 's/Foo Bar/Zick Zack'
            },
            'sender': '@bar:foo.tld'
        }
    ) == mossbot.MSG_RETURN('skip', None)

    assert logger_mock.exception.called is True
