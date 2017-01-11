import logging
import re
import requests
import sys

from bs4 import BeautifulSoup
from collections import OrderedDict
from matrix_client.api import MatrixRequestError
from matrix_client.client import MatrixClient
from requests.exceptions import MissingSchema

logging.basicConfig(level=logging.DEBUG)


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
    logging.info('matched url route')
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
        logging.debug(event)
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

                elif msg[0] == 'skip':
                    pass

                else:
                    logging.warning(
                        'could not recognize msg type "{}"'.format(msg[0])
                    )

    def on_invite(self, room_id, state):
        """Callback for recieving invites.
        """
        logging.info('got invite for room {}'.format(room_id))
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
            # get rooms and join them
            for room_id in self.client.get_rooms():
                logging.info('join room {}'.format(room_id))

                room = self.client.join_room(room_id)
                room.add_listener(self.on_message)

            self.client.add_invite_listener(self.on_invite)
            self.client.start_listener_thread()

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
    import yaml

    if len(sys.argv) == 2:
        with open(sys.argv[1], 'r') as f:
            config = yaml.load(f)

        MatrixHandler(config).connect()
    else:
        print('Provide config yaml.')
        sys.exit()
