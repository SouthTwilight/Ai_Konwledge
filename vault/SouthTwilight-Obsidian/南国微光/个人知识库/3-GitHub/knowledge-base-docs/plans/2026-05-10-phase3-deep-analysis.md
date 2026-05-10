# AI 个人知识库 V3 — Phase 3 深度分析计划

> 计划日期: 2026-05-10  
> 前置文档: phase1-midterm-assessment.md, phase2-expansion-plan.md  
> 项目路径: `/mnt/e/WSL/knowledge-base/`  
> 当前基线: Phase 1 + 1.5 + 2 全部完成，122 个测试，5 种内容源，Cron 定时运行

---

## 一、Phase 3 范围定义

### 1.1 核心目标

Phase 3 的主题是「**从信息收集到知识理解**」—— 在前两阶段建立了稳定采集管道之后，Phase 3 让系统开始理解知识之间的深层关系。

```
Phase 1-2: 抓取 → 筛选 → 摘要 → 写入     (信息管线)
Phase 3:   分析 → 聚类 → 关联 → 导航       (知识理解)
```

### 1.2 里程碑规划

```
M5: GitHub 提取器重构 — 项目能力分析    (1.5天)
M6: L3 深度分析 — GLM-5.1 逐篇深解       (1.5天)
M7: 主题聚类 — 向量嵌入 + 相似度分组      (2天)
M8: MOC 自动生成 — 知识地图              (1.5天)
M9: 感知增强 — Playwright JS 渲染 + 去重升级  (1.5天)
```

**总计预估: 7.5 天**

### 1.3 Phase 3 不做什么

以下功能**不包括**在 Phase 3 范围：

- **不是全文搜索引擎** — 不建 Elastic/Meilisearch 索引
- **不是 RAG 问答** — 不做向量数据库 + LLM 问答链
- **不是 API 暴露** — 不提供 HTTP 接口或 Obsidian 插件
- **不是多用户系统** — 始终是单用户个人知识库
- **不分析代码本身** — GitHub 提取器分析 README/文档，不分析源码

---

## 二、当前状态基线

### 2.1 代码结构

```
pipeline/
├── main.py                  ← CLI, 5种来源: rss|url|feishu|github|email
├── config.py                ← 模型配置 + EmailConfig + FeishuConfig
├── models.py                ← Article dataclass, 6种来源枚举
├── extractors/              ← 5个抓取器 (rss/web/feishu/github/email)
├── processors/              ← L1(评分) + L2(摘要), 都用 GLM-4.7
├── formatters/
│   └── obsidian_writer.py   ← Markdown + frontmatter + wikilink
├── utils/
│   └── dedup.py             ← SQLite URL哈希去重
├── configs/                 ← YAML RSS源配置
└── tests/                   ← 122 tests, 12个测试文件
```

### 2.2 知识库产出

```
vault/.../个人知识库/
├── 2-Articles/              ← RSS/URL/飞书 (按日期)
├── 3-GitHub/                ← GitHub Release (按日期)
├── 4-Newsletters/           ← Email Newsletter (按日期)
├── 5-Topics/                ← 空，等待 MOC 自动生成
└── 6-System/                ← 项目文档
```

### 2.3 AI 模型使用

| 层级 | 模型 | 用途 | 状态 |
|------|------|------|------|
| L1 | GLM-4.7 | 相关性评分 | 运行中 |
| L2 | GLM-4.7 | 结构化摘要 | 运行中 |
| L3 | GLM-5.1 | 深度分析 | **计划中** |

### 2.4 GitHub 提取器现状（待重构）

当前实现聚焦 Release Notes，但用户真实需求是**理解项目本身**：

| 当前行为 | 目标行为 |
|----------|----------|
| 抓取 Release Notes | 抓取并分析 README + 文档 |
| 标题: `repo v1.2.0: Bug fixes` | 标题: `repo: AI-powered code review tool` |
| 内容: 版本更新日志 | 内容: 项目是什么、解决什么问题、怎么用 |
| 每次 Release 一条 Article | 每个新仓库一条 Article（或定期更新） |

---

## 三、M5: GitHub 提取器重构 — 项目能力分析

### 目标

