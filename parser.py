def parse_headers(raw_headers: str) -> dict[str, str]:
    lines = raw_headers.split('\r\n')
    headers = {}

    for line in lines:
        values = line.split(':')

        if len(values) > 1:
            name, value = values[0].strip(), values[1].strip()
            headers[name] = value

    return headers
