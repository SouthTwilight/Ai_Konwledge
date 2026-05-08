"""Tests for Feishu document extractor."""
import pytest
from unittest.mock import MagicMock, patch

from pipeline.models import Article, ArticleSource
from pipeline.config import FeishuConfig


# ============================================================
# URL Parsing Tests
# ============================================================

class TestParseFeishuDocId:
    """Tests for parse_feishu_doc_id()."""

    def test_parse_wiki_url(self):
        from pipeline.extractors.feishu_extractor import parse_feishu_doc_id
        url = "https://oigi8odzc5w.feishu.cn/wiki/WBMfwiNkfi6uNFkRtXdcavDzn0e"
        assert parse_feishu_doc_id(url) == "WBMfwiNkfi6uNFkRtXdcavDzn0e"

    def test_parse_docx_url(self):
        from pipeline.extractors.feishu_extractor import parse_feishu_doc_id
        url = "https://test.feishu.cn/docx/ABCD1234"
        assert parse_feishu_doc_id(url) == "ABCD1234"

    def test_parse_docs_url(self):
        from pipeline.extractors.feishu_extractor import parse_feishu_doc_id
        url = "https://test.feishu.cn/docs/XYZ789"
        assert parse_feishu_doc_id(url) == "XYZ789"

    def test_parse_with_query_params(self):
        from pipeline.extractors.feishu_extractor import parse_feishu_doc_id
        url = "https://test.feishu.cn/wiki/DOCID?from=from_copylink"
        assert parse_feishu_doc_id(url) == "DOCID"

    def test_parse_with_trailing_slash(self):
        from pipeline.extractors.feishu_extractor import parse_feishu_doc_id
        url = "https://test.feishu.cn/wiki/DOCID/"
        assert parse_feishu_doc_id(url) == "DOCID"

    def test_parse_invalid_url_not_feishu(self):
        from pipeline.extractors.feishu_extractor import parse_feishu_doc_id
        assert parse_feishu_doc_id("https://google.com") is None

    def test_parse_invalid_url_wrong_path(self):
        from pipeline.extractors.feishu_extractor import parse_feishu_doc_id
        assert parse_feishu_doc_id("https://test.feishu.cn/something/else") is None

    def test_parse_empty_string(self):
        from pipeline.extractors.feishu_extractor import parse_feishu_doc_id
        assert parse_feishu_doc_id("") is None


# ============================================================
# FeishuClient Tests
# ============================================================

class TestFeishuClient:
    """Tests for FeishuClient API interactions."""

    def test_get_token_success(self):
        from pipeline.extractors.feishu_extractor import FeishuClient
        config = FeishuConfig(app_id="test_app", app_secret="test_secret")

        with patch('httpx.Client') as mock_client_cls:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "code": 0,
                "msg": "ok",
                "tenant_access_token": "t-abc123",
                "expire": 7200,
            }
            mock_response.raise_for_status.return_value = None
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            client = FeishuClient(config)
            token = client._get_token()
            assert token == "t-abc123"

    def test_get_token_caching(self):
        from pipeline.extractors.feishu_extractor import FeishuClient
        import time
        config = FeishuConfig(app_id="test_app", app_secret="test_secret")

        client = FeishuClient(config)
        client._token = "t-cached"
        client._token_expires_at = time.time() + 3600  # Still valid

        # Should return cached token without making HTTP call
        token = client._get_token()
        assert token == "t-cached"

    def test_get_raw_content_success(self):
        from pipeline.extractors.feishu_extractor import FeishuClient
        config = FeishuConfig(app_id="test_app", app_secret="test_secret")

        client = FeishuClient(config)
        with patch.object(client, '_get_token', return_value='t-xxx'):
            with patch('httpx.Client') as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "code": 0,
                    "data": {
                        "content": "## Hello World\n\nThis is a test document.",
                    },
                }
                mock_response.raise_for_status.return_value = None
                mock_client = MagicMock()
                mock_client.get.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                content = client.get_raw_content("TESTDOCID")
                assert "Hello World" in content
                assert "test document" in content

    def test_get_raw_content_api_error(self):
        from pipeline.extractors.feishu_extractor import FeishuClient
        config = FeishuConfig(app_id="test_app", app_secret="test_secret")

        client = FeishuClient(config)
        with patch.object(client, '_get_token', return_value='t-xxx'):
            with patch('httpx.Client') as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "code": 99991668,
                    "msg": "document not found",
                }
                mock_response.raise_for_status.return_value = None
                mock_client = MagicMock()
                mock_client.get.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                content = client.get_raw_content("INVALID_ID")
                assert content is None


# ============================================================
# extract_feishu_doc Integration Tests
# ============================================================

class TestExtractFeishuDoc:
    """Tests for the top-level extract_feishu_doc() function."""

    def test_extract_success(self):
        from pipeline.extractors.feishu_extractor import extract_feishu_doc
        config = FeishuConfig(app_id="test", app_secret="secret")

        with patch(
            'pipeline.extractors.feishu_extractor.FeishuClient.get_raw_content',
            return_value="# Test Doc\n\nContent here."
        ):
            article = extract_feishu_doc(
                "https://test.feishu.cn/wiki/DOCID123", config
            )
            assert article is not None
            assert article.source == ArticleSource.FEISHU
            assert article.title == "Test Doc"
            assert "Content here" in article.content_raw

    def test_extract_invalid_url(self):
        from pipeline.extractors.feishu_extractor import extract_feishu_doc
        config = FeishuConfig(app_id="test", app_secret="secret")
        article = extract_feishu_doc("https://google.com", config)
        assert article is None

    def test_extract_api_failure(self):
        from pipeline.extractors.feishu_extractor import extract_feishu_doc
        config = FeishuConfig(app_id="test", app_secret="secret")

        with patch(
            'pipeline.extractors.feishu_extractor.FeishuClient.get_raw_content',
            return_value=None
        ):
            article = extract_feishu_doc(
                "https://test.feishu.cn/wiki/DOCID123", config
            )
            assert article is None

    def test_extract_uses_url_as_source_url(self):
        from pipeline.extractors.feishu_extractor import extract_feishu_doc
        config = FeishuConfig(app_id="test", app_secret="secret")
        url = "https://test.feishu.cn/wiki/DOCID123"

        with patch(
            'pipeline.extractors.feishu_extractor.FeishuClient.get_raw_content',
            return_value="# Title\nBody text."
        ):
            article = extract_feishu_doc(url, config)
            assert article.url == url

    def test_extract_title_from_first_heading(self):
        from pipeline.extractors.feishu_extractor import extract_feishu_doc
        config = FeishuConfig(app_id="test", app_secret="secret")

        with patch(
            'pipeline.extractors.feishu_extractor.FeishuClient.get_raw_content',
            return_value="# My Document Title\n\nSome content here."
        ):
            article = extract_feishu_doc(
                "https://test.feishu.cn/wiki/ABC", config
            )
            assert article.title == "My Document Title"

    def test_extract_fallback_title_when_no_heading(self):
        from pipeline.extractors.feishu_extractor import extract_feishu_doc
        config = FeishuConfig(app_id="test", app_secret="secret")

        with patch(
            'pipeline.extractors.feishu_extractor.FeishuClient.get_raw_content',
            return_value="Just plain text without any heading."
        ):
            article = extract_feishu_doc(
                "https://test.feishu.cn/wiki/ABC", config
            )
            # Should use doc_id as fallback title
            assert article.title == "ABC"
