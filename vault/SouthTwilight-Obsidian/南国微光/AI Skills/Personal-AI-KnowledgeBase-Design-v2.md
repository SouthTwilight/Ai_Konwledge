# 个人 AI 知识库系统 — 完整设计方案

> 版本: v2.0 | 日期: 2026-05-07 | 作者: Hermes Agent (经用户确认)

---

## 目录

1. [项目概述](#1-项目概述)
2. [原方案问题深度分析](#2-原方案问题深度分析)
3. [修订方案架构总览](#3-修订方案架构总览)
4. [技术栈选型与对比](#4-技术栈选型与对比)
5. [Token 优化与成本控制策略](#5-token-优化与成本控制策略)
6. [组件能力边界与调用协议](#6-组件能力边界与调用协议)
7. [完整数据流设计](#7-完整数据流设计)
8. [实施路线图](#8-实施路线图)
9. [部署与运维方案](#9-部署与运维方案)
10. [附录：备选方案对比](#10-附录备选方案对比)

---

## 1. 项目概述

### 1.1 目标

构建一个 **端到端的个人 AI 知识库系统**，实现从「内容发现」到「知识沉淀」再到「自由检索」的完整闭环：

| 环节 | 能力 | 用户体验 |
|------|------|---------|
| 内容发现 | 多源订阅（RSS、社交媒体分享） | 手机端一键触发 |
| 知识处理 | AI 驱动的提取、压缩、结构化 | 全自动，无需人工干预 |
| 知识存储 | 本地优先、可离线、双向链接 | 如同阅读自己的第二大脑 |
| 知识同步 | 多设备同步、版本历史 | 无缝切换设备 |

### 1.2 设计原则

1. **Windows 优先** — 所有组件可原生运行在 Windows 上，降低使用门槛
2. **离线优先** — 核心知识库本地存储，网络仅用于同步和 AI 处理
3. **手机交互** — 通过飞书/微信等 IM 平台实现移动端指令
4. **Token 经济** — 分层模型策略 + 压缩技术，控制 API 成本
5. **数据主权** — 所有知识以开放格式（Markdown）存储，不锁定在任何平台

---

## 2. 原方案问题深度分析

### 2.1 问题一：Hermes Agent 不适配 Windows

**症状**：Hermes Agent 需要在 Linux/macOS/WSL 环境运行，原生 Windows 不支持。

**根因分析**：

```
Hermes Agent 的 Linux 依赖链：
  Python 3.11+ (OK, Windows 支持)
    ├── prompt_toolkit (OK)
    ├── ripgrep (需要 WSL 或 Windows 二进制)  
    ├── tmux (Linux only — 用于多 agent 管理)
    ├── shell 工具链 (bash/grep/sed/awk — Windows 需 Git Bash)
    └── 部分 Python 库 (fcntl, pty — Unix only)
```

**影响评估**：

| 影响维度 | 严重程度 | 说明 |
|----------|---------|------|
| 安装体验 | ⚠️ 中 | 需要 WSL2 环境，对非技术用户门槛高 |
| 日常使用 | ✅ 低 | WSL2 已成熟，用户已有 WSL 环境 |
| 手机交互 | ✅ 无影响 | Gateway 独立运行，与本地环境无关 |
| 后台运行 | ⚠️ 中 | WSL2 关闭后 gateway 会停止，需要 systemd 配置 |

**结论**：Hermes Agent 的 Windows 问题并非"完全不可用"，而是"使用摩擦大"。**当前用户已有 WSL 环境，核心问题在于 gateway 的稳定运行和系统集成度。**

### 2.2 问题二：Token 消耗过高

**量化分析**（以处理一篇 5000 字中文技术文章为例）：

| 阶段 | 操作 | Token 消耗（估算） |
|------|------|-------------------|
| 内容抓取 | RSS → 正文提取 | ~2000 input |
| 初步清洗 | 去广告/去冗余 | ~3000 input + ~500 output |
| 摘要生成 | AI 摘要 | ~8000 input + ~1000 output |
| 深度解析 | 知识图谱提取 | ~10000 input + ~2000 output |
| 标签生成 | 分类标记 | ~2000 input + ~300 output |
| Obsidian 格式化 | 模板填充 | ~1000 input + ~500 output |
| **单篇合计** | | **~26,000 input + ~4,300 output** |

假设日均处理 20 篇文章，月均 600 篇：
- 月 input: ~15.6M tokens
- 月 output: ~2.6M tokens
- **DeepSeek 价格**: ~$3.5/月
- **Claude Sonnet 价格**: ~$55/月
- **GPT-4o 价格**: ~$75/月

**根因**：未做分层处理，所有内容都用同一模型全量处理。

### 2.3 问题三：Hermes Agent ↔ NotebookLM 边界模糊

**NotebookLM 的特性与限制**：

| 特性 | 说明 |
|------|------|
| 核心能力 | 基于上传文档的深度阅读理解、问答、摘要 |
| 输入方式 | 手动上传 PDF/网页/文本（**无公开 API**） |
| 输出方式 | 网页界面查看、导出为笔记（**无法编程调用**） |
| 适合场景 | 研究单个主题、深度阅读少量文档 |
| 不适合场景 | 大规模自动化管道处理 |

**核心矛盾**：NotebookLM 是「交互式阅读工具」而非「管道化处理器」。它无法被 Hermes Agent 程序化调用，导致管道在此断裂：

```
Hermes Agent（自动） ──X──> NotebookLM（手动） ──> Obsidian
                        ↑
                  此处需要人工介入
```

**结论**：NotebookLM 应被替换为 **可编程调用的 AI 处理管道**，或者退化为「深度研究时的手动辅助工具」。

---

## 3. 修订方案架构总览

### 3.1 架构全景图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        📱 交互层 (Mobile First)                      │
│                                                                      │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐   │
│   │  飞书 Bot │   │ 微信 Bot  │   │  Obsidian  │   │ 浏览器书签插件 │   │
│   │ (指令/分享)│   │ (指令/分享)│   │  (桌面读写) │   │ (一键收藏)    │   │
│   └─────┬────┘   └─────┬────┘   └─────┬────┘   └──────┬───────┘   │
│         └──────────────┴──────────────┴───────────────┘             │
│                            │                                         │
└────────────────────────────┼────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   🧠 Hermes Agent (编排中枢)                          │
│                   运行环境: WSL2 / Docker / 云服务器                   │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ Cron 调度引擎 │  │ Gateway 网关  │  │ 内容管道编排器             │  │
│  │ - RSS 定时抓取│  │ - 飞书/微信   │  │ - 去重 & 优先级排序        │  │
│  │ - 日/周摘要  │  │ - 指令路由    │  │ - Token 预算管理           │  │
│  │ - 清理维护   │  │ - 状态反馈    │  │ - 多级处理管道调度         │  │
│  └──────────────┘  └──────────────┘  └───────────────────────────┘  │
│                                                                      │
│  核心能力: 任务编排 · 工具调度 · 状态管理 · 跨组件协调              │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
┌──────────────────────┐ ┌──────────────┐ ┌──────────────────────┐
│   📥 内容采集层       │ │ 🤖 AI处理层  │ │  📊 知识结构化层     │
│                      │ │              │ │                      │
│  • RSS/Atom 订阅     │ │  L1: 快速过滤│ │  • 标签自动生成      │
│  • 网页正文提取       │ │  模型: DeepSeek│ │  • 知识图谱关系提取  │
│    (trafilatura)     │ │  功能: 去重/  │ │  • MOC 自动构建     │
│  • 飞书/微信分享收集  │ │  分类/相关性  │ │  • 双向链接建议      │
│  • 浏览器书签导入     │ │              │ │  • 每日/每周摘要生成  │
│                      │ │  L2: 摘要压缩 │ │                      │
│                      │ │  模型: DeepSeek│ │  输出格式:          │
│                      │ │  功能: 生成    │ │  Markdown +         │
│                      │ │  结构化摘要   │ │  YAML frontmatter   │
│                      │ │              │ │  + WikiLinks         │
│                      │ │  L3: 深度解析 │ │                      │
│                      │ │  模型: Claude  │ │                      │
│                      │ │  功能: 观点    │ │                      │
│                      │ │  提炼/批判性   │ │                      │
│                      │ │  思考/知识连接 │ │                      │
└──────────────────────┘ └──────────────┘ └──────────┬───────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     📚 Obsidian 知识库 (本地优先)                     │
│                                                                      │
│  目录结构:                                                          │
│  vault/                                                             │
│  ├── 0-Inbox/          ← 待处理收件箱                                │
│  ├── 1-Daily/          ← 每日笔记 (YYYY-MM-DD.md)                    │
│  ├── 2-Articles/       ← AI 处理后文章                               │
│  ├── 3-Topics/         ← 主题 MOC (Map of Content)                  │
│  ├── 4-Permanent/      ← 永久笔记/精炼知识                           │
│  ├── 5-Templates/      ← Obsidian 模板                              │
│  └── 6-System/         ← Dataview 查询/系统配置                      │
│                                                                      │
│  核心特性: WikiLinks · 标签 · Dataview · 图谱视图 · 本地搜索        │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ☁️ 同步与备份层                                   │
│                                                                      │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────┐    │
│  │ Remotely Save     │   │ Git 版本控制      │   │ OSS 对象存储  │    │
│  │ (Obsidian 插件)   │   │ (可选, 增量备份)  │   │ (阿里云/腾讯) │    │
│  │ S3/WebDAV 同步    │   │ 版本历史/回滚     │   │ 低成本归档    │    │
│  └──────────────────┘   └──────────────────┘   └──────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 与原方案的关键变化

| 维度 | 原方案 | 新方案 | 原因 |
|------|--------|--------|------|
| AI 核心处理器 | NotebookLM | **自建多级 LLM 管道** | NotebookLM 无 API，无法自动化 |
| 运行平台 | 仅 Linux/macOS | **WSL2（用户现有）+ Docker 备选** | 降低摩擦，利用现有环境 |
| Token 策略 | 无优化 | **L1/L2/L3 三级模型分层** | 成本降低 70-80% |
| 内容采集 | 仅 RSS | **RSS + IM 分享 + 浏览器插件** | 扩展内容来源 |
| 知识结构化 | 手动 | **自动标签 + MOC 构建 + 双向链接** | 提升知识可发现性 |

---

## 4. 技术栈选型与对比

### 4.1 编排中枢

| 候选 | Windows 原生 | API 调用 | Cron | IM 网关 | 评估 |
|------|:---:|:---:|:---:|:---:|------|
| **Hermes Agent (WSL)** | △ | ✅ | ✅ | ✅ | **选定** — 用户已有环境，功能完整 |
| n8n | ✅ | ✅ | ✅ | △ | 偏工作流，AI 能力需额外集成 |
| 自建 Python 脚本 | ✅ | ✅ | △ | △ | 灵活但开发成本高 |
| Dify | ✅ | ✅ | △ | △ | AI 应用强，但编排和 IM 偏弱 |

**选定: Hermes Agent (WSL2)**

原因：
1. 用户已有 WSL 环境和 Hermes 使用经验
2. 内置 Cron、Gateway、Memory、Skill 系统
3. 可通过 Gateway 实现手机交互（飞书/微信）
4. 可编排任意 Python 脚本和 API 调用

### 4.2 AI 处理模型（三级分层）

| 层级 | 用途 | 推荐模型 | 备选模型 | 单篇 Token 预算 |
|------|------|---------|---------|:---:|
| **L1 快速过滤** | 去重、分类、相关性判断 | DeepSeek-V3 | GLM-4-Flash, Qwen-2.5-7B | ~1,500 |
| **L2 摘要压缩** | 生成结构化摘要 | DeepSeek-R1 | GLM-4, Qwen-2.5-72B | ~5,000 |
| **L3 深度解析** | 观点提炼、知识连接、批判性思考 | Claude Sonnet 4 | GPT-4o, DeepSeek-R1 | ~10,000 |

**成本预估**（月均 600 篇文章）：

| 层级 | 模型 | 月 Token 量 | 月费用 |
|------|------|-----------|------|
| L1 | DeepSeek-V3 | ~1.8M in + ~300K out | ~$0.50 |
| L2 | DeepSeek-R1 | ~3M in + ~600K out | ~$2.00 |
| L3 | Claude Sonnet 4 | ~1M in + ~300K out | ~$5.00 |
| **合计** | | | **~$7.50/月** |

对比原方案（全部使用 Claude Sonnet）的 ~$55/月，**成本降低 86%**。

### 4.3 内容提取

| 工具 | 用途 | 特点 |
|------|------|------|
| **trafilatura** | 网页正文提取 | Python 库，准确率高，支持中文 |
| **feedparser** | RSS/Atom 解析 | Python 标准 RSS 库 |
| **newspaper3k** | 新闻文章提取 | 备选，支持多语言 |
| **readabilipy** | Mozilla Readability 移植 | 备选 |

### 4.4 知识库存储

| 候选 | 格式 | 双向链接 | 本地优先 | 插件生态 | 评估 |
|------|------|:---:|:---:|:---:|------|
| **Obsidian** | Markdown | ✅ | ✅ | ✅ | **选定** |
| Logseq | Markdown/Org | ✅ | ✅ | ✅ | 偏向大纲，不如 Obsidian 灵活 |
| Notion | 专有格式 | ❌ | ❌ | ❌ | 数据不开放，不满足本地优先原则 |
| Trilium | SQLite | ❌ | ✅ | △ | 功能强但社区小 |

**选定: Obsidian**

原因：
1. 纯 Markdown 格式，数据完全开放
2. 强大的双向链接和知识图谱
3. 丰富的插件生态（Dataview、Remotely Save、Templater）
4. 用户已熟悉 Obsidian 使用

### 4.5 同步方案

| 方案                                 | 实现                            | 优势       | 劣势       |
| ---------------------------------- | ----------------------------- | -------- | -------- |
| **Remotely Save + OSS**            | Obsidian 插件 → S3/WebDAV       | 零配置，增量同步 | 需 OSS 服务 |
| Git + GitHub                       | git auto-commit + push        | 版本历史     | 二进制文件不友好 |
| Syncthing                          | P2P 同步                        | 无服务器     | 需多设备同时在线 |
| **Remotely Save + OSS + Git (推荐)** | 主要同步用 Remotely Save，Git 做版本历史 | 双保险      | 配置稍复杂    |

---

## 5. Token 优化与成本控制策略

### 5.1 核心策略总览

```
┌──────────────────────────────────────────────────────────────┐
│                    Token 优化五层策略                          │
│                                                               │
│  Layer 5: 智能调度 ─ 根据内容价值动态选择处理深度             │
│  Layer 4: RTK 压缩 ─ Rust Token Killer 文本预处理             │
│  Layer 3: 分层模型 ─ L1(便宜)/L2(中等)/L3(贵) 三级过滤       │
│  Layer 2: 结构化输出 ─ 限制输出长度，减少废话                 │
│  Layer 1: 内容去重 ─ 相似文章去重，避免重复处理               │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Layer 1: 内容去重

```python
# 伪代码：基于语义哈希的去重
def deduplicate_articles(articles):
    seen_hashes = set()
    unique = []
    for article in articles:
        # 提取关键句做 MinHash
        key_sentences = extract_key_sentences(article.content)
        sig = minhash(key_sentences)
        if sig not in seen_hashes:
            seen_hashes.add(sig)
            unique.append(article)
    return unique
```

**预期节省**: 10-20% Token（RSS 源常有重复/转载内容）

### 5.3 Layer 2: 结构化输出

强制 LLM 输出结构化 JSON/YAML，避免冗余描述：

```yaml
# L2 摘要输出格式（约 300 tokens）
title: "文章标题"
summary: "3 句话摘要（≤150 字）"
key_points:
  - "要点 1"
  - "要点 2"
  - "要点 3"
tags: ["标签1", "标签2"]
relevance_score: 8  # 1-10
related_topics: ["相关主题1"]
```

### 5.4 Layer 3: 分层模型策略

```
内容流入
    │
    ▼
┌─────────────┐
│  L1 过滤器   │  模型: DeepSeek-V3 (极便宜)
│  相关性评分  │  Token: ~1000 in + ~200 out
│  分类标签    │  功能: 判断是否值得深度处理
└──────┬──────┘
       │
   ┌───┴───────────────┐
   │ relevance ≥ 7?    │
   └───┬───────┬───────┘
   是  │       │ 否 → 仅保存原文 + 基本标签（归档）
       ▼
┌─────────────┐
│  L2 摘要器   │  模型: DeepSeek-R1 (中等价格)
│  结构化摘要  │  Token: ~4000 in + ~500 out
│  关键要点    │  功能: 生成可读摘要
└──────┬──────┘
       │
   ┌───┴───────────────┐
   │ relevance ≥ 9?    │  ← 仅 10-20% 文章进入 L3
   └───┬───────┬───────┘
   是  │       │ 否 → 保存 L2 摘要
       ▼
┌─────────────┐
│  L3 深度解析 │  模型: Claude Sonnet (贵但质量高)
│  观点提炼    │  Token: ~8000 in + ~1000 out
│  知识连接    │  功能: 深度思考，建立知识关联
│  批判性分析  │
└─────────────┘
```

**预期效果**：
- 80% 文章仅到 L2
- 15% 文章到 L3
- 5% 文章仅归档（L1 判定低相关）
- 整体成本控制在 $7-10/月

### 5.5 Layer 4: RTK (Rust Token Killer) 集成

RTK 是一个 Rust 编写的 Token 压缩工具，可在送入 LLM 前对文本做无损/有损压缩：

```python
# 集成方式
import subprocess

def compress_with_rtk(text: str, compression_level: str = "medium") -> str:
    """使用 RTK 压缩文本以减少 Token 消耗"""
    result = subprocess.run(
        ["rtk", "compress", "--level", compression_level],
        input=text,
        capture_output=True,
        text=True
    )
    return result.stdout
```

**压缩级别**：

| 级别 | 压缩率 | 质量影响 | 适用场景 |
|------|:---:|------|------|
| light | 10-15% | 几乎无损 | L3 深度解析 |
| medium | 25-35% | 轻微信息丢失 | L2 摘要 |
| aggressive | 40-50% | 明显压缩 | L1 过滤 |

### 5.6 Layer 5: 智能调度

基于内容价值动态分配 Token 预算：

```python
def allocate_token_budget(article):
    """根据文章属性动态分配 Token 预算"""
    signals = {
        "source_authority": article.source_rating,  # 来源权威度 1-10
        "topic_interest": user_interest_score(article.tags),  # 用户兴趣度
        "freshness": hours_since_publish(article),  # 时效性
        "uniqueness": compute_uniqueness(article),  # 独特性
    }
    
    # 加权计算价值分数
    value_score = (
        0.3 * signals["source_authority"] +
        0.4 * signals["topic_interest"] +
        0.2 * signals["freshness"] +
        0.1 * signals["uniqueness"]
    )
    
    return value_score
```

### 5.7 月成本预估总表

| 项目 | 原方案 (全量 Claude) | 新方案 (分层优化) | 节省 |
|------|------:|------:|:---:|
| L1 过滤 (DeepSeek-V3) | — | ~$0.50 | — |
| L2 摘要 (DeepSeek-R1) | — | ~$2.00 | — |
| L3 深度 (Claude) | — | ~$5.00 | — |
| 全量处理 (Claude) | ~$55.00 | — | — |
| **月合计** | **~$55.00** | **~$7.50** | **86%** |
| **年合计** | **~$660** | **~$90** | **$570** |

---

## 6. 组件能力边界与调用协议

### 6.1 能力边界矩阵

```
┌──────────────────────────────────────────────────────────────────┐
│                        能力边界定义                               │
│                                                                   │
│  Hermes Agent（编排中枢）                                         │
│  ✅ 擅长: 任务调度、Cron、IM 交互、Memory、多组件编排             │
│  ❌ 不擅长: 大规模文本分析（Token 消耗大）、知识图谱持久化        │
│  📡 对外接口: Cron jobs, Gateway, Terminal, delegate_task         │
│                                                                   │
│  AI 处理管道（Python + LLM API）                                  │
│  ✅ 擅长: 文本分析、摘要、标签、结构化                           │
│  ❌ 不擅长: 任务编排、用户交互、持久化                            │
│  📡 对外接口: CLI / HTTP API (被 Hermes 调用)                     │
│                                                                   │
│  Obsidian（知识库 UI + 存储）                                     │
│  ✅ 擅长: Markdown 编辑、双向链接、知识图谱可视化、本地搜索       │
│  ❌ 不擅长: 自动化处理、AI 分析                                  │
│  📡 对外接口: 文件系统读写（Markdown）                            │
│                                                                   │
│  OSS（同步 & 备份）                                               │
│  ✅ 擅长: 文件存储、版本管理、多区域同步                         │
│  ❌ 不擅长: 内容处理                                             │
│  📡 对外接口: S3 API / WebDAV                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 调用协议定义

```
┌──────────┐      Cron 触发/IM 指令       ┌──────────────┐
│  用户     │ ──────────────────────────▶  │ Hermes Agent │
│ (飞书/微信)│ ◀──────────────────────────  │  (编排中枢)   │
└──────────┘      状态反馈/每日摘要         └──────┬───────┘
                                                   │
                          ┌────────────────────────┼────────────────────┐
                          │ subprocess/HTTP        │ file write         │
                          ▼                        ▼                    ▼
                   ┌──────────────┐        ┌──────────────┐    ┌──────────────┐
                   │ AI 处理管道   │        │ Obsidian     │    │ Git / OSS    │
                   │ (Python CLI) │        │ (Markdown)   │    │ (同步备份)   │
                   └──────────────┘        └──────────────┘    └──────────────┘

调用协议细节：

1. Hermes → AI 处理管道:
   - 方式: terminal() 调用 Python 脚本
   - 输入: JSON 文件 (包含待处理文章列表)
   - 输出: JSON 文件 (处理结果) + Markdown 文件 (Obsidian 格式)
   - 协议: 文件系统约定路径
   
2. Hermes → Obsidian:
   - 方式: 直接写入 .md 文件到 vault 目录
   - 格式: YAML frontmatter + Markdown body + WikiLinks
   - 路径: <vault>/2-Articles/<YYYY-MM-DD>-<slug>.md
   
3. Obsidian → OSS:
   - 方式: Remotely Save 插件自动同步
   - 协议: S3 API 或 WebDAV
   - 触发: Obsidian 启动时 / 定时 / 手动
```

### 6.3 文件路径约定

```
/mnt/e/WSL/knowledge-base/          ← 项目根目录
├── hermes/
│   ├── config.yaml                 ← Hermes 配置（知识库专用 profile）
│   ├── skills/                     ← 知识库专用 Skills
│   │   ├── rss-ingestion.md        # RSS 抓取 Skill
│   │   ├── article-processing.md   # 文章处理 Skill
│   │   └── daily-digest.md         # 每日摘要 Skill
│   └── cron/                       ← Cron 任务定义
│
├── pipeline/                       ← AI 处理管道
│   ├── extractors/                 # 内容提取器
│   │   ├── rss_fetcher.py
│   │   ├── web_extractor.py
│   │   └── im_collector.py
│   ├── processors/                 # AI 处理器
│   │   ├── l1_filter.py
│   │   ├── l2_summarizer.py
│   │   └── l3_deep_analyzer.py
│   ├── formatters/                 # Obsidian 格式化
│   │   └── obsidian_writer.py
│   ├── utils/
│   │   ├── token_budget.py
│   │   ├── rtk_integration.py
│   │   └── deduplication.py
│   └── requirements.txt
│
├── vault/                          ← Obsidian Vault（同步目录）
│   ├── .obsidian/                  # Obsidian 配置
│   ├── 0-Inbox/
│   ├── 1-Daily/
│   ├── 2-Articles/
│   ├── 3-Topics/
│   ├── 4-Permanent/
│   ├── 5-Templates/
│   └── 6-System/
│
└── docs/                           ← 项目文档
    ├── design/
    └── changelog/
```

---

## 7. 完整数据流设计

### 7.1 主线流程：RSS 文章处理

```
时间线: Cron 每小时触发一次

T+0:00  Hermes Agent Cron 触发 RSS 抓取 Skill
          │
T+0:05  pipeline/rss_fetcher.py
          ├── 从配置的 RSS 源列表抓取最新文章
          ├── trafilatura 提取正文
          └── 去重检查（对比已处理 URL 数据库）
          │
T+0:10  pipeline/l1_filter.py (DeepSeek-V3)
          ├── 对每篇新文章进行相关性评分 (1-10)
          ├── 生成初步分类标签
          └── 过滤掉 relevance < 5 的文章
          │
T+0:30  pipeline/l2_summarizer.py (DeepSeek-R1)
          ├── 对 relevance ≥ 5 的文章生成结构化摘要
          ├── 提取关键要点和标签
          └── 输出结构化 JSON
          │
T+1:00  pipeline/l3_deep_analyzer.py (Claude Sonnet) — 仅 relevance ≥ 8
          ├── 深度观点提炼
          ├── 与已有知识库的关联分析
          ├── 批判性思考标注
          └── 输出增强版笔记
          │
T+1:30  pipeline/obsidian_writer.py
          ├── 将处理结果转换为 Markdown + YAML frontmatter
          ├── 生成 WikiLinks 双向链接
          ├── 更新 MOC (Map of Content) 索引
          └── 写入 Obsidian Vault
          │
T+1:35  Hermes Agent 记录处理日志 → Memory
          │
T+1:36  如果配置了即时推送:
          └── Gateway 推送摘要到飞书/微信
```

### 7.2 支线流程：手机分享内容

```
用户在手机上看到感兴趣的文章
    │
    ├── 飞书: 发送链接给 Hermes Bot
    │   └── Bot 回复: "收到，已加入处理队列 ⏳"
    │
    └── 微信: 发送链接给 Hermes Bot（需公众号/企业微信）
        └── Bot 回复: "收到，已加入处理队列 ⏳"
    
    │
    ▼
Hermes Agent Gateway 接收消息
    │
    ├── 识别 URL
    ├── 提取网页内容 (trafilatura)
    ├── 加入优先级队列（手动分享 = 高优先级）
    └── 标记来源: "来自手机分享@飞书/微信"
    │
    ▼
进入 L1 → L2 → (L3) 处理管道（同上）
    │
    ▼
处理完成后:
    └── Gateway 推送: "📝 《文章标题》已处理完毕，已存入知识库。[查看摘要...]"
```

### 7.3 Obsidian 输出格式示例

```markdown
---
title: "深度学习在自然语言处理中的最新进展"
source: "https://example.com/article-123"
source_name: "机器之心"
date_processed: 2026-05-07
date_published: 2026-05-06
tags:
  - AI/NLP
  - deep-learning
  - transformer
relevance: 9
processing_level: L3
related:
  - "[[Attention机制详解]]"
  - "[[Transformer架构演进]]"
  - "[[大语言模型训练]]"
moc: "[[NLP知识索引]]"
---

# 深度学习在自然语言处理中的最新进展

> **来源**: [机器之心](https://example.com/article-123) | **发表日期**: 2026-05-06
> **AI 处理级别**: L3 深度解析 | **相关性**: 9/10

## 📌 一句话总结
2026年NLP领域的核心趋势是小型高效模型的崛起和多模态融合的深化。

## 🎯 核心要点

1. **小型模型性能突破**: 通过知识蒸馏和架构优化，10B参数模型在多项基准上接近100B模型水平
2. **多模态统一架构**: Any-to-Any 模型成为主流，文本/图像/音频统一处理
3. **推理效率提升**: 投机解码和KV缓存优化使推理速度提升3-5倍

## 💡 深度分析

### 小型模型的逆袭

传统认知中「大模型更好」的范式正在被打破。通过以下技术路径...

### 与已有知识的关联

- 与 [[大语言模型训练]] 中提到的 Scaling Law 形成有趣对比
- 补充了 [[Transformer架构演进]] 中关于高效注意力的讨论

## 🔗 延伸阅读

- [[Attention机制详解]] — 理解本文技术背景
- [[NLP知识索引]] — 相关主题汇总
- 原文链接: https://example.com/article-123

## 📝 个人笔记

[此处为手动添加的个人思考空间]
```

---

## 8. 实施路线图

### 8.1 里程碑总览

```
M0: 环境搭建         M1: 核心管道        M2: 智能处理        M3: 交互完善
[Week 1]            [Week 2-3]         [Week 4-5]         [Week 6-7]

 配置 Hermes          RSS 抓取            L1/L2/L3 管道     飞书 Bot 接入
 安装依赖            内容提取              Token 预算        微信 Bot 接入
 Obsidian Vault      去重归档             RTK 集成          每日摘要推送
 OSS 同步配置         Obsidian 输出       MOC 构建         浏览器插件
```

### 8.2 详细任务分解

---

#### M0: 环境搭建（Week 1）

**T0.1 创建知识库项目结构**
- 输入: 无
- 产出: `/mnt/e/WSL/knowledge-base/` 完整目录树
- 验证: `ls -la /mnt/e/WSL/knowledge-base/` 显示所有目录
- 关闭: commit 项目结构

**T0.2 配置 Hermes Agent 知识库专用 Profile**
- 输入: 现有 Hermes 安装
- 产出: `hermes profile create knowledge-base`，配置 model/tools/cron
- 验证: `hermes -p knowledge-base doctor` 全部通过
- 关闭: profile 配置完成

**T0.3 初始化 Obsidian Vault**
- 输入: 项目目录
- 产出: `vault/` 包含 `.obsidian/` 配置 + 6 个子目录 + 基础模板
- 验证: Obsidian 打开 vault 可正常加载
- 关闭: vault 初始化

**T0.4 配置 Obsidian 必要插件**
- 输入: Obsidian 安装
- 产出: 启用 Dataview、Templater、Remotely Save
- 验证: 插件列表显示已启用
- 关闭: 插件配置导出

**T0.5 配置 OSS 同步**
- 输入: 阿里云/腾讯云 OSS bucket
- 产出: Remotely Save 配置指向 OSS，首次同步成功
- 验证: 修改 vault 文件后 OSS 上有对应更新
- 关闭: 同步验证通过

**T0.6 安装 Python 管道依赖**
- 输入: Python 3.11+
- 产出: `pipeline/requirements.txt` 全部安装
- 验证: `python -c "import trafilatura, feedparser"` 无报错
- 关闭: 依赖就绪

---

#### M1: 核心管道（Week 2-3）

**T1.1 实现 RSS 抓取器**
- 文件: `pipeline/extractors/rss_fetcher.py`
- 功能: 读取 RSS 源列表，抓取新文章，trafilatura 提取正文，去重
- 验证: 运行脚本，输出新文章列表 JSON

**T1.2 实现 URL 内容提取器**
- 文件: `pipeline/extractors/web_extractor.py`
- 功能: 接收单个 URL，提取正文和元数据
- 验证: 传入测试 URL，返回干净的正文文本

**T1.3 实现去重与归档**
- 文件: `pipeline/utils/deduplication.py`
- 功能: 基于 URL + 语义哈希的去重，已处理 URL 持久化
- 验证: 重复文章被正确过滤

**T1.4 实现 Obsidian 格式化输出**
- 文件: `pipeline/formatters/obsidian_writer.py`
- 功能: 将处理结果转为 Markdown + YAML frontmatter，写入 vault
- 验证: 输出文件可被 Obsidian 正确渲染，标签和链接有效

**T1.5 创建 Hermes RSS 抓取 Skill**
- 文件: `hermes/skills/rss-ingestion.md`
- 功能: 定义 Cron 触发的完整 RSS 抓取工作流
- 验证: `hermes -p knowledge-base -s rss-ingestion` 手动触发成功

---

#### M2: 智能处理（Week 4-5）

**T2.1 实现 L1 过滤器**
- 文件: `pipeline/processors/l1_filter.py`
- 功能: DeepSeek-V3 调用，相关性评分，分类标签
- 验证: 输出评分 1-10 的标注结果

**T2.2 实现 L2 摘要器**
- 文件: `pipeline/processors/l2_summarizer.py`
- 功能: DeepSeek-R1 调用，结构化摘要，关键要点
- 验证: 输出符合 schema 的 JSON

**T2.3 实现 L3 深度分析器**
- 文件: `pipeline/processors/l3_deep_analyzer.py`
- 功能: Claude Sonnet 调用，观点提炼，知识关联
- 验证: 输出增强版笔记（含批判性分析）

**T2.4 实现 Token 预算管理**
- 文件: `pipeline/utils/token_budget.py`
- 功能: 动态分配 Token，日/月 Token 跟踪
- 验证: 日志输出 Token 使用统计

**T2.5 实现 RTK 集成**
- 文件: `pipeline/utils/rtk_integration.py`
- 功能: 调用 RTK 进行不同级别压缩
- 验证: 压缩前后 Token 数对比

**T2.6 实现 MOC 自动构建**
- 文件: 集成到 `obsidian_writer.py`
- 功能: 根据标签和主题自动更新 MOC 页面
- 验证: MOC 页面正确列出相关文章链接

**T2.7 创建 Hermes 文章处理 Skill**
- 文件: `hermes/skills/article-processing.md`
- 功能: 串联 L1→L2→L3→Obsidian 完整管道
- 验证: 端到端处理一篇文章

---

#### M3: 交互完善（Week 6-7）

**T3.1 配置飞书 Bot**
- 功能: 接收用户消息，识别 URL，触发处理管道
- 验证: 飞书发送 URL → Bot 回复确认 → 文章出现在 Obsidian

**T3.2 配置微信 Bot（可选）**
- 功能: 类似飞书 Bot，通过企业微信/公众号
- 验证: 微信发送 URL → Bot 回复确认

**T3.3 实现每日摘要推送**
- 文件: `hermes/skills/daily-digest.md`
- 功能: Cron 每日生成摘要，通过 Gateway 推送
- 验证: 每日收到处理统计 + 推荐文章

**T3.4 实现查询指令**
- 功能: 手机发送「查 <关键词>」返回相关知识库文章
- 验证: 查询返回准确的相关文章列表

**T3.5 浏览器书签插件（可选）**
- 功能: 一键发送当前页面到知识库
- 实现: 调用飞书/微信 Bot API
- 验证: 点击插件按钮 → Bot 收到并处理

---

### 8.3 任务统计

| 里程碑 | 任务数 | 预估时间 | 核心产出 |
|--------|:---:|------|------|
| M0 环境搭建 | 6 | 1 周 | 完整可运行的基础环境 |
| M1 核心管道 | 5 | 2 周 | 端到端 RSS→Obsidian 流程 |
| M2 智能处理 | 7 | 2 周 | L1/L2/L3 三级 AI 处理 |
| M3 交互完善 | 5 | 2 周 | 手机交互 + 每日摘要 |
| **合计** | **23** | **7 周** | **完整 AI 知识库系统** |

---

## 9. 部署与运维方案

### 9.1 运行环境配置

```yaml
# Hermes Agent 配置要点
environment: WSL2 (Ubuntu 22.04/24.04)
python: 3.11+
wsl_config:  # /etc/wsl.conf
  [boot]
  systemd=true  # 确保 gateway 作为服务运行

# WSL2 保持后台运行
# Windows 端设置: 电源选项 → 休眠改为从不
```

### 9.2 Gateway 持久化运行

```bash
# 方案 1: systemd 服务 (推荐，需 WSL2 systemd=true)
systemctl --user enable hermes-gateway
systemctl --user start hermes-gateway

# 方案 2: 备选 — 云服务器部署
# 如果 WSL 稳定性不佳，可在低成本云服务器（如阿里云 ECS 2C2G）运行
# Hermes Agent + Gateway，通过 Obsidian Remotely Save 同步到本地
```

### 9.3 Cron 任务清单

```bash
# 每 2 小时: RSS 抓取 + 快速处理
hermes cron create "0 */2 * * *" \
  -p knowledge-base \
  -s rss-ingestion \
  --name "rss-fetch"

# 每天 8:00: 深度处理前一天的高价值文章
hermes cron create "0 8 * * *" \
  -p knowledge-base \
  -s article-processing \
  --name "deep-process"

# 每天 9:00: 推送每日知识摘要
hermes cron create "0 9 * * *" \
  -p knowledge-base \
  -s daily-digest \
  --name "daily-digest"

# 每周日 3:00: Token 统计 + 知识库清理
hermes cron create "0 3 * * 0" \
  -p knowledge-base \
  -s maintenance \
  --name "weekly-maintenance"
```

### 9.4 监控指标

| 指标 | 监控方式 | 告警阈值 |
|------|---------|---------|
| 日处理文章数 | Cron 日志 | < 5 篇/天 |
| 月 Token 消耗 | Token 预算日志 | > $15/月 |
| Gateway 在线状态 | systemd 监控 | 离线 > 10 分钟 |
| RSS 源健康度 | 抓取成功率 | < 80% |
| OSS 同步状态 | Remotely Save 日志 | 同步失败 > 3 次 |

### 9.5 备份策略

```
3-2-1 备份原则:
  3 份副本: 本地 Obsidian + OSS + Git
  2 种介质: SSD (本地) + 对象存储 (云端)
  1 份异地: OSS 异地备份/跨区域复制
```

---

## 10. 附录：备选方案对比

### 方案 A: Hermes Agent (WSL) + 自建管道 + Obsidian ⭐ 推荐

| 维度 | 评估 |
|------|------|
| Windows 兼容 | ⚠️ 需 WSL2，但用户已有环境 |
| 自动化程度 | ✅ 全自动 |
| 成本 | ✅ ~$7.5/月 |
| 灵活性 | ✅ 完全可定制 |
| 实施难度 | ⚠️ 中等（需 7 周） |
| 维护成本 | ⚠️ 需要维护 Python 管道 |

### 方案 B: 全云部署 (Hermes Agent on VPS)

| 维度 | 评估 |
|------|------|
| Windows 兼容 | ✅ 浏览器访问，无本地依赖 |
| 自动化程度 | ✅ |
| 成本 | ❌ 服务器 ~$20-50/月 |
| 灵活性 | ✅ |
| 实施难度 | ⚠️ |
| 维护成本 | ⚠️ 需维护服务器 |

### 方案 C: Dify + Obsidian

| 维度 | 评估 |
|------|------|
| Windows 兼容 | ✅ Docker Desktop |
| 自动化程度 | △ Dify 工作流可自动化但 Cron 弱 |
| 成本 | ✅ ~$7.5/月 |
| 灵活性 | ⚠️ Dify 平台限制 |
| 实施难度 | ✅ 低（可视化编排） |
| 维护成本 | ✅ 低 |

### 方案 D: 纯 Obsidian 插件方案

| 维度 | 评估 |
|------|------|
| Windows 兼容 | ✅ |
| 自动化程度 | ❌ 需大量手动操作 |
| 成本 | ✅ 仅 Obsidian Sync $5/月 |
| 灵活性 | ❌ 受插件限制 |
| 实施难度 | ✅ 极低 |
| 维护成本 | ✅ 极低 |

---

## 总结

推荐 **方案 A**，核心理由：

1. **利用现有投资** — 用户已有 WSL 环境、Hermes 使用经验、Obsidian 熟悉度
2. **成本极低** — $7.5/月的 AI 成本 + OSS 存储费用
3. **数据主权** — Markdown 格式，不被任何平台锁定
4. **渐进式建设** — 7 周分 4 个里程碑，每阶段独立可用
5. **可扩展** — 管道架构支持未来加入更多数据源和处理策略

下一步：确认此方案后，可以进入 M0 环境搭建阶段。
