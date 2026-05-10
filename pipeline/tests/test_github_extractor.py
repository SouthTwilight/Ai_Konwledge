"""Tests for GitHub Project Analyzer."""
from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest

from pipeline.models import ArticleSource


# --- Fixtures ---

MOCK_STARRED_RESPONSE = [
    {"full_name": "user/project-alpha", "stargazers_count": 5000},
    {"full_name": "user/project-beta", "stargazers_count": 200},
    {"full_name": "user/project-fork", "stargazers_count": 50},
]

MOCK_REPO_INFO_ALPHA = {
    "description": "AI-powered code review tool",
    "topics": ["ai", "code-review", "llm"],
    "language": "Python",
    "stargazers_count": 5000,
    "html_url": "https://github.com/user/project-alpha",
    "homepage": "https://project-alpha.dev",
    "fork": False,
}

MOCK_REPO_INFO_BETA = {
    "description": "Fast RSS parser library",
    "topics": ["rss", "parser"],
    "language": "Rust",
    "stargazers_count": 200,
    "html_url": "https://github.com/user/project-beta",
    "homepage": "",
    "fork": False,
}

MOCK_REPO_INFO_FORK = {
    "description": "Forked project",
    "topics": [],
    "language": "Go",
    "stargazers_count": 50,
    "html_url": "https://github.com/user/project-fork",
    "homepage": "",
    "fork": True,
}

MOCK_REPO_INFO_EMPTY = {
    "description": "",
    "topics": [],
    "language": "",
    "stargazers_count": 0,
    "html_url": "https://github.com/user/project-empty",
    "homepage": "",
    "fork": False,
}

README_ALPHA = """# Project Alpha

AI-powered code review tool that integrates with GitHub PRs.

## Features
- Automatic code review suggestions
- Security vulnerability detection
- Performance optimization tips

## Installation
pip install project-alpha
"""

README_BETA = """# Project Beta

A fast RSS/Atom parser written in Rust.

## Usage
```rust
use project_beta::Parser;
let feed = Parser::parse(rss_text);
```
"""


def _mock_httpx_response(text="", json_data=None, status_code=200, headers=None):
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    if json_data is not None:
        resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


# --- Tests: get_starred_repos ---

def test_get_starred_repos_basic():
    from pipeline.extractors.github_extractor import get_starred_repos

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(json_data=MOCK_STARRED_RESPONSE)

        repos = get_starred_repos(token="fake-token", max_repos=10)
        assert repos == ["user/project-alpha", "user/project-beta", "user/project-fork"]
        mock_get.assert_called_once()


def test_get_starred_repos_max_limit():
    from pipeline.extractors.github_extractor import get_starred_repos

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(json_data=MOCK_STARRED_RESPONSE)

        repos = get_starred_repos(token="fake-token", max_repos=1)
        assert repos == ["user/project-alpha"]


def test_get_starred_repos_unauthorized():
    from pipeline.extractors.github_extractor import get_starred_repos

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(json_data={}, status_code=401)

        repos = get_starred_repos(token="bad-token")
        assert repos == []


def test_get_starred_repos_empty():
    from pipeline.extractors.github_extractor import get_starred_repos

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(json_data=[])

        repos = get_starred_repos(token="fake-token")
        assert repos == []


# --- Tests: fetch_readme ---

def test_fetch_readme_success():
    from pipeline.extractors.github_extractor import fetch_readme

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(text=README_ALPHA, status_code=200)

        content = fetch_readme("user/project-alpha", token="fake-token")
        assert "AI-powered code review" in content
        assert "pip install" in content


def test_fetch_readme_not_found():
    from pipeline.extractors.github_extractor import fetch_readme

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(text="", status_code=404)

        content = fetch_readme("user/no-readme", token="fake-token")
        assert content == ""


def test_fetch_readme_rate_limited():
    from pipeline.extractors.github_extractor import fetch_readme

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(text="", status_code=403)

        content = fetch_readme("user/repo", token="fake-token")
        assert content == ""


# --- Tests: fetch_repo_info ---

def test_fetch_repo_info_success():
    from pipeline.extractors.github_extractor import fetch_repo_info

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(json_data=MOCK_REPO_INFO_ALPHA)

        info = fetch_repo_info("user/project-alpha", token="fake-token")
        assert info["description"] == "AI-powered code review tool"
        assert info["language"] == "Python"
        assert info["stars"] == 5000
        assert info["fork"] is False
        assert "ai" in info["topics"]


def test_fetch_repo_info_not_found():
    from pipeline.extractors.github_extractor import fetch_repo_info

    with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
        mock_get.return_value = _mock_httpx_response(json_data={"message": "Not Found"}, status_code=404)

        info = fetch_repo_info("user/nonexistent", token="fake-token")
        assert info == {}


# --- Tests: _repo_to_article ---

