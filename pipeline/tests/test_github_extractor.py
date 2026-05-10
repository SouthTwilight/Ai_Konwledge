"""Tests for GitHub Release Extractor."""
from __future__ import annotations

import json
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from pipeline.models import ArticleSource


# --- Fixtures ---

MOCK_STARRED_RESPONSE = [
    {"full_name": "user/repo-a", "stargazers_count": 100},
    {"full_name": "user/repo-b", "stargazers_count": 50},
]

MOCK_RELEASES_REPO_A = [
    {
        "tag_name": "v1.2.0",
        "name": "Version 1.2.0",
        "body": "## What's New\n- Feature A\n- Bug fix B",
        "html_url": "https://github.com/user/repo-a/releases/tag/v1.2.0",
        "published_at": "2026-05-10T08:30:00Z",
        "draft": False,
        "prerelease": False,
        "author": {"login": "dev-user"},
    },
    {
        "tag_name": "v1.1.0",
        "name": "v1.1.0",
        "body": "Minor fixes.",
        "html_url": "https://github.com/user/repo-a/releases/tag/v1.1.0",
        "published_at": "2026-05-01T12:00:00Z",
        "draft": False,
        "prerelease": False,
        "author": {"login": "dev-user"},
    },
]

MOCK_RELEASES_REPO_B = [
    {
        "tag_name": "v0.9.0",
        "name": "",
        "body": "",
        "html_url": "https://github.com/user/repo-b/releases/tag/v0.9.0",
        "published_at": "2026-04-20T10:00:00Z",
        "draft": False,
        "prerelease": False,
        "author": {"login": "another-dev"},
    },
]

MOCK_RELEASE_DRAFT = {
    "tag_name": "v2.0.0-rc1",
    "name": "Release Candidate",
    "body": "Draft notes",
    "html_url": "https://github.com/user/repo-c/releases/tag/v2.0.0-rc1",
    "published_at": "2026-05-09T00:00:00Z",
    "draft": True,
    "prerelease": False,
    "author": {"login": "dev-user"},
}

MOCK_RELEASE_PRERELEASE = {
    "tag_name": "v2.0.0-beta",
    "name": "Beta",
    "body": "Beta notes",
    "html_url": "https://github.com/user/repo-c/releases/tag/v2.0.0-beta",
    "published_at": "2026-05-08T00:00:00Z",
    "draft": False,
    "prerelease": True,
    "author": {"login": "dev-user"},
}


def _mock_httpx_response(json_data, status_code=200, headers=None):
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


# --- Tests: get_starred_repos ---

def test_get_starred_repos_basic():
    from pipeline.extractors.github_extractor import get_starred_repos

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(MOCK_STARRED_RESPONSE)

        repos = get_starred_repos(token="fake-token", max_repos=10)
        assert repos == ["user/repo-a", "user/repo-b"]
        mock_get.assert_called_once()


def test_get_starred_repos_max_limit():
    from pipeline.extractors.github_extractor import get_starred_repos

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(MOCK_STARRED_RESPONSE)

        repos = get_starred_repos(token="fake-token", max_repos=1)
        assert repos == ["user/repo-a"]


def test_get_starred_repos_unauthorized():
    from pipeline.extractors.github_extractor import get_starred_repos

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response({}, status_code=401)

        repos = get_starred_repos(token="bad-token")
        assert repos == []


def test_get_starred_repos_empty():
    from pipeline.extractors.github_extractor import get_starred_repos

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response([])

        repos = get_starred_repos(token="fake-token")
        assert repos == []


# --- Tests: fetch_releases ---

def test_fetch_releases_basic():
    from pipeline.extractors.github_extractor import fetch_releases

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(MOCK_RELEASES_REPO_A)

        releases = fetch_releases("user/repo-a", token="fake-token")
        assert len(releases) == 2
        assert releases[0]["tag_name"] == "v1.2.0"


def test_fetch_releases_not_found():
    from pipeline.extractors.github_extractor import fetch_releases

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response({"message": "Not Found"}, status_code=404)

        releases = fetch_releases("user/no-releases", token="fake-token")
        assert releases == []


