import pytest
from pipeline.models import Article, ArticleSource, ProcessingLevel


def test_article_creation():
    a = Article(url="https://example.com", title="Test", source=ArticleSource.RSS)
    assert a.url == "https://example.com"
    assert a.processing_level == ProcessingLevel.RAW
    assert a.relevance_score == 0
    assert a.tags == []


def test_article_compute_hash():
    a = Article(url="https://example.com", title="Test", source=ArticleSource.WEB_URL)
    h = a.compute_hash()
    assert len(h) == 16
    assert h == a.content_hash


def test_article_to_dict():
    a = Article(url="https://example.com", title="Test", source=ArticleSource.RSS, tags=["ai"])
    d = a.to_dict()
    assert d['source'] == 'rss'
    assert d['tags'] == ['ai']
    assert 'fetched_at' in d


def test_article_source_enum():
    assert ArticleSource.RSS.value == "rss"
    assert ArticleSource.GITHUB.value == "github"
    assert ArticleSource.EMAIL.value == "email"


def test_processing_level_enum():
    assert ProcessingLevel.RAW.value == "raw"
    assert ProcessingLevel.L2_SUMMARIZED.value == "l2"


def test_article_has_linked_urls_field():
    a = Article(url="https://example.com/a", title="Test", source=ArticleSource.WEB_URL)
    assert a.linked_urls == []


def test_article_has_referenced_by_field():
    a = Article(url="https://example.com/a", title="Test", source=ArticleSource.WEB_URL)
    assert a.referenced_by == []


def test_article_linked_urls_in_to_dict():
    a = Article(url="https://example.com/a", title="Test", source=ArticleSource.WEB_URL)
    a.linked_urls = ["https://example.com/ref1", "https://example.com/ref2"]
    d = a.to_dict()
    assert d["linked_urls"] == ["https://example.com/ref1", "https://example.com/ref2"]


def test_article_referenced_by_in_to_dict():
    a = Article(url="https://example.com/a", title="Test", source=ArticleSource.WEB_URL)
    a.referenced_by = ["2-Articles/2026-05-09/ref.md"]
    d = a.to_dict()
    assert d["referenced_by"] == ["2-Articles/2026-05-09/ref.md"]
