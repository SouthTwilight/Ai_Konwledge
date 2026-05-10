"""GitHub Release Extractor — fetch releases from starred repos via GitHub REST API.

Uses the GitHub API to list starred repositories, then fetches recent releases
for each repo. Each release is converted to an Article for pipeline processing.

Environment variables:
    GITHUB_TOKEN: GitHub personal access token (required for starred repos API)
"""
from __future__ import annotations

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


def _api_headers(token: str) -> dict:
    """Build standard GitHub API headers."""
    headers = {
        "Accept": "application/vnd.github+json",
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


def fetch_releases(
    repo: str,
    token: str = "",
    limit: int = 3,
) -> List[dict]:
    """Fetch recent releases for a single repository.

    Args:
        repo: Repository full name (owner/repo).
        token: GitHub personal access token.
        limit: Max releases to fetch per repo.

    Returns:
        List of release dicts from GitHub API.
    """
    if not token:
        token = _get_github_token()

    headers = _api_headers(token)
    url = f"{GITHUB_API}/repos/{repo}/releases"
    params = {"per_page": limit}

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 404:
            logger.debug(f"No releases for {repo}")
            return []
        if resp.status_code == 403:
            logger.warning(f"Rate limited fetching releases for {repo}")
            return []
        resp.raise_for_status()
        return resp.json()

    except httpx.HTTPError as e:
        logger.error(f"Error fetching releases for {repo}: {e}")
        return []


def _parse_release_date(date_str: str) -> Optional[datetime]:
    """Parse ISO 8601 date string from GitHub API."""
    if not date_str:
        return None
    try:
        # GitHub returns e.g. "2026-05-10T08:30:00Z"
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _release_to_article(release: dict, repo: str) -> Article:
    """Convert a GitHub release dict to an Article object."""
    tag_name = release.get("tag_name", "")
    release_name = release.get("name", "") or tag_name
    body = release.get("body", "") or ""
    html_url = release.get("html_url", "")
    published_at = _parse_release_date(release.get("published_at", ""))

    # Build a readable title: "repo: tag - name"
    short_repo = repo.split("/")[-1]
    title = f"{short_repo} {tag_name}"
    if release_name and release_name != tag_name:
        title = f"{short_repo} {tag_name}: {release_name}"

    article = Article(
        url=html_url or f"https://github.com/{repo}/releases",
        title=title,
        source=ArticleSource.GITHUB,
        content_raw=body if body else f"*Release {tag_name} — no release notes provided.*",
        author=release.get("author", {}).get("login", ""),
        published_at=published_at,
        source_name=repo,
        tags=["github", "release"],
    )
    article.compute_hash()
    return article


def extract_github_releases(
    repos: Optional[List[str]] = None,
    max_repos: int = 20,
    releases_per_repo: int = 3,
    token: str = "",
) -> List[Article]:
    """Main entry point: fetch releases from starred repos → Articles.

    Args:
        repos: Optional list of specific repos to check. If None, uses starred repos.
        max_repos: Max starred repos to process (ignored if repos is provided).
        releases_per_repo: Max releases to fetch per repo.
        token: GitHub personal access token (falls back to GITHUB_TOKEN env var).

    Returns:
        List of Article objects, one per release found.
    """
    if not token:
        token = _get_github_token()

    # Resolve repos
    if repos is None:
        repos = get_starred_repos(token=token, max_repos=max_repos)

    if not repos:
        logger.warning("No repos to check for releases")
        return []

    logger.info(f"Checking releases for {len(repos)} repos")

    articles = []
    for repo in repos:
        releases = fetch_releases(repo, token=token, limit=releases_per_repo)
        for release in releases:
            # Skip drafts
            if release.get("draft", False):
                continue
            # Skip prereleases (configurable in future)
            if release.get("prerelease", False):
                continue
            article = _release_to_article(release, repo)
            articles.append(article)

    logger.info(f"Found {len(articles)} releases from {len(repos)} repos")
    return articles
