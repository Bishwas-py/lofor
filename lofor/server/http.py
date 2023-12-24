import socket
from typing import Tuple, Optional
from collections import OrderedDict
from urllib.parse import urlparse

from lofor.manager.config import ConfigManager


class Request:
    def __init__(self, raw_headers: bytes):
        self.headers = OrderedDict()

        # Process headers
        split_headers = raw_headers.decode().split('\r\n')
        request_method, path, http_version = split_headers[0].split(' ')

        self.method = request_method.strip()
        self.path = path.strip()
        self.http_version = http_version.strip()

        for header in split_headers[1:]:
            name, value = header.split(':', 1)
            self.headers[name.strip()] = value.strip()

    def set(self, name, value) -> None:
        self.headers[name] = value

    def remove(self, name) -> None:
        del self.headers[name]

    def build(self) -> str:
        _headers = f'{self.method} {self.path} {self.http_version}\r\n'
        for (name, value) in self.headers.items():
            _headers += f'{name}: {value}\r\n'

        _headers += '\r\n'
        return _headers

    def header_bytes(self) -> bytes:
        return self.build().encode()

    def __str__(self) -> str:
        return self.build()


def scan_headers(sock: socket.socket) -> Tuple[bytes, bytes]:
    data = b''

    while True:
        chunk = sock.recv(1024)

        if not chunk:
            break

        data += chunk
        if b'\r\n\r\n' in chunk:
            break

    header_content_parts = data.split(b'\r\n\r\n', 1)
    return header_content_parts[0], header_content_parts[1]


def read_body(client_socket, content_length: int, initial_bytes: bytes) -> bytes:
    data = initial_bytes

    while len(data) != content_length:
        chunk = client_socket.recv(1024)
        if not chunk:
            break

        data += chunk

    return data


config_manager = ConfigManager()
config = config_manager.read()
forwards: dict[str, dict] = config.get('forwards')


def get_matching_host_config(host: str, path: str) -> Optional[dict]:
    for (forward_rule, data) in forwards.items():
        """
        Path always starts with forward slash '/'
        Where as host level forwarding is without slash.
        """

        if host.startswith(forward_rule):
            return data

        if forward_rule.startswith('/') and path.startswith(forward_rule):
            return data

    return None


def get_host(path: str) -> Tuple[str | None, int]:
    parsed = urlparse(path)

    port = parsed.port
    if not parsed.port and parsed.scheme == 'https':
        port = 443

    return parsed.hostname, port


def modify_request(request: Request, host: str, port: int, https: bool, is_ws: bool) -> Request:
    if not is_ws:
        if https:
            request.headers['Origin'] = f'https://{host}'

        else:
            request.headers['Origin'] = host

    request.headers['Host'] = f'{host}:{port}'
    request.headers['Referer'] = host

    if not is_ws:
        request.headers['Connection'] = 'close'

    return request
