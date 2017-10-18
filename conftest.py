# pylint: disable=redefined-builtin,missing-docstring,redefined-outer-name

from io import BytesIO
from unittest import mock

import pytest
from matrix_client.room import Room
from PIL import Image
from tinydb import TinyDB

import mossbot


@pytest.fixture
def config():
    return {
        'username': 'foo',
        'password': 'bar',
        'hostname': 'bar.tld',
        'uid': '@foo:bar.tld',
        'giphy_api_key': 'f00b4r',
        'openweathermap_api_key': 'b4rf00',
    }


@pytest.fixture
def db(tmpdir):
    yield TinyDB(tmpdir.join('db.json').strpath)


@pytest.fixture
def matrix_handler(config, monkeypatch, tmpdir):

    monkeypatch.setattr(
        'mossbot.get_db',
        lambda: TinyDB(tmpdir.join('db.json').strpath)
    )

    m = mossbot.MatrixHandler(config)
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
