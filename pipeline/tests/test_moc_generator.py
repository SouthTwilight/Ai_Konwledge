"""Tests for MOC Generator."""
from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.processors.moc_generator import (
    generate_moc,
    _to_wikilink,
    _write_topic_moc,
    _write_index_moc,
    _slugify,
)


# --- Helpers ---

def _make_md_file(
    tmp_path: Path,
    title: str = "Test Article",
    tags: list = None,
    summary: str = "Summary text.",
    subdir: str = "2-Articles",
    filename: str = "",
    relevance: int = 8,
) -> Path:
    tags = tags or ["test"]
    filename = filename or f"{title.replace(' ', '-')}.md"
    d = tmp_path / subdir
    d.mkdir(parents=True, exist_ok=True)
    f = d / filename
    content = textwrap.dedent(f"""\
    ---
    title: "{title}"
    tags: {tags}
    relevance: {relevance}
    source_name: TestFeed
    ---
    ## Summary
    {summary}
    """)
    f.write_text(content, encoding="utf-8")
    return f


def _make_topic(name: str, n_articles: int = 3, tags: list = None) -> dict:
    tags = tags or [name]
    articles = [
        {
            "title": f"Article {i} for {name}",
            "tags": tags,
            "path": f"2-Articles/article-{i}.md",
            "relevance": 10 - i,
            "source_name": "TestFeed",
            "summary": f"Summary {i}",
        }
        for i in range(n_articles)
    ]
    return {
        "name": name,
        "articles": articles,
        "size": n_articles,
        "core_tags": tags,
    }


# --- Tests: _slugify ---

def test_slugify_ascii():
    assert _slugify("Hello World") == "Hello-World"


def test_slugify_chinese():
    result = _slugify("深度学习笔记")
    assert "深度学习笔记" in result


def test_slugify_special_chars():
    result = _slugify("AI/ML & Data-Science!")
    assert "/" not in result
    assert "&" not in result


def test_slugify_empty():
    assert _slugify("") == "untitled"


# --- Tests: _to_wikilink ---

def test_wikilink_with_path():
    article = {"path": "2-Articles/my-article.md", "title": "My Article"}
    result = _to_wikilink(article, Path("/vault"))
    assert result == "[[my-article|My Article]]"


def test_wikilink_no_path():
    article = {"path": "", "title": "Untitled"}
    result = _to_wikilink(article, Path("/vault"))
    assert result == "[[Untitled]]"


# --- Tests: _write_topic_moc ---

def test_write_topic_moc(tmp_path):
    moc_dir = tmp_path / "1-Dashboard"
    moc_dir.mkdir()
    topic = _make_topic("Python", 3, ["python"])
    vault = tmp_path

    result = _write_topic_moc(moc_dir, topic, vault)
    assert result is not None
    assert result.exists()
    assert result.name == "MOC-Python.md"

    content = result.read_text(encoding="utf-8")
    assert "# MOC: Python" in content
    assert "[[article-" in content
    assert "#python" in content
    assert "type: moc" in content


def test_write_topic_moc_chinese_name(tmp_path):
    moc_dir = tmp_path / "1-Dashboard"
    moc_dir.mkdir()
    topic = _make_topic("深度学习", 2, ["深度学习"])
    vault = tmp_path

    result = _write_topic_moc(moc_dir, topic, vault)
    assert result is not None
    assert "MOC-" in result.name

    content = result.read_text(encoding="utf-8")
    assert "深度学习" in content


# --- Tests: _write_index_moc ---

def test_write_index_moc(tmp_path):
    moc_dir = tmp_path / "1-Dashboard"
    moc_dir.mkdir()
    topics = [
        _make_topic("AI", 5, ["ai"]),
        _make_topic("Web", 3, ["web"]),
    ]
    vault = tmp_path

    result = _write_index_moc(moc_dir, topics, vault)
    assert result is not None
    assert result.name == "MOC-Index.md"

    content = result.read_text(encoding="utf-8")
    assert "知识地图总览" in content
    assert "2 个主题" in content
    assert "8 篇文章" in content
    assert "[[MOC-AI" in content
    assert "[[MOC-Web" in content
    assert "|------|" in content  # Table header


def test_write_index_moc_top5_cap(tmp_path):
    moc_dir = tmp_path / "1-Dashboard"
    moc_dir.mkdir()
    topic = _make_topic("BigTopic", 10, ["big"])
    vault = tmp_path

    result = _write_index_moc(moc_dir, [topic], vault)
    content = result.read_text(encoding="utf-8")
    assert "还有 5 篇文章" in content


# --- Tests: generate_moc (integration) ---

def test_generate_moc_with_mocked_cluster(tmp_path):
    """Full integration with mocked clustering."""
    for i in range(6):
        _make_md_file(
            tmp_path,
            f"Article {i}",
            ["python"] if i < 3 else ["javascript"],
            f"Summary {i}",
            "2-Articles",
            filename=f"article-{i}.md",
        )

    # Mock cluster_articles to return predictable topics
    mock_topics = [
        _make_topic("Python", 3, ["python"]),
        _make_topic("JavaScript", 3, ["javascript"]),
    ]

    with patch("pipeline.processors.moc_generator.cluster_articles", return_value=mock_topics):
        files = generate_moc(tmp_path, api_key="fake")

    assert len(files) == 3  # 2 topic MOCs + 1 index
    filenames = [f.name for f in files]
    assert "MOC-Python.md" in filenames
    assert "MOC-JavaScript.md" in filenames
    assert "MOC-Index.md" in filenames


def test_generate_moc_no_topics(tmp_path):
    """When clustering returns nothing, no files created."""
    with patch("pipeline.processors.moc_generator.cluster_articles", return_value=[]):
        files = generate_moc(tmp_path, api_key="fake")
    assert files == []


def test_generate_moc_creates_output_dir(tmp_path):
    """Output directory should be created if missing."""
    mock_topics = [_make_topic("Test", 3)]
    with patch("pipeline.processors.moc_generator.cluster_articles", return_value=mock_topics):
        files = generate_moc(tmp_path, api_key="fake", output_dir="1-Dashboard")

    assert (tmp_path / "1-Dashboard").exists()
    assert len(files) == 2  # topic + index


def test_generate_moc_frontmatter_has_auto_flag(tmp_path):
    mock_topics = [_make_topic("AI", 3, ["ai"])]
    with patch("pipeline.processors.moc_generator.cluster_articles", return_value=mock_topics):
        files = generate_moc(tmp_path, api_key="fake")

    for f in files:
        content = f.read_text(encoding="utf-8")
        assert "auto_generated: true" in content
