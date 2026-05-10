# 模型配置动态化设计文档

> 日期: 2026-05-10
> 目标: 将 L1/L2/L3 模型配置从硬编码改为 YAML 驱动，支持多 profile 切换

## 1. 现状问题

| 问题 | 位置 |
|------|------|
| `api_key`/`api_base` 三级共用，无法让不同级别用不同 provider | `config.py:40-41` |
| 模型名 `l1_model` 等虽有字段，但未从 YAML 读取 | `config.py:37-39` |
| `thinking: disabled` 硬编码在三个 processor 中 | `l1_filter.py:126`, `l2_summarizer.py:137`, `l3_analyzer.py:125` |
| `ZHIPU_API_KEY` 环境变量与 YAML 两处配置同一个 key | `config.py:87` |

## 2. 设计方案

### 2.1 YAML 结构

```yaml
name: default

# ===== RSS sources（不变）=====
sources:
  - name: 品玩
    url: https://plink.anyfeeder.com/appinn
    category: news
    max_articles: 10
  # ... 其余 source 不变

# ===== 模型配置（新增）=====
models:
  # ---- 默认 profile（智谱 GLM）----
  default:
    l1:
      base_url: "https://open.bigmodel.cn/api/paas/v4"
      model: "glm-4.7"
      max_tokens: 1024
      extra_body:
        thinking:
          type: disabled
    l2:
      base_url: "https://open.bigmodel.cn/api/paas/v4"
      model: "glm-4.7"
      max_tokens: 4096
      extra_body:
        thinking:
          type: disabled
    l3:
      base_url: "https://open.bigmodel.cn/api/paas/v4"
      model: "glm-5.1"
      max_tokens: 8192
      extra_body:
        thinking:
          type: disabled

  # ---- 示例: DeepSeek profile（按需取消注释）----
  # deepseek:
  #   l1:
  #     base_url: "https://api.deepseek.com/v1"
  #     model: "deepseek-chat"
  #     max_tokens: 1024
  #     extra_body: {}
  #   l2:
  #     base_url: "https://api.deepseek.com/v1"
  #     model: "deepseek-chat"
  #     max_tokens: 4096
  #     extra_body: {}
  #   l3:
  #     base_url: "https://api.deepseek.com/v1"
  #     model: "deepseek-chat"
  #     max_tokens: 8192
  #     extra_body: {}
```

### 2.2 API Key 机制（api_key_env）

API Key 不再使用固定的环境变量名（如 `ZHIPU_API_KEY`），改为在 YAML 中声明要读取哪个环境变量：

```yaml
models:
  default:
    l1:
      api_key_env: "GLM_API_KEY"    # 声明：从这个环境变量读取
      base_url: "https://open.bigmodel.cn/api/paas/v4"
      model: "glm-4.7"
    l2:
      api_key_env: "GLM_API_KEY"    # 同 provider 可共用同一个 key
      model: "glm-4.7"
    l3:
      api_key_env: "GLM_API_KEY"
      model: "glm-5.1"
  deepseek:
    l1:
      api_key_env: "DEEPSEEK_API_KEY"   # 不同 provider 不同 key
      base_url: "https://api.deepseek.com/v1"
      model: "deepseek-chat"
    l2:
      api_key_env: "DEEPSEEK_API_KEY"
      model: "deepseek-chat"
    l3:
      api_key_env: "DEEPSEEK_API_KEY"
      model: "deepseek-chat"
  hybrid:                               # 混搭：自动引用各自的 key
    l1:
      api_key_env: "DEEPSEEK_API_KEY"
      base_url: "https://api.deepseek.com/v1"
      model: "deepseek-chat"
      max_tokens: 1024
    l2:
      api_key_env: "DEEPSEEK_API_KEY"
      base_url: "https://api.deepseek.com/v1"
      model: "deepseek-chat"
      max_tokens: 4096
    l3:
      api_key_env: "GLM_API_KEY"        # L3 用智谱，自动读 GLM_API_KEY
      base_url: "https://open.bigmodel.cn/api/paas/v4"
      model: "glm-5.1"
      max_tokens: 8192
```

.env 文件（一次配好所有 provider 的 key）：
```env
GLM_API_KEY=xxx
DEEPSEEK_API_KEY=yyy
# 按需添加更多 provider
```

**设计原则**：
- YAML 声明逻辑（用哪个 key 的名称），env 存敏感值
- 同 provider 的 L1/L2/L3 通常共用一个 key，环境变量更少
- 切换 profile 时 API key 自动跟着切换，无需手动改

**删除**: `ZHIPU_API_KEY` — 不再使用

### 2.3 环境变量总览

| 环境变量 | 用途 | 必需 |
|---------|------|------|
| `GLM_API_KEY` | 智谱 API Key（默认 profile 使用） | 是（使用默认 profile 时） |
| `DEEPSEEK_API_KEY` | DeepSeek API Key（deepseek profile 使用） | 按需 |
| `MODEL_PROFILE` | 选择 YAML 中哪个 models profile | 否（默认 `default`） |

