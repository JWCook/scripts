#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "python-dotenv",
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
    if not GH_API_TOKEN:
        raise ValueError('GitHub personal access token required')

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


def fetch_ecr_tags(repo: str):
    """Fetch tags from Amazon ECR Public"""
    registry, repo = repo.replace('public.ecr.aws/', '').split('/')
    response = requests.post(
        'https://api.us-east-1.gallery.ecr.aws/describeImageTags',
        json={'registryAliasName': registry, 'repositoryName': repo},
    ).json()
    return [f'{i["imageTag"]} - {_format_date(i["createdAt"])}' for i in response['imageTagDetails']]


def _format_date(dt: str | None) -> str:
    return dt.split('T')[0] if dt else 'N/A'


def main():
    parser = argparse.ArgumentParser(description='Fetch all tags and dates for a Docker container')
    parser.add_argument('repo', help='Repository in format [registry/]namespace/repository')
    args = parser.parse_args()

    # Determine which registry to use based on the repository string
    if args.repo.startswith('ghcr.io/'):
        tags = fetch_ghcr_tags(args.repo.replace('ghcr.io/', ''))
    elif args.repo.startswith('public.ecr.aws/'):
        tags = fetch_ecr_tags(args.repo.replace('public.ecr.aws/', ''))
    else:
        # Assume Docker Hub for repositories without explicit registry
        tags = fetch_dockerhub_tags(args.repo.replace('docker.io/', ''))

    for tag in sorted(tags):
        print(tag)


if __name__ == '__main__':
    main()
