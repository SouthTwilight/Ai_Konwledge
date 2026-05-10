"""Tests for Web Content Extractor (with title fallback chain)."""
import pytest
from unittest.mock import patch, MagicMock
from pipeline.extractors.web_extractor import (
    extract_url,
    extract_urls,
    _extract_title_from_html,
)
from pipeline.models import ArticleSource


# --- Tests: _extract_title_from_html ---

def test_title_from_title_tag():
    html = '<html><head><title>My Article Title</title></head><body></body></html>'
    assert _extract_title_from_html(html) == "My Article Title"


def test_title_from_title_tag_with_suffix():
    html = '<html><head><title>My Article - Blog Name</title></head><body></body></html>'
    assert _extract_title_from_html(html) == "My Article"


def test_title_from_h1_fallback():
    html = '<html><head><title></title></head><body><h1>H1 Title</h1></body></html>'
    assert _extract_title_from_html(html) == "H1 Title"


def test_title_empty_when_nothing():
    html = '<html><body><p>Just a paragraph</p></body></html>'
    assert _extract_title_from_html(html) == ""


# --- Tests: extract_url ---

def test_extract_url_success():
    with patch('pipeline.extractors.web_extractor.trafilatura') as mock_traf:
        mock_traf.fetch_url.return_value = '<html><body>Content</body></html>'
        mock_traf.extract.side_effect = [
            'Clean article text',
            '{"title":"Test","author":"Author","date":"2026-01-01"}',
        ]
        article = extract_url('https://example.com/article')

    assert article is not None
    assert article.title == 'Test'
    assert article.content_raw == 'Clean article text'
    assert article.source == ArticleSource.WEB_URL
    assert article.content_hash != ""


def test_extract_url_failure():
    with patch('pipeline.extractors.web_extractor.trafilatura') as mock_traf:
        mock_traf.fetch_url.return_value = None
        result = extract_url('https://bad.example.com')
    assert result is None


def test_extract_urls_multiple():
    with patch('pipeline.extractors.web_extractor.extract_url') as mock_extract:
        mock_extract.side_effect = [
            MagicMock(url='https://a.com', source=ArticleSource.WEB_URL),
            None,
            MagicMock(url='https://c.com', source=ArticleSource.WEB_URL),
        ]
        articles = extract_urls(['https://a.com', 'https://b.com', 'https://c.com'])
    assert len(articles) == 2


def test_extract_url_title_fallback_to_html():
    """When trafilatura returns no title, fallback to HTML <title>."""
    with patch('pipeline.extractors.web_extractor.trafilatura') as mock_traf:
        mock_traf.fetch_url.return_value = '<html><head><title>HTML Title</title></head><body>Content</body></html>'
        mock_traf.extract.side_effect = [
            'article content',
            '',  # metadata (empty)
        ]
        article = extract_url('https://example.com/article')

    assert article is not None
    assert article.title == 'HTML Title'


def test_extract_url_title_fallback_to_url_slug():
    """When all title sources fail, use URL slug."""
    with patch('pipeline.extractors.web_extractor.trafilatura') as mock_traf:
        mock_traf.fetch_url.return_value = '<html><body>Content</body></html>'
        mock_traf.extract.side_effect = [
            'article content',
            '',
        ]
        article = extract_url('https://example.com/my-article-title')

    assert article is not None
    assert article.title == 'my article title'


def test_extract_url_title_fallback_to_h1():
    """When <title> is empty but <h1> exists, use h1."""
    with patch('pipeline.extractors.web_extractor.trafilatura') as mock_traf:
        mock_traf.fetch_url.return_value = '<html><head><title></title></head><body><h1>Page Heading</h1><p>Content</p></body></html>'
        mock_traf.extract.side_effect = [
            'article text',
            '',
        ]
        article = extract_url('https://example.com/page')

    assert article is not None
    assert article.title == 'Page Heading'


def test_extract_url_no_content_returns_none():
    """When trafilatura can't extract content, return None."""
    with patch('pipeline.extractors.web_extractor.trafilatura') as mock_traf:
        mock_traf.fetch_url.return_value = '<html><body></body></html>'
        mock_traf.extract.side_effect = [
            None,  # content extraction fails
            '',
        ]
        result = extract_url('https://example.com/empty')

    assert result is None
