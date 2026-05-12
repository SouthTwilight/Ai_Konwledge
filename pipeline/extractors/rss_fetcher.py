from __future__ import annotations

import logging
import re
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
        
        # 1. Try trafilatura first (works for most feeds)
        content_raw = _extract_content(url)
        
        # 2. If trafilatura failed, use feed-provided content
        #    (covers WeWe RSS fulltext, newsletters, etc.)
        if not content_raw or len(content_raw) < 100:
            feed_content = _get_feed_content(entry)
            if feed_content and len(feed_content) > len(content_raw):
                content_raw = feed_content
        
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
            content_raw=content_raw,
            author=entry.get('author', ''),
            published_at=published,
            source_name=source.name,
        )
        article.compute_hash()
        articles.append(article)
    
    logger.info(f"Fetched {len(articles)} articles from {source.name}")
    return articles


def _get_feed_content(entry) -> str:
    """Extract content from feed entry when trafilatura cannot.
    
    Checks multiple feed fields in priority order:
    1. Atom <content> (entry.content[0].value) — WeWe RSS fulltext
    2. RSS <content:encoded> (entry.content[0].value)
    3. RSS <description> (entry.description) — if >200 chars, likely full content
    4. RSS/Atom <summary> (entry.summary) — last resort, usually just a blurb
    """
    # Atom/RSS <content> or <content:encoded>
    if hasattr(entry, 'content') and entry.content:
        content_val = entry.content[0].get('value', '')
        if content_val and len(content_val) > 100:
            return _html_to_text(content_val)
    
    # RSS <description> (often contains HTML)
    desc = entry.get('description', '')
    if desc and len(desc) > 200:  # likely full content, not just a blurb
        return _html_to_text(desc)
    
    # <summary> — last resort, usually just a short blurb
    return entry.get('summary', '')


def _html_to_text(html: str) -> str:
    """Convert HTML to plain text using trafilatura's extractor.
    Falls back to stripped tags if trafilatura fails."""
    if not html:
        return ""
    try:
        text = trafilatura.extract(
            html, include_comments=False, include_tables=True,
            favor_precision=True,
        )
        if text and len(text) > 50:
            return text
    except Exception:
        pass
    # Fallback: strip all HTML tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


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
