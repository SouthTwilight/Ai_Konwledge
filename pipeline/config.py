from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIR = PROJECT_ROOT / 'pipeline'
VAULT_DIR = PROJECT_ROOT / 'vault' / 'SouthTwilight-Obsidian' / '南国微光' / '个人知识库'
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
    max_tokens_l1: int = 1024
    max_tokens_l2: int = 4096
    max_tokens_l3: int = 8192


@dataclass
class PipelineConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    rss_sources: List[RSSSource] = field(default_factory=list)
    vault_path: Path = VAULT_DIR
    # Tier thresholds for score-tiered content depth
    tier_discard_max: int = 3      # Scores 1-3: discarded entirely
    tier_compressed_max: int = 6   # Scores 4-6: compressed (current behavior)
                                    # Scores 7-10: detailed (with raw content preserved)
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
                RSSSource(name="品玩", url="https://plink.anyfeeder.com/appinn", category="news", max_articles=10),
                RSSSource(name="极客公园", url="http://www.geekpark.net/rss", category="ai", max_articles=10),
                RSSSource(name="阮一峰的网络日志", url="http://feeds.feedburner.com/ruanyifeng", category="tech", max_articles=5),
                RSSSource(name="少数派", url="https://sspai.com/feed", category="tech", max_articles=5),
                RSSSource(name="贼拉正经的技术博客", url="https://stackoverflow.wiki/blog/rss.xml", category="tech", max_articles=5),
                RSSSource(name="掮客酒馆", url="https://wechat2rss.xlab.app/feed/10fdc27bdac746197d79a7632053fee231f37bcd.xml", category="tech", max_articles=10),
                RSSSource(name="未闻Code", url="https://wechat2rss.xlab.app/feed/a148ed0a542de4be305ffa1b93e8663ad252e22c.xml", category="tech", max_articles=10),
                RSSSource(name="知乎日报", url="https://plink.anyfeeder.com/zhihu/daily", category="tech", max_articles=10),
            ]
        # Ensure data dir exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> PipelineConfig:
    return PipelineConfig()


def load_rss_config(config_path: Optional[str] = None) -> List[RSSSource]:
    """Load RSS sources from a YAML config file."""
    if config_path is None:
        config_path = str(PIPELINE_DIR / 'configs' / 'default.yaml')

    path = Path(config_path)
    if not path.is_absolute():
        path = PIPELINE_DIR / 'configs' / path.name

    if not path.exists():
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Config file not found: {path}, using hardcoded defaults")
        return _default_rss_sources()

    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    sources = []
    for item in data.get('sources', []):
        sources.append(RSSSource(
            name=item['name'],
            url=item['url'],
            category=item.get('category', 'general'),
            max_articles=item.get('max_articles', 20),
            enabled=item.get('enabled', True),
        ))
    return sources


def _default_rss_sources() -> List[RSSSource]:
    """Hardcoded default sources — fallback when no config file found."""
    return [
        RSSSource(name="品玩", url="https://plink.anyfeeder.com/appinn", category="news", max_articles=10),
        RSSSource(name="极客公园", url="http://www.geekpark.net/rss", category="ai", max_articles=10),
        RSSSource(name="阮一峰的网络日志", url="http://feeds.feedburner.com/ruanyifeng", category="tech", max_articles=5),
        RSSSource(name="少数派", url="https://sspai.com/feed", category="tech", max_articles=5),
        RSSSource(name="贼拉正经的技术博客", url="https://stackoverflow.wiki/blog/rss.xml", category="tech", max_articles=5),
        RSSSource(name="掮客酒馆", url="https://wechat2rss.xlab.app/feed/10fdc27bdac746197d79a7632053fee231f37bcd.xml", category="tech", max_articles=10),
        RSSSource(name="未闻Code", url="https://wechat2rss.xlab.app/feed/a148ed0a542de4be305ffa1b93e8663ad252e22c.xml", category="tech", max_articles=10),
        RSSSource(name="知乎日报", url="https://plink.anyfeeder.com/zhihu/daily", category="tech", max_articles=10),
    ]
