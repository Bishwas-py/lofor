import socket

server = socket.create_server(('', 7777), reuse_port=True)

FORWARD_TO = 'webmatrices.com'


def rewrite(content) -> str:
    content = content.replace('Host: localhost:7777', f'Host: https://{FORWARD_TO}/')
    print(content)
    return content


while True:
    client, addr = server.accept()
    received = client.recv(2024)
    content = received.decode()
    content = rewrite(content)

    # Sending content after rewriting
    client_fetch = socket.create_connection((FORWARD_TO, 443))
    client_fetch.send(content.encode())

    # Receive data from server
    client_receive = client_fetch.recv(2024)
    client.send(client_receive)

    client_fetch.close()
    client.close()
