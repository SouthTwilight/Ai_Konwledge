"""Web Content Extractor — extract articles from URLs.

Uses trafilatura for static content extraction.
Includes title fallback chain: trafilatura → HTML <title> → <h1> → URL slug.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import List, Optional

import trafilatura

from pipeline.models import Article, ArticleSource

logger = logging.getLogger(__name__)


def _extract_title_from_html(html: str) -> str:
    """Extract title from HTML using fallback chain: <title> → <h1> → empty."""
    # Try <title> tag
    match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        # Clean up common suffixes like " - Blog Name"
        title = re.sub(r'\s*[|\-–—].*$', '', title)
        if title:
            return title

    # Try first <h1>
    match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    if match:
        # Strip inner HTML tags
        h1 = re.sub(r'<[^>]+>', '', match.group(1)).strip()
        if h1:
            return h1

    return ""


def extract_url(url: str, source_name: str = "web") -> Optional[Article]:
    """Extract article content from a single URL.

    Args:
        url: URL to extract.
        source_name: Name of the source for metadata.

    Returns:
        Article object, or None on failure.
    """
    logger.info(f"Extracting URL: {url}")

    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.warning(f"Failed to download: {url}")
            return None

        content = None
        title = ""
        author = ""
        published = None

        # Extract clean text
        content = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
            include_links=True,
        )

        # Extract metadata
        metadata = trafilatura.extract(
            downloaded,
            output_format='json',
            include_comments=False,
        )

        if metadata:
            try:
                meta = json.loads(metadata)
                title = meta.get('title', '')
                author = meta.get('author', '')
                date_str = meta.get('date', '')
                if date_str:
                    try:
                        published = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass
            except (json.JSONDecodeError, TypeError):
                pass

        # Title fallback chain: trafilatura → HTML <title> → <h1>
        if not title and downloaded:
            title = _extract_title_from_html(downloaded)

        if not content:
            logger.warning(f"Failed to extract content: {url}")
            return None

        # Final title fallback: URL slug
        if not title:
            slug = url.rstrip('/').split('/')[-1]
            title = slug[:50].replace('-', ' ').replace('_', ' ') or "Untitled"

        article = Article(
            url=url,
            title=title,
            source=ArticleSource.WEB_URL,
            content_raw=content,
            author=author,
            published_at=published,
            source_name=source_name,
        )
        article.compute_hash()
        return article

    except Exception as e:
        logger.error(f"Error extracting {url}: {e}")
        return None


def extract_urls(urls: List[str], source_name: str = "web") -> List[Article]:
    """Extract multiple URLs into Article objects.

    Args:
        urls: List of URLs to extract.
        source_name: Name of the source.

    Returns:
        List of successfully extracted Article objects.
    """
    articles = []
    for url in urls:
        article = extract_url(url, source_name)
        if article:
            articles.append(article)
    return articles
