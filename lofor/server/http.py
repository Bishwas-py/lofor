import socket
from typing import Tuple, Optional
from collections import OrderedDict
from urllib.parse import urlparse

from lofor.manager.config import ConfigManager


class Request:
    """
    A request object for storing request information.
    """

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

    def set_headers(self, name, value) -> None:
        """
        Set new header or update existing one.
        """

        self.headers[name] = value

    def remove_headers(self, name) -> None:
        """
        Remove headers if exists.
        """

        headers_val = self.headers.get(name)
        if headers_val:
            del self.headers[name]

    def build_headers(self) -> str:
        """
        Construct request headers back to text.
        """

        _headers = f'{self.method} {self.path} {self.http_version}\r\n'
        for (name, value) in self.headers.items():
            _headers += f'{name}: {value}\r\n'

        _headers += '\r\n'
        return _headers

    def header_bytes(self) -> bytes:
        """
        Headers as bytes object.
        """

        return self.build_headers().encode()

    def __str__(self) -> str:
        return self.build_headers()


def scan_headers(sock: socket.socket) -> Tuple[bytes, bytes]:
    """
    Scans for http headers and returns header bytes and partial body bytes if any.
    """

    data = b''

    while True:
        chunk = sock.recv(1024)

        if not chunk:
            break

        data += chunk
        if b'\r\n\r\n' in chunk:
            break

    header_content_parts = data.split(b'\r\n\r\n', 1)
    header_bytes = header_content_parts[0]
    body_bytes = b''

    if len(header_content_parts) > 1:
        body_bytes = header_content_parts[1]

    return header_bytes, body_bytes


def read_body(client_socket: socket.socket, content_length: int, initial_bytes: bytes) -> bytes:
    """
    Read bytes from the client socket wit the given content length specified. Return bytes with combination to initial bytes.
    """

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
    """
    Returns the most matching host config for the current host and path.
    Host level matching will have the more priority than the path matching.
    """

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


def get_hostname_and_port(url: str) -> Tuple[str | None, int]:
    """
    Returns parsed hostname and port as Tuple.
    """

    parsed = urlparse(url)

    port = parsed.port
    if not parsed.port and parsed.scheme == 'https':
        port = 443

    return parsed.hostname, port


def modify_request(request: Request, host: str, port: int, https: bool, is_ws: bool) -> Request:
    """
    Modifies request headers for forwarding.
    """

    if not is_ws:
        if https:
            request.set_headers('Origin', f'https://{host}')

        else:
            request.set_headers('Origin', f'http://{host}:{port}')

    request.set_headers('Host', f'{host}:{port}')
    request.set_headers('Referer', host)

    if not is_ws:
        request.set_headers('Connection', 'close')

    return request
