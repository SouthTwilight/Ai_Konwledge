"""L1 Filter — Relevance scoring and classification via DeepSeek-V3.

Evaluates articles on a 1-10 relevance scale and assigns category tags.
Articles scoring below the threshold are filtered out.
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from openai import OpenAI

from pipeline.models import Article, ProcessingLevel
from pipeline.config import ModelConfig

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a content relevance evaluator for a personal AI knowledge base.

Given an article's title and content, evaluate:
1. relevance_score (1-10): How relevant is this to a tech-savvy AI/ML practitioner?
   - 8-10: Highly relevant — directly about AI/ML, software engineering, or developer tools
   - 5-7: Moderately relevant — tangentially related (startup news, tech policy, etc.)
   - 1-4: Low relevance — general news, unrelated topics, clickbait
2. tags (list of 1-3 short tags): Category labels like "ai", "llm", "open-source", "rust", "productivity"
3. language: Detected language code (en, zh, ja, etc.)
4. reason: One-sentence explanation of the score

Respond in JSON only:
{"relevance_score": <int>, "tags": ["<tag>", ...], "language": "<code>", "reason": "<text>"}
"""

USER_PROMPT_TEMPLATE = """\
Title: {title}
Source: {source_name}
Content (first 2000 chars):
{content}
"""


class L1Filter:
    """L1 relevance filter using DeepSeek-V3 (deepseek-chat)."""

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
            response = self.client.chat.completions.create(
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
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            result = json.loads(raw)

            article.relevance_score = int(result.get("relevance_score", 0))
            article.tags = result.get("tags", [])
            article.language = result.get("language", "")
            article.processing_level = ProcessingLevel.L1_FILTERED

            logger.info(
                f"L1: '{article.title[:40]}...' → score={article.relevance_score}, "
                f"tags={article.tags}, reason={result.get('reason', '')}"
            )
            return article

        except json.JSONDecodeError as e:
            logger.warning(f"L1 JSON parse error for '{article.title}': {e}")
            # Default: pass through with score 0
            article.relevance_score = 0
            article.processing_level = ProcessingLevel.L1_FILTERED
            return article
        except Exception as e:
            logger.error(f"L1 API error for '{article.title}': {e}")
            # On API failure, pass through to avoid data loss
            article.relevance_score = 5
            article.processing_level = ProcessingLevel.L1_FILTERED
            return article

    def filter_batch(
        self, articles: List[Article], threshold: int = 6
    ) -> List[Article]:
        """Filter a batch of articles. Only keeps those >= threshold."""
        filtered = []
        for article in articles:
            scored = self.filter_article(article)
            if scored and scored.relevance_score >= threshold:
                filtered.append(scored)
            else:
                logger.info(
                    f"L1 filtered out: '{article.title[:40]}...' "
                    f"(score={article.relevance_score})"
                )
        logger.info(
            f"L1 batch: {len(articles)} in → {len(filtered)} passed "
            f"(threshold={threshold})"
        )
        return filtered
