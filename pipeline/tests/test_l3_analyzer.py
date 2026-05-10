"""Tests for L3 Deep Analyzer."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest

from pipeline.models import Article, ArticleSource, ProcessingLevel
from pipeline.config import LevelModelConfig
from pipeline.processors.l3_analyzer import L3Analyzer, _extract_json


# --- Fixtures ---

MOCK_L3_RESPONSE = json.dumps({
    "concepts": [
        {"name": "Transformer架构", "definition": "基于自注意力机制的深度学习模型架构"},
        {"name": "分布式训练", "definition": "将模型训练任务分散到多个计算节点上并行执行"},
        {"name": "MoE", "definition": "混合专家模型，通过稀疏激活降低推理成本"},
    ],
    "structure_type": "analysis",
    "key_insight": "大模型训练已从单机密集计算转向分布式多节点协作",
    "assumptions": ["读者了解深度学习基础", "关注训练效率而非推理性能"],
    "position": "技术乐观主义者，认为分布式训练是大模型发展的必然方向",
})


def _mock_config():
    return LevelModelConfig(api_key="test-key", model="glm-5.1", max_tokens=8192)


def _make_detailed_article():
    return Article(
        url="https://example.com/deep-article",
        title="大模型训练技术深度解析",
        source=ArticleSource.RSS,
        content_raw="这是一篇关于大模型训练技术的深度文章..." * 50,
        content_summary="本文详细分析了大模型训练中的关键技术...",
        source_name="TechBlog",
        relevance_score=9,
        content_tier="detailed",
        tags=["ai", "llm", "training"],
        processing_level=ProcessingLevel.L2_SUMMARIZED,
        key_points=["Transformer架构是基础", "分布式训练是关键"],
        related_topics=["大语言模型", "分布式计算"],
    )


# --- Tests: _extract_json ---

def test_extract_json_plain():
    text = '{"key": "value"}'
    assert _extract_json(text) == text


def test_extract_json_with_think_block():
    text = '<think type="text">reasoning here</think {"key": "value"}'
    result = _extract_json(text)
    assert result is not None
    assert json.loads(result)["key"] == "value"


def test_extract_json_empty():
    assert _extract_json("") is None
    assert _extract_json(None) is None


def test_extract_json_invalid():
    assert _extract_json("not json at all") is None


# --- Tests: L3Analyzer.analyze_article ---

def test_analyze_article_success():
    config = _mock_config()
    analyzer = L3Analyzer(config)
    article = _make_detailed_article()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = MOCK_L3_RESPONSE

    with patch.object(analyzer.client.chat.completions, "create", return_value=mock_response):
        result = analyzer.analyze_article(article)

    assert len(result.l3_concepts) == 3
    assert result.l3_structure_type == "analysis"
    assert "分布式" in result.l3_key_insight
    assert result.content_deep != ""
    assert "核心洞见" in result.content_deep
    assert "核心概念" in result.content_deep
    assert "Transformer架构" in result.content_deep
    assert result.processing_level == ProcessingLevel.L3_DEEP


def test_analyze_article_empty_response():
    config = _mock_config()
    analyzer = L3Analyzer(config)
    article = _make_detailed_article()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.reasoning_content = None

    with patch.object(analyzer.client.chat.completions, "create", return_value=mock_response):
        result = analyzer.analyze_article(article)

    # Should return article unchanged
    assert result.l3_concepts == []
    assert result.processing_level == ProcessingLevel.L2_SUMMARIZED


def test_analyze_article_invalid_json():
    config = _mock_config()
    analyzer = L3Analyzer(config)
    article = _make_detailed_article()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is not JSON at all"

    with patch.object(analyzer.client.chat.completions, "create", return_value=mock_response):
        result = analyzer.analyze_article(article)

    assert result.l3_concepts == []


def test_analyze_article_api_error():
    config = _mock_config()
    analyzer = L3Analyzer(config)
    article = _make_detailed_article()

    with patch.object(analyzer.client.chat.completions, "create", side_effect=Exception("API Error")):
        result = analyzer.analyze_article(article)

    # Should return article unchanged, no crash
    assert result.l3_concepts == []
    assert result.processing_level == ProcessingLevel.L2_SUMMARIZED


def test_analyze_article_content_truncation():
    config = _mock_config()
    analyzer = L3Analyzer(config)
    article = _make_detailed_article()
    # Make content very long
    article.content_raw = "x" * 100000

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = MOCK_L3_RESPONSE

    with patch.object(analyzer.client.chat.completions, "create", return_value=mock_response) as mock_create:
        result = analyzer.analyze_article(article)

        # Check that content was truncated
        call_args = mock_create.call_args
        user_msg = call_args[1]["messages"][1]["content"]
        assert len(user_msg) < 100000
    assert len(result.l3_concepts) == 3


def test_analyze_article_concepts_in_output():
    config = _mock_config()
    analyzer = L3Analyzer(config)
    article = _make_detailed_article()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = MOCK_L3_RESPONSE

    with patch.object(analyzer.client.chat.completions, "create", return_value=mock_response):
        result = analyzer.analyze_article(article)

    # Check content_deep includes concepts with bold names
    assert "**Transformer架构**" in result.content_deep
    assert "**分布式训练**" in result.content_deep
    # Check assumptions section
    assert "前提假设" in result.content_deep
    # Check position
    assert "作者立场" in result.content_deep


# --- Tests: L3Analyzer.analyze_batch ---

def test_analyze_batch():
    config = _mock_config()
    analyzer = L3Analyzer(config)
    articles = [_make_detailed_article() for _ in range(3)]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = MOCK_L3_RESPONSE

    with patch.object(analyzer.client.chat.completions, "create", return_value=mock_response):
        results = analyzer.analyze_batch(articles)

    assert len(results) == 3
    assert all(len(a.l3_concepts) == 3 for a in results)


def test_analyze_batch_mixed_success_failure():
    config = _mock_config()
    analyzer = L3Analyzer(config)

    article1 = _make_detailed_article()
    article2 = _make_detailed_article()

    call_count = 0
    def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = MOCK_L3_RESPONSE
            return resp
        else:
            raise Exception("API Error")

    with patch.object(analyzer.client.chat.completions, "create", side_effect=mock_create):
        results = analyzer.analyze_batch([article1, article2])

    assert len(results) == 2
    assert len(results[0].l3_concepts) == 3  # succeeded
    assert results[1].l3_concepts == []  # failed gracefully