将 GitHub 提取器从「追踪 Release 版本」改为「分析项目能力与作用」：
- 抓取项目的 README.md 和相关文档
- 用 AI 理解项目定位：做什么、怎么用、技术栈
- 输出项目能力摘要笔记，而非版本更新日志

### 四维评估

| 维度 | 评估 |
|------|------|
| 兼容性 | 完全兼容。对外接口不变（仍返回 `List[Article]`）|
| 修改量 | 重写 github_extractor.py 核心逻辑（~200行）+ 更新测试（~15个）+ 调整 obsidian_writer 路由 |
| 维护成本 | 中。README 抓取比 Release 更稳定（README 不频繁更新），去重要从 Release URL 改为 Repo URL |
| 目标破坏 | 无。新目标比旧目标更符合「追踪技术动态」的核心定位 |

### 设计

```
GitHub Project Analyzer:
  输入: starred repos（或 --github-repos 指定）
  处理:
    1. 去重检查: 该 repo 是否已分析过（dedup key = repo full_name）
    2. README 抓取: GET /repos/{repo}/readme → 获取 Markdown 原文
    3. AI 摘要: 用 L3 模型（或简化的 L2）提取项目能力描述
    4. 补充信息: description, topics, homepage, language, stars
  输出: Article
    url = repo html_url
    title = "{repo}: {description}"
    content_raw = README 原文
    content_summary = "项目能力摘要"（AI 生成）
    tags = GitHub topics
    source = GITHUB
```

### 任务分解

#### M5.1: 重写 github_extractor.py

**保留部分:**
- API 认证（httpx + GITHUB_TOKEN）— 不变
- `get_starred_repos()` — 保留，获取 starred 仓库列表

**删除部分:**
- `fetch_releases()` — 不再需要
- `_release_to_article()` — 替换为 `_repo_to_article()`
- draft/prerelease 过滤逻辑 — 删除

**新增部分:**
- `fetch_readme(repo)` — `GET /repos/{repo}/readme`，接受 `Accept: application/vnd.github.raw+json` 获取原始 Markdown
- `fetch_repo_info(repo)` — 获取 description、topics、language、stars。**不抓取源码**
- `_analyze_project(article)` — 用 AI 提炼项目能力摘要（可复用 L2 或新建轻量分析流程）
- 去重策略变更: 按 repo full_name 去重，确保同一仓库只分析一次

#### M5.2: 更新测试

- 删除 Release 相关测试（mock release API 响应）
- 新增 README 抓取测试
- 新增项目信息获取测试
- 新增去重测试（同一 repo 不重复处理）
- 预计测试总数保持不变（~15个）

#### M5.3: 调整 Obsidian 写入

- 文章标题从 `repo v1.2.0: changelog` 改为 `repo: project description`
- `3-GitHub/` 目录下文件名从日期子目录改为按仓库组织（`3-GitHub/{repo-name}.md`），因为项目分析笔记更适合按项目而非按日期组织
- frontmatter 中增加 `github_stars`、`github_language`、`github_topics` 字段

---

## 四、M6: L3 深度分析 — GLM-5.1 逐篇深解

### 目标

对于评分 ≥ 7 的高价值文章，在 L1 筛选和 L2 摘要之后，额外进行 L3 深度分析：
- 提取文章的深层逻辑结构
- 识别与其他文章的潜在关联
- 生成结构化标签和主题向量（为 M7 聚类做准备）

### 四维评估

| 维度 | 评估 |
|------|------|
| 兼容性 | 完全兼容。作为管道可选阶段插入 L2 之后 |
| 修改量 | 新增 `l3_analyzer.py`（~200行）+ `test_l3_analyzer.py`（~10个）+ main.py 可选集成（~20行）+ config 加 L3 开关 |
| 维护成本 | 中。L3 调用 GLM-5.1，token 消耗高，需控制调用频率（仅高分文章） |
| 目标破坏 | 无。增强而非替代现有管线 |

### 设计

```
L3 Deep Analyzer:
  输入: Article（已完成 L2 摘要，relevance_score ≥ 7）
  输出: Article（content_deep 有值，新增 l3_concepts, l3_structure）
  
  AI Prompt:
    - 分析文章的核心论点、论证逻辑、关键洞见
    - 提取 5-10 个独立概念点
    - 分析文章结构（观点-论据-结论 / 问题-方案-实践 等）
    - 识别文章立场和前提假设
    - 输出 JSON: concepts[], structure_type, key_insight, position, assumptions
```

