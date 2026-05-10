"""Tests for DedupStore (URL dedup with enhanced normalization)."""
from __future__ import annotations

import os
import tempfile

import pytest

from pipeline.models import Article, ArticleSource
from pipeline.utils.dedup import DedupStore


def _make_article(
    url: str = "https://example.com/article",
    title: str = "Test Article",
    content: str = "Some content here",
    source: ArticleSource = ArticleSource.RSS,
) -> Article:
    a = Article(
        url=url,
        title=title,
        source=source,
        content_raw=content,
        source_name="TestFeed",
    )
    a.compute_hash()
    return a


# --- Basic URL dedup ---

def test_url_dedup_basic():
    store = DedupStore()
    art = _make_article("https://example.com/a")
    assert not store.is_seen(art)
    store.mark_seen(art)
    assert store.is_seen(art)


def test_url_dedup_different_urls():
    store = DedupStore()
    store.mark_seen(_make_article("https://example.com/a"))
    assert not store.is_seen(_make_article("https://example.com/b"))


# --- URL normalization ---

def test_normalizes_trailing_slash():
    store = DedupStore()
    store.mark_seen(_make_article("https://example.com/page/"))
    assert store.is_seen(_make_article("https://example.com/page"))


def test_strips_tracking_params():
    store = DedupStore()
    store.mark_seen(_make_article("https://example.com/page"))
    assert store.is_seen(_make_article("https://example.com/page?utm_source=rss&fbclid=abc"))


def test_strips_utm_params():
    store = DedupStore()
    store.mark_seen(_make_article("https://example.com/article"))
    assert store.is_seen(_make_article("https://example.com/article?utm_medium=social&utm_campaign=test"))


def test_preserves_non_tracking_params():
    store = DedupStore()
    store.mark_seen(_make_article("https://example.com/search?q=test"))
    # Same non-tracking param = same URL
    assert store.is_seen(_make_article("https://example.com/search?q=test"))
    # Different non-tracking param = different URL
    assert not store.is_seen(_make_article("https://example.com/search?q=other"))


def test_strips_fragment():
    store = DedupStore()
    store.mark_seen(_make_article("https://example.com/page"))
    assert store.is_seen(_make_article("https://example.com/page#section"))


def test_strips_gclid():
    store = DedupStore()
    store.mark_seen(_make_article("https://example.com/landing"))
    assert store.is_seen(_make_article("https://example.com/landing?gclid=abc123"))


# --- filter_new ---

def test_filter_new_all_new():
    store = DedupStore()
    articles = [_make_article(url=f"https://example.com/{i}") for i in range(5)]
    result = store.filter_new(articles)
    assert len(result) == 5


def test_filter_new_mixed():
    store = DedupStore()
    store.mark_seen(_make_article("https://example.com/1"))
    result = store.filter_new([
        _make_article("https://example.com/1"),
        _make_article("https://example.com/2"),
    ])
    assert len(result) == 1
    assert result[0].url == "https://example.com/2"


def test_filter_new_all_dups():
    store = DedupStore()
    art = _make_article("https://example.com/1")
    store.mark_seen(art)
    result = store.filter_new([_make_article("https://example.com/1")])
    assert len(result) == 0


# --- stats ---

def test_stats():
    store = DedupStore()
    store.mark_seen(_make_article("https://a.com/1", source=ArticleSource.RSS))
    store.mark_seen(_make_article("https://b.com/2", source=ArticleSource.RSS))
    store.mark_seen(_make_article("https://c.com/3", source=ArticleSource.WEB_URL))
    stats = store.stats()
    assert stats["total_seen"] == 3
    assert stats["by_source"]["rss"] == 2
    assert stats["by_source"]["web_url"] == 1


def test_stats_empty():
    store = DedupStore()
    stats = store.stats()
    assert stats["total_seen"] == 0
    assert stats["by_source"] == {}


# --- persistence ---

def test_close_and_reopen():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = DedupStore(db_path)
        store.mark_seen(_make_article("https://example.com/1"))
        store.close()

        store2 = DedupStore(db_path)
        assert store2.is_seen(_make_article("https://example.com/1"))
        assert not store2.is_seen(_make_article("https://example.com/2"))
        store2.close()
    finally:
        os.unlink(db_path)


def test_close_idempotent():
    store = DedupStore()
    store.close()
    store.close()  # Should not raise
