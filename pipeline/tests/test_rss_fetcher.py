import pytest
from unittest.mock import patch, MagicMock
from pipeline.extractors.rss_fetcher import fetch_rss, _extract_content
from pipeline.config import RSSSource
from pipeline.models import ArticleSource


def test_extract_content_returns_string():
    """Test _extract_content returns empty string on failure."""
    with patch('pipeline.extractors.rss_fetcher.trafilatura') as mock_traf:
        mock_traf.fetch_url.return_value = None
        result = _extract_content('https://bad-url.example.com')
        assert result == ""


def test_fetch_rss_empty_feed():
    """Test handling of empty RSS feed."""
    source = RSSSource(name="test", url="https://example.com/rss")
    with patch('pipeline.extractors.rss_fetcher.feedparser') as mock_fp:
        mock_fp.parse.return_value = MagicMock(entries=[])
        articles = fetch_rss(source)
        assert articles == []


def test_fetch_rss_with_entries():
    """Test parsing RSS entries into Article objects."""
    source = RSSSource(name="test", url="https://example.com/rss", max_articles=2)
    mock_entry = {
        'link': 'https://example.com/article1',
        'title': 'Test Article',
        'author': 'Test Author',
        'summary': 'Summary text',
    }
    with patch('pipeline.extractors.rss_fetcher.feedparser') as mock_fp, \
         patch('pipeline.extractors.rss_fetcher._extract_content') as mock_ext:
        mock_fp.parse.return_value = MagicMock(entries=[mock_entry])
        mock_ext.return_value = 'Full article content here'
        articles = fetch_rss(source)
    
    assert len(articles) == 1
    assert articles[0].title == 'Test Article'
    assert articles[0].source == ArticleSource.RSS
    assert articles[0].content_raw == 'Full article content here'
    assert articles[0].content_hash != ""
    assert articles[0].source_name == 'test'


def test_fetch_rss_skips_no_link():
    """Entries without links are skipped."""
    source = RSSSource(name="test", url="https://example.com/rss")
    mock_entry = {'title': 'No Link Article'}
    with patch('pipeline.extractors.rss_fetcher.feedparser') as mock_fp:
        mock_fp.parse.return_value = MagicMock(entries=[mock_entry])
        articles = fetch_rss(source)
    assert len(articles) == 0
