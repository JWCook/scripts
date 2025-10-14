#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mutagen",
# ]
# ///

import csv
from logging import basicConfig, getLogger
from pathlib import Path
from typing import Iterable

from mutagen.mp4 import MP4

logger = getLogger(__name__)
basicConfig(level='DEBUG')
BookChapters = list[tuple[str, int]]

AUDIO_DIR = Path('audio_bible')


def get_book_chapters() -> BookChapters:
    with open('books.csv') as csvfile:
        reader = csv.reader(csvfile)
        book_n_chapters = {row[0]: int(row[1]) for row in reader}

    book_chapters = []
    for book, n_chapters in book_n_chapters.items():
        for n in range(n_chapters):
            # book_chapters.append(f'{book} Chapter {n+1}')
            book_chapters.append((book, n + 1))

    return book_chapters


def write_track_name(path: Path, book_chapters: BookChapters):
    track = MP4(path)

    # Find book and chapter based on track number
    idx = track.tags['trkn']
    while isinstance(idx, Iterable):
        idx = idx[0]
    book, chapter = book_chapters[idx - 1]
    title = f'{book} Chapter {chapter}'

    # Write metadata
    track.tags['©nam'] = title
    track.tags['©grp'] = book
    track.save()

    # Rename
    new_path = path.parent / f'{idx:0>4} - {title}.m4a'
    logger.info(f'Moving {path.name} to {new_path.name}')
    path.rename(new_path)


def main():
    book_chapters = get_book_chapters()
    logger.info(f'Found {len(book_chapters)} track names')
    paths = list(AUDIO_DIR.glob('*'))
    logger.info(f'Found {len(paths)} audio files')
    for track_path in paths:
        write_track_name(track_path, book_chapters)


if __name__ == '__main__':
    main()
