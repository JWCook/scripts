#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "python-dotenv",
#     "requests-cache",
# ]
# ///
import argparse
from datetime import timedelta
from os import getenv

from dotenv import load_dotenv
from requests_cache import CachedSession

load_dotenv()
GH_API_TOKEN = getenv('GH_API_TOKEN')
session = CachedSession(
    'container_registries.db',
    use_temp=True,
    expire_after=timedelta(hours=1),
    allowable_methods=['GET', 'POST'],
)


def fetch_dockerhub_tags(repo):
    """Fetch tags from Docker Hub"""
    repo = repo.replace('docker.io/', '')
    if '/' in repo:
        org, repo = repo.split('/')
    else:
        org = 'library'

    url = f'https://hub.docker.com/v2/repositories/{org}/{repo}/tags?page_size=100'

    all_tags = []
    while url:
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        for item in data['results']:
            date_str = _format_date(item.get('last_updated'))
            all_tags.append(f'{item["name"]} - {date_str}')
        url = data.get('next')

    return all_tags


# TODO: handle /users in addition to /orgs
def fetch_ghcr_tags(repo):
    """Fetch tags from GitHub Container Registry"""
    if not GH_API_TOKEN:
        raise ValueError('GitHub personal access token required')

    org, repo = repo.replace('ghcr.io/', '').split('/')
    response = session.get(
        f'https://api.github.com/orgs/{org}/packages/container/{repo}/versions',
        headers={
            'Authorization': f'Bearer {GH_API_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
        },
    )
    response.raise_for_status()
    data = response.json()

    all_tags = []
    for item in data:
        for tag in item.get('metadata', {}).get('container', {}).get('tags', []):
            date_str = _format_date(item.get('created_at'))
            all_tags.append(f'{tag} - {date_str}')

    return all_tags


def fetch_ecr_tags(repo: str):
    """Fetch tags from Amazon ECR Public"""
    registry, repo = repo.replace('public.ecr.aws/', '').split('/')
    response = session.post(
        'https://api.us-east-1.gallery.ecr.aws/describeImageTags',
        json={'registryAliasName': registry, 'repositoryName': repo},
    )
    response.raise_for_status()
    tags_json = response.json()['imageTagDetails']
    return [f'{i["imageTag"]} - {_format_date(i["createdAt"])}' for i in tags_json]


def _format_date(dt: str | None) -> str:
    return dt.split('T')[0] if dt else 'N/A'


def fetch_tags(repo: str) -> list[str]:
    if repo.startswith('ghcr.io/'):
        tags = fetch_ghcr_tags(repo)
    elif repo.startswith('public.ecr.aws/'):
        tags = fetch_ecr_tags(repo)
    else:
        tags = fetch_dockerhub_tags(repo)
    return tags


def main():
    parser = argparse.ArgumentParser(description='Fetch all tags and dates for a Docker container')
    parser.add_argument('repo', help='Repository in format [registry/]namespace/repository')
    args = parser.parse_args()
    for tag in sorted(fetch_tags(args.repo)):
        print(tag)


if __name__ == '__main__':
    main()
