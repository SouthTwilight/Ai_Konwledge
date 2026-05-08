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
        """Determine the target subdirectory based on article source + date."""
        subdir = SOURCE_DIRS.get(article.source, "0-Inbox")
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

    def append_references(self, article_path: Path, linked_articles: List) -> None:
        """Append a ## References section with [[wikilinks]] to an existing article.

        Inserts before the ## Personal Notes section. If ## References already
        exists, appends new wikilinks to it.

        Args:
            article_path: Path to the .md file to modify.
            linked_articles: List of Article objects with obsidian_path set.
        """
        content = article_path.read_text(encoding="utf-8")

        # Build wikilink entries from article titles
        new_links = []
        for a in linked_articles:
            title = a.title or "Untitled"
            new_links.append(f"[[{title}]]")

        links_str = " ".join(new_links)

        if "## References" in content:
            # Append to existing References section
            updated = content.replace(
                "## References\n",
                f"## References\n{links_str}\n",
            )
        else:
            # Insert before ## Personal Notes
            if "## Personal Notes" in content:
                ref_section = f"## References\n\n{links_str}\n\n"
                updated = content.replace(
                    "## Personal Notes",
                    f"{ref_section}## Personal Notes",
                )
            else:
                # Append at end if no Personal Notes section
                updated = content.rstrip() + f"\n\n## References\n\n{links_str}\n"

        article_path.write_text(updated, encoding="utf-8")
        logger.info(f"Appended {len(new_links)} references to {article_path.name}")

    def append_referenced_by(self, article: Article, source_path: str) -> None:
        """Add a referenced_by entry to the linked article's frontmatter.

        Reads the article's .md file from its obsidian_path, adds or updates
        the referenced_by field in YAML frontmatter, and writes back.

        Args:
            article: The linked Article (must have obsidian_path set).
            source_path: Absolute path of the source article .md file.
        """
        if not article.obsidian_path:
            logger.warning("Cannot append referenced_by: article has no obsidian_path")
            return

        target_path = self.vault_path / article.obsidian_path
        if not target_path.exists():
            logger.warning(f"Linked article file not found: {target_path}")
            return

        content = target_path.read_text(encoding="utf-8")

        # Find frontmatter boundaries
        lines = content.split("\n")
        if not lines or lines[0].strip() != "---":
            logger.warning(f"No frontmatter found in {target_path}")
            return

        fm_end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                fm_end = i
                break

        if fm_end is None:
            logger.warning(f"Malformed frontmatter in {target_path}")
            return

        # Parse existing frontmatter
        fm_str = "\n".join(lines[1:fm_end])
        try:
            fm = yaml.safe_load(fm_str) or {}
        except yaml.YAMLError:
            logger.warning(f"Failed to parse frontmatter in {target_path}")
            return

        # Convert source absolute path to vault-relative path
        try:
            rel_source = str(Path(source_path).relative_to(self.vault_path))
        except ValueError:
            rel_source = source_path

        # Add or append referenced_by
        existing = fm.get("referenced_by", [])
        if not isinstance(existing, list):
            existing = [existing]
        if rel_source not in existing:
            existing.append(rel_source)
        fm["referenced_by"] = existing

        # Rebuild file
        new_fm = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
        new_lines = ["---", new_fm.strip(), "---"] + lines[fm_end + 1:]
        target_path.write_text("\n".join(new_lines), encoding="utf-8")
        logger.info(f"Appended referenced_by to {article.obsidian_path}")
