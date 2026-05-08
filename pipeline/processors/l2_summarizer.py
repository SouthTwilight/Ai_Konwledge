"""L2 Summarizer — Structured summary generation via GLM-4.7.

Produces a structured summary with key points, one-line TL;DR,
and related topics for each article that passed L1 filtering.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

from openai import OpenAI

from pipeline.models import Article, ProcessingLevel
from pipeline.config import ModelConfig

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a technical content summarizer for a personal knowledge base.

Given an article's title and full content, produce a structured summary.

IMPORTANT: You must respond with ONLY a valid JSON object, no other text.
Format:
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
- ALL text fields (tldr, summary, key_points, related_topics) MUST be written in Chinese (中文), regardless of the source article language
- Be factual, no speculation
"""

SYSTEM_PROMPT_DETAILED = """\
You are a technical content summarizer for a personal knowledge base.

Given an article's title and full content, produce a structured summary.
This is a HIGH-IMPORTANCE article — preserve much more detail than normal.

IMPORTANT: You must respond with ONLY a valid JSON object, no other text.
Format:
{
  "tldr": "One-sentence summary (max 30 words)",
  "summary": "6-8 sentence structured summary covering main arguments, technical details, and conclusions",
  "key_points": ["Point 1 with context", "Point 2 with context", ...],
  "related_topics": ["topic1", "topic2"],
  "content_preserved": "Lightly compressed version of the original content, preserving ALL key paragraphs and technical details. Remove only: ads, navigation text, author bios, comment prompts, and obvious boilerplate. Keep ALL substantive content intact so readers don't need to visit the original URL."
}

Rules:
- tldr: Maximum 30 words, capture the essence
- summary: 6-8 detailed sentences, cover what/why/how with technical specifics
- key_points: 4-6 bullet points, each a standalone insight with detail
- related_topics: 2-4 topics this relates to (for knowledge graph linking)
- content_preserved: Preserve ALL substantive paragraphs from the original. Remove only boilerplate (ads, nav, bios). Readers should get the full article experience.
- ALL text fields (tldr, summary, key_points, related_topics) MUST be written in Chinese (中文), regardless of the source article language
- Be factual, no speculation
"""

USER_PROMPT_TEMPLATE = """\
Title: {title}
Tags: {tags}
Content:
{content}
"""


def _extract_json(text: str) -> Optional[str]:
    """Extract JSON object from model response."""
    if not text:
        return None
    # Strip <think/> blocks (compatibility with reasoning models)
    cleaned = re.sub(r'<think\b[^>]*>.*?</think\s*>', '', text, flags=re.DOTALL)
    cleaned = cleaned.strip()
    if cleaned.startswith('{'):
        try:
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError:
            pass
    # Extract JSON with regex — find outermost braces
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        return match.group(0)
    return None


class L2Summarizer:
    """L2 structured summarizer using GLM-4.7 (reasoning model)."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
        )

    def summarize_article(self, article: Article) -> Article:
        """Generate structured summary for a single article."""
        content = article.content_raw or article.content_clean or ""

        # Select prompt and truncation based on content tier
        if article.content_tier == "detailed":
            system_prompt = SYSTEM_PROMPT_DETAILED
            max_chars = self.config.max_tokens_l2 * 2  # Less truncation for detailed
        else:
            system_prompt = SYSTEM_PROMPT
            max_chars = self.config.max_tokens_l2 * 3

        if len(content) > max_chars:
            content = content[:max_chars] + "\n[...truncated]"

        try:
            response = self.client.chat.completions.create(
                model=self.config.l2_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                        title=article.title,
                        tags=", ".join(article.tags) if article.tags else "none",
                        content=content,
                    )},
                ],
                max_tokens=self.config.max_tokens_l2,
                temperature=0.3,
                extra_body={"thinking": {"type": "disabled"}},
            )

            raw = response.choices[0].message.content

            # GLM reasoning model may return content in reasoning_content field
            if not raw:
                reasoning = getattr(response.choices[0].message, 'reasoning_content', None)
                if reasoning:
                    logger.debug(f"L2: content empty, reasoning present ({len(reasoning)} chars)")
                else:
                    logger.warning(f"L2: empty response for '{article.title[:40]}'")
                article.content_summary = "[Summary generation returned empty]"
                article.processing_level = ProcessingLevel.L2_SUMMARIZED
                return article

            json_str = _extract_json(raw)
            if not json_str:
                logger.warning(f"L2: no JSON found in response for '{article.title[:40]}': {raw[:200]}")
                article.content_summary = raw[:500]
                article.processing_level = ProcessingLevel.L2_SUMMARIZED
                return article

            result = json.loads(json_str)

            article.content_summary = result.get("summary", "")
            article.key_points = result.get("key_points", [])
            article.related_topics = result.get("related_topics", [])
            article.processing_level = ProcessingLevel.L2_SUMMARIZED

            # For detailed tier: replace content_raw with lightly-compressed version
            if article.content_tier == "detailed":
                content_preserved = result.get("content_preserved", "")
                if content_preserved:
                    article.content_raw = content_preserved

            # Store TL;DR as first key point prefix for quick display
            tldr = result.get("tldr", "")
            if tldr:
                article.content_summary = f"**TL;DR:** {tldr}\n\n{article.content_summary}"

            logger.info(f"L2: '{article.title[:40]}...' -> summary generated "
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
