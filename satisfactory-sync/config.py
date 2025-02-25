"""Load config from environment variables, and optionally from a `.env` file."""

from logging import basicConfig, getLogger
from pathlib import Path

import environ
from dotenv import load_dotenv


@environ.config(prefix=None)
class EnvConfig:
    satisfactory_host = environ.var(default='localhost')
    satisfactory_port = environ.var(default=7777)
    satisfactory_password = environ.var()
    save_name = environ.var(default='satisfactory_continue')
    sync_bucket = environ.var()
    sync_endpoint = environ.var()
    aws_access_key = environ.var()
    aws_secret_key = environ.var()
    dry_run = environ.bool_var(default=False)
    log_level = environ.var(default='INFO')

    @property
    def api_url(self):
        return f'https://{self.satisfactory_host}:{self.satisfactory_port}/api/v1'


# First load .env (if it exists), then read environment variables
load_dotenv(Path(__file__).resolve().parent / '.env')
CONFIG = environ.to_config(EnvConfig)
basicConfig(level=CONFIG.log_level)
getLogger('urllib3').setLevel('WARN')
