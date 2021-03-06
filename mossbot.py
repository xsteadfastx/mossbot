"""mossbot"""

import logging
import mimetypes
import random
import re
import sys
import time
from collections import OrderedDict
from io import BytesIO
from multiprocessing import Process
from typing import Callable, Dict, NamedTuple, Union
from urllib.parse import quote_plus, urlsplit

import click
import pendulum
import requests
import yaml
from bs4 import BeautifulSoup
from logzero import logger, loglevel
from matrix_client.client import MatrixClient
from matrix_client.room import Room
from PIL import Image
from tinydb import Query, TinyDB

##############################################################################
# TYPES and CONSTANTS #########################################################
##############################################################################


# tuple to store route return data
MSG_RETURN = NamedTuple(
    'MSG_RETURN',
    [
        ('type', str),
        ('data', Union[str, None]),
    ]
)

# type for route functions
ROUTE_TYPE = Callable[[Union[str, None], Union[str, None], Dict], MSG_RETURN]

# dict to store routes and its functions
ROUTES_TYPE = Dict[str, ROUTE_TYPE]


##############################################################################
# HELPER FUNCTIONS ###########################################################
##############################################################################


def get_db() -> TinyDB:
    """Creates database"""
    return TinyDB('db.json')


def get_giphy_reaction_url(api_key: str, term: str) -> Union[str, None]:
    """Gets a random giphy gif and returns url

    :param api_key: GIPHY api key
    :param term: search term
    :returns: gif url
    """
    term = quote_plus(term)

    url = (
        f'http://api.giphy.com/v1/gifs/search'
        f'?api_key={api_key}'
        f'&q={term}'
        f'&limit=20'
    )

    try:
        r = requests.get(url)

        if 'data' in r.json().keys() and len(r.json()['data']) >= 1:
            random_gif = random.choice(r.json()['data'])
            gif_url = random_gif['images']['downsized']['url']

            return gif_url.split('?')[0]

        logger.error('could not get reaction video url')
        return None

    except BaseException as e:
        logger.exception('could not get giphy data: %s', e)
        return None


def get_image(
        url: str
) -> Union[Dict[str, Union[int, str, BytesIO, None]], None]:
    """Downloads image and analyzes it

    :param url: image url
    :returns: dictionary with image and meta data
    """
    try:
        logger.info('downloading image: %s', url)
        r = requests.get(url)

        if r.status_code == 200:

            # loading binary data to mem
            img = BytesIO(r.content)

            # loading image to PIL
            pil_img = Image.open(img)

            # seek to 0
            img.seek(0)

            return {
                'content-type': r.headers.get('Content-Type'),
                'image': img,
                'width': pil_img.width,
                'height': pil_img.height,
            }

        raise Exception('wrong status code %s', r.status_code)

    except BaseException as e:
        logger.error('could not download and analyze img: %s', str(e))

        return None


##############################################################################
# MOSSBOT LOGIC ##############################################################
##############################################################################


