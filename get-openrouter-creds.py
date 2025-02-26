#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
# ]
# ///
import json
from pathlib import Path

import requests

KEYS_FILE = Path('~/.config/io.datasette.llm/keys.json').expanduser()
OR_KEY = json.loads(KEYS_FILE.read_text())['openrouter']

r = requests.get(
    'https://openrouter.ai/api/v1/credits',
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OR_KEY}',
    },
).json()['data']
credits = r['total_credits'] - r['total_usage']
print(f'{credits:.4}')