def test_fetch_releases_rate_limited():
    from pipeline.extractors.github_extractor import fetch_releases

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response({}, status_code=403)

        releases = fetch_releases("user/repo-a", token="fake-token")
        assert releases == []


# --- Tests: _release_to_article ---

def test_release_to_article_full():
    from pipeline.extractors.github_extractor import _release_to_article

    article = _release_to_article(MOCK_RELEASES_REPO_A[0], "user/repo-a")
    assert article.source == ArticleSource.GITHUB
    assert "repo-a" in article.title
    assert "v1.2.0" in article.title
    assert "Feature A" in article.content_raw
    assert article.url == "https://github.com/user/repo-a/releases/tag/v1.2.0"
    assert article.source_name == "user/repo-a"
    assert article.author == "dev-user"
    assert article.published_at is not None
    assert article.tags == ["github", "release"]
    assert article.content_hash != ""


def test_release_to_article_empty_body():
    from pipeline.extractors.github_extractor import _release_to_article

    article = _release_to_article(MOCK_RELEASES_REPO_B[0], "user/repo-b")
    assert article.source == ArticleSource.GITHUB
    assert "v0.9.0" in article.title
    assert "no release notes" in article.content_raw.lower()


def test_release_to_article_name_equals_tag():
    """When name == tag_name, title should not duplicate."""
    from pipeline.extractors.github_extractor import _release_to_article

    article = _release_to_article(MOCK_RELEASES_REPO_A[1], "user/repo-a")
    assert article.source == ArticleSource.GITHUB
    # Title should be "repo-a v1.1.0", not "repo-a v1.1.0: v1.1.0"
    assert article.title.count("v1.1.0") == 1


# --- Tests: extract_github_releases (integration) ---

def test_extract_github_releases_from_starred():
    from pipeline.extractors.github_extractor import extract_github_releases

    def mock_get(url, **kwargs):
        if "/user/starred" in url:
            return _mock_httpx_response(MOCK_STARRED_RESPONSE)
        if "repo-a" in url:
            return _mock_httpx_response(MOCK_RELEASES_REPO_A)
        if "repo-b" in url:
            return _mock_httpx_response(MOCK_RELEASES_REPO_B)
        return _mock_httpx_response([])

    with patch("pipeline.extractors.github_extractor.httpx.get", side_effect=mock_get):
        articles = extract_github_releases(token="fake-token")

        assert len(articles) == 3  # 2 from repo-a + 1 from repo-b
        assert all(a.source == ArticleSource.GITHUB for a in articles)
        assert all(a.content_hash for a in articles)


def test_extract_github_releases_specific_repos():
    from pipeline.extractors.github_extractor import extract_github_releases

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(MOCK_RELEASES_REPO_A)

        articles = extract_github_releases(
            repos=["user/repo-a"],
            token="fake-token",
        )
        assert len(articles) == 2


def test_extract_github_releases_skips_draft_and_prerelease():
    from pipeline.extractors.github_extractor import extract_github_releases

    releases = [MOCK_RELEASE_DRAFT, MOCK_RELEASE_PRERELEASE, MOCK_RELEASES_REPO_A[0]]

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(releases)

        articles = extract_github_releases(
            repos=["user/repo-c"],
            token="fake-token",
        )
        # Only the non-draft, non-prerelease release should be included
        assert len(articles) == 1
        assert "v1.2.0" in articles[0].title


def test_extract_github_releases_no_token():
    """Should still work but with warnings and empty starred list."""
    from pipeline.extractors.github_extractor import extract_github_releases

    with patch.dict(os.environ, {"GITHUB_TOKEN": ""}):
        with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
            mock_get.return_value = _mock_httpx_response({"message": "Requires authentication"}, status_code=401)

            articles = extract_github_releases(token="")
            assert articles == []


def test_extract_github_releases_no_repos():
    from pipeline.extractors.github_extractor import extract_github_releases

    with patch("pipeline.extractors.github_extractor.get_starred_repos", return_value=[]):
        articles = extract_github_releases(token="fake-token")
        assert articles == []
