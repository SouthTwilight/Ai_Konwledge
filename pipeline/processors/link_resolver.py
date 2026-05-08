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


def _strip_frontmatter(content: str) -> str:
    """Return the body of a Markdown file, with YAML frontmatter removed."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return content
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1:])
    return content


def _read_frontmatter_source(content: str) -> str:
    """Extract the 'source' URL from YAML frontmatter, or empty string."""
    import yaml as _yaml
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return ""
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm_str = "\n".join(lines[1:i])
            try:
                fm = _yaml.safe_load(fm_str)
                return fm.get("source", "") if isinstance(fm, dict) else ""
            except Exception:
                return ""
    return ""


def resolve_linked_articles(
    article_path: str,
    pipeline: "Pipeline",
    max_links: int = 5,
) -> dict:
    """Resolve linked articles from a processed Markdown file.

    Reads the article .md file, extracts [text](url) links from the body
    (skipping YAML frontmatter), filters by quality, fetches each linked
    article through the full pipeline (extract -> dedup -> L1 -> L2 -> write),
    then patches bidirectional [[wikilinks]].

    Args:
        article_path: Absolute or relative path to the .md file in vault.
        pipeline: Initialized Pipeline instance with dedup, L1, L2, writer.
        max_links: Maximum number of linked articles to resolve.

    Returns:
        Stats dict with keys: links_found, links_filtered_out, fetched,
        l1_passed, l2_summarized, written, errors.
    """
    from pipeline.models import Article, ArticleSource
    from pipeline.extractors.web_extractor import extract_url

    stats = {
        "links_found": 0,
        "links_filtered_out": 0,
        "fetched": 0,
        "l1_passed": 0,
        "l2_summarized": 0,
        "written": 0,
        "errors": 0,
    }

    # Read the .md file
    md_path = Path(article_path).resolve()
    if not md_path.exists():
        logger.error(f"Article file not found: {article_path}")
        stats["errors"] += 1
        return stats

    content = md_path.read_text(encoding="utf-8")

    # Strip frontmatter to get body
    body = _strip_frontmatter(content)

    # Extract and filter links
    all_links = extract_links_from_markdown(body)
    stats["links_found"] = len(all_links)

    source_url = _read_frontmatter_source(content)
    filtered_links = filter_links(all_links, source_url or "https://localhost/", max_links)
    stats["links_filtered_out"] = len(all_links) - len(filtered_links)

    if not filtered_links:
        logger.info(f"No valid external links found in {article_path}")
        return stats

    logger.info(f"Resolving {len(filtered_links)} linked articles from {article_path}")

    # Resolve each linked article
    linked_articles = []
    for text, url in filtered_links:
        try:
            logger.info(f"Fetching linked article: [{text}]({url})")
            article = extract_url(url, source_name="link-reference")
            if not article:
                logger.warning(f"Failed to extract linked article: {url}")
                stats["errors"] += 1
                continue

            stats["fetched"] += 1

            # Dedup
            new_articles = pipeline.dedup.filter_new([article])
            if not new_articles:
                logger.info(f"Linked article already processed (dedup): {url}")
                continue

            # L1 filter
            scored = pipeline.l1.filter_article(article)
            if not scored or scored.relevance_score <= 0:
                continue
            scored.content_tier = pipeline.l1._assign_tier(
                scored.relevance_score,
                pipeline.config.tier_discard_max,
                pipeline.config.tier_compressed_max,
            )
            if scored.content_tier == "discard":
                logger.info(f"Linked article discarded by L1 (score={scored.relevance_score}): {url}")
                continue
            stats["l1_passed"] += 1

            # L2 summarize
            summarized = pipeline.l2.summarize_batch([scored])
            if not summarized:
                continue
            stats["l2_summarized"] += 1

            # Write to vault
            written_path = pipeline.writer.write_article(summarized[0])
            if written_path:
                stats["written"] += 1
                linked_articles.append(summarized[0])
            else:
                stats["errors"] += 1

        except Exception as e:
            logger.error(f"Error resolving linked article {url}: {e}")
            stats["errors"] += 1

    # Patch bidirectional links
    if linked_articles:
        try:
            pipeline.writer.append_references(md_path, linked_articles)
            for ref in linked_articles:
                pipeline.writer.append_referenced_by(ref, str(md_path))
            logger.info(f"Patched {len(linked_articles)} bidirectional wikilinks")
        except Exception as e:
            logger.error(f"Failed to patch backlinks: {e}")
            stats["errors"] += 1

    logger.info(
        f"Link resolution complete: "
        f"{stats['links_found']} found, {stats['fetched']} fetched, "
        f"{stats['l1_passed']} L1 passed, {stats['written']} written, "
        f"{stats['errors']} errors"
    )
    return stats
