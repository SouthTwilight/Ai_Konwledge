"""MOC Generator — Create Obsidian Map of Content pages.

Reads clustered topics from the clusterer and generates
MOC markdown files in the vault with WikiLinks to articles.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml

from pipeline.processors.clusterer import cluster_articles, read_vault_articles

logger = logging.getLogger(__name__)


def generate_moc(
    vault_path: Path,
    api_key: str = "",
    min_cluster_size: int = 3,
    output_dir: str = "1-Dashboard",
) -> List[Path]:
    """Generate MOC (Map of Content) pages from clustered articles.

    Creates one MOC page per topic cluster, with WikiLinks to
    all articles in that cluster. Also creates a master index MOC.

    Args:
        vault_path: Path to the Obsidian vault section.
        api_key: ZhipuAI API key for embeddings.
        min_cluster_size: Minimum articles per cluster.
        output_dir: Subdirectory in vault for MOC files.

    Returns:
        List of created MOC file paths.
    """
    topics = cluster_articles(vault_path, api_key, min_cluster_size)

    if not topics:
        logger.info("No topics found, skipping MOC generation")
        return []

    moc_dir = vault_path / output_dir
    moc_dir.mkdir(parents=True, exist_ok=True)

    created_files = []

    # Generate one MOC per topic
    for topic in topics:
        moc_path = _write_topic_moc(moc_dir, topic, vault_path)
        if moc_path:
            created_files.append(moc_path)

    # Generate master index
    index_path = _write_index_moc(moc_dir, topics, vault_path)
    if index_path:
        created_files.append(index_path)

    logger.info(f"Generated {len(created_files)} MOC files")
    return created_files


def _to_wikilink(article: dict, vault_path: Path) -> str:
    """Convert article path to an Obsidian WikiLink."""
    path = article.get("path", "")
    title = article.get("title", "Untitled")
    # Use relative path without extension for WikiLink
    if path:
        stem = Path(path).stem
        return f"[[{stem}|{title}]]"
    return f"[[{title}]]"


def _write_topic_moc(
    moc_dir: Path,
    topic: dict,
    vault_path: Path,
) -> Optional[Path]:
    """Write a single topic MOC file.

    Args:
        moc_dir: Directory to write MOC file.
        topic: Topic dict from clusterer.
        vault_path: Root vault path.

    Returns:
        Path to created file, or None on error.
    """
    name = topic["name"]
    safe_name = _slugify(name)
    filename = f"MOC-{safe_name}.md"
    filepath = moc_dir / filename

    # Build frontmatter
    frontmatter = {
        "title": f"MOC: {name}",
        "type": "moc",
        "tags": topic.get("core_tags", []),
        "article_count": topic["size"],
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "auto_generated": True,
    }

    # Build body
    parts = []
    parts.append(f"# MOC: {name}\n")
    parts.append(f"> {topic['size']} 篇文章 | 生成于 {datetime.now().strftime('%Y-%m-%d')}\n")

    # Core tags
    if topic.get("core_tags"):
        parts.append("## 主题标签\n")
        parts.append(" ".join(f"#{t}" for t in topic["core_tags"]))
        parts.append("")

    # Article list with WikiLinks, grouped by source if possible
    parts.append("## 文章列表\n")

    # Sort articles by relevance score descending
    sorted_articles = sorted(
        topic["articles"],
        key=lambda a: a.get("relevance", 0),
        reverse=True,
    )

    for article in sorted_articles:
        wikilink = _to_wikilink(article, vault_path)
        source = article.get("source_name", "")
        relevance = article.get("relevance", 0)
        tag_str = ""
        if article.get("tags"):
            tag_str = " " + " ".join(f"#{t}" for t in article["tags"][:3])

        line = f"- {wikilink}"
        if source:
            line += f" — *{source}*"
        if tag_str:
            line += tag_str
        parts.append(line)

    parts.append("")

    # Compose file
    content = "---\n" + yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False) + "---\n\n"
    content += "\n".join(parts)

    try:
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Created MOC: {filepath.name}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to write MOC {filename}: {e}")
        return None


def _write_index_moc(
    moc_dir: Path,
    topics: List[dict],
    vault_path: Path,
) -> Optional[Path]:
    """Write the master index MOC linking to all topic MOCs.

    Returns:
        Path to created file, or None on error.
    """
    filepath = moc_dir / "MOC-Index.md"

    frontmatter = {
        "title": "知识地图总览",
        "type": "moc-index",
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "topic_count": len(topics),
        "total_articles": sum(t["size"] for t in topics),
        "auto_generated": True,
    }

    parts = []
    parts.append("# 知识地图总览\n")
    parts.append(f"> {len(topics)} 个主题 | {sum(t['size'] for t in topics)} 篇文章 | 更新于 {datetime.now().strftime('%Y-%m-%d')}\n")

    # Summary table
    parts.append("## 主题概览\n")
    parts.append("| 主题 | 文章数 | 核心标签 |")
    parts.append("|------|--------|----------|")
    for topic in topics:
        safe_name = _slugify(topic["name"])
        moc_link = f"[[MOC-{safe_name}|{topic['name']}]]"
        tags = ", ".join(f"#{t}" for t in topic.get("core_tags", [])[:3])
        parts.append(f"| {moc_link} | {topic['size']} | {tags} |")
    parts.append("")

    # Topic sections with top articles
    for topic in topics:
        safe_name = _slugify(topic["name"])
        parts.append(f"## [[MOC-{safe_name}|{topic['name']}]]\n")
        # Show top 5 articles
        top_articles = sorted(
            topic["articles"],
            key=lambda a: a.get("relevance", 0),
            reverse=True,
        )[:5]
        for article in top_articles:
            wikilink = _to_wikilink(article, vault_path)
            parts.append(f"- {wikilink}")
        if topic["size"] > 5:
            parts.append(f"- *...还有 {topic['size'] - 5} 篇文章*")
        parts.append("")

    content = "---\n" + yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False) + "---\n\n"
    content += "\n".join(parts)

    try:
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Created Index MOC: {filepath.name}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to write Index MOC: {e}")
        return None


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    # Keep Chinese characters, letters, numbers, hyphens
    slug = re.sub(r'[^\w\u4e00-\u9fff\u3400-\u4dbf-]', '-', text)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug[:60] if slug else "untitled"
