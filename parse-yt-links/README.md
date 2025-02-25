# parse-yt-links
Script to parse basic attributes from YouTube videos (date, title, and views), given a text document containing YouTube URLs.
Uses public HTML; no API key required.

## Usage
```bash
parse-yt-links.py <input-file>
```

Example:
```bash
$ ./parse-yt-links.py test.md
[2020-04-06] [65,881,112] This Video Has 65,881,112 Views (https://youtu.be/BxV14h0kFs0)
[2018-06-25] [10,178,035] Horizons mission - Soyuz: launch to orbit (https://www.youtube.com/watch?v=fr_hXLDLc38)
[2023-06-02] [3,770] Keynote Speaker - Ned Batchelder (https://www.youtube.com/watch?v=n5QaOADqSyY)
```
