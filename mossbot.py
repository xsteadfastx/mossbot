import logging
import re
import requests
import sys

from bs4 import BeautifulSoup
from matrix_client.api import MatrixRequestError
from matrix_client.client import MatrixClient
from requests.exceptions import MissingSchema

import config


logging.basicConfig(level=logging.DEBUG)


class MossBot(object):

    def __init__(self):
        self.routes = {}

    def route(self, route_str):

        def decorator(f):
            self.routes[route_str] = f

            return f

        return decorator

    def serve(self, raw_msg):
        for k in self.routes.keys():
            m = re.search(k, raw_msg)

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
    return ('notice', 'Good morning, thats a nice TNETENNBA')


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
    try:
        r = requests.get(route)
        soup = BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        logging.warning('url_title could not get html title: {}'.format(e))
        return ('skip', None)

    return (
        'html',
        '<a href="{}">{}</a>'.format(route, soup.title.string)
    )


def on_message(room, event):
    """Callback for recieved messages.

    Gets events and checks if something can be triggered.
    """
    logging.debug(event)
    if event['content'].get('msgtype') == 'm.text' and event['sender'] != \
            config.UID:

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
                    room.client.api.get_html_body(msg[1])
                )

            elif msg[0] == 'skip':
                pass

            else:
                logging.warning(
                    'could not recognize msg type "{}"'.format(msg[0])
                )


def main(host, username, password, room_id_alias):
    client = MatrixClient(host)

    try:
        client.login_with_password(username, password)

    except MatrixRequestError as e:
        print(e)
        if e.code == 403:
            print("Bad username or password.")
            sys.exit(4)
        else:
            print("Check your sever details are correct.")
            sys.exit(2)

    except MissingSchema as e:
        print("Bad URL format.")
        print(e)
        sys.exit(3)

    try:
        room = client.join_room(room_id_alias)
        room.add_listener(on_message)
        client.start_listener_thread()

        try:
            while True:
                True
        except KeyboardInterrupt:
            print('bye')

    except MatrixRequestError as e:
        print(e)
        if e.code == 400:
            print("Room ID/Alias in the wrong format")
            sys.exit(11)
        else:
            print("Couldn't find room.")
            sys.exit(12)


if __name__ == '__main__':
    main(config.HOSTNAME, config.USERNAME, config.PASSWORD, config.ROOM)
