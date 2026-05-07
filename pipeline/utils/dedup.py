from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Set

from pipeline.models import Article

logger = logging.getLogger(__name__)


class DedupStore:
    """SQLite-backed deduplication store for articles."""

    def __init__(self, db_path: str | Path = ":memory:"):
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create the dedup table if it doesn't exist."""
        conn = self._get_conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS seen_articles (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                content_hash TEXT,
                first_seen TEXT NOT NULL,
                source TEXT
            )
        ''')
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
        return self._conn

    def _url_hash(self, url: str) -> str:
        """Normalize and hash URL for dedup."""
        # Strip trailing slashes and query params for normalization
        normalized = url.rstrip('/')
        # Remove common tracking params
        if '?' in normalized:
            base, params = normalized.split('?', 1)
            keep = [p for p in params.split('&')
                    if not p.startswith(('utm_', 'ref=', 'source='))]
            if keep:
                normalized = base + '?' + '&'.join(keep)
            else:
                normalized = base
        return hashlib.md5(normalized.encode()).hexdigest()

    def is_seen(self, article: Article) -> bool:
        """Check if an article has been seen before."""
        conn = self._get_conn()
        url_hash = self._url_hash(article.url)
        row = conn.execute(
            'SELECT 1 FROM seen_articles WHERE url_hash = ?', (url_hash,)
        ).fetchone()
        return row is not None

    def mark_seen(self, article: Article) -> None:
        """Mark an article as seen."""
        conn = self._get_conn()
        url_hash = self._url_hash(article.url)
        conn.execute(
            'INSERT OR IGNORE INTO seen_articles (url_hash, url, title, content_hash, first_seen, source) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (url_hash, article.url, article.title, article.content_hash,
             datetime.now().isoformat(), article.source.value)
        )
        conn.commit()

    def filter_new(self, articles: List[Article]) -> List[Article]:
        """Return only articles not seen before, and mark them as seen."""
        new_articles = []
        for article in articles:
            if not self.is_seen(article):
                self.mark_seen(article)
                new_articles.append(article)
            else:
                logger.debug(f"Skipping duplicate: {article.title}")
        logger.info(f"Dedup: {len(articles)} total, {len(new_articles)} new, {len(articles) - len(new_articles)} duplicates")
        return new_articles

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
