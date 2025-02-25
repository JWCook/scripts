#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "python-dotenv",
#     "requests-cache",
# ]
# ///
import argparse
from dataclasses import dataclass
from datetime import timedelta
from fnmatch import fnmatch
from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from requests_cache import CachedSession

load_dotenv(Path(__file__).resolve().parent / '.env')
GH_API_TOKEN = getenv('GH_API_TOKEN')
IGNORE_TAGS = ['sha256-*', 'master-*', '*.dev*']

session = CachedSession(
    'container_registries.db',
    use_temp=True,
    expire_after=timedelta(hours=1),
    allowable_methods=['GET', 'POST'],
)


@dataclass
class Tag:
    name: str
    ts: str | None

    @property
    def date(self) -> str:
        return self.ts.split('T')[0] if self.ts else 'N/A'

    @property
    def is_ignored(self):
        return any(fnmatch(self.name, pat) for pat in IGNORE_TAGS)

    def __str__(self) -> str:
        return f'{self.name} - {self.date}'


def fetch_dockerhub_tags(repo) -> list[Tag]:
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
            all_tags.append(Tag(name=item['name'], ts=item.get('last_updated')))
        url = data.get('next')

    return all_tags


# TODO: handle /users in addition to /orgs
def fetch_ghcr_tags(repo) -> list[Tag]:
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
            all_tags.append(Tag(name=tag, ts=item.get('created_at')))

    return all_tags


def fetch_ecr_tags(repo: str) -> list[Tag]:
    """Fetch tags from Amazon ECR Public"""
    registry, repo = repo.replace('public.ecr.aws/', '').split('/')
    response = session.post(
        'https://api.us-east-1.gallery.ecr.aws/describeImageTags',
        json={'registryAliasName': registry, 'repositoryName': repo},
    )
    response.raise_for_status()
    tags_json = response.json()['imageTagDetails']
    return [Tag(name=i['imageTag'], ts=i['createdAt']) for i in tags_json]


def fetch_tags(repo: str) -> list[str]:
    if repo.startswith('ghcr.io/'):
        tags = fetch_ghcr_tags(repo)
    elif repo.startswith('public.ecr.aws/'):
        tags = fetch_ecr_tags(repo)
    else:
        tags = fetch_dockerhub_tags(repo)
    return sorted([str(tag) for tag in tags if not tag.is_ignored])


def main():
    parser = argparse.ArgumentParser(description='Fetch all tags and dates for a Docker container')
    parser.add_argument('repo', help='Repository in format [registry/]namespace/repository')
    args = parser.parse_args()
    for tag in fetch_tags(args.repo):
        print(tag)


if __name__ == '__main__':
    main()
