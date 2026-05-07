from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIR = PROJECT_ROOT / 'pipeline'
VAULT_DIR = PROJECT_ROOT / 'vault'
DATA_DIR = PIPELINE_DIR / 'data'


@dataclass
class RSSSource:
    name: str
    url: str
    category: str = "general"
    max_articles: int = 20
    enabled: bool = True


@dataclass
class ModelConfig:
    provider: str = "zhipu"
    l1_model: str = "glm-4.7"
    l2_model: str = "glm-4.7"
    l3_model: str = "glm-5.1"
    api_base: str = "https://open.bigmodel.cn/api/paas/v4"
    api_key: str = ""
    max_tokens_l1: int = 500
    max_tokens_l2: int = 2000
    max_tokens_l3: int = 4000


@dataclass
class PipelineConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    rss_sources: List[RSSSource] = field(default_factory=list)
    vault_path: Path = VAULT_DIR
    relevance_threshold: int = 6  # Articles scoring >= this pass L1
    max_articles_per_run: int = 50
    dedup_db_path: Path = DATA_DIR / 'seen_articles.db'
    log_level: str = "INFO"

    def __post_init__(self):
        # Load API key from env
        if not self.model.api_key:
            self.model.api_key = os.getenv('ZHIPU_API_KEY', '')
        # Default RSS sources
        if not self.rss_sources:
            self.rss_sources = [
                RSSSource(name="Hacker News", url="https://hnrss.org/frontpage", category="tech"),
                RSSSource(name="The Verge AI", url="https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", category="ai"),
                RSSSource(name="Ars Technica AI", url="https://feeds.arstechnica.com/arstechnica/features", category="tech"),
                RSSSource(name="MIT Tech Review", url="https://www.technologyreview.com/feed/", category="tech"),
            ]
        # Ensure data dir exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> PipelineConfig:
    return PipelineConfig()
