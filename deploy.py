"""docker deploy script"""

import docker

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

print('starting mossbot...')
client.containers.run(
    'xsteadfastx/mossbot',
    auto_remove=False,
    detach=True,
    volumes={
        '/opt/mossbot/config.yml': {
            'bind': '/app/config.yml',
            'mode': 'ro'
        }
    },
    name='mossbot',
)
print('started')
