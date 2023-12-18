import socket
import ssl

# Specify the host and port for the HTTPS connection
host = 'erasebg.org'
port = 443

# Create a socket connection
client = socket.create_connection((host, port))

# Wrap the socket with SSL
client_socket = socket.create_connection((host, port))
ssl_context = ssl.create_default_context()
ssl_socket = ssl_context.wrap_socket(client_socket, server_hostname=host)

# Send an example GET request
ssl_socket.sendall(b"GET / HTTP/1.1\r\nHost: erasebg.org\r\n\r\n")


def read_all():
    response = ''
    while True:
        data = ssl_socket.recv(1024)
        if not data:
            break

        response += data.decode()
        if data.decode().endswith('0\r\n\r\n'):
            return response.replace('0\r\n\r\n', '')

    return response

    # Close the SSL socket


res = read_all()
ssl_socket.close()