> 环境变量名由 YAML 中的 `api_key_env` 字段决定，不限于上表。用户可自由命名。

### 2.4 Profile 切换机制

```bash
# 使用默认 profile（智谱 GLM）— GLM_API_KEY 已在 .env 中
python -m pipeline.main

# 切换到 DeepSeek profile — 自动读取 DEEPSEEK_API_KEY
MODEL_PROFILE=deepseek python -m pipeline.main

# 混搭 profile — L1/L2 读 DEEPSEEK_API_KEY，L3 读 GLM_API_KEY
MODEL_PROFILE=hybrid python -m pipeline.main
```

## 3. 代码改动范围

### 3.1 `config.py` — 数据模型 + YAML 加载

**删除**:
- `ZHIPU_API_KEY` 环境变量读取（L87）
- `ModelConfig` 中的 `provider` 字段（无实际用途）

**新增 dataclass**:
```python
@dataclass
class LevelModelConfig:
    """单级处理器模型配置"""
    base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    api_key_env: str = "GLM_API_KEY"  # 声明从哪个环境变量读取
    api_key: str = ""                 # __post_init__ 中自动填充
    model: str = "glm-4.7"
    max_tokens: int = 1024
    extra_body: dict = field(default_factory=dict)
```

**修改 `PipelineConfig`**:
- `model: ModelConfig` → `l1_model: LevelModelConfig` / `l2_model: LevelModelConfig` / `l3_model: LevelModelConfig`
- `__post_init__` 中根据每级的 `api_key_env` 读取实际 API Key

**修改 `load_config()`**:
- 解析 YAML 的 `models.<profile>.l1/l2/l3` 段
- 读取 `MODEL_PROFILE` 环境变量选择 profile
- 缺省字段 fallback 到合理默认值
- 校验：profile 不存在 → 报错列出可用 profile；api_key 为空 → 报错提示缺少哪个 env var

### 3.2 `l1_filter.py` — 适配新配置

```python
# Before
api_key=config.api_key,
base_url=config.api_base,
model=self.config.l1_model,
extra_body={"thinking": {"type": "disabled"}},

# After
api_key=self.l1_config.api_key,
base_url=self.l1_config.base_url,
model=self.l1_config.model,
extra_body=self.l1_config.extra_body,
```

构造函数从 `self.config.model` 改为 `self.config.l1_model`。

### 3.3 `l2_summarizer.py` — 同 L1 模式

同上，`self.config.l2_model`。

### 3.4 `l3_analyzer.py` — 同 L1 模式

同上，`self.config.l3_model`。

### 3.5 `.env` 文件（用户侧）

```env
# Before
ZHIPU_API_KEY=xxx

# After
GLM_API_KEY=xxx
# DEEPSEEK_API_KEY=yyy       # 按需添加
# MODEL_PROFILE=default       # 可选，不设则用 default
```

## 4. 向后兼容

| 场景 | 处理 |
|------|------|
| YAML 没有 `models` 段 | 全部 fallback 到硬编码默认值（智谱 GLM） |
| 只设 `L1_API_KEY`，L2/L3 不设 | L2/L3 启动时报错提示缺少对应环境变量 |
| `MODEL_PROFILE` 指定的 profile 不存在 | 报错退出，列出可用 profile |
| `extra_body` 不写 | 默认空 dict `{}`，不传额外参数 |

## 5. 不改动的文件

- `clusterer.py` — Embedding API 用独立 `EMBEDDING_API_BASE` 环境变量，不走 L1/L2/L3 配置
- `obsidian_writer.py` — 不涉及模型
- `extractors/*` — 不涉及模型
- `retry.py` — 不涉及模型
- 测试文件 — 需要适配新的 config 结构

## 6. 测试计划

| 测试项 | 验证点 |
|--------|--------|
| YAML 含 `models.default` 完整配置 | 三级 processor 正确读取各自的 base_url/model/max_tokens/extra_body/api_key |
| YAML 无 `models` 段 | fallback 到默认值，行为与改动前一致 |
| `MODEL_PROFILE=deepseek` + YAML 有 `models.deepseek` | 使用 deepseek 配置 + `DEEPSEEK_API_KEY` |
| `MODEL_PROFILE=hybrid` | L1/L2 读 DEEPSEEK_API_KEY，L3 读 GLM_API_KEY |
| `MODEL_PROFILE=nonexist` | 启动报错，提示可用 profile 列表 |
| `GLM_API_KEY` 未设 + YAML `api_key_env: "GLM_API_KEY"` | 启动报错提示缺少 `GLM_API_KEY` 环境变量 |
| `extra_body` 为空 dict | API 调用不含 extra_body 参数 |
| `api_key_env` 省略 | fallback 默认 `GLM_API_KEY` |
