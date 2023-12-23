import sys
from typing import Callable

from manager.config import ConfigManager, SchemeNotProvidedException
from server import serve

entry = """\033[92m
+--------------------------------------------+
|                                            |
|         Welcome to the "Lofor"             |
|                                            |
+--------------------------------------------+

The reverse proxy for development.
Version: 0.1

Commands:
----------------------------------------------
To start:
- lofor start

To forward:
 - lofor forward / http://localhost:5173
 - lofor forward /api/ https://example.com/api/

To list forwards:
 - lofor list

To remove:
 - lofor remove /api/
-----------------------------------------------
\033[0m
"""

config_manager = ConfigManager()


def parse_args(commands: dict):
    if len(sys.argv) == 1:
        print(entry)
        return

    command = sys.argv[1]
    func = commands.get(command)
    if func:
        func()

    else:
        print('Invalid command')
        print(entry)


def handle_forward():
    if len(sys.argv) < 4:
        print('Invalid number of arguments.')
        print('Example command: lofor forward /api/ https://example.com/api/')
        return

    forward_from = sys.argv[2]
    forward_to = sys.argv[3]
    try:
        config_manager.set_forward(forward_from, forward_to)
    except SchemeNotProvidedException as error:
        print(error)
        print('Example command: lofor forward /api/ http://127.0.0.1:8000')


def handle_remove():
    if len(sys.argv) < 3:
        print('Invalid number of arguments')
        return

    forward_from = sys.argv[2]
    has_key = config_manager.remove_forward(forward_from)
    if not has_key:
        print(f'The forward path "{forward_from}" does not exist. Please run "lofor list" to see all available paths.')
    else:
        print(f'Successfully removed forward "{forward_from}".')


def handle_list():
    config = config_manager.read()
    forwards = config.get('forwards')
    print('\033[92m---------------------------------------------')
    print('Forwards list')
    print('forward from ===> forward to')
    print('---------------------------------------------\033[0m')

    print('\033[94m', end='')
    for (forward_from, details) in forwards.items():
        print(f'{forward_from} ===> {details.get("proxy_to")}')

    print('\033[0m', end='')
    if len(forwards.items()):
        print()


def handle_start():
    print('Listening on http://127.0.0.1:7777')
    serve.start()


def handle_cli():
    commands: dict[str, Callable] = {
        'forward': handle_forward,
        'remove': handle_remove,
        'list': handle_list,
        'start': handle_start
    }

    parse_args(commands)


if __name__ == '__main__':
    handle_cli()
