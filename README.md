# AI 个人知识库 V3

AI 驱动的个人知识库流水线：RSS / Web URL / 飞书文档 → AI 处理 → Obsidian Vault

自动从 RSS 订阅源、网页 URL 或飞书文档抓取文章，使用智谱 GLM 系列模型进行三级处理：GLM-4.7 筛选相关性并生成摘要，GLM-5.1 进行深度分析，最终输出格式美观的 Markdown 笔记到 Obsidian 知识库。

---

## 系统架构

```
┌──────────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐     ┌────────────────┐
│   内容源     │────▶│   抓取    │────▶│  去重    │────▶│ L1 筛选  │────▶│   L2 摘要      │
│  RSS / URL   │     │ trafilatura│     │  SQLite  │     │ GLM-4.7  │     │   GLM-4.7      │
│              │     │ feedparser │     │          │     │          │     │                │
└──────────────┘     └───────────┘     └──────────┘     └──────────┘     └───────┬────────┘
                                                                            │
                          ┌──────────────────────────────────────────────────┘
                          │ 评分分层
                          ├── 得分 < 4  → 丢弃（不相关）
                          ├── 得分 4-6  → 压缩摘要
                          └── 得分 ≥ 7  → 完整摘要 + 原文
                          ▼
                   ┌────────────────┐
                   │ Obsidian 写入  │
                   │ YYYY-MM-DD/    │
                   │ [SN] slug.md   │
                   └────────────────┘
```

**流水线 5 个阶段：**

1. **抓取 (Extract)** — 从 YAML 配置文件加载 RSS 订阅源、单个 URL（trafilatura 解析）或飞书文档（开放平台 API）
2. **去重 (Deduplicate)** — 基于 SQLite 的 URL/内容哈希去重，跳过已处理文章
3. **L1 筛选 (Filter)** — GLM-4.7 评估相关性（1-10 分）、分配标签、检测语言
4. **L2 摘要 (Summarize)** — GLM-4.7 生成 TL;DR、详细摘要、关键要点、关联主题（仅评分 ≥ 4 的文章）
5. **写入 (Write)** — 按日期分目录、文件名含评分前缀，格式化为 Obsidian 风格 Markdown

**AI 模型配置（智谱清言）：**

| 处理层级 | 模型 | 用途 |
|----------|------|------|
| L1 筛选 | GLM-4.7 | 相关性评分、标签分类、语言检测 |
| L2 摘要 | GLM-4.7 | 结构化摘要、关键要点、关联主题 |
| L3 深度分析（计划中） | GLM-5.1 | 深度内容分析、主题聚类 |

---

## 快速开始

### 环境要求

