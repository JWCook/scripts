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
from logging import basicConfig, getLogger
from os import getenv
from pathlib import Path
from typing import Iterator

import requests
from dateutil.parser import parse as parse_date
from dotenv import load_dotenv
from requests_cache import NEVER_EXPIRE, CachedSession

load_dotenv(Path(__file__).resolve().parent / '.env')
DT_FORMAT = '%Y-%m-%d'
GH_API_TOKEN = getenv('GH_API_TOKEN')
IGNORE_TAGS = [
    'sha256-*',
    'sha-*',
    'main',
    'main-*',
    'master-*',
    '*.dev*',
    '*-test',
    '*arm32*',
    '*arm64*',
]

logger = getLogger(__name__)
session = CachedSession(
    'container_registries.db',
    use_cache_dir=True,
    allowable_methods=['GET', 'POST'],
    urls_expire_after={
        '*/v2/*/manifests/*': NEVER_EXPIRE,
        '*/v2/*/blobs/*': NEVER_EXPIRE,
        'gitlab.com/api/v4/projects/*/registry/repositories/*/tags/*': NEVER_EXPIRE,
        '*': timedelta(hours=1),
    },
)


@dataclass
class Tag:
    name: str
    ts: str | None = None

    @property
    def date(self) -> str:
        return parse_date(self.ts).strftime(DT_FORMAT) if self.ts else ''

    @property
    def is_ignored(self):
        return any(fnmatch(self.name, pat) for pat in IGNORE_TAGS)

    def __str__(self) -> str:
        date_str = f' - {self.date}' if self.date else ''
        return f'{self.name}{date_str}'


def fetch_dockerhub_tags(repo) -> Iterator[Tag]:
    """Fetch tags from Docker Hub"""
    repo = repo.replace('docker.io/', '')
    if '/' in repo:
        org, repo = repo.split('/')
    else:
        org = 'library'

    url = f'https://hub.docker.com/v2/repositories/{org}/{repo}/tags?page_size=100'
    while url:
        response = session.get(url)
        response.raise_for_status()
        tags_json = response.json().get('results', [])
        for item in tags_json:
            yield Tag(name=item['name'], ts=item.get('last_updated'))
        url = response.json().get('next')


def fetch_ghcr_tags(repo: str) -> Iterator[Tag]:
    """Fetch tags from GitHub Container Registry.

    Uses the GitHub REST API when an access token is available,
    otherwise falls back to the OCI Distribution Spec with anonymous token exchange
    """
    path = repo.replace('ghcr.io/', '')

    if not GH_API_TOKEN:
        token_url = f'https://ghcr.io/token?service=ghcr.io&scope=repository:{path}:pull'
        yield from _fetch_oci_tags(host='https://ghcr.io', path=path, token_url=token_url)
        return

    org, image = path.split('/', 1)
    response = session.get(
        f'https://api.github.com/orgs/{org}/packages/container/{image}/versions',
        headers={
            'Authorization': f'Bearer {GH_API_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
        },
    )
    response.raise_for_status()
    for item in response.json():
        for tag in item.get('metadata', {}).get('container', {}).get('tags', []):
            yield Tag(name=tag, ts=item.get('created_at'))


def fetch_quay_tags(repo: str) -> Iterator[Tag]:
    """Fetch tags from Quay.io"""
    repo = repo.replace('quay.io/', '')
    response = session.get(f'https://quay.io/api/v1/repository/{repo}/tag/')
    response.raise_for_status()
    yield from (
        Tag(name=item['name'], ts=item.get('last_modified'))
        for item in response.json().get('tags', [])
    )


def fetch_ecr_tags(repo: str) -> Iterator[Tag]:
    """Fetch tags from Amazon ECR Public"""
    registry, repo = repo.replace('public.ecr.aws/', '').split('/')
    response = session.post(
        'https://api.us-east-1.gallery.ecr.aws/describeImageTags',
        json={'registryAliasName': registry, 'repositoryName': repo},
    )
    response.raise_for_status()
    yield from (
        Tag(name=i['imageTag'], ts=i['createdAt']) for i in response.json()['imageTagDetails']
    )


