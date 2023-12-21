from json import JSONDecodeError
from pathlib import Path
import json
import os


class SchemeNotProvidedException(Exception):
    pass


class ConfigManager:
    def __init__(self):
        self.config_dir = Path(os.getcwd()).joinpath('.configs/')

        if not self.config_dir.exists():
            self.config_dir.mkdir()

    def read(self) -> dict:
        config_file = self.config_dir.joinpath('config.json')
        if not config_file.exists():
            return {
                'forwards': {}
            }

        with open(config_file) as file:
            content = file.read()

        try:
            return json.loads(content)
        except (Exception, JSONDecodeError) as error:
            if isinstance(error, JSONDecodeError):
                raise Exception('Error reading config file')

            raise error

    def save(self, config: dict) -> None:
        config_file = self.config_dir.joinpath('config.json')
        with open(config_file, 'w') as file:
            file.write(json.dumps(config))

    def is_https(self, url: str) -> bool:
        return url.startswith('https://')

    def set_forward(self, forward_from: str, forward_to: str) -> None:
        if not (forward_to.startswith('http') or forward_to.startswith('https')):
            raise SchemeNotProvidedException('URL must start with http or https')

        config = self.read()
        config['forwards'][forward_from] = {'proxy_to': forward_to, 'https': self.is_https(forward_to)}
        self.save(config)

    def remove_forward(self, forward_from: str) -> bool:
        config = self.read()
        has_key = config['forwards'][forward_from] is not None
        if has_key:
            del config['forwards'][forward_from]

        self.save(config)
        return has_key
