"""Tests for Topic Clusterer."""
from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pipeline.processors.clusterer import (
    read_vault_articles,
    _parse_frontmatter,
    _extract_summary,
    _embed_text_zhipu,
    _cluster_hdbscan,
    _cluster_fallback,
    _name_cluster,
    cluster_articles,
    _cluster_by_tags,
)


# --- Helpers ---

def _make_md_file(
    tmp_path: Path,
    title: str = "Test Article",
    tags: list = None,
    summary: str = "This is a summary.",
    subdir: str = "2-Articles",
    filename: str = "",
) -> Path:
    """Create a minimal markdown file with frontmatter in the vault."""
    tags = tags or ["test"]
    filename = filename or f"{title.replace(' ', '-')}.md"
    d = tmp_path / subdir
    d.mkdir(parents=True, exist_ok=True)
    f = d / filename
    content = textwrap.dedent(f"""\
    ---
    title: "{title}"
    tags: {tags}
    relevance: 8
    source_name: TestFeed
    ---
    ## Summary
    {summary}
    ## Key Points
    - Point 1
    - Point 2
    """)
    f.write_text(content, encoding="utf-8")
    return f


def _mock_embedding_response(n: int, dim: int = 256):
    """Create a mock httpx response for embedding API."""
    import numpy as np
    data = {
        "data": [
            {"embedding": np.random.randn(dim).tolist(), "index": i}
            for i in range(n)
        ]
    }
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


# --- Tests: _parse_frontmatter ---

def test_parse_frontmatter_valid():
    content = '---\ntitle: "Hello"\ntags: [a, b]\n---\nBody text'
    result = _parse_frontmatter(content)
    assert result["title"] == "Hello"
    assert result["tags"] == ["a", "b"]


def test_parse_frontmatter_no_frontmatter():
    assert _parse_frontmatter("Just plain text") is None


def test_parse_frontmatter_unclosed():
    assert _parse_frontmatter("---\ntitle: X\nNo closing") is None


# --- Tests: _extract_summary ---

def test_extract_summary_plain():
    content = "---\ntitle: T\n---\nSome body text here."
    result = _extract_summary(content)
    assert "Some body text here" in result


def test_extract_summary_truncation():
    content = "---\n---\n" + "x" * 1000
    result = _extract_summary(content)
    assert len(result) <= 500


def test_extract_summary_strips_formatting():
    content = "---\n---\n## Heading\n**bold** and [link](http://x)"
    result = _extract_summary(content)
    assert "##" not in result
    assert "**" not in result


# --- Tests: _embed_text_zhipu ---

def test_embed_text_success():
    texts = ["hello world", "test text"]
    with patch("pipeline.processors.clusterer.httpx.post") as mock_post:
        mock_post.return_value = _mock_embedding_response(2)
        result = _embed_text_zhipu(texts, "fake-key")

    assert len(result) == 2
    assert len(result[0]) == 256
    mock_post.assert_called_once()


def test_embed_text_no_api_key():
    result = _embed_text_zhipu(["test"], "")
    assert result == []


def test_embed_text_api_error():
    with patch("pipeline.processors.clusterer.httpx.post", side_effect=Exception("fail")):
        result = _embed_text_zhipu(["test"], "key")
    assert result == [[]]


def test_embed_text_batching():
    """Test that >16 texts are split into batches."""
    texts = [f"text {i}" for i in range(20)]
    with patch("pipeline.processors.clusterer.httpx.post") as mock_post:
        mock_post.return_value = _mock_embedding_response(16)
        # First batch 16, second batch 4 — need different responses
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            batch_input = kwargs.get("json", {}).get("input", [])
            return _mock_embedding_response(len(batch_input))

        mock_post.side_effect = side_effect
        result = _embed_text_zhipu(texts, "fake-key")

    assert len(result) == 20
    assert mock_post.call_count == 2


# --- Tests: _cluster_hdbscan ---

def test_cluster_hdbscan_basic():
    """With enough distinct embeddings, should produce clusters."""
    import numpy as np
    np.random.seed(42)
    # Create 3 distinct clusters
    embeddings = []
    for _ in range(5):
        embeddings.append(np.random.randn(10).tolist())
    for _ in range(5):
        embeddings.append((np.random.randn(10) + 10).tolist())
    for _ in range(5):
        embeddings.append((np.random.randn(10) + 20).tolist())

    labels = _cluster_hdbscan(embeddings, min_cluster_size=3)
    assert len(labels) == 15
    unique = set(labels)
    assert len(unique) >= 2  # At least 2 clusters (plus noise)


def test_cluster_hdbscan_too_few():
    result = _cluster_hdbscan([[1, 2], [3, 4]], min_cluster_size=5)
    assert result == [-1, -1]


# --- Tests: _cluster_fallback ---

