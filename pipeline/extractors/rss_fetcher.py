from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

import feedparser
import trafilatura

from pipeline.models import Article, ArticleSource
from pipeline.config import RSSSource

logger = logging.getLogger(__name__)


def fetch_rss(source: RSSSource) -> List[Article]:
    """Fetch and parse RSS feed, extract full article content."""
    logger.info(f"Fetching RSS: {source.name} ({source.url})")
    
    feed = feedparser.parse(source.url)
    if not feed.entries:
        logger.warning(f"No entries found for {source.name}")
        return []
    
    articles = []
    for entry in feed.entries[:source.max_articles]:
        url = entry.get('link', '')
        if not url:
            continue
        
        # Extract full content via trafilatura
        content_raw = _extract_content(url)
        
        # Parse publish date
        published = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass
        
        article = Article(
            url=url,
            title=entry.get('title', 'Untitled'),
            source=ArticleSource.RSS,
            content_raw=content_raw or entry.get('summary', ''),
            author=entry.get('author', ''),
            published_at=published,
            source_name=source.name,
        )
        article.compute_hash()
        articles.append(article)
    
    logger.info(f"Fetched {len(articles)} articles from {source.name}")
    return articles


def _extract_content(url: str) -> str:
    """Extract clean text content from a URL using trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            result = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                favor_precision=True,
            )
            return result or ""
    except Exception as e:
        logger.warning(f"Failed to extract {url}: {e}")
    return ""


def fetch_all_rss(sources: List[RSSSource]) -> List[Article]:
    """Fetch from all enabled RSS sources."""
    all_articles = []
    for source in sources:
        if not source.enabled:
            continue
        try:
            articles = fetch_rss(source)
            all_articles.extend(articles)
        except Exception as e:
            logger.error(f"Error fetching {source.name}: {e}")
    return all_articles
