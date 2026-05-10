from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

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
DEFAULT_CONFIG_PATH = PIPELINE_DIR / 'configs' / 'default.yaml'


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
class FeishuConfig:
    """Feishu Open Platform API configuration."""
    app_id: str = ""
    app_secret: str = ""


@dataclass
class EmailConfig:
    """IMAP email configuration for Newsletter extraction."""
    imap_server: str = ""
    imap_port: int = 993
    username: str = ""
    app_password: str = ""  # Environment variable: EMAIL_APP_PASSWORD
    sender_whitelist: List[str] = field(default_factory=list)  # Allowed sender addresses
    max_emails: int = 10
    mark_as_read: bool = True


@dataclass
class PipelineConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    rss_sources: List[RSSSource] = field(default_factory=list)
    feishu: FeishuConfig = field(default_factory=FeishuConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
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
        # Load Feishu credentials from env
        if not self.feishu.app_id:
            self.feishu.app_id = os.getenv('FEISHU_APP_ID', '')
        if not self.feishu.app_secret:
            self.feishu.app_secret = os.getenv('FEISHU_APP_SECRET', '')
        # Load Email credentials from env
        if not self.email.app_password:
            self.email.app_password = os.getenv('EMAIL_APP_PASSWORD', '')
        if not self.email.username:
            self.email.username = os.getenv('EMAIL_USERNAME', '')
        if not self.email.imap_server:
            self.email.imap_server = os.getenv('EMAIL_IMAP_SERVER', '')
        # Ensure data dir exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_rss_sources_from_yaml(path: Path) -> List[RSSSource]:
    """Parse a YAML file into a list of RSSSource objects."""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not data or 'sources' not in data:
        return []

    sources = []
    for item in data['sources']:
        sources.append(RSSSource(
            name=item['name'],
            url=item['url'],
            category=item.get('category', 'general'),
            max_articles=item.get('max_articles', 20),
            enabled=item.get('enabled', True),
        ))
    return sources


def load_config(config_path: Optional[str] = None) -> PipelineConfig:
    """Load pipeline config, with RSS sources from a YAML config file.

    Args:
        config_path: Path to YAML config file. Defaults to pipeline/configs/default.yaml.
                     If the file doesn't exist, RSS sources will be empty.

    Returns:
        Fully configured PipelineConfig instance.
    """
    # Resolve config file path
    if config_path is None:
        path = DEFAULT_CONFIG_PATH
    else:
        path = Path(config_path)
        if not path.is_absolute():
            path = PIPELINE_DIR / 'configs' / path.name

    # Load RSS sources from YAML
    rss_sources: List[RSSSource] = []
    if path.exists():
        rss_sources = _load_rss_sources_from_yaml(path)
    else:
        import logging
        logging.getLogger(__name__).warning(
            f"Config file not found: {path}, no RSS sources loaded"
        )

    return PipelineConfig(rss_sources=rss_sources)
