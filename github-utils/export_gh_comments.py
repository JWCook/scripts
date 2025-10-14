#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "dotenv",
#     "requests-cache",
# ]
# ///
from datetime import datetime
from os import environ
from pathlib import Path

from dotenv import load_dotenv
from requests_cache import CachedSession

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / '.env')

SESSION = CachedSession(
    SCRIPT_DIR / 'github.db', expire_after=360, allowable_methods=('GET', 'POST')
)
SESSION.headers.update({'Authorization': f'Bearer {environ.get("GITHUB_TOKEN")}'})

QUERY = """
query($username: String!, $cursor: String) {
    user(login: $username) {
    issueComments(first: 100, after: $cursor) {
    totalCount
    pageInfo {
        hasNextPage
        endCursor
    }
    nodes {
        createdAt
        url
        bodyText
        issue {
        title
        repository {
            nameWithOwner
        }
        }
    }
    }
    repositoryDiscussionComments(first: 100, after: $cursor) {
    totalCount
    pageInfo {
        hasNextPage
        endCursor
    }
    nodes {
        createdAt
        url
        bodyText
        discussion {
        title
        repository {
            nameWithOwner
        }
        }
    }
    }
    pullRequests(first: 100, after: $cursor) {
    totalCount
    pageInfo {
        hasNextPage
        endCursor
    }
    nodes {
        createdAt
        url
        bodyText
        title
        repository {
            nameWithOwner
        }
    }
    }
    contributionsCollection {
        pullRequestReviewContributions(first: 100, after: $cursor) {
        totalCount
        pageInfo {
            hasNextPage
            endCursor
        }
        nodes {
            pullRequestReview {
            createdAt
            url
            bodyText
            pullRequest {
                title
                repository {
                nameWithOwner
                }
            }
            }
        }
        }
    }
}
}
"""


def get_current_user() -> str:
    """Get the currently logged in user's GitHub username"""
    response = SESSION.get('https://api.github.com/user')
    response.raise_for_status()
    return response.json()['login']


def fetch_github_comments(username: str, cursor=None):
    """Fetch all comments made by a GitHub user using the GitHub GraphQL API"""
    response = SESSION.post(
        'https://api.github.com/graphql',
        json={
            'query': QUERY,
            'variables': {'username': username, 'cursor': cursor},
        },
    )
    response.raise_for_status()
    user_data = response.json()['data']['user']

    # Issue comments
    comments = []
    for comment in user_data['issueComments']['nodes']:
        comments.append(
            {
                'type': 'Issue Comment',
                'created_at': comment['createdAt'],
                'repository': comment['issue']['repository']['nameWithOwner'],
                'title': comment['issue']['title'],
                'url': comment['url'],
                'body': comment['bodyText'],
            }
        )

    # PR descriptions
    pull_requests = user_data['pullRequests']['nodes']
    for pr in pull_requests:
        if pr['bodyText']:
            comments.append(
                {
                    'type': 'Pull Request Description',
                    'created_at': pr['createdAt'],
                    'repository': pr['repository']['nameWithOwner'],
                    'title': pr['title'],
                    'url': pr['url'],
                    'body': pr['bodyText'],
                }
            )

    # PR review comments
    pr_review_contributions = user_data['contributionsCollection'][
        'pullRequestReviewContributions'
    ]['nodes']
    for contribution in pr_review_contributions:
        review = contribution['pullRequestReview']
        if review['bodyText']:
            comments.append(
                {
                    'type': 'Pull Request Review',
                    'created_at': review['createdAt'],
                    'repository': review['pullRequest']['repository']['nameWithOwner'],
                    'title': review['pullRequest']['title'],
                    'url': review['url'],
                    'body': review['bodyText'],
                }
            )

    # Discussion comments
    discussion_comments = user_data['repositoryDiscussionComments']['nodes']
    for comment in discussion_comments:
        comments.append(
            {
                'type': 'Discussion Comment',
                'created_at': comment['createdAt'],
                'repository': comment['discussion']['repository']['nameWithOwner'],
                'title': comment['discussion']['title'],
                'url': comment['url'],
                'body': comment['bodyText'],
            }
        )

    # Check if there are more comments to fetch
    page_infos = [
        user_data['issueComments']['pageInfo'],
        user_data['pullRequests']['pageInfo'],
        user_data['contributionsCollection']['pullRequestReviewContributions']['pageInfo'],
        user_data['repositoryDiscussionComments']['pageInfo'],
    ]
    next_cursor = next(
        (p['endCursor'] for p in page_infos if p['hasNextPage']),
        None,
    )
    if next_cursor:
        return comments + fetch_github_comments(username, next_cursor)
    return comments


def deduplicate_comments(comments: list[dict]) -> list[dict]:
    """Deduplicate comments based on type + URL.
    Duplicates can occur due to comment edits.
    """
    unique_comments = []
    seen = set()
    for comment in comments:
        key = (comment['type'], comment['url'])
        if key not in seen:
            seen.add(key)
            unique_comments.append(comment)
    return unique_comments


def format_comments(comments: list[dict]):
    """Format comments as Markdown and save to a file"""
    comments = deduplicate_comments(comments)
    comments.sort(key=lambda x: x['created_at'], reverse=True)
    n_comments = len(comments)

    if filename := environ.get('GITHUB_COMMENTS_FILE'):
        file_path = Path(filename).expanduser()
    else:
        file_path = Path('github_comments.md')

    with file_path.open('w') as f:
        for i, comment in enumerate(comments):
            created_at = datetime.fromisoformat(
                comment['created_at'].replace('Z', '+00:00')
            ).strftime('%Y-%m-%d')
            f.write(f'# Comment {n_comments - i} [{created_at}]: {comment["title"]}\n')
            f.write(f'{comment["url"]}\n\n')
            f.write(comment['body'])
            f.write('\n\n\n')

    print(f'{len(comments)} comments saved to: {file_path}')


def main():
    username = get_current_user()
    print(f'Fetching comments for: {username}')
    comments = fetch_github_comments(username)
    format_comments(comments)
    SESSION.cache.delete(expired=True)


if __name__ == '__main__':
    main()