### 任务分解

#### M6.1: 创建 l3_analyzer.py

**文件:** `pipeline/processors/l3_analyzer.py`

核心逻辑:
1. 使用 GLM-5.1 模型（`config.l3_model`），更大 token 配额
2. 设计 L3 专用的 system prompt 和 JSON schema
3. 仅对 `content_tier == "detailed"` 的文章执行
4. 提取的 concepts 存入 `article.l3_concepts`（新增字段）
5. 结构分析存入 `article.content_deep`

L3 Prompt 设计要点:
- 要求识别**概念性知识单元**（不是简单标签）
- 每个概念附带一句话定义
- 输出结构化 JSON，便于后续聚类

#### M6.2: 扩展 Article 模型

**修改:** `pipeline/models.py`

```python
# 新增字段
l3_concepts: List[dict] = field(default_factory=list)  
# 格式: [{"name": "concept_name", "definition": "one sentence"}, ...]
l3_structure_type: str = ""  # "argument", "tutorial", "news", "analysis", ...
l3_key_insight: str = ""     # 核心洞见（一句话）
```

#### M6.3: 集成到 Pipeline

**修改:** `pipeline/main.py`

- `run()` 方法: L2 完成后，对 `content_tier == "detailed"` 的文章调用 L3
- 新增 `--skip-l3` 参数（省钱时使用）
- L3 失败不影响流程（降级优雅处理）

#### M6.4: 配置扩展

**修改:** `pipeline/config.py`

- 新增 `l3_enabled: bool = True`
- 新增 `l3_min_score: int = 7`（仅对 ≥7 分的文章执行）
- 已有 `l3_model` 和 `max_tokens_l3` 配置项

---

## 七、M7: 主题聚类 — 向量嵌入 + 相似度分组

### 目标

基于文章的概念特征，自动发现知识主题：
- 为每篇文章生成向量嵌入
- 使用聚类算法将文章分组为主题
- 为主题命名并识别核心文章

### 四维评估

| 维度 | 评估 |
|------|------|
| 兼容性 | 并行于现有管线，不影响抓取→筛选→摘要流程 |
| 修改量 | 新增依赖（sentence-transformers 或调用嵌入 API）+ 新模块 `clusterer.py`（~250行）+ tests（~10个）|
| 维护成本 | 中。向量模型更新和聚类参数调优需要持续关注 |
| 目标破坏 | 无。仅增加新能力 |

### 设计

```
Topic Clusterer:
  输入: 已处理文章的 l3_concepts（从已生成笔记中读取）
  处理:
    1. 文本嵌入: 对每篇文章的概念列表 + 摘要生成向量
    2. 降维: UMAP 降维到 2D（用于可视化）+ 更低维（用于聚类）
    3. 聚类: HDBSCAN 自动确定主题数量
    4. 主题命名: 提取每个聚类的代表性概念
  输出: 主题列表 [{name, articles, core_article, score}]
```

### 技术选型

| 组件 | 方案 | 理由 |
|------|------|------|
| 嵌入模型 | `sentence-transformers` + `all-MiniLM-L6-v2` | 轻量（80MB）、本地运行、无需 API |
| 降维 | `umap-learn` | 比 t-SNE 快、保留全局结构 |
| 聚类 | HDBSCAN | 自动确定聚类数、处理噪声点 |
| 主题命名 | GLM-5.1（L3 模型）| 用概念列表+代表性文章生成主题名 |

### 任务分解

#### M7.1: 安装依赖 + 创建嵌入模块

- 新增 `sentence-transformers`、`umap-learn`、`hdbscan` 到 requirements.txt
- 创建 `pipeline/processors/embedder.py`:
  - `load_model()` — 延迟加载嵌入模型
  - `embed_article(article)` — 生成单个文章向量
  - `embed_batch(articles)` — 批量生成向量

#### M7.2: 创建 clusterer.py

**文件:** `pipeline/processors/clusterer.py`

