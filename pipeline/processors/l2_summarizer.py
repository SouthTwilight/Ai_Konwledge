"""L2 Summarizer — Structured summary generation via DeepSeek-R1.

Produces a structured summary with key points, one-line TL;DR,
and related topics for each article that passed L1 filtering.
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
You are a technical content summarizer for a personal knowledge base.

Given an article's title and full content, produce a structured summary.

Respond in JSON only with these fields:
{
  "tldr": "One-sentence summary (max 30 words)",
  "summary": "3-5 sentence structured summary covering the main points",
  "key_points": ["Point 1", "Point 2", ...],
  "related_topics": ["topic1", "topic2"]
}

Rules:
- tldr: Maximum 30 words, capture the essence
- summary: 3-5 sentences, cover what/why/how
- key_points: 3-5 bullet points, each a standalone insight
- related_topics: 2-4 topics this relates to (for knowledge graph linking)
- Write in the same language as the source article
- Be factual, no speculation
"""

USER_PROMPT_TEMPLATE = """\
Title: {title}
Tags: {tags}
Content:
{content}
"""


class L2Summarizer:
    """L2 structured summarizer using DeepSeek-R1 (deepseek-reasoner)."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
        )

    def summarize_article(self, article: Article) -> Article:
        """Generate structured summary for a single article."""
        content = article.content_raw or article.content_clean or ""
        # Truncate to avoid token limits (roughly 4 chars per token)
        max_chars = self.config.max_tokens_l2 * 3
        if len(content) > max_chars:
            content = content[:max_chars] + "\n[...truncated]"

        try:
            response = self.client.chat.completions.create(
                model=self.config.l2_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                        title=article.title,
                        tags=", ".join(article.tags) if article.tags else "none",
                        content=content,
                    )},
                ],
                max_tokens=self.config.max_tokens_l2,
                temperature=0.3,
            )

            raw = response.choices[0].message.content
            # DeepSeek-R1 includes <think/> blocks — extract JSON after closing tag
            json_str = self._extract_json(raw)
            result = json.loads(json_str)

            article.content_summary = result.get("summary", "")
            article.key_points = result.get("key_points", [])
            article.related_topics = result.get("related_topics", [])
            article.processing_level = ProcessingLevel.L2_SUMMARIZED

            # Store TL;DR as first key point prefix for quick display
            tldr = result.get("tldr", "")
            if tldr:
                article.content_summary = f"**TL;DR:** {tldr}\n\n{article.content_summary}"

            logger.info(f"L2: '{article.title[:40]}...' → summary generated "
                        f"({len(article.key_points)} key points)")
            return article

        except json.JSONDecodeError as e:
            logger.warning(f"L2 JSON parse error for '{article.title}': {e}")
            article.content_summary = raw[:500] if raw else ""
            article.processing_level = ProcessingLevel.L2_SUMMARIZED
            return article
        except Exception as e:
            logger.error(f"L2 API error for '{article.title}': {e}")
            article.content_summary = f"[Summary generation failed: {str(e)[:100]}]"
            article.processing_level = ProcessingLevel.L2_SUMMARIZED
            return article

    def summarize_batch(self, articles: List[Article]) -> List[Article]:
        """Generate summaries for a batch of articles."""
        results = []
        for article in articles:
            summarized = self.summarize_article(article)
            results.append(summarized)
        logger.info(f"L2 batch: {len(articles)} articles summarized")
        return results

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from DeepSeek-R1 response (may contain <think/> blocks)."""
        # Strip <think...</think?> blocks
        import re
        # Remove think blocks
        cleaned = re.sub(r'<think\b[^>]*>.*?</think\s*>', '', text, flags=re.DOTALL)
        # Try to find JSON object
        match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
        if match:
            return match.group(0)
        # Fallback: return cleaned text
        return cleaned.strip()
