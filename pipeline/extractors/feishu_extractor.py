"""Feishu Document Extractor — Fetch documents via Feishu Open Platform API.

Supports:
  - wiki pages: https://{tenant}.feishu.cn/wiki/{doc_id}
  - docx pages: https://{tenant}.feishu.cn/docx/{doc_id}
  - docs pages: https://{tenant}.feishu.cn/docs/{doc_id}

Authentication uses tenant_access_token (app_id + app_secret).
"""
from __future__ import annotations

import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse

import httpx

from pipeline.config import FeishuConfig
from pipeline.models import Article, ArticleSource

logger = logging.getLogger(__name__)

FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


# ============================================================
# URL Parsing
# ============================================================

def parse_feishu_doc_id(url: str) -> Optional[str]:
    """Extract document_id from a Feishu document URL.

    Supported formats:
      - https://{tenant}.feishu.cn/wiki/{doc_id}
      - https://{tenant}.feishu.cn/docx/{doc_id}
      - https://{tenant}.feishu.cn/docs/{doc_id}

    Returns None if the URL is not a valid Feishu document link.
    """
    try:
        parsed = urlparse(url)
        if 'feishu.cn' not in parsed.netloc:
            return None
        match = re.match(r'/(?:wiki|docx|docs)/([^/?]+)', parsed.path)
        return match.group(1) if match else None
    except Exception:
        return None


# ============================================================
# Feishu API Client
# ============================================================

class FeishuClient:
    """Feishu Open Platform API client with automatic token management."""

    def __init__(self, config: FeishuConfig):
        self.config = config
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    def _get_token(self) -> str:
        """Obtain tenant_access_token, with caching until near-expiry."""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.config.app_id,
            "app_secret": self.config.app_secret,
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(
                f"Feishu token request failed: code={data.get('code')} "
                f"msg={data.get('msg')}"
            )

        self._token = data["tenant_access_token"]
        self._token_expires_at = time.time() + data.get("expire", 7200)
        logger.debug("Feishu tenant_access_token refreshed, expires in %ds",
                      data.get("expire", 7200))
        return self._token

    def get_raw_content(self, document_id: str) -> Optional[str]:
        """Fetch document raw content as Markdown.

        Uses the /docx/v1/documents/{id}/raw_content endpoint.

        Returns the Markdown string on success, or None on failure.
        """
        token = self._get_token()
        url = f"{FEISHU_API_BASE}/docx/v1/documents/{document_id}/raw_content"
        headers = {"Authorization": f"Bearer {token}"}

        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 0:
            logger.error(
                "Feishu API error for doc %s: code=%s msg=%s",
                document_id, data.get("code"), data.get("msg"),
            )
            return None

        content = data.get("data", {}).get("content", "")
        if not content:
            logger.warning("Feishu doc %s: empty content returned", document_id)
        return content


# ============================================================
# Top-level extractor function
# ============================================================

def _extract_title_from_markdown(md_text: str, doc_id: str) -> str:
    """Extract title from the first Markdown heading, or fallback to doc_id."""
    match = re.match(r'^#\s+(.+)$', md_text, re.MULTILINE)
    return match.group(1).strip() if match else doc_id


def extract_feishu_doc(url: str, config: FeishuConfig) -> Optional[Article]:
    """Extract a Feishu document by URL and return an Article.

    Args:
        url: Full Feishu document URL.
        config: FeishuConfig with app_id and app_secret.

    Returns:
        Article with source=FEISHU, or None if extraction fails.
    """
    doc_id = parse_feishu_doc_id(url)
    if not doc_id:
        logger.error("Cannot parse Feishu doc ID from URL: %s", url)
        return None

    try:
        client = FeishuClient(config)
        content = client.get_raw_content(doc_id)
    except Exception as e:
        logger.error("Feishu extraction failed for %s: %s", url, e)
        return None

    if not content:
        return None

    title = _extract_title_from_markdown(content, doc_id)

    article = Article(
        url=url,
        title=title,
        source=ArticleSource.FEISHU,
        content_raw=content,
        source_name="feishu",
    )
    logger.info("Extracted Feishu doc: %s (%d chars)", title, len(content))
    return article
