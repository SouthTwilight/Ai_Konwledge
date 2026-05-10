"""GitHub Project Analyzer — fetch and analyze starred repos' README.

Analyzes GitHub repositories by fetching their README and metadata,
producing Article objects that describe what each project does.

Environment variables:
    GITHUB_TOKEN: GitHub personal access token (required for starred repos API)
"""
from __future__ import annotations

import base64
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from pipeline.models import Article, ArticleSource

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
DEFAULT_PER_PAGE = 30


def _get_github_token() -> str:
    """Get GitHub token from environment."""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        logger.warning("GITHUB_TOKEN not set — API rate limit will be 60/hr")
    return token


def _api_headers(token: str, accept: str = "application/vnd.github+json") -> dict:
    """Build standard GitHub API headers."""
    headers = {
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_starred_repos(
    token: str = "",
    max_repos: int = 20,
) -> List[str]:
    """Fetch starred repository full names (owner/repo).

    Args:
        token: GitHub personal access token.
        max_repos: Maximum number of repos to return.

    Returns:
        List of 'owner/repo' strings.
    """
    if not token:
        token = _get_github_token()

    headers = _api_headers(token)
    repos = []
    page = 1

    while len(repos) < max_repos:
        url = f"{GITHUB_API}/user/starred"
        params = {"per_page": min(DEFAULT_PER_PAGE, max_repos - len(repos)), "page": page}

        try:
            resp = httpx.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code == 401:
                logger.error("GitHub API: unauthorized — check GITHUB_TOKEN")
                return repos
            if resp.status_code == 403:
                logger.error("GitHub API: rate limited")
                return repos
            resp.raise_for_status()

            data = resp.json()
            if not data:
                break

            for item in data:
                repos.append(item["full_name"])
                if len(repos) >= max_repos:
                    break

            # Check if there are more pages
            link_header = resp.headers.get("link", "")
            if 'rel="next"' not in link_header:
                break
            page += 1

        except httpx.HTTPError as e:
            logger.error(f"GitHub API error fetching starred repos: {e}")
            break

    logger.info(f"Fetched {len(repos)} starred repos")
    return repos[:max_repos]


def fetch_readme(repo: str, token: str = "") -> str:
    """Fetch README content for a repository.

    Tries raw Markdown first, falls back to base64-decoded content.

    Args:
        repo: Repository full name (owner/repo).
        token: GitHub personal access token.

    Returns:
        README text content, or empty string on failure.
    """
    if not token:
        token = _get_github_token()

    # Try raw Markdown endpoint first
    headers = _api_headers(token, accept="application/vnd.github.raw+json")
    url = f"{GITHUB_API}/repos/{repo}/readme"

    try:
        resp = httpx.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.text
        if resp.status_code == 404:
            logger.debug(f"No README found for {repo}")
            return ""
        if resp.status_code == 403:
            logger.warning(f"Rate limited fetching README for {repo}")
            return ""
        resp.raise_for_status()
        return resp.text

    except httpx.HTTPError as e:
        logger.error(f"Error fetching README for {repo}: {e}")
        return ""


def fetch_repo_info(repo: str, token: str = "") -> dict:
    """Fetch repository metadata.

    Args:
        repo: Repository full name (owner/repo).
        token: GitHub personal access token.

    Returns:
        Dict with description, topics, language, stars, html_url, etc.
    """
    if not token:
        token = _get_github_token()

    headers = _api_headers(token)
    url = f"{GITHUB_API}/repos/{repo}"

    try:
        resp = httpx.get(url, headers=headers, timeout=30)
        if resp.status_code == 403:
            logger.warning(f"Rate limited fetching info for {repo}")
            return {}
        if resp.status_code == 404:
            logger.debug(f"Repo not found: {repo}")
            return {}
        resp.raise_for_status()
        data = resp.json()
        return {
            "description": data.get("description", ""),
            "topics": data.get("topics", []),
            "language": data.get("language", ""),
            "stars": data.get("stargazers_count", 0),
            "html_url": data.get("html_url", f"https://github.com/{repo}"),
            "homepage": data.get("homepage", ""),
            "fork": data.get("fork", False),
        }

    except httpx.HTTPError as e:
        logger.error(f"Error fetching info for {repo}: {e}")
        return {}


def _repo_to_article(repo: str, info: dict, readme: str) -> Article:
    """Convert repo info + README into an Article object.

    Args:
        repo: Repository full name (owner/repo).
        info: Repository metadata from fetch_repo_info.
        readme: README content.

    Returns:
        Article representing this project.
    """
    short_name = repo.split("/")[-1]
    description = info.get("description", "")
    topics = info.get("topics", [])
    language = info.get("language", "")
    stars = info.get("stars", 0)
    html_url = info.get("html_url", f"https://github.com/{repo}")

    # Title: "repo-name: description" or just "repo-name"
    if description:
        title = f"{short_name}: {description}"
    else:
        title = short_name

    # Tags from GitHub topics + language
    tags = list(topics)
    if language and language.lower() not in [t.lower() for t in tags]:
        tags.append(language.lower())
    if "github" not in tags:
        tags.append("github")

    # Content: README or fallback to description
    content_raw = readme if readme else (description or f"*No README available for {repo}.*")

    article = Article(
        url=html_url,
        title=title,
        source=ArticleSource.GITHUB,
        content_raw=content_raw,
        author=repo.split("/")[0],
        published_at=datetime.now(timezone.utc),
        source_name=repo,
        tags=tags[:8],  # Cap at 8 tags
    )
    article.compute_hash()
    return article


def extract_github_projects(
    repos: Optional[List[str]] = None,
    max_repos: int = 20,
    token: str = "",
) -> List[Article]:
    """Main entry point: analyze GitHub projects → Articles.

    Fetches README and metadata for each repo, producing Article objects
    that describe what each project does.

    Args:
        repos: Optional list of specific repos (owner/repo).
               If None, uses starred repos.
        max_repos: Max starred repos to process (ignored if repos is provided).
        token: GitHub personal access token (falls back to GITHUB_TOKEN env var).

    Returns:
        List of Article objects, one per repo with a README.
    """
    if not token:
        token = _get_github_token()

    # Resolve repos
    if repos is None:
        repos = get_starred_repos(token=token, max_repos=max_repos)

    if not repos:
        logger.warning("No repos to analyze")
        return []

    logger.info(f"Analyzing {len(repos)} repos")

    articles = []
    for repo in repos:
        info = fetch_repo_info(repo, token=token)

        # Skip forks unless explicitly requested
        if info.get("fork", False):
            logger.debug(f"Skipping fork: {repo}")
            continue

        readme = fetch_readme(repo, token=token)

        # Skip repos with no README and no description
        if not readme and not info.get("description"):
            logger.debug(f"Skipping repo with no content: {repo}")
            continue

        article = _repo_to_article(repo, info, readme)
        articles.append(article)

    logger.info(f"Generated {len(articles)} project articles from {len(repos)} repos")
    return articles
