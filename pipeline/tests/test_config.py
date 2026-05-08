import pytest
from pipeline.config import PipelineConfig, RSSSource, ModelConfig, load_config, VAULT_DIR
from pipeline.config import DEFAULT_CONFIG_PATH


def test_default_config():
    cfg = load_config()
    assert isinstance(cfg, PipelineConfig)
    assert cfg.tier_discard_max == 3
    assert cfg.tier_compressed_max == 6
    # With default.yaml present, should have sources
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
    assert mc.max_tokens_l1 == 1024


def test_vault_path():
    cfg = load_config()
    assert cfg.vault_path.exists()


def test_rss_sources_structure():
    cfg = load_config()
    for src in cfg.rss_sources:
        assert src.name
        assert src.url.startswith('http')
        assert src.category


def test_load_rss_config_from_yaml(tmp_path):
    yaml_content = """name: test-feeds
sources:
  - name: TestBlog
    url: https://testblog.com/rss
    category: tech
    max_articles: 5
"""
    config_file = tmp_path / "test-feeds.yaml"
    config_file.write_text(yaml_content, encoding='utf-8')
    cfg = load_config(str(config_file))
    assert len(cfg.rss_sources) == 1
    src = cfg.rss_sources[0]
    assert src.name == "TestBlog"
    assert src.url == "https://testblog.com/rss"
    assert src.category == "tech"
    assert src.max_articles == 5


def test_load_config_missing_file():
    cfg = load_config("/nonexistent/path/config.yaml")
    # Missing file → empty sources list (with a warning)
    assert cfg.rss_sources == []


def test_load_rss_config_enabled_field(tmp_path):
    yaml_content = """name: test
sources:
  - name: EnabledFeed
    url: https://enabled.com/rss
    enabled: true
  - name: DisabledFeed
    url: https://disabled.com/rss
    enabled: false
"""
    config_file = tmp_path / "test.yaml"
    config_file.write_text(yaml_content, encoding='utf-8')
    cfg = load_config(str(config_file))
    assert len(cfg.rss_sources) == 2
    assert cfg.rss_sources[0].enabled is True
    assert cfg.rss_sources[1].enabled is False


def test_default_config_loads_default_yaml():
    """Default config path should load pipeline/configs/default.yaml."""
    assert DEFAULT_CONFIG_PATH.exists()
    cfg = load_config()
    assert len(cfg.rss_sources) == 8
    names = [s.name for s in cfg.rss_sources]
    assert "品玩" in names
    assert "阮一峰的网络日志" in names
