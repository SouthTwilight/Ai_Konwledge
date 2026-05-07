import pytest
from pipeline.config import PipelineConfig, RSSSource, ModelConfig, load_config, VAULT_DIR


def test_default_config():
    cfg = load_config()
    assert isinstance(cfg, PipelineConfig)
    assert cfg.relevance_threshold == 6
    assert len(cfg.rss_sources) > 0


def test_rss_source():
    src = RSSSource(name="test", url="https://example.com/rss")
    assert src.category == "general"
    assert src.enabled is True
    assert src.max_articles == 20


def test_model_config_defaults():
    mc = ModelConfig()
    assert mc.l1_model == "glm-4.7"
    assert mc.l2_model == "glm-4.7"
    assert mc.max_tokens_l1 == 500


def test_vault_path():
    cfg = load_config()
    assert cfg.vault_path.exists()


def test_rss_sources_structure():
    cfg = load_config()
    for src in cfg.rss_sources:
        assert src.name
        assert src.url.startswith('http')
        assert src.category
