import logging
import mimetypes
import re
import sys
import time

from collections import OrderedDict
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

import click

from matrix_client.api import MatrixRequestError
from matrix_client.client import MatrixClient

import requests

from requests.exceptions import MissingSchema

import yaml


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class MossBot(object):

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

                return func(route=route, msg=msg)

        return None


MOSS = MossBot()


@MOSS.route(r'^(?P<route>ping)\s?(?P<msg>.*)?')
def ping(route=None, msg=None):
    """Pongs back in a Moss way.
    """
    logger.info('matched "{}" as ping route'.format(route))
    return ('notice', 'Good morning, thats a nice TNETENNBA')


@MOSS.route(r'(?P<route>^http[s]?://.*(?:jpg|jpeg|png|gif)$)')
def image(route=None, msg=None):
    """Posts image.
    """
    logger.info('matched "{}" as image route'.format(route))
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
    """Takes postet urls and parses the title.
    """
    logger.info('matched "{}" as url route'.format(route))
    try:
        logger.debug('get "{}"'.format(route))
        r = requests.get(route)
        logger.debug('parse for title')
        soup = BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        logger.warning('url_title could not get html title: {}'.format(e))
        return ('skip', None)

    title = soup.title.string
    logger.info('url title: {}'.format(title))

    return (
        'html',
        '<a href="{}">{}</a>'.format(route, title)
    )


class MatrixHandler(object):

    def __init__(self, config):
        self.hostname = config['hostname']
        self.username = config['username']
        self.password = config['password']
        self.uid = config['uid']

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
                    self.write_image(room, msg[1])

                elif msg[0] == 'skip':
                    pass

                else:
                    logger.error(
                        'could not recognize msg type "{}"'.format(msg[0])
                    )

    def on_invite(self, room_id, state):
        """Callback for recieving invites.
        """
        logger.info('got invite for room {}'.format(room_id))
        self.client.join_room(room_id)

    def connect(self):
        """Connection handler.
        """
        self.client = MatrixClient(self.hostname)

        try:
            self.client.login_with_password(self.username, self.password)

        except MatrixRequestError as e:
            print(e)
            if e.code == 403:
                logger.error('Bad username or password.')
                sys.exit(4)
            else:
                logger.error('Check your sever details are correct.')
                sys.exit(2)

        except MissingSchema as e:
            print("Bad URL format.")
            print(e)
            sys.exit(3)

        try:

            try:

                while True:
                    # we have to deal with internet problems and
                    # reconnects. so this parts is in a while loop that
                    # gets kicked in every 10 minutes

                    # get rooms and join them
                    for room_id in self.client.get_rooms():
                        logger.info('join room {}'.format(room_id))

                        room = self.client.join_room(room_id)
                        room.add_listener(self.on_message)

                    self.client.add_invite_listener(self.on_invite)

                    logger.debug('start listener thread')
                    self.client.start_listener_thread()

                    time.sleep(600)

                    logger.debug('stop listener thread')
                    self.client.stop_listener_thread()

            except KeyboardInterrupt:
                print('bye')

        except MatrixRequestError as e:
            print(e)
            if e.code == 400:
                logger.error('Room ID/Alias in the wrong format')
                sys.exit(11)
            else:
                logger.error('Couldnt find room.')
                sys.exit(12)

    def write_image(self, room, image_url):
        # analyze image url
        name = urlsplit(image_url).path.split('/')[-1]
        filetype = mimetypes.guess_type(image_url)[0]

        # get file
        logger.info('download {}'.format(image_url))
        response = requests.get(image_url, stream=True)
        response.raw.decode_content = True

        # upload it to homeserver
        logger.info('upload file')
        uploaded = self.client.upload(response.raw, filetype)
        logger.debug('upload: {}'.format(uploaded))

        # send image to room
        logger.info('send image: {}'.format(name))
        room.send_image(uploaded, name)


@click.command()
@click.argument('config', type=click.File('r'))
@click.option('--debug', is_flag=True)
def main(config, debug):
    if debug:
        logger.setLevel(logging.DEBUG)

    MatrixHandler(yaml.load(config)).connect()


if __name__ == '__main__':
    main()