核心逻辑:
1. 从 vault 读取所有已处理文章的前元数据（tags, l3_concepts）
2. 生成嵌入向量
3. UMAP 降维（保留 5 维用于聚类 + 2 维用于可视化）
4. HDBSCAN 聚类
5. 为每个聚类：
   - 提取代表性概念（TF-IDF 或频率统计）
   - 用 L3 模型生成主题名称
   - 标识核心文章（离聚类中心最近的文章）

#### M7.3: 集成到 Pipeline + 创建 CLI

- 新增 `python -m pipeline.main --source cluster` 命令
- 聚类结果写入 `5-Topics/` 目录
- 更新每篇文章的 frontmatter，添加 `cluster_id` 和 `topic` 字段

---

## 八、M8: MOC 自动生成 — 知识地图

### 目标

基于 M7 的聚类结果，自动生成 Map of Content (MOC) 笔记：
- 每个主题生成一个 MOC 页面
- MOC 包含主题简述、核心文章列表、相关概念
- 文章间通过 wikilink 互连

### 四维评估

| 维度 | 评估 |
|------|------|
| 兼容性 | 完全兼容。仅写入新笔记到 `5-Topics/` |
| 修改量 | 新增 `moc_generator.py`（~200行）+ tests（~8个）|
| 维护成本 | 低。MOC 生成是聚类结果的确定性转换 |
| 目标破坏 | 无。增强知识库导航能力 |

### 设计

```
MOC Generator:
  输入: 聚类结果（M7 输出）
  处理:
    1. 为每个主题创建一个 MOC 页面
    2. 用 AI 生成主题简述（2-3句话）
    3. 列出核心文章（带 wikilink 和一句话摘要）
    4. 列出相关概念（带定义）
    5. 生成主题间交叉引用（相关内容链接）
  输出: vault/.../5-Topics/{topic-name}.md
```

### MOC 模板

```markdown
---
topic: 大语言模型训练
created: 2026-05-10
article_count: 12
core_article: [[[S9] Llama-4训练细节揭秘]]
clusters: [a3f2b1]
---

# 大语言模型训练

## 概述

关于这个主题，目前收集了 12 篇文章。核心聚焦于...

## 核心文章

- [[[S9] Llama-4训练细节揭秘]] — Meta 公开的分布式训练架构
- [[[S8] Qwen3技术报告深度解读]] — 阿里的 MoE 架构创新
- ...

## 相关概念

- **MoE 混合专家**: 通过稀疏激活降低推理成本
- **RLHF 强化学习人类反馈**: ...

## 相关内容

- [[MOC: AI 推理优化]]
- [[MOC: 开源大模型生态]]
```

### 任务分解

#### M8.1: 创建 moc_generator.py

- 从 clusterer 获取聚类结果
- 为每个主题生成 MOC 笔记
- 处理文章 wikilink 路径和相对引用
- 生成主题间交叉引用

#### M8.2: 更新文章笔记

- 每篇文章 frontmatter 中添加 `moc: [[MOC: topic-name]]`
- 在文章 `## Related` 部分添加 MOC 链接

#### M8.3: 集成到 Pipeline

- MOC 生成作为聚类后的可选步骤
- `--source cluster` 命令自动包含 MOC 生成

---

## 九、M9: 感知增强 — Playwright JS 渲染 + 去重升级

### 目标

解决中评报告中已确认的两个痛点：
1. JS 渲染页面提取失败（SPA、少数派等）
2. 标题提取质量不可靠（依赖 trafilatura 的元数据提取）

### 四维评估

| 维度 | 评估 |
|------|------|
| 兼容性 | 完全兼容。作为可选增强模式 |
| 修改量 | 新增 playwright 集成（~100行）+ 调整 web_extractor（~40行）+ tests（~5个）|
| 维护成本 | 中。Playwright 需要浏览器二进制文件，增加部署复杂度 |
| 目标破坏 | 无。解决已知问题 |

### 设计

```
Playwright Renderer:
  输入: URL
  处理:
    1. Chromium headless 打开页面
    2. 等待网络空闲 + DOM 稳定
    3. 提取渲染后的 HTML
    4. 传给 trafilatura 做正文提取
  输出: 正文文本（与现有 web_extractor 输出一致）
  
  触发条件:
    - trafilatura 直接提取返回空或过短
    - 用户显式指定 --render-js 参数
```

### 任务分解

#### M9.1: 安装 Playwright

