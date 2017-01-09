import re
import sys

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError
from requests.exceptions import MissingSchema


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
                msg = matches.get('msg')

                func = self.routes.get(k)

                return func(msg=msg)


moss = MossBot()


@moss.route(r'(?P<route>hello moss)\s?(?P<msg>.*)?')
def hello(msg=None):
    return 'hello moss'


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

    except MatrixRequestError as e:
        print(e)
        if e.code == 400:
            print("Room ID/Alias in the wrong format")
            sys.exit(11)
        else:
            print("Couldn't find room.")
            sys.exit(12)


if __name__ == '__main__':
    main()
