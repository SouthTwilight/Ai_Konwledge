# AI 个人知识库 V3

AI 驱动的个人知识库流水线：RSS / Web URL → AI 处理 → Obsidian Vault

自动从 RSS 订阅源或网页 URL 抓取文章，使用 DeepSeek-V3 筛选相关内容，DeepSeek-R1 生成结构化摘要，最终输出格式美观的 Markdown 笔记到 Obsidian 知识库。

---

## 系统架构

```
┌──────────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐     ┌────────────────┐
│   内容源     │────▶│   抓取    │────▶│  去重    │────▶│ L1 筛选  │────▶│   L2 摘要      │
│  RSS / URL   │     │ trafilatura│     │  SQLite  │     │ DeepSeek │     │ DeepSeek-R1    │
│              │     │ feedparser │     │          │     │   V3     │     │                │
└──────────────┘     └───────────┘     └──────────┘     └──────────┘     └───────┬────────┘
                                                                            │
                                                                            ▼
                                                                   ┌────────────────┐
                                                                   │ Obsidian 写入  │
                                                                   │ Markdown +     │
                                                                   │ YAML frontmatter│
                                                                   └────────────────┘
```

**流水线 5 个阶段：**

1. **抓取 (Extract)** — 抓取 RSS 订阅源或单个 URL，用 trafilatura 解析正文
2. **去重 (Deduplicate)** — 基于 SQLite 的 URL/内容哈希去重，跳过已处理文章
3. **L1 筛选 (Filter)** — DeepSeek-V3 评估相关性（1-10 分）、分配标签、检测语言
4. **L2 摘要 (Summarize)** — DeepSeek-R1 生成 TL;DR、详细摘要、关键要点、关联主题
5. **写入 (Write)** — 格式化为 Obsidian 风格的 Markdown，含 YAML frontmatter

---

## 快速开始

### 环境要求

