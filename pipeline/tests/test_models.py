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
