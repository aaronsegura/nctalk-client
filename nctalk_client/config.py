"""Manage configuration loading/saving for nctalk app."""

import json
import stat
import os
import asyncio

import platformdirs as pdir

from typing import Any


class NCTalkConfiguration(dict):

    _config = {}

    def __init__(self):
        super().__init__(self)

        self.config_path = pdir.user_config_path("nctalk")
        self.config_file = f'{self.config_path}/configuration.json'
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from config file if one exists."""
        with open(self.config_file, "r") as fp:
            self._config = json.loads(fp.read())

    def save_config(self) -> None:
        """Save configuration to file."""
        self.config_path.mkdir(parents=True, exist_ok=True, mode=stat.S_IRWXU)
        with open(self.config_file, "w") as fp:
            fp.write(json.dumps(self._config))
        os.chmod(self.config_file, mode=stat.S_IRUSR | stat.S_IWUSR)

    def __getitem__(self, key, default: Any = None) -> Any:
        return self.get(key, default)

    def get(self, key, default: Any = None):
        if key in self._config:
            return self._config[key]
        elif default:
            return default
        else:
            raise KeyError(f'No such configuration item: {key}')

    def __setitem__(self, key, val) -> None:
        self.put(key, val)

    def put(self, key: Any, val: Any) -> None:
        self._config[key] = val