- Python 3.11+
- DeepSeek API 密钥（[点击获取](https://platform.deepseek.com/)）

### 安装步骤

```bash
cd /path/to/knowledge-base

# 创建虚拟环境
python3.11 -m venv pipeline/.venv
source pipeline/.venv/bin/activate

# 安装依赖
pip install -r pipeline/requirements.txt
```

### 配置 API 密钥

在项目根目录创建 `.env` 文件：

```bash
echo 'DEEPSEEK_API_KEY=sk-你的密钥' > .env
```

或者通过环境变量设置：

```bash
export DEEPSEEK_API_KEY=sk-你的密钥
```

### 运行流水线

```bash
cd /path/to/knowledge-base
source pipeline/.venv/bin/activate

# 处理所有 RSS 订阅源（默认）
python -m pipeline.main --source rss

# 处理单个 URL
python -m pipeline.main --source url --url "https://example.com/article"

# 试运行（不调用 LLM、不写文件，仅抓取 + 去重）
python -m pipeline.main --source rss --dry-run

# 限制最多处理 5 篇文章
python -m pipeline.main --source rss --limit 5

# 详细日志输出
python -m pipeline.main --source rss --log-level DEBUG
```

---

## 命令行参数

```
python -m pipeline.main [选项]
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--source` | `rss` 或 `url` | `rss` | 内容来源类型 |
| `--url` | 字符串 | 无 | 要处理的单个 URL（使用 `--source url` 时必填） |
| `--dry-run` | 开关 | False | 仅抓取 + 去重，跳过 LLM 调用和文件写入 |
| `--limit` | 整数 | 无 | 最多处理的文章数量 |
| `--log-level` | 字符串 | `INFO` | 日志级别：DEBUG、INFO、WARNING、ERROR |

---

## 配置说明

所有配置集中在 `pipeline/config.py`，关键配置如下：

### RSS 订阅源（内置 4 个）

| 名称 | 地址 | 分类 |
|------|------|------|
| Hacker News | `hnrss.org/frontpage` | tech |
| The Verge AI | `theverge.com/rss/ai-artificial-intelligence/index.xml` | ai |
| Ars Technica | `feeds.arstechnica.com/arstechnica/features` | tech |
| MIT Tech Review | `technologyreview.com/feed/` | tech |

添加自定义 RSS 源 — 编辑 `pipeline/config.py` 中的 `load_config()`：

```python
@dataclass
class RSSSource:
    name: str           # 显示名称
    url: str            # RSS 订阅地址
    category: str       # 内容分类标签
    max_articles: int   # 每次运行最多抓取篇数（默认 20）
    enabled: bool       # 是否启用（默认 True）
```

### 模型设置

| 设置项 | 默认值 | 说明 |
|--------|--------|------|
| `provider` | deepseek | API 提供商 |
| `l1_model` | deepseek-chat | L1 相关性评分模型 |
| `l2_model` | deepseek-reasoner | L2 摘要生成模型 |
| `api_base` | https://api.deepseek.com | API 接口地址 |
| `relevance_threshold` | 6 | 通过 L1 筛选的最低分数（1-10） |
| `max_articles_per_run` | 50 | 每次运行硬上限 |

### 环境变量

| 变量 | 是否必填 | 说明 |
|------|----------|------|
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API 密钥，用于 LLM 调用 |

---

## Obsidian 知识库结构

```
vault/
├── 0-Inbox/        ← 手动添加 / 未处理内容
├── 1-Daily/        ← 每日笔记
├── 2-Articles/     ← AI 处理后的文章（RSS/URL 来源）
├── 3-GitHub/       ← GitHub 仓库动态（计划中）
├── 4-Newsletters/  ← 邮件订阅（计划中）
├── 5-Topics/       ← 主题知识地图（MOC）
├── 5-Templates/    ← 笔记模板
│   ├── article-note.md
│   ├── daily-note.md
│   └── moc.md
├── 6-Permanent/    ← 永久笔记
└── 6-System/       ← 系统文档
```

**来源类型 → 目录映射：**

| 来源类型 | 目标目录 |
|----------|----------|
| RSS | `vault/2-Articles/` |
| WEB_URL | `vault/2-Articles/` |
| GITHUB | `vault/3-GitHub/` |
| EMAIL | `vault/4-Newsletters/` |
| MANUAL | `vault/0-Inbox/` |

### 输出笔记格式

每篇处理后的文章会生成一个 Markdown 文件，包含 YAML frontmatter：

```markdown
---
title: "文章标题"
source: RSS
source_name: Hacker News
author: 作者名
published_at: 2026-05-07T12:00:00
fetched_at: 2026-05-07T19:30:00
tags: [ai, llm, training]
relevance_score: 8
processing_level: L2_SUMMARIZED
content_hash: a1b2c3d4e5f6
---

# 文章标题

> 来源: [Hacker News](https://...) | 作者: 作者名

## 摘要

**TL;DR:** 一句话总结。

2-3 段详细摘要...

## 关键要点

- 要点 1
- 要点 2
- 要点 3

## 关联主题

[[AI 训练]] [[大语言模型]]

## 标签

#ai #llm #training

---

*原文: 3,500 字*

## 个人笔记

```

---

## 依赖包

| 包名 | 版本要求 | 用途 |
|------|----------|------|
| trafilatura | >=1.6.0 | 网页正文提取 |
| feedparser | >=6.0.0 | RSS/Atom 订阅源解析 |
| pyyaml | >=6.0 | YAML frontmatter 生成 |
| openai | >=1.0.0 | OpenAI 兼容 API 客户端（用于 DeepSeek） |
| httpx | >=0.25.0 | HTTP 客户端 |
| python-dotenv | >=1.0.0 | .env 文件加载 |
| pytest | >=7.0.0 | 测试框架 |

---

## 测试

```bash
cd /path/to/knowledge-base
source pipeline/.venv/bin/activate

# 运行全部测试
pytest pipeline/tests/ -v

# 运行指定模块测试
pytest pipeline/tests/test_l1_filter.py -v
```

共 **46 个测试**，覆盖 9 个测试文件。所有外部依赖（feedparser、trafilatura、OpenAI API）均已 mock，无需网络连接。

| 模块 | 测试数 | 覆盖范围 |
|------|--------|----------|
| main.py | 4 | CLI 流程、试运行、文章数量限制 |
| rss_fetcher.py | 4 | 订阅源解析、正文提取 |
| web_extractor.py | 3 | URL 提取、批量模式 |
| dedup.py | 5 | 去重、URL 标准化、SQLite |
| l1_filter.py | 4 | 相关性评分、阈值筛选、错误处理 |
| l2_summarizer.py | 5 | 摘要生成、R1 think 块剥离、JSON 解析 |
| obsidian_writer.py | 11 | frontmatter、目录路由、文件名冲突、批量写入 |
| config.py | 5 | 默认配置、环境变量加载 |
| models.py | 5 | Article 数据模型、哈希计算、序列化 |

---

## 项目目录结构

```
knowledge-base/
├── README.md                    ← 本文档
├── .env                         ← API 密钥（已被 gitignore）
├── .gitignore
├── docs/
│   └── plans/                   ← 里程碑规划文档
├── pipeline/
│   ├── __init__.py
│   ├── main.py                  ← CLI 入口
│   ├── config.py                ← 配置数据类
│   ├── models.py                ← Article、ArticleSource、ProcessingLevel
│   ├── requirements.txt         ← Python 依赖
│   ├── .venv/                   ← Python 3.11 虚拟环境
│   ├── data/                    ← 运行时数据（seen_articles.db）
│   ├── extractors/              ← 内容抓取器
│   │   ├── rss_fetcher.py       ← RSS 订阅源抓取 + 正文提取
│   │   └── web_extractor.py     ← 单 URL 正文提取
│   ├── processors/              ← AI 处理器
│   │   ├── l1_filter.py         ← L1 相关性评分（DeepSeek-V3）
│   │   └── l2_summarizer.py     ← L2 摘要生成（DeepSeek-R1）
│   ├── formatters/              ← 格式化输出
│   │   └── obsidian_writer.py   ← Markdown 格式化 + 文件写入
│   ├── utils/                   ← 工具模块
│   │   └── dedup.py             ← SQLite 去重存储
│   └── tests/                   ← 46 个 pytest 测试
├── vault/                       ← Obsidian 知识库输出目录
│   ├── .obsidian/
│   ├── 0-Inbox/
│   ├── 1-Daily/
│   ├── 2-Articles/
│   ├── 3-GitHub/
│   ├── 4-Newsletters/
│   ├── 5-Topics/
│   ├── 5-Templates/
│   ├── 6-Permanent/
│   └── 6-System/
```

---

## 开发路线图

- [x] **Phase 1（M0+M1）** — 核心流水线：RSS/Web 抓取、去重、L1 筛选、L2 摘要、Obsidian 写入
- [ ] **Phase 2** — Hermes Cron 定时调度、GitHub 提取器、邮件提取器
- [ ] **Phase 3** — L3 深度分析（Claude Sonnet）、主题聚类、MOC 自动生成

---

## 许可证

个人项目，保留所有权利。