def test_repo_to_article_with_readme():
    from pipeline.extractors.github_extractor import _repo_to_article

    article = _repo_to_article("user/project-alpha", MOCK_REPO_INFO_ALPHA, README_ALPHA)
    assert article.source == ArticleSource.GITHUB
    assert "project-alpha" in article.title
    assert "AI-powered code review tool" in article.title
    assert "AI-powered code review" in article.content_raw
    assert article.url == "https://github.com/user/project-alpha"
    assert article.source_name == "user/project-alpha"
    assert article.author == "user"
    assert "ai" in article.tags
    assert "python" in article.tags
    assert "github" in article.tags
    assert article.content_hash != ""


def test_repo_to_article_no_description():
    from pipeline.extractors.github_extractor import _repo_to_article

    info = {"description": "", "topics": [], "language": "", "stars": 0,
            "html_url": "https://github.com/user/plain", "homepage": "", "fork": False}
    article = _repo_to_article("user/plain", info, "Some README content")
    assert article.title == "plain"
    assert "Some README content" in article.content_raw


def test_repo_to_article_tags_capped():
    from pipeline.extractors.github_extractor import _repo_to_article

    info = {"description": "Test", "topics": ["a", "b", "c", "d", "e", "f", "g"],
            "language": "Python", "stars": 0,
            "html_url": "https://github.com/user/taggy", "homepage": "", "fork": False}
    article = _repo_to_article("user/taggy", info, "README")
    assert len(article.tags) <= 8


def test_repo_to_article_no_readme():
    from pipeline.extractors.github_extractor import _repo_to_article

    article = _repo_to_article("user/project-beta", MOCK_REPO_INFO_BETA, "")
    assert article.source == ArticleSource.GITHUB
    assert "Fast RSS parser" in article.title
    assert "Fast RSS parser" in article.content_raw


# --- Tests: extract_github_projects (integration) ---

def test_extract_github_projects_from_starred():
    from pipeline.extractors.github_extractor import extract_github_projects

    def mock_get(url, **kwargs):
        if "/user/starred" in url:
            return _mock_httpx_response(json_data=MOCK_STARRED_RESPONSE)
        if "project-alpha" in url and "/readme" in url:
            return _mock_httpx_response(text=README_ALPHA, status_code=200)
        if "project-alpha" in url and "/readme" not in url:
            return _mock_httpx_response(json_data=MOCK_REPO_INFO_ALPHA)
        if "project-beta" in url and "/readme" in url:
            return _mock_httpx_response(text=README_BETA, status_code=200)
        if "project-beta" in url and "/readme" not in url:
            return _mock_httpx_response(json_data=MOCK_REPO_INFO_BETA)
        if "project-fork" in url and "/readme" in url:
            return _mock_httpx_response(text="Fork README", status_code=200)
        if "project-fork" in url and "/readme" not in url:
            return _mock_httpx_response(json_data=MOCK_REPO_INFO_FORK)
        return _mock_httpx_response(text="", status_code=404)

    with patch("pipeline.extractors.github_extractor.httpx.get", side_effect=mock_get):
        articles = extract_github_projects(token="fake-token")

        # 3 starred, but project-fork is a fork → 2 articles
        assert len(articles) == 2
        assert all(a.source == ArticleSource.GITHUB for a in articles)
        assert all(a.content_hash for a in articles)
        # Alpha should have AI tags
        alpha = [a for a in articles if "alpha" in a.source_name][0]
        assert "ai" in alpha.tags


def test_extract_github_projects_specific_repos():
    from pipeline.extractors.github_extractor import extract_github_projects

    def mock_get(url, **kwargs):
        if "/readme" in url:
            return _mock_httpx_response(text=README_ALPHA, status_code=200)
        return _mock_httpx_response(json_data=MOCK_REPO_INFO_ALPHA)

    with patch("pipeline.extractors.github_extractor.httpx.get", side_effect=mock_get):
        articles = extract_github_projects(
            repos=["user/project-alpha"],
            token="fake-token",
        )
        assert len(articles) == 1
        assert "project-alpha" in articles[0].title


def test_extract_github_projects_skips_empty_repos():
    from pipeline.extractors.github_extractor import extract_github_projects

    def mock_get(url, **kwargs):
        if "/readme" in url:
            return _mock_httpx_response(text="", status_code=404)
        return _mock_httpx_response(json_data=MOCK_REPO_INFO_EMPTY)

    with patch("pipeline.extractors.github_extractor.httpx.get", side_effect=mock_get):
        articles = extract_github_projects(
            repos=["user/project-empty"],
            token="fake-token",
        )
        assert len(articles) == 0


def test_extract_github_projects_no_token():
    from pipeline.extractors.github_extractor import extract_github_projects

    with patch.dict(os.environ, {"GITHUB_TOKEN": ""}):
        with patch("pipeline.extractors.github_extractor.httpx.get") as mock_get:
            mock_get.return_value = _mock_httpx_response(json_data={"message": "Requires auth"}, status_code=401)

            articles = extract_github_projects(token="")
            assert articles == []


def test_extract_github_projects_no_repos():
    from pipeline.extractors.github_extractor import extract_github_projects

    with patch("pipeline.extractors.github_extractor.get_starred_repos", return_value=[]):
        articles = extract_github_projects(token="fake-token")
        assert articles == []
