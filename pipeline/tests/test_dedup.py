import pytest
from pipeline.models import Article, ArticleSource
from pipeline.utils.dedup import DedupStore


@pytest.fixture
def store():
    s = DedupStore(":memory:")
    yield s
    s.close()


def _make_article(url: str, title: str = "Test") -> Article:
    a = Article(url=url, title=title, source=ArticleSource.RSS)
    a.compute_hash()
    return a


def test_new_article_not_seen(store):
    a = _make_article("https://example.com/article1")
    assert not store.is_seen(a)


def test_mark_seen(store):
    a = _make_article("https://example.com/article1")
    store.mark_seen(a)
    assert store.is_seen(a)


def test_filter_new_removes_duplicates(store):
    articles = [
        _make_article("https://example.com/a"),
        _make_article("https://example.com/b"),
        _make_article("https://example.com/a"),  # duplicate
    ]
    new = store.filter_new(articles)
    assert len(new) == 2


def test_url_normalization(store):
    """Trailing slashes and utm params should be normalized."""
    a1 = _make_article("https://example.com/article")
    a2 = _make_article("https://example.com/article/")
    a3 = _make_article("https://example.com/article?utm_source=rss")

    store.mark_seen(a1)
    assert store.is_seen(a2)   # trailing slash normalized
    assert store.is_seen(a3)   # utm params stripped


def test_different_urls_not_duplicates(store):
    a1 = _make_article("https://example.com/article1")
    a2 = _make_article("https://example.com/article2")

    store.mark_seen(a1)
    assert not store.is_seen(a2)
