#! /usr/bin/env python
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from operator import attrgetter
from pathlib import Path

from requests_cache import CachedSession

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
            url=url.split("&")[0],
            date=_get_date(html),
            title=_get_title(html),
            views=_get_view_count(html),
        )

    @property
    def date_str(self):
        return self.date.strftime("%Y-%m-%d")

    def __str__(self):
        return f'[{self.date_str}] [{self.views:,}] {self.title} ({self.url})'


def parse_videos(source: Path | str, sort_col: str = 'views') -> list[Video]:
    """Get Video objects from a text file containing YouTube URLs"""
    return sorted(
        [Video.from_url(url) for url in _get_yt_urls(source)],
        key=attrgetter(sort_col),
        reverse=True,
    )


def to_md(videos: list[Video], dest: str | Path = None, table: bool = False) -> str:
    """Convert a list of Video objects to a Markdown list or table"""
    md = f'# Videos ({len(videos)})\n\n'
    md += _md_table(videos) if table else _md_list(videos)

    if dest:
        with Path(dest).open('w') as f:
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
    md = '| Date | Title | Views | URL |\n'
    md += '| --- | --- | --- | --- |\n'
    for v in videos:
        md += f'| {v.date_str} | {v.title} | {v.views:,} | [{v.url}]({v.url}) |\n'
    return md


def _get_html(url: str) -> str:
    """Get HTML by URL or YouTube video ID"""
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={url}"
    return session.get(url).text


def _get_view_count(html: str) -> int:
    views = re.search(r'"views":{"simpleText":"([^"]+) views"', html)

    try:
        return int(views.group(1).replace(",", ""))
    except (AttributeError, TypeError, ValueError):
        return 0


def _get_title(html: str) -> str:
    title = re.search(r'<title>([^<]+)</title>', html)
    return title.group(1).replace(" - YouTube", "")


def _get_date(html: str) -> datetime:
    match = re.search(r'"dateText":{"simpleText":"([^"]+)"', html)
    date_str = match.group(1)
    return datetime.strptime(date_str, '%b %d, %Y')


def _get_yt_urls(source: Path | str):
    """Extract any youtube URLs from a text file or string"""
    if isinstance(source, Path):
        source = source.read_text()

    # Too lazy to get this regex working
    # return re.findall(r"https?://(?:www\.)?(?:youtu\.be/|youtube\.com\S+)", text)

    urls = re.findall(r"(https?://[^\s^\)]+)", source)
    return [url for url in urls if 'youtube.com' in url or 'youtu.be' in url]


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] in ('-h', '--help'):
        print(f"Usage: {sys.argv[0]} [path]")
        sys.exit(0)

    videos = parse_videos(Path(sys.argv[1]))
    # to_md(videos, Path('table.md'), table=True)
    for video in videos:
        print(video)