class MossBot(object):
    """Bot routing logic"""

    __slots__ = ['routes']

    def __init__(self) -> None:
        # stores all routes and its functions
        self.routes = OrderedDict()  # type: ROUTES_TYPE

    def route(self, route: str) -> Callable:
        """Decorator to save routes to a dictionary"""

        def decorator(f: Callable) -> Callable:
            """Decorates the function."""
            self.routes[route] = f

            return f

        return decorator

    def serve(self, event: Dict) -> Union[MSG_RETURN, None]:
        """Returns the right function for matching route

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

                    return func(route, msg, event)

        return None


MOSS = MossBot()


##############################################################################
# ROUTES #####################################################################
##############################################################################


@MOSS.route(r'^(?P<route>!ping)$')
def ping(route: str, msg: str, event: Dict) -> MSG_RETURN:
    """Pongs back in a Moss way"""
    oneliners = (
        'Good morning, thats a nice TNETENNBA',
        'Ow. Four! I mean, five! I mean, fire!',
        'Did you see that ludicrous display last night?',
    )

    return MSG_RETURN('notice', random.choice(oneliners))


@MOSS.route(r'(?P<route>^http[s]?://.*(?:jpg|jpeg|png|gif)$)')
def image(route: str, msg: str, event: Dict) -> MSG_RETURN:
    """Posts image"""
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
def url_title(route: str, msg: str, event: Dict) -> MSG_RETURN:
    """Takes postet urls and parses the title"""
    try:

        logger.debug('get "%s"', route)
        r = requests.get(route)
        logger.debug('parse for title')
        soup = BeautifulSoup(r.text, 'html.parser')

    except BaseException as e:
        logger.exception('url_title could not get html title: %s', e)

        return MSG_RETURN('skip', None)

    title = soup.title.string
    logger.info('url title: %s', title)

    return MSG_RETURN(
        'html',
        f'<a href="{route}">{title}</a>'
    )


@MOSS.route(r'^(?P<route>!reaction)\s+(?P<msg>.+)')
def reaction(route: str, msg: str, event: Dict) -> MSG_RETURN:
    """Posts reaction gif

    :param route: reaction route
    :param msg: reaction to look for
    """
    try:

        gif_url = get_giphy_reaction_url(
            event['config']['giphy_api_key'],
            msg
        )
        if gif_url:
            return MSG_RETURN('image', gif_url)

        logger.error('no gif url')

    except BaseException as e:
        logger.exception('could not get reaction: %s', e)

    return MSG_RETURN('skip', None)


@MOSS.route(r'^s/(?P<route>.+)/(?P<msg>.+)$')
def replace(route: str, msg: str, event: Dict) -> MSG_RETURN:
    """Search and replace

    :param route: search term
    :param msg: replace term
    :param event: full event dict
    """
    try:

        db = get_db()
        msgs_table = db.table('msgs')
        stored_msg = Query()

        # get all user msgs
        all_sender_msgs = msgs_table.search(
            stored_msg.sender == event['sender']
        )

        for user_msg in reversed(all_sender_msgs):

            # message should not match the route
            if not re.match(r'^s/.+/.+$', user_msg['body']):

                sender = user_msg['sender']
                body = user_msg['body'].replace(route, msg)

                return MSG_RETURN(
                    'html',
                    f'<i><b>{sender}</b>: {body}</i>'
                )

        logger.warning(
            'no usable msg for search and replace'
        )
        return MSG_RETURN('skip', None)

    except BaseException as e:
        logger.exception('could not search and replace: %s', e)
        return MSG_RETURN('skip', None)


@MOSS.route(r'^(?P<route>!weather)\s+(?P<msg>.+)$')
def weather(route: str, msg: str, event: Dict) -> MSG_RETURN:
    """Gets weather

    :param route: weather route
    :param msg: city to look for
    :param event: full event dict
    """
    try:

        api_key = event['config']['openweathermap_api_key']

        r = requests.get(
            (
                'http://api.openweathermap.org/data/2.5/'
                f'weather?q={msg}&APPID={api_key}&units=metric'
            )
        )

        weather_data = r.json()
        logger.debug('got weather data: %s', weather_data)

        if weather_data['cod'] == '404':
            return MSG_RETURN('notice', f'could not find city {msg}')

        weather_in_words = weather_data['weather'][0]['main']
        temp = weather_data['main']['temp']
        city = weather_data['name']

        return MSG_RETURN(
            'html',
            (
                f'The weather in <i>{city}</i>: '
                f'<b>{weather_in_words}</b> with a temperature of '
                f'<b>{temp}°C</b>'
            )
        )

    except BaseException as e:
        logger.exception('problem with getting weather: %s', e)
        return MSG_RETURN('notice', 'problem with getting weather')


##############################################################################
# MATRIX HANDLING ############################################################
##############################################################################


class MatrixHandler(object):
    """Handling matrix connection and bot integration"""

    __slots__ = [
        'client',
        'config',
        'db',
        'giphy_api_key',
        'hostname',
        'openweathermap_api_key',
        'password',
        'stored_msg',
        'sync_process',
        'uid',
        'username',
    ]

    def __init__(self, config: Dict[str, str]) -> None:
        self.config = config

        self.hostname = config['hostname']
        self.username = config['username']
        self.password = config['password']
        self.uid = config['uid']

        self.db = get_db()
        self.stored_msg = Query()

        self.giphy_api_key = config['giphy_api_key']
        self.openweathermap_api_key = config['openweathermap_api_key']

    def on_message(self, room: Room, event: Dict) -> None:
        """Callback for recieved messages

        Gets events and checks if something can be triggered.
        """
        logger.debug(event)

        logger.info('stores msg in db')
        self.store_msg(event)

        if event['content'].get('msgtype') == 'm.text' and event['sender'] != \
                self.uid:

            # add config to event
            event['config'] = self.config

            # gives event to mossbot and watching out for a return message
            msg = MOSS.serve(event)

            if msg and msg.data:

                if msg.type == 'text':
                    logger.info('sending text msg...')
                    room.send_text(msg.data)

                elif msg.type == 'notice':
                    logger.info('sending notice msg...')
                    room.send_notice(msg.data)

                elif msg.type == 'html':
                    logger.info('sending html msg...')
                    room.send_html(msg.data)

                elif msg.type == 'image':
                    logger.info('sending image msg...')
                    self.write_media('image', room, msg.data)

                else:
                    logger.error(
                        'could not recognize msg type "%s"',
                        msg[0]
                    )

            elif msg and msg.type == 'skip':
                logger.info('skipping msg...')

            else:
                logger.debug('no matching in event')

    def on_invite(self, room_id, state):
        """Callback for recieving invites"""
        logger.info('got invite for room %s', room_id)
        self.client.join_room(room_id)

    def listen_forever(self, timeout_ms: int = 30000) -> None:
        """Loop to run _sync in a process"""
        while True:

            try:
                # pylint: disable=protected-access
                self.client._sync(timeout_ms)
            except BaseException as e:
                logger.exception('problem with sync: %s', e)
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
                logger.exception('problem while try to connect: %s', e)
                time.sleep(10)

    def write_media(self, media_type: str, room: Room, url: str) -> None:
        """Get media, upload it and post to room
        """
        # image is the only media type supported right now
        if media_type != 'image':
            logger.error('%s as media type is not supported', media_type)
            return None

        # getting image and analyze it
        logger.info('download %s', url)
        image_data = get_image(url)
        logger.debug('got image_data: %s', image_data)

        if not image_data:
            logger.error('got no image_data')
            return

        # analyze image file and create image info dict
        media_info = {}  # type: Dict[str, Union[str, int, BytesIO, None]]

        # getting mimetype
        media_info['mimetype'] = image_data.get('content-type')
        if not media_info['mimetype']:
            media_info['mimetype'] = mimetypes.guess_type(url)[0]

        # getting name
        name = urlsplit(url).path.split('/')[-1]

        # image size
        media_info['h'] = image_data.get('height')
        media_info['w'] = image_data.get('width')

        logger.debug('media_info content: %s', media_info)

        # upload it to homeserver
        logger.info('upload file')
        uploaded = self.client.upload(
            image_data['image'],
            media_info['mimetype']
        )
        logger.debug('upload: %s', uploaded)

        # send image to room
        logger.info('send media: %s', name)
        room.send_image(
            uploaded,
            name,
            **media_info
        )

    def store_msg(self, event: Dict) -> None:
        """Store msgs in a db"""
        logger.debug('got event to store: %s', str(event))

        try:

            msgs_table = self.db.table('msgs')

            if event['content']['msgtype'] == 'm.text':

                all_sender_msgs = msgs_table.search(
                    self.stored_msg.sender == event['sender']
                )

                while len(all_sender_msgs) >= 10:

                    msgs_table.remove(doc_ids=[all_sender_msgs[0].doc_id])

                    all_sender_msgs = msgs_table.search(
                        self.stored_msg.sender == event['sender']
                    )

                msgs_table.insert(
                    {
                        'sender': event['sender'],
                        'body': event['content']['body'],
                    }
                )

        except BaseException:
            logger.exception('could not store msg')

            return None


##############################################################################
# USER INTERFACE
##############################################################################


@click.command()
@click.argument('config', type=click.File('r'))
@click.option('--debug', is_flag=True)
def main(config: click.File, debug: bool) -> None:
    """Main"""
    if debug:
        loglevel(logging.DEBUG)

    MatrixHandler(yaml.load(config)).connect()


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    main()
