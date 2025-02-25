#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests-cache",
#     "rich",
# ]
# ///

import argparse
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from html import unescape
from logging import basicConfig, getLogger
from operator import attrgetter
from pathlib import Path
from urllib.parse import unquote

from requests_cache import CachedSession
from rich.progress import track

logger = getLogger(__name__)
session = CachedSession('yt_pages.db', expire_after=timedelta(hours=1))


@dataclass
class Video:
    url: str = field(default=None)
    date: datetime = field(default=None)
    title: str = field(default=None)
    views: int = field(default=None)

    @classmethod
    def from_url(cls, url: str) -> 'Video':
        html = _get_html(url)
        return cls(
            url=_normalize_url(url),
            date=_get_date(html),
            title=_get_title(html),
            views=_get_view_count(html),
        )

    @property
    def date_str(self):
        return self.date.strftime('%Y-%m-%d')

    def __str__(self):
        return f'[{self.date_str}] [{self.views:,}] {self.title} ({self.url})'


def parse_videos(
    input_file: str | str, sort_col: str = 'date', ascending: bool = False
) -> list[Video]:
    """Get Video objects from a text file containing YouTube URLs"""
    urls = _get_yt_urls(input_file)
    videos = []
    for url in track(urls, description='Fetching video metadata...'):
        videos.append(Video.from_url(url))

    logger.debug(f'Found {len(videos)} video links in {input_file}')
    return sorted(videos, key=attrgetter(sort_col), reverse=not ascending)


def to_md(videos: list[Video], output_file: str = None, table: bool = False) -> str:
    """Convert a list of Video objects to a Markdown list or table"""
    md = f'# Videos ({len(videos)})\n\n'
    md += _md_table(videos) if table else _md_list(videos)

    if not videos:
        logger.warning('No videos found')
        return md

    if output_file:
        logger.debug(f'Writing {"table" if table else "list"} to {output_file}')
        with Path(output_file).open('w') as f:
            f.write(md)
    return md


def _md_list(
    videos: list[Video],
) -> str:
    md = ''
    for v in videos:
        md += f'* [{v.title}]({v.url}) ({v.date_str}; {v.views:,} views)\n'
    return md


def _md_table(videos: list[Video]) -> str:
    md = '| Date Uploaded | Views | Title |\n'
    md += '| ------------ | ----- | ----- |\n'
    for v in videos:
        md += f'| {v.date_str} | {v.views:,} | [{v.title}]({v.url}) |\n'
    return md


def _get_html(url: str) -> str:
    """Get HTML by URL or YouTube video ID"""
    if not url.startswith('http'):
        url = f'https://www.youtube.com/watch?v={url}'
    return session.get(url).text


def _normalize_url(url: str) -> str:
    """Convert any YouTube URL to a short url"""
    if url.startswith('http'):
        url = url.split('&')[0]
        url = unquote(url)
        url = url.replace('https://www.youtube.com/watch?v=', 'https://youtu.be/')
    return url


def _get_view_count(html: str) -> int:
    views = re.search(r'"views":{"simpleText":"([^"]+) views"', html)

    try:
        return int(views.group(1).replace(',', ''))
    except (AttributeError, TypeError, ValueError):
        return 0


def _get_title(html: str) -> str:
    title = re.search(r'<title>([^<]+)</title>', html)
    title = title.group(1).replace(' - YouTube', '')
    return unescape(title)


def _get_date(html: str) -> datetime:
    match = re.search(r'"dateText":{"simpleText":"([^"]+)"', html)
    date_str = match.group(1)
    return datetime.strptime(date_str, '%b %d, %Y')


def _get_yt_urls(input_file: str):
    """Extract any youtube URLs from a text file or string"""
    content = Path(input_file).read_text()

    # Too lazy to get this regex working
    # return re.findall(r'https?://(?:www\.)?(?:youtu\.be/|youtube\.com\S+)', text)

    urls = re.findall(r'(https?://[^\s^\)]+)', content)
    return [url for url in urls if 'youtube.com' in url or 'youtu.be' in url]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='Path to text file containing YouTube URLs')
    parser.add_argument(
        '-i',
        '--inplace',
        action='store_true',
        help='Overwrite input file',
    )
    parser.add_argument(
        '-o',
        '--output_file',
        help='Output file',
    )
    parser.add_argument(
        '-r',
        '--reverse',
        action='store_true',
        help='Reverse sort order (ascending)',
    )
    parser.add_argument(
        '-s',
        '--sort',
        choices=['date', 'title', 'views'],
        default='date',
        help='Sort order for output',
    )
    parser.add_argument(
        '-t',
        '--table',
        action='store_true',
        help='Output a Markdown table instead of list',
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='Enable verbose logging',
    )
    args = parser.parse_args()

    if args.verbose:
        basicConfig(level='INFO')
        logger.setLevel('DEBUG')

    videos = parse_videos(args.input_file, sort_col=args.sort, ascending=args.reverse)
    output_file = args.input_file if args.inplace else args.output_file
    to_md(videos, output_file, table=args.table)

    if not output_file or args.verbose:
        for video in videos:
            print(video)


if __name__ == '__main__':
    main()
