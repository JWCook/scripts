#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyyaml",
# ]
# ///

import argparse
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ServiceImage:
    service: str  # compose service name
    image: str  # full image string, e.g. "nginx:1.25"

    @property
    def name(self) -> str:
        """Image name without tag, e.g. 'nginx'"""
        return self.image.split(':')[0]

    @property
    def tag(self) -> str:
        """Tag portion, e.g. '1.25', or 'latest' if unspecified"""
        parts = self.image.split(':')
        return parts[1] if len(parts) > 1 else 'latest'

    def __str__(self) -> str:
        return f'{self.service}: {self.image}'


def get_images(compose_file: Path) -> list[ServiceImage]:
    """Parse a docker-compose.yml and return service/image pairs."""
    with compose_file.open() as f:
        config = yaml.safe_load(f)
    services = config.get('services', {})
    result = []
    for name, svc in services.items():
        if image := svc.get('image'):
            result.append(ServiceImage(service=name, image=image))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description='List images and tags from a docker-compose.yml')
    parser.add_argument(
        'compose_file',
        nargs='?',
        default='docker-compose.yml',
        type=Path,
        help='Path to docker-compose.yml (default: ./docker-compose.yml)',
    )
    args = parser.parse_args()
    for item in get_images(args.compose_file):
        print(item)


if __name__ == '__main__':
    main()
