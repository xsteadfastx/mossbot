# pylint: disable=redefined-builtin,missing-docstring,redefined-outer-name

from io import BytesIO

from unittest import mock

from PIL import Image

from matrix_client.room import Room

import mossbot

import pytest

from tinydb import TinyDB


@pytest.fixture
def config():
    return {
        'username': 'foo',
        'password': 'bar',
        'hostname': 'bar.tld',
        'uid': '@foo:bar.tld',
        'giphy_api_key': 'f00b4r',
    }


@pytest.fixture
def db(tmpdir):
    yield TinyDB(tmpdir.join('db.json').strpath)


@pytest.fixture
def matrix_handler(config, db):
    m = mossbot.MatrixHandler(config, db)
    m.client = mock.Mock()

    yield m


@pytest.fixture
def room():
    yield mock.Mock(spec=Room)


@pytest.fixture
def gif_image():
    gif_file = BytesIO()
    image = Image.new('RGBA', size=(50, 50), color=(155, 0, 0))
    image.save(gif_file, 'gif')
    gif_file.name = 'test.gif'
    gif_file.seek(0)

    yield gif_file
