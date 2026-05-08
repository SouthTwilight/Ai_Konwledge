"""Tests for link resolver module."""
import pytest
from pipeline.processors.link_resolver import extract_links_from_markdown, filter_links


# --- extract_links_from_markdown tests ---

def test_extract_single_link():
    content = "See [this article](https://example.com/a) for more."
    links = extract_links_from_markdown(content)
    assert links == [("this article", "https://example.com/a")]


def test_extract_multiple_links():
    content = "[one](https://a.com) and [two](https://b.com/page)"
    links = extract_links_from_markdown(content)
    assert len(links) == 2
    assert links[0] == ("one", "https://a.com")
    assert links[1] == ("two", "https://b.com/page")


def test_extract_no_links():
    content = "Plain text without any links."
    links = extract_links_from_markdown(content)
    assert links == []


def test_extract_links_with_special_chars_in_text():
    content = "[C++ primer](https://cpp.com) and [读《红楼梦》](https://hlm.cn)"
    links = extract_links_from_markdown(content)
    assert len(links) == 2
    assert links[0] == ("C++ primer", "https://cpp.com")
    assert links[1] == ("读《红楼梦》", "https://hlm.cn")


def test_extract_ignore_image_links():
    content = "![image](https://img.com/pic.png) and [real link](https://real.com)"
    links = extract_links_from_markdown(content)
    assert links == [("real link", "https://real.com")]


def test_extract_empty_content():
    assert extract_links_from_markdown("") == []


# --- filter_links tests ---

SOURCE_URL = "https://mysite.com/blog/article"


def test_filter_excludes_same_domain():
    links = [("ref", "https://mysite.com/other-post")]
    result = filter_links(links, SOURCE_URL)
    assert result == []


def test_filter_excludes_non_http():
    links = [("mail", "mailto:user@example.com"), ("js", "javascript:void(0)"), ("tel", "tel:+123")]
    result = filter_links(links, SOURCE_URL)
    assert result == []


def test_filter_excludes_anchor_only():
    links = [("section", "#section-1"), ("top", "#")]
    result = filter_links(links, SOURCE_URL)
    assert result == []


def test_filter_keeps_valid_link():
    links = [("good", "https://other.com/article")]
    result = filter_links(links, SOURCE_URL)
    assert result == [("good", "https://other.com/article")]


def test_filter_deduplicates():
    links = [("a", "https://site-a.com/page1"), ("b", "https://site-a.com/page1"), ("c", "https://site-b.com/page2")]
    result = filter_links(links, SOURCE_URL)
    assert result == [("a", "https://site-a.com/page1"), ("c", "https://site-b.com/page2")]


def test_filter_excludes_social_domains():
    links = [
        ("tw", "https://twitter.com/user/status/123"),
        ("gh", "https://github.com/user/repo"),
        ("x", "https://x.com/user"),
    ]
    result = filter_links(links, SOURCE_URL)
    assert result == [("gh", "https://github.com/user/repo")]


def test_filter_respects_max_links():
    links = [("a", f"https://site{i}.com/page") for i in range(10)]
    result = filter_links(links, SOURCE_URL, max_links=3)
    assert len(result) == 3


def test_filter_keeps_arxiv():
    links = [("paper", "https://arxiv.org/abs/2301.12345")]
    result = filter_links(links, SOURCE_URL)
    assert result == [("paper", "https://arxiv.org/abs/2301.12345")]


def test_filter_excludes_bare_domain():
    """Bare domain URLs like https://twitter.com (no path) should be excluded."""
    links = [("bare", "https://twitter.com")]
    result = filter_links(links, SOURCE_URL)
    assert result == []


# --- _strip_frontmatter tests ---

from pipeline.processors.link_resolver import _strip_frontmatter, _read_frontmatter_source


def test_strip_frontmatter_removes_yaml():
    content = "---\ntitle: Test\nsource: https://x.com\n---\n# Body\n\nText here.\n"
    body = _strip_frontmatter(content)
    assert body.startswith("# Body")
    assert "title" not in body


def test_strip_frontmatter_no_frontmatter():
    content = "# Just a heading\n\nNo frontmatter here.\n"
    body = _strip_frontmatter(content)
    assert body == content


