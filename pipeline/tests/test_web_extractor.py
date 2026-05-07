import pytest
from unittest.mock import patch, MagicMock
from pipeline.extractors.web_extractor import extract_url, extract_urls
from pipeline.models import ArticleSource


def test_extract_url_success():
    """Test successful URL extraction."""
    with patch('pipeline.extractors.web_extractor.trafilatura') as mock_traf:
        mock_traf.fetch_url.return_value = '<html><body>Content</body></html>'
        mock_traf.extract.side_effect = [
            'Clean article text',  # First call: content extraction
            '{"title":"Test","author":"Author","date":"2026-01-01"}',  # Second: metadata
        ]
        article = extract_url('https://example.com/article')

    assert article is not None
    assert article.title == 'Test'
    assert article.content_raw == 'Clean article text'
    assert article.source == ArticleSource.WEB_URL
    assert article.content_hash != ""


def test_extract_url_failure():
    """Test URL extraction failure returns None."""
    with patch('pipeline.extractors.web_extractor.trafilatura') as mock_traf:
        mock_traf.fetch_url.return_value = None
        result = extract_url('https://bad.example.com')
    assert result is None


def test_extract_urls_multiple():
    """Test batch URL extraction."""
    with patch('pipeline.extractors.web_extractor.extract_url') as mock_extract:
        mock_extract.side_effect = [
            MagicMock(url='https://a.com', source=ArticleSource.WEB_URL),
            None,  # Second URL fails
            MagicMock(url='https://c.com', source=ArticleSource.WEB_URL),
        ]
        articles = extract_urls(['https://a.com', 'https://b.com', 'https://c.com'])

    assert len(articles) == 2  # Only successful extractions
