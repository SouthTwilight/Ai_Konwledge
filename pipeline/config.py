from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

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

_logger = logging.getLogger(__name__)


@dataclass
class RSSSource:
    name: str
    url: str
    category: str = "general"
    max_articles: int = 20
    enabled: bool = True


@dataclass
class LevelModelConfig:
    """Single-level model configuration (one per L1/L2/L3 processor).

    api_key_env: declares which environment variable holds the API key.
    api_key: resolved at load time from api_key_env via os.getenv().
    """
    base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    api_key_env: str = "GLM_API_KEY"
    api_key: str = ""
    model: str = "glm-4.7"
    max_tokens: int = 1024
    extra_body: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv(self.api_key_env, "")


# ---------------------------------------------------------------------------
# Legacy ModelConfig — kept for backward compatibility in tests.
# Will be removed in a future cleanup.
# ---------------------------------------------------------------------------
@dataclass
class ModelConfig:
    """Legacy single-provider config. Tests construct this directly.

    DEPRECATED: real code uses LevelModelConfig per level.
    """
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
    l1_model: LevelModelConfig = field(default_factory=LevelModelConfig)
    l2_model: LevelModelConfig = field(default_factory=LevelModelConfig)
    l3_model: LevelModelConfig = field(default_factory=LevelModelConfig)
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
    # L3 deep analysis settings
    l3_enabled: bool = True
    l3_min_score: int = 7  # Only analyze articles with score >= this

    def __post_init__(self):
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


# ---------------------------------------------------------------------------
# YAML loading helpers
# ---------------------------------------------------------------------------

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


def _parse_level_config(data: Dict[str, Any], defaults: Dict[str, Any]) -> LevelModelConfig:
    """Parse one level (l1/l2/l3) dict from YAML into LevelModelConfig.

    Missing keys fall back to *defaults* dict.
    """
    merged = {**defaults, **data}
    return LevelModelConfig(
        base_url=merged.get('base_url', 'https://open.bigmodel.cn/api/paas/v4'),
        api_key_env=merged.get('api_key_env', 'GLM_API_KEY'),
        model=merged.get('model', 'glm-4.7'),
        max_tokens=merged.get('max_tokens', 1024),
        extra_body=merged.get('extra_body', {}),
    )


def _load_models_from_yaml(path: Path) -> Dict[str, Dict[str, LevelModelConfig]]:
    """Load models section from YAML.  Returns {profile_name: {l1: cfg, l2: cfg, l3: cfg}}."""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not data or 'models' not in data:
        return {}

    result: Dict[str, Dict[str, LevelModelConfig]] = {}
    for profile_name, profile_data in data['models'].items():
        levels: Dict[str, LevelModelConfig] = {}
        for level_key in ('l1', 'l2', 'l3'):
            level_dict = profile_data.get(level_key, {}) or {}
            # Defaults per level
            if level_key == 'l1':
                defaults = {'model': 'glm-4.7', 'max_tokens': 1024}
            elif level_key == 'l2':
                defaults = {'model': 'glm-4.7', 'max_tokens': 4096}
            else:
                defaults = {'model': 'glm-5.1', 'max_tokens': 8192}
            levels[level_key] = _parse_level_config(level_dict, defaults)
        result[profile_name] = levels
    return result


def _resolve_profile(
    models_map: Dict[str, Dict[str, LevelModelConfig]],
    profile_name: str,
) -> Dict[str, LevelModelConfig]:
    """Select a profile from the models map, with validation."""
    if profile_name not in models_map:
        available = ', '.join(sorted(models_map.keys()))
        raise ValueError(
            f"MODEL_PROFILE='{profile_name}' not found in YAML models section. "
            f"Available profiles: [{available}]"
        )
    return models_map[profile_name]


def load_config(config_path: Optional[str] = None) -> PipelineConfig:
    """Load pipeline config, with RSS sources and models from a YAML config file.

    Args:
        config_path: Path to YAML config file. Defaults to pipeline/configs/default.yaml.
                     If the file doesn't exist, RSS sources will be empty and model
                     config falls back to hardcoded defaults.

    Returns:
        Fully configured PipelineConfig instance.
    """
    # Resolve config file path
    if config_path is None:
        path = DEFAULT_CONFIG_PATH
    else:
        path = Path(config_path)
        if not path.is_absolute():
            path = Path.cwd() / path

    # Load RSS sources from YAML
    rss_sources: List[RSSSource] = []
    l1_model: Optional[LevelModelConfig] = None
    l2_model: Optional[LevelModelConfig] = None
    l3_model: Optional[LevelModelConfig] = None

    if path.exists():
        rss_sources = _load_rss_sources_from_yaml(path)

        # Load models section
        try:
            models_map = _load_models_from_yaml(path)
            if models_map:
                profile_name = os.getenv('MODEL_PROFILE', 'default')
                levels = _resolve_profile(models_map, profile_name)
                l1_model = levels['l1']
                l2_model = levels['l2']
                l3_model = levels['l3']
                _logger.info(
                    f"Loaded model profile '{profile_name}': "
                    f"L1={l1_model.model}, L2={l2_model.model}, L3={l3_model.model}"
                )
        except ValueError as e:
            _logger.error(str(e))
            raise
    else:
        _logger.warning(f"Config file not found: {path}, using defaults")

    # Fallback defaults if no models section in YAML
    if l1_model is None:
        l1_model = LevelModelConfig(model="glm-4.7", max_tokens=1024)
    if l2_model is None:
        l2_model = LevelModelConfig(model="glm-4.7", max_tokens=4096)
    if l3_model is None:
        l3_model = LevelModelConfig(model="glm-5.1", max_tokens=8192)

    return PipelineConfig(
        l1_model=l1_model,
        l2_model=l2_model,
        l3_model=l3_model,
        rss_sources=rss_sources,
    )
