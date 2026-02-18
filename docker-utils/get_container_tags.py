#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "python-dateutil",
#     "python-dotenv",
#     "requests",
#     "requests-cache",
# ]
# ///
import argparse
from dataclasses import dataclass
from datetime import timedelta
from fnmatch import fnmatch
from logging import getLogger
from os import getenv
from pathlib import Path

import requests
from dateutil.parser import parse as parse_date
from dotenv import load_dotenv
from requests_cache import NEVER_EXPIRE, CachedSession

load_dotenv(Path(__file__).resolve().parent / '.env')
DT_FORMAT = '%Y-%m-%d'
GH_API_TOKEN = getenv('GH_API_TOKEN')
IGNORE_TAGS = ['sha256-*', 'main', 'main-*', 'master-*', '*.dev*', '*arm64*']

logger = getLogger(__name__)
session = CachedSession(
    'container_registries.db',
    use_temp=True,
    allowable_methods=['GET', 'POST'],
    urls_expire_after={
        'codeberg.org/v2/*/manifests/*': NEVER_EXPIRE,
        'codeberg.org/v2/*/blobs/*': NEVER_EXPIRE,
        '*': timedelta(hours=1),
    },
)


@dataclass
class Tag:
    name: str
    ts: str | None

    @property
    def date(self) -> str:
        return parse_date(self.ts).strftime(DT_FORMAT) if self.ts else ''

    @property
    def is_ignored(self):
        return any(fnmatch(self.name, pat) for pat in IGNORE_TAGS)

    def __str__(self) -> str:
        date_str = f' - {self.date}' if self.date else ''
        return f'{self.name}{date_str}'


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


def fetch_codeberg_tags(repo: str) -> list[Tag]:
    """Fetch tags from Codeberg (Forgejo) container registry using OCI Distribution Spec"""
    path = repo.replace('codeberg.org/', '')  # e.g. "owner/image"
    base = f'https://codeberg.org/v2/{path}'

    # Codeberg requires a Bearer token even for public images (anonymous token exchange)
    token_resp = session.get(
        f'https://codeberg.org/v2/token?service=container_registry&scope=repository:{path}:pull'
    )
    token_resp.raise_for_status()
    token = token_resp.json()['token']
    auth_headers = {'Authorization': f'Bearer {token}'}

    # Paginate tag list
    tags = []
    url = f'{base}/tags/list?n=100'
    while url:
        response = session.get(url, headers=auth_headers)
        response.raise_for_status()
        data = response.json()
        tags.extend(data.get('tags') or [])
        # Pagination via Link header (relative URLs)
        link = response.headers.get('Link', '')
        next_url = next(
            (p.split(';')[0].strip().strip('<>') for p in link.split(',') if 'rel="next"' in p),
            None,
        )
        url = (
            f'https://codeberg.org{next_url}' if next_url and next_url.startswith('/') else next_url
        )

    logger.info('Fetching timestamps for {len(tags)} tags')
    return [Tag(name=tag, ts=_fetch_oci_timestamp(base, tag, auth_headers)) for tag in tags]


def _fetch_oci_timestamp(base: str, tag: str, auth_headers: dict) -> str | None:
    """Get the created timestamp for an OCI tag via manifest -> config blob"""
    try:
        resp = session.get(
            f'{base}/manifests/{tag}',
            headers={
                **auth_headers,
                'Accept': 'application/vnd.oci.image.manifest.v1+json,application/vnd.oci.image.index.v1+json',
            },
        )
        resp.raise_for_status()
        manifest = resp.json()
        # For multi-arch image indexes, resolve the first child manifest
        if manifest.get('mediaType') == 'application/vnd.oci.image.index.v1+json':
            sub_digest = (manifest.get('manifests') or [{}])[0].get('digest')
            if not sub_digest:
                return None
            resp = session.get(f'{base}/manifests/{sub_digest}', headers=auth_headers)
            resp.raise_for_status()
            manifest = resp.json()
        digest = manifest.get('config', {}).get('digest')
        if not digest:
            return None
        blob_resp = session.get(f'{base}/blobs/{digest}', headers=auth_headers)
        blob_resp.raise_for_status()
        return blob_resp.json().get('created')
    except requests.HTTPError:
        return None


def fetch_tags(repo: str) -> list[str]:
    repo = repo.replace('lscr.io/', 'ghcr.io/')
    if repo.startswith('ghcr.io/'):
        tags = fetch_ghcr_tags(repo)
    elif repo.startswith('quay.io/'):
        tags = fetch_quay_tags(repo)
    elif repo.startswith('public.ecr.aws/'):
        tags = fetch_ecr_tags(repo)
    elif repo.startswith('codeberg.org/'):
        tags = fetch_codeberg_tags(repo)
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
