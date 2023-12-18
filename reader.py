def read_headers(sock) -> str:
    buffer_size = 1024
    data = ''

    while True:
        chunk = sock.recv(buffer_size).decode()

        if not chunk:
            break

        data += chunk

        if "\r\n\r\n" in chunk:
            break

    return data


def read_body(sock):
    pass
