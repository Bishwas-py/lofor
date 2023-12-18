import socket
import ssl
import threading
from typing import Callable

server = socket.create_server(('', 7777), reuse_port=True)

FORWARD_TO = 'app.erasebg.org'


def rewrite(content) -> str:
    content = content.replace('Host: localhost:7777', f'Host: {FORWARD_TO}:443')
    content = content.replace('GET /', f'GET https://{FORWARD_TO}/')
    content = content.replace('HEAD /', f'HEAD https://{FORWARD_TO}/')
    content = content.replace('Origin: http://localhost:7777', f'Origin: https://{FORWARD_TO}')
    content = content.replace('Connection: keep-alive', 'Connection: close')
    # print(content)
    return content


def create_ssl_socket(host, port):
    client_socket = socket.create_connection((host, port))
    ssl_context = ssl.create_default_context()
    ssl_socket = ssl_context.wrap_socket(client_socket, server_hostname=host)
    return ssl_socket


def handle_client(client):
    content = client.recv(2048).decode()
    content = rewrite(content)
    print('---------- RECEIVED -----------------')
    print(content)
    print('------------------------------------')

    # Sending content after rewriting
    ssl_socket = create_ssl_socket(FORWARD_TO, 443)
    ssl_socket.sendall(content.encode())

    while True:
        data = ssl_socket.recv(1024)
        client.send(data)

    ssl_socket.close()
    client.close()
    print('OK')


def run(context, send_header_callback: Callable, modify_receive_headers: Callable):
    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_client, args=(client,)).start()


def _send_headers(context, headers: dict):
    target_host = context['Host']
    headers['Host'] = target_host
    return headers


run({'Host': 'sagasab.com'}, _send_headers, None)
