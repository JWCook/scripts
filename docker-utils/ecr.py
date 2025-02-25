#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
# ]
# ///
import requests

# Fetch a list of all tags available for the public ERC image: public.ecr.aws/aws-dynamodb-local/aws-dynamodb-local
# Run with ./ecr.py
r = requests.post(
    'https://api.us-east-1.gallery.ecr.aws/describeImageTags',
    json={'registryAliasName': 'aws-dynamodb-local', 'repositoryName': 'aws-dynamodb-local'},
)
print(r.text)
