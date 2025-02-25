import pytest
from get_container_tags import fetch_tags


@pytest.mark.parametrize(
    'repo, expected_tag',
    [
        ('ghcr.io/home-assistant/home-assistant', '2025.2.5 - 2025-02-21'),
        ('public.ecr.aws/aws-dynamodb-local/aws-dynamodb-local', '2.0.0 - 2023-10-03'),
        ('grafana/grafana', '9.0.0 - 2022-06-14'),
        ('redis', '7.0.0 - 2022-05-29'),
    ],
)
def test_fetch_tags(repo, expected_tag):
    assert expected_tag in fetch_tags(repo)
