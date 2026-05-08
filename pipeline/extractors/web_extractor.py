from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

import trafilatura

from pipeline.models import Article, ArticleSource

logger = logging.getLogger(__name__)


def extract_url(url: str, source_name: str = "web") -> Optional[Article]:
    """Extract article content from a single URL."""
    logger.info(f"Extracting URL: {url}")

    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.warning(f"Failed to download: {url}")
            return None

        # Extract clean text
        content = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
            include_links=True,
        )
        if not content:
            logger.warning(f"Failed to extract content: {url}")
            return None

        # Try to extract metadata
        metadata = trafilatura.extract(
            downloaded,
            output_format='json',
            include_comments=False,
        )

        title = ""
        author = ""
        published = None

        if metadata:
            try:
                import json
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

        article = Article(
            url=url,
            title=title or url.split('/')[-1][:50] or "Untitled",
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
    """Extract multiple URLs into Article objects."""
    articles = []
    for url in urls:
        article = extract_url(url, source_name)
        if article:
            articles.append(article)
    return articles
