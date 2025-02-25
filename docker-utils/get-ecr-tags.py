#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "boto3",
#     "requests",
# ]
# ///

import boto3


def get_all_tags(repo):
    """Retrieve all tags for a specified public ECR repository."""
    repo = repo.replace('public.ecr.aws/', '')
    client = boto3.client('ecr-public', region_name='us-east-1')
    response = client.describe_image_tags(
        registryAliasName='aws-dynamodb-local', repositoryName='aws-dynamodb-local'
    )
    print(response)
    return sorted([i['imageTags'] for i in response['imageTagDetails']])


def main():
    # parser = argparse.ArgumentParser(description='Get all tags for an ECR public image')
    # parser.add_argument('repo', help='ECR public repository (public.ecr.aws/org/repo)')
    # args = parser.parse_args()
    # tags = get_all_tags(args.repo)
    tags = get_all_tags('public.ecr.aws/aws-dynamodb-local/aws-dynamodb-local')
    for tag in tags:
        print(tag)
    print(f'\nTotal tags: {len(tags)}')


if __name__ == '__main__':
    main()
