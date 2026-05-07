from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict


class ArticleSource(str, Enum):
    RSS = "rss"
    WEB_URL = "web_url"
    GITHUB = "github"
    EMAIL = "email"
    MANUAL = "manual"


class ProcessingLevel(str, Enum):
    RAW = "raw"
    L1_FILTERED = "l1"
    L2_SUMMARIZED = "l2"
    L3_DEEP = "l3"
    ARCHIVED = "archived"


@dataclass
class Article:
    """Unified article model used throughout the pipeline."""
    
    url: str
    title: str
    source: ArticleSource
    
    content_raw: str = ""
    content_clean: str = ""
    content_summary: str = ""
    content_deep: str = ""
    
    author: str = ""
    published_at: Optional[datetime] = None
    fetched_at: datetime = field(default_factory=datetime.now)
    source_name: str = ""
    language: str = ""
    
    processing_level: ProcessingLevel = ProcessingLevel.RAW
    relevance_score: int = 0
    tags: List[str] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)
    related_topics: List[str] = field(default_factory=list)
    
    content_hash: str = ""
    obsidian_path: str = ""
    
    def compute_hash(self) -> str:
        import hashlib
        self.content_hash = hashlib.sha256(
            (self.url + self.title + self.content_raw[:500]).encode()
        ).hexdigest()[:16]
        return self.content_hash
    
    def to_dict(self) -> Dict:
        import dataclasses
        d = dataclasses.asdict(self)
        d['source'] = self.source.value
        d['processing_level'] = self.processing_level.value
        if self.published_at:
            d['published_at'] = self.published_at.isoformat()
        d['fetched_at'] = self.fetched_at.isoformat()
        return d
