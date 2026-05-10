"""Obsidian Formatter — Convert processed articles to Obsidian Markdown.

Generates files with YAML frontmatter, WikiLinks for related topics,
and writes to the appropriate vault subdirectory.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml

from pipeline.models import Article, ArticleSource, ProcessingLevel

logger = logging.getLogger(__name__)

# Map source types to vault subdirectories
SOURCE_DIRS = {
    ArticleSource.RSS: "2-Articles",
    ArticleSource.WEB_URL: "2-Articles",
    ArticleSource.FEISHU: "2-Articles",
    ArticleSource.GITHUB: "3-GitHub",
    ArticleSource.EMAIL: "4-Newsletters",
    ArticleSource.MANUAL: "0-Inbox",
}


def _slugify(text: str) -> str:
    """Create a filesystem-safe slug from text."""
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[\s_]+', '-', slug).strip('-')
    # Truncate to reasonable length
    return slug[:80] or "untitled"


class ObsidianWriter:
    """Write processed articles as Obsidian-compatible Markdown files."""

    def __init__(self, vault_path: Path):
        self.vault_path = Path(vault_path)

    def _get_target_dir(self, article: Article) -> Path:
        """Determine the target subdirectory based on article source + date.
        
        GitHub articles are organized by repo name (not date) since they
        represent project analyses, not time-series events.
        """
        subdir = SOURCE_DIRS.get(article.source, "0-Inbox")
        if article.source == ArticleSource.GITHUB:
            # Use repo name as subdirectory: 3-GitHub/{repo-name}/
            repo_name = article.source_name.split("/")[-1] if article.source_name else "unknown"
            return self.vault_path / subdir / repo_name
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self.vault_path / subdir / date_str

    def _build_frontmatter(self, article: Article) -> str:
        """Build YAML frontmatter for the article."""
        fm = {
            "title": article.title,
            "source": article.url,
            "source_name": article.source_name,
            "author": article.author or None,
            "date_processed": datetime.now().strftime("%Y-%m-%d"),
            "date_published": (
                article.published_at.strftime("%Y-%m-%d")
                if article.published_at else None
            ),
            "tags": article.tags or [],
            "relevance": article.relevance_score,
            "level": article.processing_level.value,
            "hash": article.content_hash,
        }
        # Remove None values
        fm = {k: v for k, v in fm.items() if v is not None}

        return yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def _build_body(self, article: Article) -> str:
        """Build the Markdown body content."""
        parts = []

        # Header
        parts.append(f"# {article.title}\n")

        # Meta line
        meta_parts = [f"Source: [{article.source_name}]({article.url})"]
        if article.author:
            meta_parts.append(f"Author: {article.author}")
        parts.append("> " + " | ".join(meta_parts) + "\n")

        # Summary
        if article.content_summary:
            parts.append("## Summary\n")
            parts.append(article.content_summary + "\n")

        # Key Points
        if article.key_points:
            parts.append("## Key Points\n")
            for point in article.key_points:
                parts.append(f"- {point}")
            parts.append("")

        # L3 Deep Analysis
        if article.content_deep:
            parts.append("## Deep Analysis\n")
            parts.append(article.content_deep + "\n")

        # Related Topics as WikiLinks
        if article.related_topics:
            parts.append("## Related\n")
            links = " ".join(f"[[{t}]]" for t in article.related_topics)
            parts.append(links + "\n")

        # Tags section
        if article.tags:
            parts.append("## Tags\n")
            parts.append(" ".join(f"#{t}" for t in article.tags) + "\n")

        # Raw content section — tier-dependent
        if article.content_tier == "detailed" and article.content_raw:
            parts.append("## 原文内容\n")
            parts.append(article.content_raw + "\n")
        elif article.content_raw:
            word_count = len(article.content_raw.split())
            parts.append(f"\n---\n*原文: {word_count} words*\n")

        # Personal notes placeholder
        parts.append("\n## Personal Notes\n")

        return "\n".join(parts)

    def format_article(self, article: Article) -> tuple[str, str]:
        """Format an article to Obsidian Markdown.

        Returns:
            (filename, content) tuple
        """
        frontmatter = self._build_frontmatter(article)
        body = self._build_body(article)

        score_prefix = f"[S{article.relevance_score}] " if article.relevance_score > 0 else ""
        filename = f"{score_prefix}{_slugify(article.title)}.md"
        content = f"---\n{frontmatter}---\n{body}"

        return filename, content

    def write_article(self, article: Article) -> Optional[Path]:
        """Write a single article to the vault. Returns the file path."""
        target_dir = self._get_target_dir(article)
        target_dir.mkdir(parents=True, exist_ok=True)

        filename, content = self.format_article(article)

        # Handle filename collisions
        filepath = target_dir / filename
        counter = 1
        while filepath.exists():
            stem = filepath.stem
            filepath = target_dir / f"{stem}-{counter}.md"
            counter += 1

        filepath.write_text(content, encoding="utf-8")
        article.obsidian_path = str(filepath.relative_to(self.vault_path))

        logger.info(f"Written: {article.obsidian_path}")
        return filepath

    def write_batch(self, articles: List[Article]) -> List[Path]:
        """Write a batch of articles to the vault."""
        paths = []
        for article in articles:
            path = self.write_article(article)
            if path:
                paths.append(path)
        logger.info(f"Wrote {len(paths)} articles to vault")
        return paths

    def preview(self, article: Article) -> str:
        """Preview the formatted content without writing to disk."""
        _, content = self.format_article(article)
        return content
