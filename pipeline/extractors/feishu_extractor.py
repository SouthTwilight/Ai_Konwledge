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

    def get_document_info(self, document_id: str) -> Optional[dict]:
        """Fetch document metadata (title, revision_id, etc.).

        Uses the /docx/v1/documents/{id} endpoint.

        Returns a dict with at least {"title": str} on success,
        or None on failure.
        """
        token = self._get_token()
        url = f"{FEISHU_API_BASE}/docx/v1/documents/{document_id}"
        headers = {"Authorization": f"Bearer {token}"}

        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 0:
            logger.error(
                "Feishu doc info API error for %s: code=%s msg=%s",
                document_id, data.get("code"), data.get("msg"),
            )
            return None

        doc = data.get("data", {}).get("document")
        if not doc:
            return None
        return doc

    def get_blocks(self, document_id: str) -> list:
        """Fetch all document blocks with rich content (including hyperlinks).

        Paginates through all blocks. Returns a flat list of block dicts.
        """
        token = self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        all_blocks = []
        page_token = None

        while True:
            url = f"{FEISHU_API_BASE}/docx/v1/documents/{document_id}/blocks"
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token

            with httpx.Client(timeout=30) as client:
                resp = client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()

            if data.get("code") != 0:
                logger.error(
                    "Feishu blocks API error for %s: code=%s msg=%s",
                    document_id, data.get("code"), data.get("msg"),
                )
                break

            items = data.get("data", {}).get("items", [])
            all_blocks.extend(items)

            page_token = data.get("data", {}).get("page_token")
            if not page_token:
                break

        return all_blocks


# ============================================================
# Top-level extractor function
# ============================================================

def _extract_title_from_markdown(md_text: str, doc_id: str) -> str:
    """Extract title from the first Markdown heading, or fallback to doc_id."""
    match = re.match(r'^#\s+(.+)$', md_text, re.MULTILINE)
    return match.group(1).strip() if match else doc_id


# Mapping from block_type int to string key used in the API response.
_BLOCK_TYPE_NAMES = {
    2: "text", 3: "heading1", 4: "heading2", 5: "heading3",
    6: "heading4", 7: "heading5", 8: "heading6", 9: "heading7",
    10: "heading8", 11: "heading9", 12: "bullet", 13: "ordered",
    14: "code", 15: "quote", 16: "todo", 18: "callout",
}


def extract_links_from_blocks(blocks: list) -> list:
    """Extract hyperlinks from Feishu document blocks.

    Returns list of (text, url) tuples.
    """
    from urllib.parse import unquote

    link_items = []
    for block in blocks:
        bt = block.get("block_type")
        name = _BLOCK_TYPE_NAMES.get(bt)
        if not name:
            continue
        sub = block.get(name)
        if not sub or not isinstance(sub, dict):
            continue
        for el in sub.get("elements", []):
            text_run = el.get("text_run")
            if not text_run:
                continue
            link = text_run.get("text_element_style", {}).get("link")
            if link and link.get("url"):
                url = unquote(link["url"])
                text = text_run.get("content", "").strip()
                if text and url:
                    link_items.append((text, url))

    return link_items


def inject_links_into_markdown(content: str, links: list) -> str:
    """Replace plain text mentions with [text](url) Markdown links.

    For each (text, url) pair, finds the first occurrence of *text* in
    the content that is NOT already inside a Markdown link, and wraps it.
    """
    for text, url in links:
        # Skip if the text already appears inside a link [...](...)
        # Pattern: the text preceded by ]( or not preceded by [
        escaped = re.escape(text)
        # Find occurrences not already part of a markdown link
        pattern = rf'(?<!\[\S*){escaped}(?!\S*\]\()'
        # Simple approach: if text exists and is not preceded by [xxx, replace first occurrence
        # We use a safe approach - check if it's already linked
        idx = 0
        while idx < len(content):
            pos = content.find(text, idx)
            if pos == -1:
                break
            # Check if already inside a link: look back for '[...' without ']'
            before = content[max(0, pos - 200):pos]
            # Count unmatched '['
            open_brackets = before.count('[') - before.count(']')
            if open_brackets > 0:
                # Already inside a link text, skip
                idx = pos + len(text)
                continue
            # Replace this occurrence
            replacement = f"[{text}]({url})"
            content = content[:pos] + replacement + content[pos + len(text):]
            break  # Only replace first occurrence per link

    return content


def _resolve_title(client: "FeishuClient", doc_id: str, content: str) -> str:
    """Resolve document title with three-level priority:

    1. API metadata title (most reliable)
    2. First Markdown heading in content
    3. doc_id as last resort
    """
    # Priority 1: API metadata
    try:
        info = client.get_document_info(doc_id)
        if info and info.get("title"):
            return info["title"]
    except Exception as e:
        logger.warning("Feishu get_document_info failed for %s: %s", doc_id, e)

    # Priority 2: First Markdown heading
    match = re.match(r'^#\s+(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Priority 3: doc_id
    return doc_id


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

    # Enrich content with hyperlinks from the Blocks API.
    # raw_content loses links; blocks API preserves them.
    try:
        blocks = client.get_blocks(doc_id)
        links = extract_links_from_blocks(blocks)
        if links:
            logger.info("Feishu doc %s: injecting %d hyperlinks from blocks", doc_id, len(links))
            content = inject_links_into_markdown(content, links)
    except Exception as e:
        logger.warning("Feishu block enrichment failed for %s (non-fatal): %s", doc_id, e)

    title = _resolve_title(client, doc_id, content)

    article = Article(
        url=url,
        title=title,
        source=ArticleSource.FEISHU,
        content_raw=content,
        source_name="feishu",
    )
    logger.info("Extracted Feishu doc: %s (%d chars)", title, len(content))
    return article