def test_read_frontmatter_source_extracts_url():
    content = "---\ntitle: Test\nsource: https://example.com/a\ntags: [ai]\n---\n# Body\n"
    url = _read_frontmatter_source(content)
    assert url == "https://example.com/a"


def test_read_frontmatter_source_empty_on_no_fm():
    content = "# No frontmatter\n"
    url = _read_frontmatter_source(content)
    assert url == ""


# --- resolve_linked_articles tests (mocked) ---

from unittest.mock import patch, MagicMock
from pipeline.processors.link_resolver import resolve_linked_articles
from pipeline.models import Article, ArticleSource
import tempfile, os
from pathlib import Path


def _make_mock_pipeline():
    """Create a mock Pipeline with all dependencies."""
    pipeline = MagicMock()
    pipeline.config = MagicMock()
    pipeline.config.tier_discard_max = 3
    pipeline.config.tier_compressed_max = 6
    pipeline.dedup = MagicMock()
    pipeline.dedup.filter_new = lambda articles: articles
    pipeline.l1 = MagicMock()
    pipeline.l1.filter_article = lambda a: a
    pipeline.l1._assign_tier = lambda s, d, c: "detailed" if s > c else "compressed" if s > d else "discard"
    pipeline.l2 = MagicMock()
    pipeline.l2.summarize_batch = lambda articles: articles
    pipeline.writer = MagicMock()
    pipeline.writer.write_article = MagicMock(return_value=Path("/tmp/ref.md"))
    pipeline.writer.append_references = MagicMock()
    pipeline.writer.append_referenced_by = MagicMock()
    return pipeline


@patch("pipeline.extractors.web_extractor.extract_url")
def test_resolve_no_links_in_body(mock_extract):
    """Article with no links returns zero stats."""
    content = "---\ntitle: Test\nsource: https://mysite.com/a\n---\n# Test\n\nPlain text.\n\n## Personal Notes\n"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(content)
        tmp = f.name
    try:
        pipeline = _make_mock_pipeline()
        stats = resolve_linked_articles(tmp, pipeline, max_links=5)
        assert stats["links_found"] == 0
        assert stats["fetched"] == 0
        mock_extract.assert_not_called()
    finally:
        os.unlink(tmp)


@patch("pipeline.extractors.web_extractor.extract_url")
def test_resolve_filters_same_domain_links(mock_extract):
    """Same-domain links are excluded, nothing fetched."""
    content = "---\ntitle: Test\nsource: https://mysite.com/a\n---\n# Test\n\nSee [ref](https://mysite.com/other).\n\n## Personal Notes\n"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(content)
        tmp = f.name
    try:
        pipeline = _make_mock_pipeline()
        stats = resolve_linked_articles(tmp, pipeline, max_links=5)
        assert stats["links_found"] == 1
        assert stats["links_filtered_out"] == 1
        assert stats["fetched"] == 0
        mock_extract.assert_not_called()
    finally:
        os.unlink(tmp)


@patch("pipeline.extractors.web_extractor.extract_url")
def test_resolve_success_flow(mock_extract):
    """Full flow: one valid external link -> fetch -> write -> backlink."""
    ref_article = Article(
        url="https://other.com/article",
        title="Referenced Article",
        source=ArticleSource.WEB_URL,
        content_raw="Ref content",
        source_name="link-reference",
    )
    ref_article.relevance_score = 8
    ref_article.compute_hash()
    mock_extract.return_value = ref_article

    content = "---\ntitle: Test\nsource: https://mysite.com/a\n---\n# Test\n\nSee [ref](https://other.com/article).\n\n## Personal Notes\n"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(content)
        tmp = f.name
    try:
        pipeline = _make_mock_pipeline()
        stats = resolve_linked_articles(tmp, pipeline, max_links=5)
        assert stats["links_found"] == 1
        assert stats["fetched"] == 1
        assert stats["written"] == 1
        pipeline.writer.append_references.assert_called_once()
        pipeline.writer.append_referenced_by.assert_called_once()
    finally:
        os.unlink(tmp)
