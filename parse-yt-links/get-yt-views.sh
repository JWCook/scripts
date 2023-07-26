#! /usr/bin/bash
# Print the number of views for a given YouTube URL
curl -s "$1" \
    | grep -Po '"views":{"simpleText":"([^"]+) views"' \
    | grep -Po '[0-9,]+' \
    | sed 's/,//'