- Python 3.11+
- 智谱 API 密钥（[点击获取](https://open.bigmodel.cn/)）

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
echo 'ZHIPU_API_KEY=你的密钥' > .env
```

或者通过环境变量设置：

```bash
export ZHIPU_API_KEY=你的密钥
```

### 运行流水线

```bash
cd /path/to/knowledge-base
source pipeline/.venv/bin/activate

# 使用默认配置处理 RSS 订阅源
python -m pipeline.main --source rss

# 使用指定 YAML 配置文件
python -m pipeline.main --source rss --config pipeline/configs/tech-feeds.yaml

# 处理单个 URL
python -m pipeline.main --source url --url "https://example.com/article"

# 处理飞书文档
python -m pipeline.main --source feishu --feishu-url "https://xxx.feishu.cn/wiki/DOCID"

# 试运行（不调用 LLM、不写文件，仅抓取 + 去重）
python -m pipeline.main --source rss --dry-run

# 限制最多处理 5 篇文章
python -m pipeline.main --source rss --limit 5

# 深挖已处理文章中的引用链接（双向 wikilink）
python -m pipeline.main --source resolve --from "vault/SouthTwilight-Obsidian/南国微光/个人知识库/2-Articles/2026-05-08/[S8] some-article.md"

# 深挖时限制最多抓取 3 篇引用文章
python -m pipeline.main --source resolve --from "path/to/article.md" --max-links 3

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
| `--source` | `rss`、`url`、`feishu` 或 `resolve` | `rss` | 内容来源类型 |
| `--url` | 字符串 | 无 | 要处理的单个 URL（使用 `--source url` 时必填） |
| `--feishu-url` | 字符串 | 无 | 飞书文档 URL（使用 `--source feishu` 时必填） |
| `--from` | 文件路径 | 无 | 已处理文章的 .md 路径（使用 `--source resolve` 时必填） |
| `--max-links` | 整数 | 5 | 深挖时最多抓取的引用文章数（使用 `--source resolve`） |
| `--config` | 文件路径 | 无 | RSS 源配置文件（YAML 格式，不指定则使用内置默认源） |
| `--dry-run` | 开关 | False | 仅抓取 + 去重，跳过 LLM 调用和文件写入 |
| `--limit` | 整数 | 无 | 最多处理的文章数量 |
| `--log-level` | 字符串 | `INFO` | 日志级别：DEBUG、INFO、WARNING、ERROR |

---

## 配置说明

### RSS 订阅源（YAML 配置文件）

RSS 源通过 YAML 配置文件管理，支持多个配置方案切换：

**默认配置** `pipeline/configs/default.yaml`（8 个源）：

| 名称 | 地址 | 分类 |
|------|------|------|
| 品玩 | plink.anyfeeder.com/appinn | news |
| 极客公园 | www.geekpark.net/rss | ai |
| 阮一峰的网络日志 | feeds.feedburner.com/ruanyifeng | tech |
| 少数派 | sspai.com/feed | tech |
| 贼拉正经的技术博客 | stackoverflow.wiki/blog/rss.xml | tech |
| 掮客酒馆 | wechat2rss.xlab.app | tech |
| 未闻Code | wechat2rss.xlab.app | tech |
| 知乎日报 | plink.anyfeeder.com/zhihu/daily | tech |

**技术精选** `pipeline/configs/tech-feeds.yaml`（3 个源）：阮一峰、贼拉正经、未闻Code

**YAML 配置格式：**

```yaml
name: my-feeds
sources:
  - name: 源名称
    url: https://example.com/rss.xml
    category: tech
    max_articles: 10
    enabled: true          # 可选，默认 true
```

### 模型设置

所有配置集中在 `pipeline/config.py`，关键配置如下：

| 设置项 | 默认值 | 说明 |
|--------|--------|------|
| `provider` | zhipu | API 提供商 |
| `l1_model` | glm-4.7 | L1 相关性评分模型 |
| `l2_model` | glm-4.7 | L2 摘要生成模型 |
| `l3_model` | glm-5.1 | L3 深度分析模型（计划中） |
| `api_base` | https://open.bigmodel.cn/api/paas/v4 | 智谱 API 接口地址 |
| `relevance_threshold` | 6 | 通过 L1 筛选的最低分数（1-10） |
| `tier_discard_max` | 3 | 评分 ≤ 此值直接丢弃 |
| `tier_compressed_max` | 6 | 评分 ≤ 此值生成压缩摘要 |
| `max_articles_per_run` | 50 | 每次运行硬上限 |

### 环境变量

| 变量 | 是否必填 | 说明 |
|------|----------|------|
| `ZHIPU_API_KEY` | 是 | 智谱 API 密钥，用于 LLM 调用 |
| `FEISHU_APP_ID` | 飞书必填 | 飞书企业自建应用 App ID |
| `FEISHU_APP_SECRET` | 飞书必填 | 飞书企业自建应用 App Secret |

---

## 评分分层机制

L1 筛选给出 1-10 的相关性评分后，文章按分数分为三个处理层级：

| 分数范围 | 处理方式 | 文件名示例 | 输出内容 |
|----------|----------|------------|----------|
| 1-3 | **丢弃** | 不生成文件 | — |
| 4-6 | **压缩摘要** | `[S5] some-article.md` | TL;DR + 关键要点（无原文） |
| 7-10 | **完整摘要** | `[S8] great-article.md` | TL;DR + 详细摘要 + 关键要点 + 原文 |

文件名中的 `[SN]` 前缀让用户在 Obsidian 文件列表中直接看到文章重要性，无需打开文件。

---

## Obsidian 知识库结构

```
vault/
└── SouthTwilight-Obsidian/          ← Obsidian 仓库根目录
    ├── .obsidian/                   ← Obsidian 配置
    └── 南国微光/                     ← 知识空间
        └── 个人知识库/               ← 管线写入目标
            ├── 0-Inbox/             ← 手动添加 / 未处理内容
            ├── 1-Daily/             ← 每日笔记
            ├── 2-Articles/          ← AI 处理后的文章
            │   └── 2026-05-08/      ← 按日期分组
            │       ├── [S8] ai-article.md
            │       ├── [S5] tech-news.md
            │       └── [S9] llm-paper.md
            ├── 3-GitHub/            ← GitHub 仓库动态（计划中）
            ├── 4-Newsletters/       ← 邮件订阅（计划中）
            ├── 5-Topics/            ← 主题知识地图（MOC）
            ├── 5-Templates/         ← 笔记模板
            ├── 6-Permanent/         ← 永久笔记
            └── 6-System/            ← 系统文档
```

**来源类型 → 目录映射：**

| 来源类型 | 目标目录 |
|----------|----------|
| RSS | `南国微光/个人知识库/2-Articles/YYYY-MM-DD/` |
| WEB_URL | `南国微光/个人知识库/2-Articles/YYYY-MM-DD/` |
| FEISHU | `南国微光/个人知识库/2-Articles/YYYY-MM-DD/` |
| GITHUB | `南国微光/个人知识库/3-GitHub/`（计划中） |
| EMAIL | `南国微光/个人知识库/4-Newsletters/`（计划中） |
| MANUAL | `南国微光/个人知识库/0-Inbox/` |

### 输出笔记格式

每篇处理后的文章生成 Markdown 文件，包含 YAML frontmatter：

```markdown
---
title: "文章标题"
source: RSS
source_name: Hacker News
author: 作者名
published_at: 2026-05-08T12:00:00
fetched_at: 2026-05-08T19:30:00
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

## 原文内容

（评分 ≥ 7 的文章保留完整原文）
```

---

## 日志

管线自动记录日志到控制台和文件：

| 目标 | 级别 | 位置 |
|------|------|------|
| 控制台 | 按 `--log-level` 设置（默认 INFO） | 标准输出 |
| 文件 | 始终 DEBUG | `pipeline/logs/pipeline_YYYYMMDD_HHMMSS.log` |
| 最新 | 始终 DEBUG | `pipeline/logs/pipeline_latest.log`（最近一次运行的软链接/副本） |

调试失败运行时，先查看 `pipeline/logs/`，文件日志包含完整的 DEBUG 输出和原始 API 响应。

---

## 依赖包

| 包名 | 版本要求 | 用途 |
|------|----------|------|
| trafilatura | >=1.6.0 | 网页正文提取 |
| feedparser | >=6.0.0 | RSS/Atom 订阅源解析 |
| pyyaml | >=6.0 | YAML 配置文件解析 |
| openai | >=1.0.0 | OpenAI 兼容 API 客户端（用于智谱 API） |
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

共 **110 个测试**，覆盖 11 个测试文件。所有外部依赖（feedparser、trafilatura、OpenAI API、飞书 API）均已 mock，无需网络连接。

| 模块 | 测试数 | 覆盖范围 |
|------|--------|----------|
| main.py | 6 | CLI 流程、试运行、文章数量限制、飞书来源 |
| rss_fetcher.py | 4 | 订阅源解析、正文提取 |
| web_extractor.py | 3 | URL 提取、批量模式 |
| feishu_extractor.py | 18 | URL 解析、Token 缓存、API 调用、文档提取、标题回退 |
| dedup.py | 5 | 去重、URL 标准化、SQLite |
| l1_filter.py | 4 | 相关性评分、阈值筛选、错误处理 |
| l2_summarizer.py | 5 | 摘要生成、JSON 解析、错误处理 |
| link_resolver.py | 22 | 链接提取、过滤、frontmatter 解析、编排流程 |
| obsidian_writer.py | 23 | frontmatter、目录路由、文件名冲突、评分分层、双向链接回写 |
| config.py | 9 | 默认配置、YAML 加载、enabled 字段、环境变量 |
| models.py | 9 | Article 数据模型、哈希计算、序列化、linked_urls/referenced_by |

---

## 项目目录结构

```
knowledge-base/
├── README.md                    ← 本文档
├── .env                         ← API 密钥（已被 gitignore）
├── .gitignore
├── docs/
│   └── plans/                   ← 里程碑规划文档
│       └── 2026-05-08-phase-1.5-enhancement.md
├── pipeline/
│   ├── __init__.py
│   ├── main.py                  ← CLI 入口
│   ├── config.py                ← 配置数据类 + YAML 加载
│   ├── models.py                ← Article、ArticleSource、ProcessingLevel
│   ├── requirements.txt         ← Python 依赖
│   ├── .venv/                   ← Python 3.11 虚拟环境
│   ├── configs/                 ← RSS 源配置文件
│   │   ├── default.yaml         ← 默认配置（8 个源）
│   │   └── tech-feeds.yaml      ← 技术精选（3 个源）
│   ├── data/                    ← 运行时数据（seen_articles.db）
│   ├── logs/                    ← 运行日志（pipeline_*.log）
│   ├── extractors/              ← 内容抓取器
│   │   ├── rss_fetcher.py       ← RSS 订阅源抓取 + 正文提取
│   │   ├── web_extractor.py     ← 单 URL 正文提取
│   │   └── feishu_extractor.py  ← 飞书文档提取（开放平台 API）
│   ├── processors/              ← AI 处理器
│   │   ├── l1_filter.py         ← L1 相关性评分（GLM-4.7）
│   │   ├── l2_summarizer.py     ← L2 摘要生成（GLM-4.7）
│   │   └── link_resolver.py    ← 引用链接深挖 + 双向 wikilink
│   ├── formatters/              ← 格式化输出
│   │   └── obsidian_writer.py   ← Markdown 格式化 + 日期目录 + 评分分层
│   ├── utils/                   ← 工具模块
│   │   └── dedup.py             ← SQLite 去重存储
│   └── tests/                   ← 110 个 pytest 测试
├── vault/                       ← Obsidian 知识库
│   └── SouthTwilight-Obsidian/  ← Obsidian 仓库根目录
│       ├── .obsidian/
│       └── 南国微光/
│           └── 个人知识库/
│               ├── 0-Inbox/
│               ├── 1-Daily/
│               ├── 2-Articles/  ← 按日期子目录 + 评分前缀文件名
│               ├── 3-GitHub/
│               ├── 4-Newsletters/
│               ├── 5-Topics/
│               ├── 6-Permanent/
│               └── 6-System/
```

---

## 开发路线图

- [x] **Phase 1（M0+M1）** — 核心流水线：RSS/Web 抓取、去重、L1 筛选（GLM-4.7）、L2 摘要（GLM-4.7）、Obsidian 写入
- [x] **Phase 1.5（增强）** — 评分分层内容深度、日期子目录、文件名评分前缀、YAML 配置文件支持
- [x] **Phase 2a（飞书提取器）** — 飞书文档提取：开放平台 API 鉴权、tenant_access_token 缓存、Markdown 原文提取
- [x] **Phase 2a+（链接深挖）** — 正文超链接保留、引用文章深挖（`--source resolve`）、双向 `[[wikilink]]`、Obsidian 笔记互联
- [ ] **Phase 2b** — Hermes Cron 定时调度、GitHub 提取器、邮件提取器
- [ ] **Phase 3** — L3 深度分析（GLM-5.1）、主题聚类、MOC 自动生成

---

## 许可证

个人项目，保留所有权利。
