# AI 个人知识库 V3 — Phase 2 扩展实施计划

> 计划日期: 2026-05-10（v2 修订版 — 链接深挖功能已回退）
> 前置文档: phase1-midterm-assessment.md, Personal-AI-KnowledgeBase-Design-v3-comparison
> 项目路径: `/mnt/e/WSL/knowledge-base/`

---

## 一、Phase 2 范围定义

### 1.1 依据来源

本计划综合两份文档确定 Phase 2 范围：

| 来源 | Phase 2 定义 |
|------|-------------|
| **中期评估报告** | P0=Cron调度, P1=GitHub提取器, P1=Email提取器 |
| **V3 Design Comparison** | GitHub Release追踪, Email Newsletter |

### 1.2 已移除的内容

**链接深挖功能（link_resolver + Blocks API 链接提取）已完整回退**（commit 8b61c84, 2026-05-10）。

回退理由（经四维评估框架分析）：

| 维度   | 评估结果                                                                                                   |
| ---- | ------------------------------------------------------------------------------------------------------ |
| 兼容性  | 需要独立的并行处理管线（Blocks API → link injection → linked_urls → resolve），与核心管道 Extract→L1→L2→Write 耦合度低但维护成本独立 |
| 修改量  | 跨 10 个文件，1073+ 行代码，占项目总量约 38%                                                                          |
| 维护成本 | Blocks API 分页逻辑、URL编码处理、frontmatter linked_urls 双向同步、dedup/vault 文件反同步问题——每个新 extractor 都需适配链接提取       |
| 目标破坏 | 核心目标是「自动抓取→筛选→摘要→写入」，链接深挖偏离了这一目标；用户手动 `--source url <link>` 可覆盖需求                                      |

超链接保留（`include_links=True`）不受影响，用户可手动处理感兴趣的链接。

### 1.3 Phase 2 里程碑（修订后）

```
M2: Hermes Cron 自动化调度       (定时运行, 0.5天)
M3: GitHub Release 提取器        (新数据源, 1天)
M4: Email/Newsletter 提取器      (新数据源, 1.5天)
```

**总计预估: 3 天**（含测试编写）

---

## 二、当前状态基线

### 2.1 代码库快照

```
pipeline/
├── main.py                  ← CLI entry, 支持 --source rss|url|feishu
├── config.py                ← PipelineConfig, ModelConfig, FeishuConfig
├── models.py                ← Article dataclass + 枚举 (6种来源)
├── extractors/
│   ├── rss_fetcher.py       ← feedparser + trafilatura
│   ├── web_extractor.py     ← trafilatura (include_links=True)
│   └── feishu_extractor.py  ← Feishu Open API (raw_content + doc_info)
├── processors/
│   ├── l1_filter.py         ← GLM-4.7 评分 1-10
│   └── l2_summarizer.py     ← GLM-4.7 结构化摘要
├── formatters/
│   └── obsidian_writer.py   ← Markdown + frontmatter + wikilink
├── utils/
│   └── dedup.py             ← SQLite URL hash 去重
├── configs/
│   ├── default.yaml         ← 8 个 RSS 源
│   └── tech-feeds.yaml      ← 3 个纯技术源
└── tests/                   ← 80 tests (9 测试文件), 全部通过
```

### 2.2 产出物快照

```
vault/.../2-Articles/
├── 2026-05-08/  (12 articles: S4×1, S5×5, S6×3, S8×3)
└── 2026-05-10/  (1 article:  S8×1)
```

### 2.3 已有但未使用的枚举值

`models.py` 中的 `ArticleSource` 枚举已包含 `GITHUB` 和 `EMAIL`，`obsidian_writer._get_target_dir()` 已有路由映射（`GITHUB → 3-GitHub/`, `EMAIL → 4-Newsletters/`）。新增提取器无需修改模型或格式化器。

---

## 三、M2: Hermes Cron 自动化调度

### 目标

利用 Hermes Agent 的 cronjob 功能，实现管道的定时自动运行。每天自动抓取 RSS → 处理 → 写入 Obsidian。

### 前置条件

- Hermes Agent cronjob 功能可用
- 管道已稳定运行（80 tests passing）
- RSS 配置文件 `pipeline/configs/default.yaml` 已包含活跃源

### 设计决策

**方案选择**: Hermes Cron → `terminal()` 调用 `python -m pipeline.main`

理由：
1. 管道本身是独立的 CLI 工具，不需要 Hermes 的 delegate_task 子代理
2. terminal() 直接调用最简单、最可靠
3. cronjob 的 `notify_on_complete` 可在完成时通知用户
4. 管道自带日志系统（`pipeline/logs/`），便于事后排查

### 任务分解

#### Task M2.1: 创建 Cron Job