def test_cluster_fallback_enough():
    result = _cluster_fallback([[1], [2], [3]])
    assert len(result) == 3


def test_cluster_fallback_too_few():
    result = _cluster_fallback([[1], [2]])
    assert result == [-1, -1]


# --- Tests: _name_cluster ---

def test_name_cluster_with_tags():
    articles = [
        {"tags": ["ai", "python", "ai"]},
        {"tags": ["ai", "ml"]},
    ]
    name = _name_cluster(articles)
    assert "ai" in name


def test_name_cluster_no_tags():
    articles = [{"tags": []}, {"tags": []}]
    name = _name_cluster(articles)
    assert "2 articles" in name


# --- Tests: _cluster_by_tags ---

def test_cluster_by_tags_basic():
    articles = [
        {"title": "A", "tags": ["python", "ai"], "path": "a.md"},
        {"title": "B", "tags": ["python", "web"], "path": "b.md"},
        {"title": "C", "tags": ["python", "data"], "path": "c.md"},
        {"title": "D", "tags": ["python"], "path": "d.md"},
    ]
    topics = _cluster_by_tags(articles, min_size=3)
    assert len(topics) >= 1
    # Python tag should group at least 3
    python_topic = [t for t in topics if t["name"] == "python"]
    assert len(python_topic) == 1
    assert python_topic[0]["size"] >= 3


def test_cluster_by_tags_too_few():
    articles = [
        {"title": "A", "tags": ["rare"], "path": "a.md"},
        {"title": "B", "tags": ["other"], "path": "b.md"},
    ]
    topics = _cluster_by_tags(articles, min_size=3)
    assert topics == []


# --- Tests: read_vault_articles ---

def test_read_vault_articles(tmp_path):
    _make_md_file(tmp_path, "AI Revolution", ["ai", "llm"], "About AI", "2-Articles")
    _make_md_file(tmp_path, "Python Tips", ["python"], "Python tricks", "2-Articles")
    _make_md_file(tmp_path, "GitHub Tool", ["github"], "A tool", "3-GitHub")

    articles = read_vault_articles(tmp_path)
    assert len(articles) == 3
    titles = [a["title"] for a in articles]
    assert "AI Revolution" in titles
    assert "Python Tips" in titles


def test_read_vault_articles_empty(tmp_path):
    articles = read_vault_articles(tmp_path)
    assert articles == []


def test_read_vault_articles_skips_no_frontmatter(tmp_path):
    d = tmp_path / "2-Articles"
    d.mkdir(parents=True)
    (d / "plain.md").write_text("No frontmatter here", encoding="utf-8")
    articles = read_vault_articles(tmp_path)
    assert articles == []


# --- Tests: cluster_articles (integration) ---

def test_cluster_articles_tag_fallback(tmp_path):
    """When no embedding API key, should fall back to tag clustering."""
    for i in range(5):
        _make_md_file(
            tmp_path,
            f"Article {i}",
            ["python", "test"],
            f"Summary {i}",
            "2-Articles",
            filename=f"article-{i}.md",
        )

    with patch.dict(os.environ, {"ZHIPU_API_KEY": ""}):
        topics = cluster_articles(tmp_path, api_key="", min_cluster_size=3)

    # Should find at least one topic via tag fallback
    assert len(topics) >= 1
    assert any("python" in t["name"] or "test" in t["name"] for t in topics)


def test_cluster_articles_with_embedding(tmp_path):
    """With mocked embedding API, should produce clusters."""
    for i in range(8):
        _make_md_file(
            tmp_path,
            f"Article {i}",
            ["ai"] if i < 4 else ["web"],
            f"Summary {i}",
            "2-Articles",
            filename=f"article-{i}.md",
        )

    def mock_embed_response(*args, **kwargs):
        batch_input = kwargs.get("json", {}).get("input", [])
        import numpy as np
        np.random.seed(42)
        n = len(batch_input)
        # Create 2 distinct clusters
        embeddings = []
        for i in range(n):
            if i < n // 2:
                embeddings.append((np.random.randn(16) + 5).tolist())
            else:
                embeddings.append((np.random.randn(16) - 5).tolist())
        data = {"data": [{"embedding": e, "index": i} for i, e in enumerate(embeddings)]}
        resp = MagicMock()
        resp.json.return_value = data
        resp.raise_for_status.return_value = None
        return resp

    with patch("pipeline.processors.clusterer.httpx.post", side_effect=mock_embed_response):
        topics = cluster_articles(tmp_path, api_key="fake-key", min_cluster_size=3)

    # Should get at least 1 cluster
    assert len(topics) >= 1


def test_cluster_articles_too_few(tmp_path):
    _make_md_file(tmp_path, "Solo", ["rare"], "Only one", "2-Articles")
    topics = cluster_articles(tmp_path, api_key="", min_cluster_size=3)
    assert topics == []
