"""Tests for the end-to-end pipeline (main.py)."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from pipeline.models import Article, ArticleSource, ProcessingLevel
from pipeline.config import PipelineConfig, ModelConfig
from pipeline.main import Pipeline


@pytest.fixture
def mock_config(tmp_path):
    return PipelineConfig(
        model=ModelConfig(api_key="test-key"),
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