**目标:** 注册 Hermes cron job，每天定时运行管道

**实现:**

```
hermes cron create \
  --name "knowledge-base-rss" \
  --schedule "0 8 * * *" \
  --prompt "运行知识库 RSS 管道。执行: cd /mnt/e/WSL/knowledge-base && source pipeline/.venv/bin/activate && python -m pipeline.main --source rss --config pipeline/configs/default.yaml。报告执行结果摘要。" \
  --toolsets terminal
```

调度规则:
- 每天早上 8:00 运行
- 使用 default.yaml 配置（8 个 RSS 源）
- 完成后通知用户

**验证:**
1. cronjob 注册成功
2. 手动触发一次（`hermes cron run <job_id>`）
3. 检查 vault 是否有新文章生成
4. 检查 `pipeline/logs/` 日志正常

#### Task M2.2: 添加技术源 Cron Job（可选）

如果需要更频繁的技术源更新：

```
hermes cron create \
  --name "knowledge-base-tech" \
  --schedule "0 14 * * *" \
  --prompt "运行知识库技术源管道。执行: cd /mnt/e/WSL/knowledge-base && source pipeline/.venv/bin/activate && python -m pipeline.main --source rss --config pipeline/configs/tech-feeds.yaml。报告执行结果摘要。" \
  --toolsets terminal
```

---

## 四、M3: GitHub Release 提取器

### 目标

监控 GitHub Starred 仓库的 Release 动态，自动抓取 Release Notes 并进入管道处理。

### 四维评估

| 维度 | 评估 |
|------|------|
| 兼容性 | 完全兼容。新 extractor 遵循统一接口（返回 `List[Article]`），下游 L1/L2/Writer 无需修改 |
| 修改量 | 新增 1 个 extractor 文件（~150 行）+ 1 个测试文件（~120 行）+ main.py 加 `--source github`（~10 行） |
| 维护成本 | 低。GitHub API 稳定，`gh release list` CLI 可用。无额外状态管理 |
| 目标破坏 | 无。直接服务于「追踪技术动态」的核心目标 |

### 设计

```
GitHub Release Extractor:
  输入: GitHub username (从 gh CLI 获取 starred repos)
  处理: gh release list --repo <repo> --limit 3
  输出: List[Article]，每条 Release = 1 Article
    url = release.html_url
    title = "<repo> <tag>: <release_name>"
    content_raw = release body (Markdown)
    source = ArticleSource.GITHUB
    source_name = repo name
```

### 任务分解

#### Task M3.1: 创建 github_extractor.py 骨架

**文件:** `pipeline/extractors/github_extractor.py`

```python
"""GitHub Release Extractor — fetch releases from starred repos."""

import logging
import subprocess
import json
from typing import List, Optional

from pipeline.models import Article, ArticleSource

logger = logging.getLogger(__name__)


def get_starred_repos(limit: int = 20) -> List[str]:
    """Get list of starred repo full names (owner/repo)."""
    ...


def fetch_releases(repo: str, limit: int = 3) -> List[dict]:
    """Fetch recent releases for a repo using gh CLI."""
    ...


def extract_github_releases(
    repos: Optional[List[str]] = None,
    max_repos: int = 20,
    releases_per_repo: int = 3,
) -> List[Article]:
    """Main entry: fetch releases from starred repos → Articles."""
    ...
```

**验证:** `python -c "from pipeline.extractors.github_extractor import extract_github_releases; print('OK')"`

#### Task M3.2: 实现 get_starred_releases + fetch_releases

**依赖:** `gh` CLI 已安装并认证

核心逻辑:
1. `gh api user/starred --paginate -q '.[].full_name'` 获取 starred repos
2. `gh release list --repo <repo> --limit N --json tagName,name,url,body,publishedAt` 获取 releases
3. 转换为 Article 对象

**错误处理:**
- `gh` CLI 不存在 → 明确报错
- repo 无 releases → 跳过，不报错
- rate limit → 记录日志，返回已获取的数据

#### Task M3.3: 编写测试

**文件:** `pipeline/tests/test_github_extractor.py`

测试策略:
- Mock `subprocess.run` 模拟 `gh` CLI 输出
- 测试 Article 转换逻辑
- 测试空 releases、rate limit、CLI 不存在等边界情况

预计 ~8-10 个测试用例。

#### Task M3.4: 集成到 main.py

**修改:** `pipeline/main.py`

```python
# argparse choices 添加 "github"
parser.add_argument(
    "--source", choices=["rss", "url", "feishu", "github"], default="rss",
)

# Pipeline._extract 添加分支
elif source == "github":
    from pipeline.extractors.github_extractor import extract_github_releases
    return extract_github_releases()
```

