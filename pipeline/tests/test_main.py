"""Tests for the end-to-end pipeline (main.py)."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from pipeline.models import Article, ArticleSource, ProcessingLevel
from pipeline.config import PipelineConfig, LevelModelConfig, FeishuConfig, EmailConfig
from pipeline.main import Pipeline


@pytest.fixture
def mock_config(tmp_path):
    return PipelineConfig(
        l1_model=LevelModelConfig(api_key="test-key", model="glm-4.7", max_tokens=1024),
        l2_model=LevelModelConfig(api_key="test-key", model="glm-4.7", max_tokens=4096),
        l3_model=LevelModelConfig(api_key="test-key", model="glm-5.1", max_tokens=8192),
        feishu=FeishuConfig(app_id="test_app", app_secret="test_secret"),
        email=EmailConfig(
            imap_server="imap.test.com",
            username="test@test.com",
            app_password="test-pass",
            sender_whitelist=["test.com"],
        ),
        vault_path=tmp_path / "vault",
        dedup_db_path=":memory:",
        tier_discard_max=3,
        tier_compressed_max=6,
        rss_sources=[],
    )


@pytest.fixture
def sample_articles():
    return [
        Article(
            url=f"https://example.com/article-{i}",
            title=f"Test Article {i}",
            source=ArticleSource.RSS,
            content_raw=f"This is test article {i} about AI and machine learning. " * 20,
            source_name="TestFeed",
            content_tier="compressed",
        )
        for i in range(3)
    ]


class TestPipeline:

    @patch("pipeline.main.L2Summarizer")
    @patch("pipeline.main.L1Filter")
    @patch("pipeline.main.extract_url")
    def test_url_source(self, mock_extract, mock_l1_cls, mock_l2_cls, mock_config, sample_articles):
        article = sample_articles[0]
        article.relevance_score = 9
        article.content_tier = "detailed"
        article.tags = ["ai"]
        article.processing_level = ProcessingLevel.L1_FILTERED
        mock_extract.return_value = article

        mock_l1 = MagicMock()
        mock_l1.filter_batch.return_value = [article]
        mock_l1_cls.return_value = mock_l1

        mock_l2 = MagicMock()
        article_l2 = article
        article_l2.content_summary = "Summary"
        article_l2.key_points = ["point 1"]
        article_l2.processing_level = ProcessingLevel.L2_SUMMARIZED
        mock_l2.summarize_batch.return_value = [article_l2]
        mock_l2_cls.return_value = mock_l2

        p = Pipeline(mock_config)
        stats = p.run(source="url", url="https://example.com/test")

        assert stats["fetched"] == 1
        assert stats["new"] == 1
        assert stats["written"] == 1

    def test_dry_run(self, mock_config, sample_articles):
        p = Pipeline(mock_config)

        with patch.object(p, '_extract', return_value=sample_articles):
            stats = p.run(dry_run=True)

        assert stats["fetched"] == 3
        assert stats["new"] == 3
        assert stats["written"] == 0  # dry run skips writing

    def test_no_new_articles(self, mock_config):
        p = Pipeline(mock_config)

        with patch.object(p, '_extract', return_value=[]):
            stats = p.run()

        assert stats["fetched"] == 0
        assert stats["written"] == 0

    def test_limit(self, mock_config, sample_articles):
        p = Pipeline(mock_config)

        with patch.object(p, '_extract', return_value=sample_articles):
            stats = p.run(dry_run=True, limit=2)

        assert stats["new"] == 2  # Limited to 2

    @patch("pipeline.main.L2Summarizer")
    @patch("pipeline.main.L1Filter")
    @patch("pipeline.extractors.feishu_extractor.FeishuClient.get_raw_content")
    def test_feishu_source(self, mock_get_raw, mock_l1_cls, mock_l2_cls, mock_config):
        mock_get_raw.return_value = "# Feishu Test Doc\n\nContent from Feishu."

        article = Article(
            url="https://test.feishu.cn/wiki/DOCID",
            title="Feishu Test Doc",
            source=ArticleSource.FEISHU,
            content_raw="# Feishu Test Doc\n\nContent from Feishu.",
            source_name="feishu",
            relevance_score=8,
            content_tier="detailed",
            processing_level=ProcessingLevel.L1_FILTERED,
            tags=["feishu"],
        )

        mock_l1 = MagicMock()
        mock_l1.filter_batch.return_value = [article]
        mock_l1_cls.return_value = mock_l1

        mock_l2 = MagicMock()
        article_l2 = article
        article_l2.content_summary = "Feishu summary"
        article_l2.processing_level = ProcessingLevel.L2_SUMMARIZED
        mock_l2.summarize_batch.return_value = [article_l2]
        mock_l2_cls.return_value = mock_l2

        p = Pipeline(mock_config)
        stats = p.run(source="feishu", feishu_url="https://test.feishu.cn/wiki/DOCID")

        assert stats["fetched"] == 1
        assert stats["written"] == 1

    @patch("pipeline.main.L2Summarizer")
    @patch("pipeline.main.L1Filter")
    @patch("pipeline.extractors.github_extractor.httpx.get")
    def test_github_source(self, mock_httpx, mock_l1_cls, mock_l2_cls, mock_config):
        """Test --source github extracts project info and processes them."""
        def mock_get(url, **kwargs):
            if "/readme" in url:
                return MagicMock(
                    status_code=200, text="# Test Project\n\nA test project.",
                    headers={}, raise_for_status=MagicMock(), json=MagicMock(return_value={}),
                )
            # repo info
            return MagicMock(
                status_code=200,
                json=lambda: {
                    "description": "Test project",
                    "topics": ["test"],
                    "language": "Python",
                    "stargazers_count": 100,
                    "html_url": "https://github.com/user/repo",
                    "homepage": "",
                    "fork": False,
                },
                headers={}, raise_for_status=MagicMock(),
            )

        mock_httpx.side_effect = mock_get

        article = Article(
            url="https://github.com/user/repo",
            title="repo: Test project",
            source=ArticleSource.GITHUB,
            content_raw="# Test Project\n\nA test project.",
            source_name="user/repo",
            relevance_score=8,
            content_tier="detailed",
            processing_level=ProcessingLevel.L1_FILTERED,
            tags=["github", "python"],
        )

        mock_l1 = MagicMock()
        mock_l1.filter_batch.return_value = [article]
        mock_l1_cls.return_value = mock_l1

        mock_l2 = MagicMock()
        article.content_summary = "Summary"
        article.processing_level = ProcessingLevel.L2_SUMMARIZED
        mock_l2.summarize_batch.return_value = [article]
        mock_l2_cls.return_value = mock_l2

        p = Pipeline(mock_config)
        stats = p.run(source="github", github_repos=["user/repo"])

        assert stats["fetched"] >= 1
        assert stats["written"] >= 1

    @patch("pipeline.main.L2Summarizer")
    @patch("pipeline.main.L1Filter")
    @patch("imaplib.IMAP4_SSL")
    def test_email_source(self, mock_imap, mock_l1_cls, mock_l2_cls, mock_config):
        """Test --source email extracts newsletters and processes them."""
        from email.mime.text import MIMEText

        mock_mail = MagicMock()
        mock_mail.search.return_value = ("OK", [b"1"])
        msg = MIMEText("Newsletter content here.")
        msg["Subject"] = "Test Newsletter"
        msg["From"] = "news@test.com"
        msg["Date"] = "Sat, 10 May 2026 08:00:00 +0000"
        msg["Message-ID"] = "<test@test.com>"
        mock_mail.fetch.return_value = ("OK", [(b"1 (RFC822 {123}", msg.as_bytes()), b")"])
        mock_imap.return_value = mock_mail

        article = Article(
            url="email://abc123",
            title="Test Newsletter",
            source=ArticleSource.EMAIL,
            content_raw="Newsletter content here.",
            source_name="news@test.com",
            relevance_score=7,
            content_tier="compressed",
            processing_level=ProcessingLevel.L1_FILTERED,
            tags=["newsletter"],
        )

        mock_l1 = MagicMock()
        mock_l1.filter_batch.return_value = [article]
        mock_l1_cls.return_value = mock_l1

        mock_l2 = MagicMock()
        article.content_summary = "Summary"
        article.processing_level = ProcessingLevel.L2_SUMMARIZED
        mock_l2.summarize_batch.return_value = [article]
        mock_l2_cls.return_value = mock_l2

        p = Pipeline(mock_config)
        stats = p.run(source="email")

        assert stats["fetched"] >= 1
        assert stats["written"] >= 1
