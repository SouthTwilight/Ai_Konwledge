"""L1 Filter — Relevance scoring and classification via GLM-4.7.

Evaluates articles on a 1-10 relevance scale and assigns category tags.
Articles scoring below the threshold are filtered out.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

from openai import OpenAI

from pipeline.models import Article, ProcessingLevel
from pipeline.config import ModelConfig
from pipeline.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a content relevance evaluator for a personal AI knowledge base.
The user is a tech-savvy AI/ML practitioner.

Given an article's title and content, evaluate:
1. relevance_score (1-10) using the rubric below
2. tags (list of 1-3 short tags): Category labels like "ai", "llm", "open-source", "rust", "productivity"
3. language: Detected language code (en, zh, ja, etc.)
4. reason: One-sentence explanation of the score

## Scoring Rubric

### 9-10 (Must Read / 必读)
- Major AI/ML breakthrough announcements, new model releases (GPT, Claude, Gemini, DeepSeek, Qwen)
- Core software engineering paradigm shifts
- Significant open-source releases in AI/ML toolchain (LangChain, PyTorch, transformers, vLLM, llama.cpp)
- Authoritative technical deep-dives with novel insights
- Research papers with immediate practical implications

### 7-8 (Highly Relevant / 高度相关)
- Practical AI/ML tutorials with working code examples
- Developer tool evaluations, comparisons, benchmarks
- LLM integration guides, prompt engineering techniques, RAG patterns
- Significant security vulnerabilities or CVEs
- Performance optimization deep-dives with measurable results
- New programming language features or major framework updates

### 5-6 (Moderately Relevant / 中等相关)
- Tech industry news: funding, acquisitions, product launches
- Startup stories and founder interviews
- General software engineering articles (not AI-specific)
- Tech policy, regulation, or legal analysis
- Career growth, engineering management, productivity advice

### 3-4 (Low Relevance / 低相关)
- Consumer software/app reviews
- General science articles without a tech/engineering angle
- Tech-adjacent culture content
- Hardware/gadget reviews without software engineering relevance

### 1-2 (Irrelevant / 不相关)
- Entertainment, lifestyle, sports, travel
- Historical essays without tech connection
- Political commentary, opinion pieces on non-tech topics

IMPORTANT: You must respond with ONLY a valid JSON object, no other text.
Format: {"relevance_score": <int>, "tags": ["<tag>", ...], "language": "<code>", "reason": "<text>"}
IMPORTANT: The "reason" field MUST be written in Chinese (中文), regardless of the source article language.
"""

USER_PROMPT_TEMPLATE = """\
Title: {title}
Source: {source_name}
Content (first 2000 chars):
{content}
"""


def _extract_json(text: str) -> Optional[str]:
    """Extract JSON object from model response text."""
    if not text:
        return None
    # Try direct parse first
    text = text.strip()
    if text.startswith('{'):
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass
    # Extract JSON with regex
    match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return None


class L1Filter:
    """L1 relevance filter using GLM-4.7 (reasoning model)."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
        )

    def filter_article(self, article: Article) -> Optional[Article]:
        """Evaluate a single article. Returns None if below threshold."""
        content_preview = article.content_raw[:2000] if article.content_raw else article.title

        try:
            response = retry_with_backoff(
                lambda: self.client.chat.completions.create(
                    model=self.config.l1_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                            title=article.title,
                            source_name=article.source_name,
                            content=content_preview,
                        )},
                    ],
                    max_tokens=self.config.max_tokens_l1,
                    temperature=0.1,
                    extra_body={"thinking": {"type": "disabled"}},
                ),
                label=f"L1 filter '{article.title[:30]}'",
            )

            raw = response.choices[0].message.content

            # GLM reasoning model may return content in reasoning_content field
            if not raw:
                reasoning = getattr(response.choices[0].message, 'reasoning_content', None)
                if reasoning:
                    logger.debug(f"L1: content empty, reasoning present ({len(reasoning)} chars)")
                else:
                    logger.warning(f"L1: empty response for '{article.title[:40]}'")
                article.relevance_score = 0
                article.processing_level = ProcessingLevel.L1_FILTERED
                return article

            json_str = _extract_json(raw)
            if not json_str:
                logger.warning(f"L1: no JSON found in response for '{article.title[:40]}': {raw[:200]}")
                article.relevance_score = 0
                article.processing_level = ProcessingLevel.L1_FILTERED
                return article

            result = json.loads(json_str)

            article.relevance_score = int(result.get("relevance_score", 0))
            article.tags = result.get("tags", [])
            article.language = result.get("language", "")
            article.processing_level = ProcessingLevel.L1_FILTERED

            logger.info(
                f"L1: '{article.title[:40]}...' -> score={article.relevance_score}, "
                f"tags={article.tags}, reason={result.get('reason', '')}"
            )
            return article

        except Exception as e:
            logger.error(f"L1 API error for '{article.title}': {e}")
            # On API failure, pass through to avoid data loss
            article.relevance_score = 5
            article.processing_level = ProcessingLevel.L1_FILTERED
            return article

    def _assign_tier(self, score: int, tier_discard_max: int, tier_compressed_max: int) -> str:
        """Assign content tier based on relevance score."""
        if score <= tier_discard_max:
            return "discard"
        elif score <= tier_compressed_max:
            return "compressed"
        else:
            return "detailed"

    def filter_batch(
        self, articles: List[Article], config
    ) -> List[Article]:
        """Filter a batch of articles. Assigns tiers, returns only compressed+detailed."""
        filtered = []
        discarded = 0
        for article in articles:
            scored = self.filter_article(article)
            if scored and scored.relevance_score > 0:
                scored.content_tier = self._assign_tier(
                    scored.relevance_score, config.tier_discard_max, config.tier_compressed_max
                )
                if scored.content_tier == "discard":
                    discarded += 1
                    logger.info(
                        f"L1 discarded (score={scored.relevance_score}): "
                        f"'{article.title[:40]}...'"
                    )
                else:
                    filtered.append(scored)
            else:
                discarded += 1
        logger.info(
            f"L1 batch: {len(articles)} in -> {len(filtered)} passed, {discarded} discarded "
            f"(discard<={config.tier_discard_max}, compressed<={config.tier_compressed_max})"
        )
        return filtered
