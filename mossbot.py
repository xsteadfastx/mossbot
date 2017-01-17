import logging
import mimetypes
import random
import re
import sys
import time

from collections import OrderedDict
from multiprocessing import Process
from urllib.parse import quote_plus, urlsplit

from bs4 import BeautifulSoup

import click

from matrix_client.client import MatrixClient

import pendulum

import requests

import yaml


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class MossBot(object):
    """Bot routing logic."""

    def __init__(self):
        self.routes = OrderedDict()

    def route(self, route_str):

        def decorator(f):
            self.routes[route_str] = f

            return f

        return decorator

    def serve(self, raw_msg):
        for k in self.routes.keys():
            m = re.search(k, raw_msg, re.IGNORECASE)

            if m:
                matches = m.groupdict()
                route = matches.get('route')
                msg = matches.get('msg')

                func = self.routes.get(k)

                logger.info(
                    (
                        f'matched route "{route}" '
                        f'with msg "{msg}" from "{raw_msg}" '
                        f'and triggered "{func.__name__}"'
                    )
                )

                return func(route=route, msg=msg)

        return None


MOSS = MossBot()


@MOSS.route(r'^(?P<route>!ping)$')
def ping(route=None, msg=None):
    """Pongs back in a Moss way."""
    oneliners = (
        'Good morning, thats a nice TNETENNBA',
        'Ow. Four! I mean, five! I mean, fire!',
        'Did you see that ludicrous display last night?',
    )

    return ('notice', random.choice(oneliners))


@MOSS.route(r'(?P<route>^http[s]?://.*(?:jpg|jpeg|png|gif)$)')
def image(route=None, msg=None):
    """Posts image."""
    return ('image', route)


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
def url_title(route=None, msg=None):
    """Takes postet urls and parses the title."""
    try:

        logger.debug('get "{}"'.format(route))
        r = requests.get(route)
        logger.debug('parse for title')
        soup = BeautifulSoup(r.text, 'html.parser')

    except BaseException as e:
        logger.warning(f'url_title could not get html title: {str(e)}')

        return ('skip', None)

    title = soup.title.string
    logger.info('url title: {}'.format(title))

    return (
        'html',
        f'<a href="{route}">{title}</a>'
    )


@MOSS.route(r'^(?P<route>!reaction)\s+(?P<msg>.+)')
def reaction(route=None, msg=None):
    """Posts reaction gif."""
    return ('reaction', msg)


def get_giphy_reaction_url(api_key, tag):
    """Gets a random giphy gif and returns url."""
    tag = quote_plus(tag)
    url = f'http://api.giphy.com/v1/gifs/random?api_key={api_key}&tag={tag}'

    try:
        r = requests.get(url)

        if 'data' in r.json().keys():
            return r.json()['data']['image_mp4_url']

        else:
            logger.error('could not get reaction video url')
            return None

    except BaseException as e:
        logger.error(f'could not get giphy data: {str(e)}')
        return None


class MatrixHandler(object):
    """Handling matrix connection and bot integration."""

    def __init__(self, config):
        self.hostname = config.get('hostname')
        self.username = config.get('username')
        self.password = config.get('password')
        self.uid = config.get('uid')
        self.giphy_api_key = config.get('giphy_api_key')

        self.client = None
        self.sync_process = None

    def on_message(self, room, event):
        """Callback for recieved messages.

        Gets events and checks if something can be triggered.
        """
        logger.debug(event)
        if event['content'].get('msgtype') == 'm.text' and event['sender'] != \
                self.uid:

            msg = MOSS.serve(event['content']['body'])
            if msg:

                if msg[0] == 'text':
                    room.send_text(msg[1])

                elif msg[0] == 'notice':
                    room.send_notice(msg[1])

                elif msg[0] == 'html':
                    room.client.api.send_message_event(
                        room.room_id,
                        'm.room.message',
                        room.client.api.get_html_body(
                            msg[1],
                            msgtype='m.notice'
                        )
                    )

                elif msg[0] == 'image':
                    self.write_media('image', room, msg[1])

                elif msg[0] == 'reaction':
                    video_url = get_giphy_reaction_url(
                        self.giphy_api_key,
                        msg[1]
                    )
                    self.write_media('video', room, video_url)

                elif msg[0] == 'skip':
                    pass

                else:
                    logger.error(
                        'could not recognize msg type "{}"'.format(msg[0])
                    )

    def on_invite(self, room_id, state):
        """Callback for recieving invites."""
        logger.info('got invite for room {}'.format(room_id))
        self.client.join_room(room_id)

    def listen_forever(self, timeout_ms=30000):
        """Loop to run _sync in a process."""
        while True:

            try:
                self.client._sync(timeout_ms)

            except BaseException as e:
                logger.error(f'problem with sync: {str(e)}')
                time.sleep(10)

            time.sleep(0.1)

    def start_listener_process(self, timeout_ms=30000):
        """Create sync process."""
        self.sync_process = Process(
            target=self.listen_forever,
            args=(timeout_ms, )
        )
        self.sync_process.daemon = True
        self.sync_process.start()

    def connect(self):
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
                    logger.info('join room {}'.format(room_id))

                    room = self.client.join_room(room_id)
                    room.add_listener(self.on_message)

                self.client.add_invite_listener(self.on_invite)
                self.start_listener_process()

                start_time = pendulum.now()
                while True:

                    if pendulum.now() >= start_time.add(minutes=10):

                        logging.info('planed reconnect')
                        self.sync_process.terminate()

                        break

                    time.sleep(0.1)

            except KeyboardInterrupt:
                logger.info('GoodBye')
                self.sync_process.terminate()
                sys.exit()

            except BaseException as e:
                logger.error(f'problem while try to connect: {str(e)}')
                time.sleep(10)

    def write_media(self, media_type, room, url):
        """Get media, upload it and post to room.
        """
        # analyze url
        name = urlsplit(url).path.split('/')[-1]
        filetype = mimetypes.guess_type(url)[0]

        # get file
        logger.info('download {}'.format(url))
        response = requests.get(url, stream=True)
        response.raw.decode_content = True

        # upload it to homeserver
        logger.info('upload file')
        uploaded = self.client.upload(response.raw, filetype)
        logger.debug('upload: {}'.format(uploaded))

        # send image to room
        logger.info('send media: {}'.format(name))

        if media_type == 'image':
            room.send_image(uploaded, name)
        elif media_type == 'video':
            room.send_video(uploaded, name)


@click.command()
@click.argument('config', type=click.File('r'))
@click.option('--debug', is_flag=True)
def main(config, debug):
    if debug:
        logger.setLevel(logging.DEBUG)

    MatrixHandler(yaml.load(config)).connect()


if __name__ == '__main__':
    main()
