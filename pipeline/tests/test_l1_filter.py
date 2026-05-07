"""Tests for L1 Filter processor."""
import json
import pytest
from unittest.mock import patch, MagicMock

from pipeline.models import Article, ArticleSource, ProcessingLevel
from pipeline.config import ModelConfig
from pipeline.processors.l1_filter import L1Filter


@pytest.fixture
def sample_article():
    return Article(
        url="https://example.com/test-llm-article",
        title="GPT-5 Released with 10x Performance Gains",
        source=ArticleSource.RSS,
        content_raw="OpenAI has released GPT-5, the latest generation of their "
                    "large language model. The new model shows 10x improvements "
                    "in reasoning, coding, and multimodal understanding...",
        source_name="TechNews",
    )


@pytest.fixture
def l1_filter():
    config = ModelConfig(api_key="test-key")
    return L1Filter(config)


def _mock_response(score, tags, language="en", reason="test"):
    """Create a mock OpenAI response."""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps({
        "relevance_score": score,
        "tags": tags,
        "language": language,
        "reason": reason,
    })
    return mock_resp


class TestL1Filter:

    @patch("pipeline.processors.l1_filter.OpenAI")
    def test_high_relevance_passes(self, mock_openai_cls, sample_article, l1_filter):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(
            9, ["ai", "llm"]
        )
        l1_filter.client = mock_client

        result = l1_filter.filter_article(sample_article)
        assert result.relevance_score == 9
        assert result.tags == ["ai", "llm"]
        assert result.processing_level == ProcessingLevel.L1_FILTERED

    @patch("pipeline.processors.l1_filter.OpenAI")
    def test_low_relevance_keeps_article_but_low_score(self, mock_openai_cls, sample_article, l1_filter):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(
            2, ["gossip"]
        )
        l1_filter.client = mock_client

        result = l1_filter.filter_article(sample_article)
        assert result.relevance_score == 2

    @patch("pipeline.processors.l1_filter.OpenAI")
    def test_batch_filter_threshold(self, mock_openai_cls):
        config = ModelConfig(api_key="test-key")
        f = L1Filter(config)
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        articles = [
            Article(url=f"https://example.com/{i}", title=f"Article {i}",
                    source=ArticleSource.RSS, content_raw="AI content " * 50)
            for i in range(5)
        ]

        # Scores: 9, 7, 5, 3, 1  → threshold=6 keeps first 2
        scores = [9, 7, 5, 3, 1]
        responses = [_mock_response(s, ["ai"]) for s in scores]
        mock_client.chat.completions.create.side_effect = responses

        f.client = mock_client
        results = f.filter_batch(articles, threshold=6)
        assert len(results) == 2

    @patch("pipeline.processors.l1_filter.OpenAI")
    def test_api_error_passes_through(self, mock_openai_cls, sample_article, l1_filter):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API down")
        l1_filter.client = mock_client

        result = l1_filter.filter_article(sample_article)
        assert result.relevance_score == 5  # Default on error
        assert result.processing_level == ProcessingLevel.L1_FILTERED
