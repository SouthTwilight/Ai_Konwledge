"""L3 Deep Analyzer — In-depth analysis via GLM-5.1.

For high-value articles (score >= 7), performs deep analysis to extract:
- Core concepts with definitions
- Article structure type (argument, tutorial, news, etc.)
- Key insight (one sentence)
- Underlying assumptions
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
You are a deep content analyst for a personal AI knowledge base.

Given an article's title, summary, and full content, perform a deep analysis.

IMPORTANT: You must respond with ONLY a valid JSON object, no other text.
Format:
{
  "concepts": [
    {"name": "concept name", "definition": "one sentence definition"},
    ...
  ],
  "structure_type": "one of: argument, tutorial, news, analysis, review, opinion, research, reference",
  "key_insight": "the single most important takeaway in one sentence",
  "assumptions": ["assumption 1", "assumption 2"],
  "position": "author's stance or perspective (neutral if objective)"
}

Rules:
- concepts: Extract 5-10 independent conceptual knowledge units from the article.
  Each concept should be a self-contained idea that could be understood independently.
- structure_type: Classify the article's organizational pattern.
- key_insight: The ONE sentence that captures the article's most valuable contribution.
- assumptions: Identify 2-4 underlying premises the author relies on.
- position: What perspective does the author take? (e.g., "enthusiastic advocate", "cautious skeptic")
- ALL text fields MUST be written in Chinese (中文), regardless of the source article language.
- Be factual and analytical, no speculation beyond what the article states.
"""

USER_PROMPT_TEMPLATE = """\
Title: {title}
Tags: {tags}
Summary: {summary}

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


class L3Analyzer:
    """L3 deep analyzer using GLM-5.1."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
        )

    def analyze_article(self, article: Article) -> Article:
        """Perform deep analysis on a single article.

        Args:
            article: Article that has passed L2 summarization.

        Returns:
            The same article with L3 fields populated.
        """
        content = article.content_raw or article.content_clean or ""
        summary = article.content_summary or ""

        # Truncate content to fit token limits
        max_chars = self.config.max_tokens_l3 * 2
        if len(content) > max_chars:
            content = content[:max_chars] + "\n[...truncated for analysis]"

        try:
            response = self.client.chat.completions.create(
                model=self.config.l3_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                        title=article.title,
                        tags=", ".join(article.tags) if article.tags else "none",
                        summary=summary[:500] if summary else "N/A",
                        content=content,
                    )},
                ],
                max_tokens=self.config.max_tokens_l3,
                temperature=0.2,
                extra_body={"thinking": {"type": "disabled"}},
            )

            raw = response.choices[0].message.content

            if not raw:
                reasoning = getattr(response.choices[0].message, 'reasoning_content', None)
                if reasoning:
                    logger.debug(f"L3: content empty, reasoning present ({len(reasoning)} chars)")
                else:
                    logger.warning(f"L3: empty response for '{article.title[:40]}'")
                return article

            json_str = _extract_json(raw)
            if not json_str:
                logger.warning(f"L3: no JSON found for '{article.title[:40]}': {raw[:200]}")
                return article

            result = json.loads(json_str)

            # Populate L3 fields
            article.l3_concepts = result.get("concepts", [])
            article.l3_structure_type = result.get("structure_type", "")
            article.l3_key_insight = result.get("key_insight", "")

            # Build deep analysis text for obsidian output
            deep_parts = []
            if article.l3_key_insight:
                deep_parts.append(f"**核心洞见:** {article.l3_key_insight}")
            if article.l3_structure_type:
                deep_parts.append(f"**文章类型:** {article.l3_structure_type}")
            assumptions = result.get("assumptions", [])
            if assumptions:
                deep_parts.append("**前提假设:**\n" + "\n".join(f"- {a}" for a in assumptions))
            position = result.get("position", "")
            if position:
                deep_parts.append(f"**作者立场:** {position}")
            if article.l3_concepts:
                concepts_text = "\n".join(
                    f"- **{c['name']}**: {c.get('definition', '')}" 
                    for c in article.l3_concepts
                )
                deep_parts.append(f"**核心概念:**\n{concepts_text}")

            article.content_deep = "\n\n".join(deep_parts)
            article.processing_level = ProcessingLevel.L3_DEEP

            logger.info(
                f"L3: '{article.title[:40]}...' -> "
                f"{len(article.l3_concepts)} concepts, "
                f"type={article.l3_structure_type}"
            )
            return article

        except json.JSONDecodeError as e:
            logger.warning(f"L3 JSON parse error for '{article.title}': {e}")
            return article
        except Exception as e:
            logger.error(f"L3 API error for '{article.title}': {e}")
            return article

    def analyze_batch(self, articles: List[Article]) -> List[Article]:
        """Perform deep analysis on a batch of articles.

        Args:
            articles: Articles that have passed L2 summarization.

        Returns:
            Same articles with L3 fields populated where successful.
        """
        results = []
        for article in articles:
            analyzed = self.analyze_article(article)
            results.append(analyzed)
        logger.info(f"L3 batch: {len(articles)} articles analyzed")
        return results
