"""Link Resolver — Extract, filter, and resolve hyperlinks from processed articles.

Scans a processed article's Markdown for [text](url) hyperlinks,
filters out noise (same-domain, social, non-http), fetches linked
articles, runs them through the pipeline, and creates bidirectional
[[wikilinks]] between the source and referenced articles.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Tuple, TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from pipeline.main import Pipeline

logger = logging.getLogger(__name__)

# Domains to exclude — social media, video platforms, messaging apps
SOCIAL_DOMAINS = {
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "weibo.com", "t.me", "discord.com",
    "youtube.com", "youtu.be", "bilibili.com",
}

# Link pattern: [text](url) but NOT ![text](url) — exclude image embeds
LINK_RE = re.compile(r'(?<!\!)\[([^\]]+)\]\((https?://[^)]+)\)')


def extract_links_from_markdown(content: str) -> List[Tuple[str, str]]:
    """Extract all [text](url) Markdown links from content.

    Returns list of (link_text, url) tuples in order of appearance.
    Excludes image embeds (![alt](url)).
    """
    if not content:
        return []
    return [(m.group(1), m.group(2)) for m in LINK_RE.finditer(content)]


def filter_links(
    links: List[Tuple[str, str]],
    source_url: str,
    max_links: int = 5,
) -> List[Tuple[str, str]]:
    """Filter extracted links to keep only valuable reference URLs.

    Excludes:
    - Same-domain URLs (internal navigation)
    - Non-http/https protocols (mailto, javascript, tel)
    - Anchor-only links (#section)
    - Social media domains
    - Duplicates (by URL)

    Returns at most max_links results.
    """
    source_domain = urlparse(source_url).netloc.lower()
    seen_urls = set()
    result = []

    for text, url in links:
        url = url.strip()

        # Exclude non-http protocols
        if not url.startswith(("http://", "https://")):
            continue

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Exclude same-domain
        if domain == source_domain:
            continue

        # Exclude anchor-only or bare domain links with no path content
        if not parsed.path or parsed.path == "/":
            if not parsed.query:
                continue

        # Exclude social media
        if domain in SOCIAL_DOMAINS:
            continue

        # Deduplicate
        if url in seen_urls:
            continue
        seen_urls.add(url)

        result.append((text, url))
        if len(result) >= max_links:
            break

    return result
