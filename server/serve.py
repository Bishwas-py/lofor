import socket
import ssl
import threading
from typing import Union

from server import http

PORT = 7777


def start():
    server = socket.create_server(('', PORT))
    server.listen()

    while True:
        client_sock, _ = server.accept()
        thread = threading.Thread(target=handle_client, args=(client_sock,))
        thread.daemon = True
        thread.start()


def handle_path_not_configured(sock: socket.socket):
    pass


def create_socket_client(host, port, is_https: bool) -> Union[socket.socket | ssl.SSLSocket]:
    client_socket = socket.create_connection((host, port))

    if is_https:
        ssl_context = ssl.create_default_context()
        ssl_socket = ssl_context.wrap_socket(client_socket, server_hostname=host)
        return ssl_socket

    return client_socket


def handle_client(client_socket: socket.socket):
    raw_headers, body_part = http.scan_headers(client_socket)
    request = http.Request(raw_headers)
    forward_from = request.path

    matching_config = http.get_matching_host_config(request.path)
    if not matching_config:
        handle_path_not_configured(client_socket)

    proxy_to = matching_config.get('proxy_to')
    host, port = http.get_host(proxy_to)
    https = matching_config.get('https')

    if not port:
        port = 443 if https else 80

    modified_request = http.modify_request(request, request.path, host, port, https)
    forward_to = modified_request.path

    print(f'\033[94mForwarding {forward_from} ==> {forward_to}\033[0m')
    forward_client = create_socket_client(host, port, https)
    forward_client.sendall(modified_request.header_bytes())

    if body_part:
        forward_client.sendall(body_part)

    while True:
        chunk = forward_client.recv(1024)
        if not chunk:
            break

        client_socket.sendall(chunk)

    forward_client.close()