def fetch_codeberg_tags(repo: str) -> Iterator[Tag]:
    """Fetch tags from Codeberg (Forgejo) container registry using OCI Distribution Spec"""
    path = repo.replace('codeberg.org/', '')  # e.g. "owner/image"
    # Codeberg requires a Bearer token even for public images (anonymous token exchange)
    token_url = (
        f'https://codeberg.org/v2/token?service=container_registry&scope=repository:{path}:pull'
    )
    yield from _fetch_oci_tags(host='https://codeberg.org', path=path, token_url=token_url)


def fetch_gitlab_tags(repo: str) -> Iterator[Tag]:
    """Fetch tags from GitLab Container Registry via GitLab REST API"""
    # repo format: registry.gitlab.com/group/project[/image]
    path = repo.replace('registry.gitlab.com/', '')  # e.g. "group/project"
    encoded_path = path.replace('/', '%2F')
    base = f'https://gitlab.com/api/v4/projects/{encoded_path}/registry/repositories'

    # Find the registry repository ID
    response = session.get(base)
    response.raise_for_status()
    repos = response.json()
    if not repos:
        return
    repo_id = repos[0]['id']

    # Paginate tags via Link header
    url: str | None = f'{base}/{repo_id}/tags?per_page=100'
    tags = []
    while url:
        response = session.get(url)
        response.raise_for_status()
        tags.extend(Tag(name=item['name']) for item in response.json())
        link = response.headers.get('Link', '')
        url = next(
            (p.split(';')[0].strip().strip('<>') for p in link.split(',') if 'rel="next"' in p),
            None,
        )

    # Fetch created_at per tag
    n_printable = sum(1 for t in tags if not t.is_ignored)
    logger.info(f'Fetching timestamps for {n_printable}/{len(tags)} tags')
    for t in tags:
        if not t.is_ignored:
            detail = session.get(f'{base}/{repo_id}/tags/{t.name}')
            t.ts = detail.json().get('created_at') if detail.ok else None
        yield t


def _fetch_oci_tags(host: str, path: str, token_url: str) -> Iterator[Tag]:
    """Fetch tags from an OCI-compatible registry using anonymous token exchange"""
    token_resp = session.get(token_url)
    token_resp.raise_for_status()
    token = token_resp.json()['token']
    auth_headers = {'Authorization': f'Bearer {token}'}

    base = f'{host}/v2/{path}'
    tags: list[Tag] = []
    url: str | None = f'{base}/tags/list?n=100'
    while url:
        response = session.get(url, headers=auth_headers)
        response.raise_for_status()
        if response_tags := response.json().get('tags'):
            tags.extend(Tag(name=t) for t in response_tags)
        # Pagination via Link header (may contain relative URLs)
        link = response.headers.get('Link', '')
        next_url = next(
            (p.split(';')[0].strip().strip('<>') for p in link.split(',') if 'rel="next"' in p),
            None,
        )
        url = f'{host}{next_url}' if next_url and next_url.startswith('/') else next_url

    n_printable = sum(1 for t in tags if not t.is_ignored)
    logger.info(f'Fetching timestamps for {n_printable}/{len(tags)} tags')
    for t in tags:
        if not t.is_ignored:
            t.ts = _fetch_oci_timestamp(base, t.name, auth_headers)
        yield t


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
    elif repo.startswith('registry.gitlab.com/'):
        tags = fetch_gitlab_tags(repo)
    else:
        tags = fetch_dockerhub_tags(repo)
    return sorted([str(tag) for tag in tags if not tag.is_ignored])


def main():
    parser = argparse.ArgumentParser(description='Fetch all tags and dates for a Docker container')
    parser.add_argument('repo', help='Repository in format [registry/]namespace/repository')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    if args.verbose:
        basicConfig(level='INFO')
    for tag in fetch_tags(args.repo):
        print(tag)


if __name__ == '__main__':
    main()
