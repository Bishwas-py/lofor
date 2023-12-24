import socket
import ssl
import threading
from typing import Union

from lofor.server import http


def start(host, port):
    server = socket.create_server((host, port))
    server.listen()

    while True:
        """
        Spawn new thread to handle each client. Currently, keep-alive connection is not supported yet except for 
        websocket connection. So for every new resources request like Javascript, stylesheets, 
        new connections are created.
        
        For HTTP, we just close the connection after receiving data from the target server and close the connection.
        Closing connection after sending all data tells the client, the response is completed.
        """
        client_sock, _ = server.accept()
        thread = threading.Thread(target=handle_client, args=(client_sock,))
        thread.daemon = True
        thread.start()


def handle_path_not_configured(client_socket: socket.socket):
    """
    If path is not set, display the HTTP 404 error message with instructions.
    """

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

    # Keep alive not supported. Close connection, so that server knows all the data has been received.
    client_socket.close()


def create_socket_client(host, port, is_https: bool) -> Union[socket.socket | ssl.SSLSocket]:
    """
    Creates a new socket client based on the socket type.

    If the target origin is https, creates a client socket with ssl support else normal socket client.
    """

    client_socket = socket.create_connection((host, port))

    if is_https:
        ssl_context = ssl.create_default_context()
        ssl_socket = ssl_context.wrap_socket(client_socket, server_hostname=host)
        return ssl_socket

    return client_socket


def handle_receive_from_target_server(target_socket: socket.socket, client_socket: socket.socket):
    """
    Forwards incoming bytes received from the target socket to the client socket.
    Automatically closes the client socket if the target socket is closed.
    """

    try:
        while True:
            chunk = target_socket.recv(1024)
            if not chunk:
                break

            client_socket.sendall(chunk)
    except socket.error:
        client_socket.close()


def handle_receive_from_request_client(client_socket: socket.socket, target_socket: socket.socket):
    """
    Forwards the incoming bytes received from the client (browser or any http client) to the target server.
    Automatically closes connection to the target socket if the target client is closed.
    """

    try:
        while True:
            chunk = client_socket.recv(1024)
            if not chunk:
                break

            target_socket.sendall(chunk)
    except socket.error:
        target_socket.close()


def handle_client(client_socket: socket.socket):
    """
    Process incoming bytes received from the client and target server.
    """

    raw_headers, body_part = http.scan_headers(client_socket)
    request = http.Request(raw_headers)
    original_host = request.headers['Host']
    is_websocket = request.headers.get('Upgrade', '').lower() == 'websocket'

    # Search and return the most matching target host based on the client send host and pathname.
    matching_config = http.get_matching_host_config(host=original_host, path=request.path)

    # Check if the path is matched or not in the config.
    if not matching_config:
        # Display path not configured message
        handle_path_not_configured(client_socket)
        return

    proxy_to: str = matching_config.get('proxy_to')  # Target host
    host, port = http.get_hostname_and_port(proxy_to)  # Host and port based on the matching host
    https: bool = matching_config.get('https')  # True if site is https else False

    if not port:
        port = 443 if https else 80

    modified_request = http.modify_request(request, host, port, https, is_websocket)
    scheme = 'https' if https else 'http'

    # Print forwarding logs
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
            # Handle websocket protocol
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
            # Handle HTTP protocol
            chunk = forward_client.recv(1024)
            if not chunk:
                forward_client.close()
                break

            client_socket.sendall(chunk)

    except socket.error:
        print('Connection closed')

    # Only HTTP connection closing is handled here. Websocket connection will be not closed.
    if not is_websocket:
        """
        Once all the page is received from target server and sent to client, close the connection.
        """
        client_socket.close()
