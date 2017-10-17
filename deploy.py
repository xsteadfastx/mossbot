"""docker deploy script"""

import os
import sys

import docker
from tinydb import TinyDB

client = docker.from_env()

try:

    print('stopping mossbot container...')
    mossbot_container = client.containers.get('mossbot')
    mossbot_container.stop()
    mossbot_container.wait()
    print('stopped')

    try:

        print('removing mossbot container...')
        mossbot_container.remove()
        print('removed')

    except docker.errors.NotFound:

        print('no mossbot container to remove')

except docker.errors.NotFound:
    print('no running mossbot container')

# create data directory if needed
if not os.path.exists('/opt/mossbot'):
    print('creating data directory...')
    os.makedirs('/opt/mossbot')

# init db if not there
if not os.path.exists('/opt/mossbot/db.json'):
    print('init db...')
    TinyDB('/opt/mossbot/db.json')

print('fixing permissions...')
os.chown('/opt/mossbot/db.json', 1000, 1000)

print('starting mossbot...')
client.containers.run(
    'xsteadfastx/mossbot',
    auto_remove=False,
    detach=True,
    volumes={
        '/opt/mossbot/config.yml': {
            'bind': '/app/config.yml',
            'mode': 'ro'
        },
        '/opt/mossbot/db.json': {
            'bind': '/app/db.json',
        }
    },
    name='mossbot',
)
try:
    client.containers.get('mossbot')
    print('started')
    sys.exit(0)
except docker.errors.NotFound:
    print('container not running!')
    sys.exit(1)
