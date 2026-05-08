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
