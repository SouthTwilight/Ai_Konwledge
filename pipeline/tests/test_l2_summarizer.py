"""Tests for L2 Summarizer processor."""
import json
import pytest
from unittest.mock import patch, MagicMock

from pipeline.models import Article, ArticleSource, ProcessingLevel
from pipeline.config import LevelModelConfig
from pipeline.processors.l2_summarizer import L2Summarizer, _extract_json


@pytest.fixture
def l1_article():
    """Article that has passed L1 filtering."""
    return Article(
        url="https://example.com/llm-article",
        title="GPT-5 Released with Major Improvements",
        source=ArticleSource.RSS,
        content_raw="OpenAI has released GPT-5, the latest generation of their "
                    "large language model. The new model shows 10x improvements "
                    "in reasoning, coding, and multimodal understanding. Key features "
                    "include native tool use, 1M context window, and real-time learning.",
        source_name="TechNews",
        relevance_score=9,
        tags=["ai", "llm"],
        processing_level=ProcessingLevel.L1_FILTERED,
        content_tier="compressed",
    )


@pytest.fixture
def summarizer():
    config = LevelModelConfig(api_key="test-key", model="glm-4.7", max_tokens=4096)
    return L2Summarizer(config)


def _mock_summary_response(tldr, summary, key_points, related_topics):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps({
        "tldr": tldr,
        "summary": summary,
        "key_points": key_points,
        "related_topics": related_topics,
    })
    # No reasoning_content for normal response
    mock_resp.choices[0].message.reasoning_content = None
    return mock_resp


def _mock_think_response(tldr, summary, key_points, related_topics):
    """Simulate model response with <think/> block (compatibility test)."""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    body = json.dumps({
        "tldr": tldr,
        "summary": summary,
        "key_points": key_points,
        "related_topics": related_topics,
    })
    mock_resp.choices[0].message.content = f"<think\nLet me analyze this...\nThe key points are...\n</think\n{body}"
    mock_resp.choices[0].message.reasoning_content = None
    return mock_resp


class TestL2Summarizer:

    @patch("pipeline.processors.l2_summarizer.OpenAI")
    def test_basic_summary(self, mock_openai_cls, l1_article, summarizer):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_summary_response(
            "GPT-5 released with 10x performance gains.",
            "OpenAI released GPT-5 with major improvements in reasoning and coding.",
            ["10x reasoning improvement", "1M context window", "Real-time learning"],
            ["openai", "llm", "gpt"],
        )
        summarizer.client = mock_client

        result = summarizer.summarize_article(l1_article)
        assert result.processing_level == ProcessingLevel.L2_SUMMARIZED
        assert "TL;DR" in result.content_summary
        assert len(result.key_points) == 3
        assert len(result.related_topics) == 3

    @patch("pipeline.processors.l2_summarizer.OpenAI")
    def test_think_block_compatibility(self, mock_openai_cls, l1_article, summarizer):
        """Verify <think/> blocks are correctly stripped."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_think_response(
            "GPT-5 released.",
            "Summary text.",
            ["Point 1"],
            ["ai"],
        )
        summarizer.client = mock_client

        result = summarizer.summarize_article(l1_article)
        assert result.processing_level == ProcessingLevel.L2_SUMMARIZED
        assert "TL;DR" in result.content_summary

    @patch("pipeline.processors.l2_summarizer.OpenAI")
    def test_api_error_graceful(self, mock_openai_cls, l1_article, summarizer):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Network error")
        summarizer.client = mock_client

        result = summarizer.summarize_article(l1_article)
        assert result.processing_level == ProcessingLevel.L2_SUMMARIZED
        assert "failed" in result.content_summary.lower()

    def test_extract_json_pure(self):
        text = '{"tldr": "test", "summary": "hello"}'
        assert _extract_json(text) == text

    def test_extract_json_with_think_block(self):
        text = '<think\nreasoning here\n</think\n{"tldr": "test"}'
        result = _extract_json(text)
        parsed = json.loads(result)
        assert parsed["tldr"] == "test"
