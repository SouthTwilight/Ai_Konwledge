import pytest
import os
from pipeline.config import (
    PipelineConfig, RSSSource, LevelModelConfig, load_config, VAULT_DIR
)
from pipeline.config import DEFAULT_CONFIG_PATH


# --- Legacy / basic tests ---

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


def test_level_model_config_defaults():
    mc = LevelModelConfig(api_key="test")
    assert mc.model == "glm-4.7"
    assert mc.max_tokens == 1024
    assert mc.base_url == "https://open.bigmodel.cn/api/paas/v4"
    assert mc.api_key_env == "GLM_API_KEY"


def test_level_model_config_api_key_env(monkeypatch):
    monkeypatch.setenv("MY_CUSTOM_KEY", "custom-value")
    mc = LevelModelConfig(api_key_env="MY_CUSTOM_KEY")
    assert mc.api_key == "custom-value"


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


# --- Model profile tests ---

def test_default_yaml_loads_models():
    """default.yaml has models.default — should load L1/L2/L3 configs."""
    cfg = load_config()
    assert cfg.l1_model.model == "glm-4.7"
    assert cfg.l1_model.max_tokens == 1024
    assert cfg.l2_model.model == "glm-4.7"
    assert cfg.l2_model.max_tokens == 4096
    assert cfg.l3_model.model == "glm-5.1"
    assert cfg.l3_model.max_tokens == 8192


def test_default_yaml_extra_body():
    """default.yaml extra_body should be parsed correctly."""
    cfg = load_config()
    assert cfg.l1_model.extra_body == {"thinking": {"type": "disabled"}}
    assert cfg.l2_model.extra_body == {"thinking": {"type": "disabled"}}
    assert cfg.l3_model.extra_body == {"thinking": {"type": "disabled"}}


def test_default_yaml_api_key_env():
    """default.yaml api_key_env should be GLM_API_KEY."""
    cfg = load_config()
    assert cfg.l1_model.api_key_env == "GLM_API_KEY"
    assert cfg.l2_model.api_key_env == "GLM_API_KEY"
    assert cfg.l3_model.api_key_env == "GLM_API_KEY"


def test_model_profile_switch(tmp_path, monkeypatch):
    """MODEL_PROFILE env var should switch to a different profile."""
    yaml_content = """name: multi-profile
sources: []
models:
  default:
    l1:
      api_key_env: "GLM_API_KEY"
      model: "glm-4.7"
      max_tokens: 1024
    l2:
      api_key_env: "GLM_API_KEY"
      model: "glm-4.7"
      max_tokens: 4096
    l3:
      api_key_env: "GLM_API_KEY"
      model: "glm-5.1"
      max_tokens: 8192
  deepseek:
    l1:
      api_key_env: "DEEPSEEK_API_KEY"
      base_url: "https://api.deepseek.com/v1"
      model: "deepseek-chat"
      max_tokens: 2048
    l2:
      api_key_env: "DEEPSEEK_API_KEY"
      base_url: "https://api.deepseek.com/v1"
      model: "deepseek-chat"
      max_tokens: 6000
    l3:
      api_key_env: "DEEPSEEK_API_KEY"
      base_url: "https://api.deepseek.com/v1"
      model: "deepseek-chat"
      max_tokens: 10000
"""
    config_file = tmp_path / "multi.yaml"
    config_file.write_text(yaml_content, encoding='utf-8')

    monkeypatch.setenv("MODEL_PROFILE", "deepseek")
    cfg = load_config(str(config_file))

    assert cfg.l1_model.model == "deepseek-chat"
    assert cfg.l1_model.max_tokens == 2048
    assert cfg.l1_model.api_key_env == "DEEPSEEK_API_KEY"
    assert cfg.l1_model.base_url == "https://api.deepseek.com/v1"
    assert cfg.l3_model.max_tokens == 10000


def test_model_profile_invalid(tmp_path, monkeypatch):
    """MODEL_PROFILE pointing to nonexistent profile should raise ValueError."""
    yaml_content = """name: test
sources: []
models:
  default:
    l1:
      model: "glm-4.7"
    l2:
      model: "glm-4.7"
    l3:
      model: "glm-5.1"
"""
    config_file = tmp_path / "test.yaml"
    config_file.write_text(yaml_content, encoding='utf-8')

    monkeypatch.setenv("MODEL_PROFILE", "nonexist")
    with pytest.raises(ValueError, match="not found"):
        load_config(str(config_file))


def test_yaml_without_models_section(tmp_path):
    """YAML without models section should fallback to defaults."""
    yaml_content = """name: no-models
sources:
  - name: Test
    url: https://test.com/rss
"""
    config_file = tmp_path / "no-models.yaml"
    config_file.write_text(yaml_content, encoding='utf-8')
    cfg = load_config(str(config_file))

    assert cfg.l1_model.model == "glm-4.7"
    assert cfg.l2_model.model == "glm-4.7"
    assert cfg.l3_model.model == "glm-5.1"
    assert cfg.l1_model.extra_body == {}


def test_api_key_resolved_from_env(monkeypatch, tmp_path):
    """api_key_env should resolve the actual key from environment."""
    monkeypatch.setenv("MY_TEST_KEY", "sk-12345")
    yaml_content = """name: key-test
sources: []
models:
  default:
    l1:
      api_key_env: "MY_TEST_KEY"
      model: "glm-4.7"
    l2:
      api_key_env: "MY_TEST_KEY"
      model: "glm-4.7"
    l3:
      api_key_env: "MY_TEST_KEY"
      model: "glm-5.1"
"""
    config_file = tmp_path / "key-test.yaml"
    config_file.write_text(yaml_content, encoding='utf-8')
    cfg = load_config(str(config_file))

    assert cfg.l1_model.api_key == "sk-12345"
    assert cfg.l2_model.api_key == "sk-12345"


def test_hybrid_profile(tmp_path, monkeypatch):
    """Hybrid profile: different levels use different providers/keys."""
    monkeypatch.setenv("DSK_KEY", "dsk-xxx")
    monkeypatch.setenv("GLM_KEY", "glm-yyy")
    monkeypatch.setenv("MODEL_PROFILE", "hybrid")

    yaml_content = """name: hybrid-test
sources: []
models:
  default:
    l1: {model: "glm-4.7"}
    l2: {model: "glm-4.7"}
    l3: {model: "glm-5.1"}
  hybrid:
    l1:
      api_key_env: "DSK_KEY"
      base_url: "https://api.deepseek.com/v1"
      model: "deepseek-chat"
      max_tokens: 1024
    l2:
      api_key_env: "DSK_KEY"
      base_url: "https://api.deepseek.com/v1"
      model: "deepseek-chat"
      max_tokens: 4096
    l3:
      api_key_env: "GLM_KEY"
      base_url: "https://open.bigmodel.cn/api/paas/v4"
      model: "glm-5.1"
      max_tokens: 8192
"""
    config_file = tmp_path / "hybrid.yaml"
    config_file.write_text(yaml_content, encoding='utf-8')
    cfg = load_config(str(config_file))

    assert cfg.l1_model.api_key == "dsk-xxx"
    assert cfg.l1_model.base_url == "https://api.deepseek.com/v1"
    assert cfg.l3_model.api_key == "glm-yyy"
    assert cfg.l3_model.model == "glm-5.1"
