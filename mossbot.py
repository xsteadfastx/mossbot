"""mossbot"""

import logging

import mimetypes

import random

import re

import sys

import time

from collections import OrderedDict

from multiprocessing import Process

from typing import Callable, Dict, NamedTuple, Union

from urllib.parse import quote_plus, urlsplit

from bs4 import BeautifulSoup

import click

import logzero
from logzero import logger

from matrix_client.client import MatrixClient
from matrix_client.room import Room

import pendulum

import requests

import yaml


# tuple to store route return data
MSG_RETURN = NamedTuple(
    'MSG_RETURN',
    [
        ('type', str),
        ('data', Union[str, None]),
    ]
)

# type for route functions
ROUTE_TYPE = Callable[[Union[str, None], Union[str, None]], MSG_RETURN]

# dict to store routes and its functions
ROUTES_TYPE = Dict[str, ROUTE_TYPE]


class MossBot(object):
    """Bot routing logic."""

    def __init__(self) -> None:
        # stores all routes and its functions
        self.routes = OrderedDict()  # type: ROUTES_TYPE

    def route(self, route: str) -> Callable:
        """Decorator to save routes to a dictionary."""

        def decorator(f: Callable) -> Callable:
            """Decorates the function."""
            self.routes[route] = f

            return f

        return decorator

    def serve(self, event: Dict) -> Union[MSG_RETURN, None]:
        """Returns the right function for matching route.

        :param event: Event json object
        :returns: Matched function from route
        """
        raw_msg = event['content']['body']
        for k in self.routes.keys():
            m = re.search(k, raw_msg, re.IGNORECASE)

            if m:
                matches = m.groupdict()
                route = matches.get('route')
                msg = matches.get('msg')

                func = self.routes.get(k)

                if func:

                    logger.info(
                        (
                            'matched route %s '
                            'with msg %s '
                            'from %s '
                            'and triggered "%s"'
                        ),
                        route, msg, raw_msg, func.__name__
                    )

                    return func(route, msg)

                logger.error('%s not in routes', k)

                return None

        return None


MOSS = MossBot()


@MOSS.route(r'^(?P<route>!ping)$')
def ping(route: str, msg: str) -> MSG_RETURN:
    """Pongs back in a Moss way."""
    oneliners = (
        'Good morning, thats a nice TNETENNBA',
        'Ow. Four! I mean, five! I mean, fire!',
        'Did you see that ludicrous display last night?',
    )

    return MSG_RETURN('notice', random.choice(oneliners))


@MOSS.route(r'(?P<route>^http[s]?://.*(?:jpg|jpeg|png|gif)$)')
def image(route: str, msg: str) -> MSG_RETURN:
    """Posts image."""
    return MSG_RETURN('image', route)


@MOSS.route(
    (
        r'(?i)(?P<route>\b((?:https?://|www\d{0,3}[.]'
        r'|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|'
        r'\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+'
        r'(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)'
        r'|[^\s`!()\[\]{};:\'\".,<>?'
        r'\xab\xbb\u201c\u201d\u2018\u2019])))'
        r'\s?(?P<msg>.*)?'
    )
)
def url_title(route: str, msg: str) -> MSG_RETURN:
    """Takes postet urls and parses the title."""
    try:

        logger.debug('get "%s"', route)
        r = requests.get(route)
        logger.debug('parse for title')
        soup = BeautifulSoup(r.text, 'html.parser')

    except BaseException as e:
        logger.warning('url_title could not get html title: %s', e)

        return MSG_RETURN('skip', None)

    title = soup.title.string
    logger.info('url title: %s', title)

    return MSG_RETURN(
        'html',
        f'<a href="{route}">{title}</a>'
    )


@MOSS.route(r'^(?P<route>!reaction)\s+(?P<msg>.+)')
def reaction(route: str, msg: str) -> MSG_RETURN:
    """Posts reaction gif."""
    return MSG_RETURN('reaction', msg)


def get_giphy_reaction_url(api_key: str, term: str) -> Union[str, None]:
    """Gets a random giphy gif and returns url."""
    term = quote_plus(term)

    url = (
        f'http://api.giphy.com/v1/gifs/search'
        f'?api_key={api_key}'
        f'&q={term}'
        f'&limit=5'
    )

    try:
        r = requests.get(url)

        if 'data' in r.json().keys() and len(r.json()['data']) >= 1:
            gif_url = r.json()['data'][0]['images']['downsized']['url']

            return gif_url.split('?')[0]

        logger.error('could not get reaction video url')
        return None

    except BaseException as e:
        logger.error('could not get giphy data: %s', e)
        return None


