"""Topic Clusterer — Embed articles and cluster into themes.

Uses ZhipuAI embedding API for vector generation,
UMAP for dimensionality reduction, and HDBSCAN for clustering.
Falls back to simple TF-IDF based clustering if dependencies are unavailable.
"""
from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
import yaml

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def read_vault_articles(vault_path: Path) -> List[dict]:
    """Read all processed articles from the Obsidian vault.

    Scans 2-Articles/, 3-GitHub/, and 4-Newsletters/ for markdown files,
    extracting frontmatter metadata and content summary.

    Returns:
        List of article dicts with keys: title, tags, summary, path, concepts, source
    """
    articles = []
    subdirs = ["2-Articles", "3-GitHub", "4-Newsletters"]

    for subdir in subdirs:
        target = vault_path / subdir
        if not target.exists():
            continue
        for md_file in target.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                meta = _parse_frontmatter(content)
                if not meta:
                    continue
                articles.append({
                    "title": meta.get("title", md_file.stem),
                    "tags": meta.get("tags", []),
                    "summary": _extract_summary(content),
                    "path": str(md_file.relative_to(vault_path)),
                    "relevance": meta.get("relevance", 0),
                    "source_name": meta.get("source_name", ""),
                    "concepts": [],  # Will be populated if L3 data available
                })
            except Exception as e:
                logger.debug(f"Error reading {md_file}: {e}")

    logger.info(f"Read {len(articles)} articles from vault")
    return articles


def _parse_frontmatter(content: str) -> Optional[dict]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    try:
        return yaml.safe_load(content[3:end])
    except yaml.YAMLError:
        return None


def _extract_summary(content: str) -> str:
    """Extract text content after frontmatter, limited to ~500 chars."""
    # Skip frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:]

    # Remove markdown formatting
    text = re.sub(r'#+\s+', '', content)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links → text
    text = re.sub(r'[\*\#\|\>]', '', text)
    text = re.sub(r'\n{2,}', '\n', text).strip()

    return text[:500]


def _embed_text_zhipu(texts: List[str], api_key: str) -> List[List[float]]:
    """Generate embeddings using ZhipuAI embedding API.

    Args:
        texts: List of text strings to embed.
        api_key: ZhipuAI API key.

    Returns:
        List of embedding vectors.
    """
    if not api_key:
        logger.warning("No API key for embedding generation")
        return []

    embeddings = []
    # Process in batches of 16 (ZhipuAI limit)
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            resp = httpx.post(
                "https://open.bigmodel.cn/api/paas/v4/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "embedding-3",
                    "input": batch,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            # Sort by index to maintain order
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            embeddings.extend([item["embedding"] for item in sorted_data])
        except Exception as e:
            logger.error(f"Embedding API error: {e}")
            # Return empty for failed batch
            embeddings.extend([[] for _ in batch])

    return embeddings


def _cluster_hdbscan(embeddings: List[List[float]], min_cluster_size: int = 3) -> List[int]:
    """Cluster embeddings using HDBSCAN.

    Returns:
        List of cluster labels (-1 for noise).
    """
    try:
        import numpy as np
        from hdbscan import HDBSCAN

        X = np.array(embeddings)
        if len(X) < min_cluster_size:
            return [-1] * len(X)

        clusterer = HDBSCAN(min_cluster_size=min_cluster_size, min_samples=2)
        clusterer.fit(X)
        return clusterer.labels_.tolist()
    except ImportError:
        logger.warning("hdbscan not available, using fallback clustering")
        return _cluster_fallback(embeddings)


def _cluster_fallback(embeddings: List[List[float]]) -> List[int]:
    """Simple fallback: assign all articles to cluster 0 if enough articles."""
    if len(embeddings) >= 3:
        return [0] * len(embeddings)
    return [-1] * len(embeddings)


def _name_cluster(
    cluster_articles: List[dict],
    api_key: str = "",
) -> str:
    """Generate a name for a cluster of articles.

    Uses tag frequency for naming, with optional AI refinement.
    """
    # Collect all tags
    all_tags = []
    for art in cluster_articles:
        all_tags.extend(art.get("tags", []))

    if not all_tags:
        return f"Topic ({len(cluster_articles)} articles)"

    # Find most common tags
    tag_counts = Counter(all_tags)
    top_tags = [t for t, _ in tag_counts.most_common(3)]

    if len(top_tags) == 1:
        return top_tags[0]
    return " / ".join(top_tags)


def cluster_articles(
    vault_path: Path,
    api_key: str = "",
    min_cluster_size: int = 3,
) -> List[dict]:
    """Main entry: read vault articles → embed → cluster → return topics.

    Args:
        vault_path: Path to the Obsidian vault section.
        api_key: ZhipuAI API key for embeddings.
        min_cluster_size: Minimum articles per cluster.

    Returns:
        List of topic dicts, each with:
          - name: Topic name
          - articles: List of article dicts in this topic
          - size: Number of articles
          - core_tags: Top tags for this topic
    """
    articles = read_vault_articles(vault_path)
    if len(articles) < 2:
        logger.info("Not enough articles for clustering")
        return []

    # Build text for embedding: tags + summary
    texts = []
    for art in articles:
        parts = []
        if art["tags"]:
            parts.append("Tags: " + ", ".join(art["tags"]))
        if art["summary"]:
            parts.append(art["summary"][:300])
        texts.append(" | ".join(parts) if parts else art["title"])

    # Generate embeddings
    if not api_key:
        api_key = os.getenv("ZHIPU_API_KEY", "")

    embeddings = _embed_text_zhipu(texts, api_key)

    if not embeddings or any(len(e) == 0 for e in embeddings):
        logger.warning("Embedding generation failed, using tag-based fallback")
        return _cluster_by_tags(articles, min_cluster_size)

    # Cluster
    labels = _cluster_hdbscan(embeddings, min_cluster_size)

    # Build topic results
    topics = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue  # noise
        if label not in topics:
            topics[label] = []
        topics[label].append(articles[idx])

    results = []
    for label, topic_articles in topics.items():
        name = _name_cluster(topic_articles, api_key)
        all_tags = []
        for a in topic_articles:
            all_tags.extend(a.get("tags", []))
        tag_counts = Counter(all_tags)

        results.append({
            "name": name,
            "articles": topic_articles,
            "size": len(topic_articles),
            "core_tags": [t for t, _ in tag_counts.most_common(5)],
        })

    # Sort by size descending
    results.sort(key=lambda x: x["size"], reverse=True)

    logger.info(f"Generated {len(results)} topics from {len(articles)} articles")
    return results


def _cluster_by_tags(articles: List[dict], min_size: int = 3) -> List[dict]:
    """Fallback clustering using tag co-occurrence.

    Groups articles that share at least one tag.
    """
    # Build tag → articles mapping
    tag_map = {}
    for art in articles:
        for tag in art.get("tags", []):
            tag_map.setdefault(tag, []).append(art)

    # Keep only tags with enough articles
    topics = []
    used_articles = set()
    for tag, arts in sorted(tag_map.items(), key=lambda x: -len(x[1])):
        if len(arts) < min_size:
            continue
        # Only include articles not already assigned
        unique_arts = [a for a in arts if a["path"] not in used_articles]
        if len(unique_arts) < min_size:
            continue
        for a in unique_arts:
            used_articles.add(a["path"])
        topics.append({
            "name": tag,
            "articles": unique_arts,
            "size": len(unique_arts),
            "core_tags": [tag],
        })

    logger.info(f"Tag-based fallback: {len(topics)} topics")
    return topics