**验证:**
1. `python -m pipeline.main --source github --dry-run` 无报错
2. 全量测试通过

---

## 五、M4: Email/Newsletter 提取器

### 目标

通过 IMAP 连接邮箱，过滤 Newsletter 邮件，提取正文进入管道处理。

### 四维评估

| 维度 | 评估 |
|------|------|
| 兼容性 | 完全兼容。新 extractor 返回 `List[Article]`，下游管道无需修改 |
| 修改量 | 新增 1 个 extractor（~200 行）+ 1 个测试文件（~150 行）+ main.py 加 `--source email`（~10 行）+ config 添加 EmailConfig（~15 行） |
| 维护成本 | 中。IMAP 连接需邮箱凭据（app password），HTML→Markdown 转换需处理多样格式 |
| 目标破坏 | 无。直接服务于「追踪技术动态」的核心目标 |

### 设计

```
Email Newsletter Extractor:
  输入: IMAP 配置 (server, port, username, app_password, sender_whitelist)
  处理: 
    1. IMAP 连接 → 搜索未读邮件
    2. 白名单过滤: 仅处理特定发件人
    3. HTML → Markdown (html2text 或 markdownify)
    4. 去重: Message-ID 哈希
  输出: List[Article]，每封 Newsletter = 1 Article
    url = message_id (或 archive URL 如有)
    title = Subject header
    content_raw = Markdown body
    source = ArticleSource.EMAIL
    source_name = sender name
```

### 任务分解

#### Task M4.1: 添加 EmailConfig 到 config.py

**修改:** `pipeline/config.py`

```python
@dataclass
class EmailConfig:
    imap_server: str = ""
    imap_port: int = 993
    username: str = ""
    app_password: str = ""  # 环境变量 EMAIL_APP_PASSWORD
    sender_whitelist: List[str] = field(default_factory=list)  # 允许的发件人
    max_emails: int = 10
    mark_as_read: bool = True
```

#### Task M4.2: 创建 email_extractor.py

**文件:** `pipeline/extractors/email_extractor.py`

核心逻辑:
1. `imaplib.IMAP4_SSL` 连接
2. `SEARCH UNSEEN FROM <sender>` 搜索
3. `email` 标准库解析 MIME
4. `html2text` 或 `markdownify` 转换 HTML → Markdown
5. 返回 `List[Article]`

**错误处理:**
- IMAP 连接失败 → 明确报错
- 无新邮件 → 返回空列表
- HTML 解析失败 → 保留纯文本 fallback

#### Task M4.3: 编写测试

**文件:** `pipeline/tests/test_email_extractor.py`

测试策略:
- Mock `imaplib.IMAP4_SSL`
- Mock `html2text` 转换
- 测试白名单过滤
- 测试 MIME 多部分解析
- 测试空收件箱

预计 ~10 个测试用例。

#### Task M4.4: 集成到 main.py + 添加依赖

**修改:**
- `pipeline/main.py`: 添加 `--source email`
- `pipeline/requirements.txt`: 添加 `markdownify` 或 `html2text`

**验证:**
1. 全量测试通过
2. `python -m pipeline.main --source email --dry-run`（需邮箱配置）

---

## 六、Phase 2 执行顺序与依赖

```
M2 (Cron) ←── 无前置依赖，可立即开始
  │
  ├── M3 (GitHub) ←── 独立于 M2，但建议 M2 完成后一起加入 Cron
  │
  └── M4 (Email) ←── 独立于 M2/M3，最后实现

推荐执行顺序: M2 → M3 → M4
  理由: M2 最快完成（0.5天），验证 Cron 可用后，M3/M4 完成即加入自动调度
```

---

## 七、Phase 2 完成标准

| 里程碑 | 完成条件 |
|--------|---------|
| M2 | Cron job 注册成功，手动触发运行正常，日志输出正确 |
| M3 | `--source github` 可用，抓取 starred repos releases，写入 `3-GitHub/` 目录，测试通过 |
| M4 | `--source email` 可用，IMAP 连接正常，Newsletter 写入 `4-Newsletters/` 目录，测试通过 |
| 全局 | 测试数量 ≥ 100（当前 80 + 新增 ~20-25），无回归 |

---

## 八、Phase 3 展望（不在本计划范围）

Phase 3 预计包含（来自 V3 Design Comparison）：

| 功能 | 说明 |
|------|------|
| L3 深度分析 | GLM-5.1 对高价值文章做深度解析 |
| 主题聚类 | 向量嵌入 + 聚类，自动发现知识主题 |
| MOC 自动生成 | 基于聚类结果生成 Map of Content |
| Playwright JS 渲染 | 解决 SPA 页面提取失败问题 |

---

*计划生成: Hermes Agent @ GLM-5.1*
*修订日期: 2026-05-10*