class MatrixHandler(object):
    """Handling matrix connection and bot integration."""

    def __init__(self, config: Dict[str, str]) -> None:
        self.hostname = config['hostname']
        self.username = config['username']
        self.password = config['password']
        self.uid = config['uid']
        self.giphy_api_key = config['giphy_api_key']

        # self.client = None
        # self.sync_process = None

    def on_message(self, room: Room, event: Dict) -> None:
        """Callback for recieved messages.

        Gets events and checks if something can be triggered.
        """
        logger.debug(event)
        if event['content'].get('msgtype') == 'm.text' and event['sender'] != \
                self.uid:

            msg = MOSS.serve(event)
            if msg and msg.data:

                if msg.type == 'text':
                    room.send_text(msg.data)

                elif msg.type == 'notice':
                    room.send_notice(msg.data)

                elif msg.type == 'html':
                    room.send_html(msg.data)

                elif msg.type == 'image':
                    self.write_media('image', room, msg.data)

                elif msg.type == 'reaction':
                    if msg.data:
                        gif_url = get_giphy_reaction_url(
                            self.giphy_api_key,
                            msg.data
                        )
                        if gif_url:
                            self.write_media('image', room, gif_url)
                        else:
                            logger.error('no video_url')

                elif msg.type == 'skip':
                    pass

                else:
                    logger.error(
                        'could not recognize msg type "%s"',
                        msg[0]
                    )

            else:
                logger.error('no msg or msg.data')

    def on_invite(self, room_id, state):
        """Callback for recieving invites."""
        logger.info('got invite for room %s', room_id)
        self.client.join_room(room_id)

    def listen_forever(self, timeout_ms: int = 30000) -> None:
        """Loop to run _sync in a process."""
        while True:

            try:
                # pylint: disable=protected-access
                self.client._sync(timeout_ms)
            except BaseException as e:
                logger.error('problem with sync: %s', e)
                time.sleep(10)

            time.sleep(0.1)

    def start_listener_process(self, timeout_ms: int = 30000) -> None:
        """Create sync process."""
        self.sync_process = Process(
            target=self.listen_forever,
            args=(timeout_ms, ),
            daemon=True,
        )
        self.sync_process.start()

    def connect(self) -> None:
        """Connection handler."""
        while True:

            try:

                logger.info('create matrix client')
                self.client = MatrixClient(self.hostname)

                logger.info('login with password')
                self.client.login_with_password(
                    self.username,
                    self.password
                )

                for room_id in self.client.get_rooms():
                    logger.info('join room %s', room_id)

                    room = self.client.join_room(room_id)
                    room.add_listener(self.on_message)

                self.client.add_invite_listener(self.on_invite)
                self.start_listener_process()

                start_time = pendulum.now()
                while True:

                    if pendulum.now() >= start_time.add(minutes=10):

                        logger.info('planed reconnect')
                        self.sync_process.terminate()

                        break

                    time.sleep(0.1)

            except KeyboardInterrupt:
                logger.info('GoodBye')
                self.sync_process.terminate()
                sys.exit()

            except BaseException as e:
                logger.error('problem while try to connect: %s', e)
                time.sleep(10)

    def write_media(self, media_type: str, room: Room, url: str) -> None:
        """Get media, upload it and post to room.
        """
        # analyze url
        name = urlsplit(url).path.split('/')[-1]
        filetype = mimetypes.guess_type(url)[0]

        # get file
        logger.info('download %s', url)
        response = requests.get(url, stream=True)
        response.raw.decode_content = True

        # upload it to homeserver
        logger.info('upload file')
        uploaded = self.client.upload(response.raw, filetype)
        logger.debug('upload: %s', uploaded)

        # send image to room
        logger.info('send media: %s', name)

        if media_type == 'image':
            room.send_image(uploaded, name)
        elif media_type == 'video':
            room.send_video(uploaded, name)


@click.command()
@click.argument('config', type=click.File('r'))
@click.option('--debug', is_flag=True)
def main(config: click.File, debug: bool) -> None:
    """ Main. """
    if debug:
        logzero.loglevel(logging.DEBUG)

    MatrixHandler(yaml.load(config)).connect()


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
