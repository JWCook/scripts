#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "python-dateutil",
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

from dateutil.parser import parse as parse_date
from dotenv import load_dotenv
from requests_cache import CachedSession

load_dotenv(Path(__file__).resolve().parent / '.env')
DT_FORMAT = '%Y-%m-%d'
GH_API_TOKEN = getenv('GH_API_TOKEN')
IGNORE_TAGS = ['sha256-*', 'main', 'main-*', 'master-*', '*.dev*', '*arm64*']

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
        return parse_date(self.ts).strftime(DT_FORMAT) if self.ts else 'N/A'

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
        tags_json = response.json().get('results', [])
        for item in tags_json:
            all_tags.append(Tag(name=item['name'], ts=item.get('last_updated')))
        url = response.json().get('next')

    return all_tags


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
    tags_json = response.json()

    all_tags = []
    for item in tags_json:
        for tag in item.get('metadata', {}).get('container', {}).get('tags', []):
            all_tags.append(Tag(name=tag, ts=item.get('created_at')))
    return all_tags


def fetch_quay_tags(repo: str) -> list[Tag]:
    """Fetch tags from Quay.io"""
    repo = repo.replace('quay.io/', '')
    response = session.get(f'https://quay.io/api/v1/repository/{repo}/tag/')
    response.raise_for_status()
    tags_json = response.json().get('tags', [])
    return [Tag(name=item['name'], ts=item.get('last_modified')) for item in tags_json]


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
    repo = repo.replace('lscr.io/', 'ghcr.io/')
    if repo.startswith('ghcr.io/'):
        tags = fetch_ghcr_tags(repo)
    elif repo.startswith('quay.io/'):
        tags = fetch_quay_tags(repo)
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