```bash
pip install playwright
playwright install chromium
```

#### M9.2: 创建 renderer.py

**文件:** `pipeline/extractors/web_renderer.py`

核心逻辑:
1. `render_page(url)` — 用 Playwright 打开 URL 获取完整 HTML
2. `extract_with_fallback(url)` — 先用 trafilatura，失败时 fallback 到 Playwright
3. 缓存渲染结果（同一 URL 24h 内不重复渲染）

#### M9.3: 集成到 web_extractor

- `extract_url()` 增加 `use_playwright=False` 参数
- trafilatura 返回空时自动启用 Playwright
- 新增 `--render-js` CLI 参数

#### M9.4: 标题提取改进

- trafilatura 提取的标题为空时，从 `<title>` / `<h1>` / `og:title` 中回退
- Playwright 模式下额外提取 og/meta 标签

---

## 十、Phase 3 执行顺序与依赖

```
M5 (GitHub重构) ←── 无前置依赖，可立即开始
  │                  用户已明确需求变更，优先处理
  │
  ├── M6 (L3深度分析) ←── 需要 models.py 扩展 (M5 可能也扩展)
  │      │
  │      ├── M7 (主题聚类) ←── 依赖 L3 concepts 输出
  │      │      │
  │      │      └── M8 (MOC生成) ←── 依赖聚类结果
  │      │
  │      └── M9 (感知增强) ←── 独立于 L3/聚类/MOC
  │
推荐执行顺序: M5 → M6 → M7 → M8 → M9
               M9 可以在任意时间点并行
```

### 依赖关系图

```
M5 (GitHub重构)
 │
 ├─→ M6 (L3分析) ──→ M7 (聚类) ──→ M8 (MOC)
 │
 └─→ M9 (感知增强, 独立)
```

---

## 十一、Phase 3 完成标准

| 里程碑 | 完成条件 |
|--------|---------|
| M5 | `--source github` 抓取 README 并生成项目能力摘要，测试通过 |
| M6 | L3 深度分析可选执行，输出 concepts 和 structure 到 frontmatter，测试通过 |
| M7 | `--source cluster` 命令可用，生成聚类结果写入 `5-Topics/`，测试通过 |
| M8 | 每个主题有 MOC 页面，文章互连，测试通过 |
| M9 | Playwright 渲染解决 SPA 提取问题，标题回退生效，测试通过 |
| 全局 | 测试数量 ≥ 150，无回归 |

---

## 十二、Phase 3 不做的功能（明确搁置）

以下功能**不列入**任何 Phase 计划：

### ✗ 全文搜索引擎

这是工具层的功能，不是知识层的功能。如果需要搜索，用 Obsidian 内置搜索或系统 `grep`，不需要自建索引。

### ✗ RAG 问答

需要向量数据库（ChromaDB/FAISS）+ 嵌入模型持久化 + 对话接口。这是另一个独立系统的范围，不应该耦合到采集管线中。

### ✗ 自动翻译

中文用户读中文摘要已足够。英文原文可以保留在 `content_raw` 中供参考。

### ✗ Web 前端 / Dashboard

Obsidian 就是 UI。不需要额外的 Web 界面来展示统计。

### ✗ 社交媒体集成

微信公众号、Twitter、Reddit 爬取涉及反爬和 API 限制，维护成本远大于价值。

### ✗ 代码分析

GitHub 提取器**不分析项目源码**。用户明确表示关心的是「项目能做什么」，不是「代码怎么写」。

---

## 十三、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| GLM-5.1 API 不稳定 | 中 | L3 分析失败，Article 丢失深度内容 | 优雅降级：L3 失败不影响管道 |
| 向量嵌入模型下载失败 | 低 | 聚类功能不可用 | 延迟加载，首次使用时检查 |
| Playwright 浏览器二进制体积大 | 低 | WSL 磁盘压力 | 可选安装，不阻塞其他功能 |
| 聚类结果不理想 | 中 | MOC 质量差 | HDBSCAN 自动确定聚类数，备选参数预设 |
| README 过长超出 token 限制 | 中 | 项目分析不完整 | 截断 + 智能分段处理 |

---

*计划生成: Hermes Agent @ DeepSeek-V4*  
*日期: 2026-05-10*
