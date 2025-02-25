#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
# ]
# ///
import argparse
import sys
from os import getenv

import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException

load_dotenv()
GH_API_TOKEN = getenv('GH_API_TOKEN')


def fetch_dockerhub_tags(repository):
    """Fetch tags from Docker Hub"""
    if '/' not in repository:
        repository = f'library/{repository}'

    url = f'https://hub.docker.com/v2/repositories/{repository}/tags?page_size=100'
    all_tags = []

    while url:
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            for item in data['results']:
                date_str = _format_date(item.get('last_updated'))
                all_tags.append(f'{item["name"]} - {date_str}')

            url = data.get('next')
        except RequestException as e:
            print(f'Error fetching Docker Hub tags: {e}')
            break

    return all_tags


def fetch_ghcr_tags(repository):
    """Fetch tags from GitHub Container Registry"""
    headers = {
        'Authorization': f'Bearer {GH_API_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
    }
    # TODO: handle /users
    url = f'https://api.github.com/orgs/{repository.split("/")[0]}/packages/container/{repository.split("/")[1]}/versions'
    all_tags = []

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        for item in data:
            # Some versions might have multiple tags
            for tag in item.get('metadata', {}).get('container', {}).get('tags', []):
                date_str = _format_date(item.get('created_at'))
                all_tags.append(f'{tag} - {date_str}')
    except requests.exceptions.RequestException as e:
        print(f'Error fetching GitHub Container Registry tags: {e}', file=sys.stderr)

    return all_tags


# TODO: maybe this can't be done with unauthenticated calls
def fetch_ecr_tags(repo: str):
    """Fetch tags from Amazon ECR Public"""
    # repo = repo.split("/", 1)[-1]
    url = f'https://public.ecr.aws/v2/{repo}/tags/list'

    try:
        response = requests.get(url)
        response.raise_for_status()
        all_tags = response.json().get('tags', [])

        # For ECR Public, we might need additional API calls to get the date
        # for tag in tags:
        #     # date_str = _format_date('??')
        #     all_tags.append(f"{tag} - N/A")
    except RequestException as e:
        print(f'Error fetching ECR Public tags: {e}')

    return all_tags


def _format_date(dt: str | None) -> str:
    return dt.split('T')[0] if dt else 'N/A'


def main():
    parser = argparse.ArgumentParser(description='Fetch all tags and dates for a Docker container')
    parser.add_argument('repo', help='Repository in format [registry/]namespace/repository')
    args = parser.parse_args()

    # Determine which registry to use based on the repository string
    if args.repository.startswith('ghcr.io/'):
        tags = fetch_ghcr_tags(args.repo.replace('ghcr.io/', ''))
    elif args.repository.startswith('public.ecr.aws/'):
        tags = fetch_ecr_tags(args.repo.replace('public.ecr.aws/', ''))
    else:
        # Assume Docker Hub for repositories without explicit registry
        tags = fetch_dockerhub_tags(args.repo.replace('docker.io/', ''))

    for tag in sorted(tags):
        print(tag)


if __name__ == '__main__':
    main()
