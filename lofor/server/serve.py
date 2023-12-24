import socket
import ssl
import threading
from typing import Union

from lofor.server import http


def start(host, port):
    server = socket.create_server((host, port))
    server.listen()

    while True:
        client_sock, _ = server.accept()
        thread = threading.Thread(target=handle_client, args=(client_sock,))
        thread.daemon = True
        thread.start()


def handle_path_not_configured(client_socket: socket.socket):
    response = 'HTTP/1.1 404 NOT_FOUND\r\n'
    response += 'Content-Type: text/html\r\n'
    response += '\r\n'
    response += '''
    <html>
      <head>
        <title>Lofor</title>
      </head>
      <body>
        <h1>404 Not Found</h1>
        <p>This path is not configured. Please run "lofor forward / forward_to" to add new forward rule.</p>
      </body>
    </html>
    '''
    client_socket.sendall(response.encode())
    client_socket.close()


def create_socket_client(host, port, is_https: bool) -> Union[socket.socket | ssl.SSLSocket]:
    client_socket = socket.create_connection((host, port))

    if is_https:
        ssl_context = ssl.create_default_context()
        ssl_socket = ssl_context.wrap_socket(client_socket, server_hostname=host)
        return ssl_socket

    return client_socket


def handle_receive_from_target_server(receive_from: socket.socket, client_socket: socket.socket):
    try:
        while True:
            chunk = receive_from.recv(1024)
            if not chunk:
                break

            client_socket.sendall(chunk)
    except socket.error:
        client_socket.close()


def handle_receive_from_request_client(client_socket: socket.socket, target_socket: socket.socket):
    try:
        while True:
            chunk = client_socket.recv(1024)
            if not chunk:
                break

            target_socket.sendall(chunk)
    except socket.error:
        target_socket.close()


def handle_client(client_socket: socket.socket):
    raw_headers, body_part = http.scan_headers(client_socket)
    request = http.Request(raw_headers)
    original_host = request.headers['Host']
    is_websocket = request.headers.get('Upgrade', '').lower() == 'websocket'

    matching_config = http.get_matching_host_config(host=original_host, path=request.path)
    if not matching_config:
        handle_path_not_configured(client_socket)
        return

    proxy_to = matching_config.get('proxy_to')
    host, port = http.get_host(proxy_to)
    https = matching_config.get('https')

    if not port:
        port = 443 if https else 80

    modified_request = http.modify_request(request, host, port, https, is_websocket)
    scheme = 'https' if https else 'http'
    print(f'\033[94mForwarding http://{original_host}{request.path} ==> {scheme}://{host}:{port}{request.path}\033[0m')

    try:
        forward_client = create_socket_client(host, port, https)
        forward_client.sendall(modified_request.header_bytes())

        """
        Read request body. The request like POST can contain the body.
        """
        content_length = int(modified_request.headers.get('Content-Length', 0))
        if content_length:
            body = http.read_body(client_socket, content_length, body_part)
            forward_client.sendall(body)

        if is_websocket:
            print('Starting new threads for websocket.')
            receive_from_target_server = threading.Thread(target=handle_receive_from_target_server,
                                                          args=(forward_client, client_socket))
            receive_from_target_server.daemon = True
            receive_from_target_server.start()

            receive_from_client = threading.Thread(target=handle_receive_from_request_client,
                                                   args=(client_socket, forward_client))
            receive_from_client.daemon = True
            receive_from_client.start()

        while not is_websocket:
            chunk = forward_client.recv(1024)
            if not chunk:
                forward_client.close()
                break

            client_socket.sendall(chunk)

    except socket.error:
        print('Connection closed')

    if not is_websocket:
        client_socket.close()
