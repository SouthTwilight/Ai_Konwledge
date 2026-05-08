# 飞书文档提取器 — 设计文档与执行计划

**创建日期：** 2026-05-09
**状态：** 待实施

---

## 一、项目概述

为知识库管线新增飞书文档提取器，通过飞书开放平台 API 直接获取文档 Markdown 原文，纳入现有 L1→L2→Obsidian 处理链路。

**核心价值：** 用户粘贴飞书文档链接 → 自动提取全文 → AI 分析摘要 → 存入 Obsidian。解决当前 trafilatura 无法处理飞书 SPA 页面的问题。

**适用范围（Phase 1）：** 用户所在组织的飞书文档（租户 Token 鉴权）。跨组织分享文档后续扩展。

---

## 二、技术方案

### 2.1 飞书开放平台 API

```
GET https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/raw_content
```

- 返回文档的 Block 数组（JSON），包含文本、标题、列表、代码块等
- 鉴权：`Authorization: Bearer {tenant_access_token}`
- 无需申请额外权限（企业自建应用默认开通 `docx:document:readonly` 即可）
- 文档必须属于该应用的租户范围（同一组织）

### 2.2 链路设计

```
飞书 URL → 解析 doc_id → FeishuClient.get_raw_content() → Markdown 文本
    → Article(FEISHU) → Dedup → L1 Filter → L2 Summarize → Obsidian
```

### 2.3 数据模型变更

**ArticleSource 枚举新增：**
```python
FEISHU = "feishu"
```

**config.py 新增 FeishuConfig：**
```python
@dataclass
class FeishuConfig:
    app_id: str = ""
    app_secret: str = ""
    # 可选：缓存 token，避免每次请求都重新获取
```

**环境变量（.env）：**
```
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx
```

---

## 三、架构设计

```
pipeline/
├── config.py              ← 新增 FeishuConfig，PipelineConfig.feishu: FeishuConfig
├── models.py              ← 新增 ArticleSource.FEISHU
├── extractors/
│   └── feishu_extractor.py  ← 新增：FeishuClient + extract_feishu_doc()
├── formatters/
│   └── obsidian_writer.py   ← SOURCE_DIRS 新增 FEISHU → "2-Articles"
├── main.py                  ← 新增 --source feishu --feishu-url
└── tests/
    └── test_feishu_extractor.py  ← 新增测试
```

### 3.1 feishu_extractor.py 类设计

```python
class FeishuClient:
    """飞书开放平台 API 客户端"""

    def __init__(self, config: FeishuConfig):
        self.config = config
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    def _get_token(self) -> str:
        """获取 tenant_access_token，自动缓存"""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        # POST /open-apis/auth/v3/tenant_access_token/internal
        # body: {"app_id": "...", "app_secret": "..."}
        # 缓存 token + expire (默认 2 小时)

    def get_raw_content(self, document_id: str) -> str:
        """获取文档原始内容，返回 Markdown 字符串"""
        # GET /open-apis/docx/v1/documents/{document_id}/raw_content
        # 解析 blocks → 拼接为 Markdown

    def _blocks_to_markdown(self, blocks: list) -> str:
        """将飞书 Block 数组转为 Markdown 文本"""


def extract_feishu_doc(url: str, config: FeishuConfig) -> Optional[Article]:
    """从飞书文档 URL 提取内容，返回 Article 对象"""
    # 1. 从 URL 解析 document_id
    # 2. 调用 FeishuClient.get_raw_content()
    # 3. 构造 Article(FEISHU) 返回
```

### 3.2 URL 解析逻辑

飞书文档链接格式：
- `https://{domain}.feishu.cn/wiki/{doc_id}`
- `https://{domain}.feishu.cn/docx/{doc_id}`
- `https://{domain}.feishu.cn/docs/{doc_id}`

从 URL 路径中提取 `doc_id`（斜杠后、`?` 前的一段）。

---

## 四、执行计划

> 每个任务按 TDD 模式：先写测试 → 确认失败 → 写实现 → 确认通过 → 提交。

---

### Task 1: 新增 ArticleSource.FEISHU 枚举

**涉及文件：**
- 修改: `pipeline/models.py`

**Step 1: 添加枚举值**

在 `ArticleSource` 类中 `MANUAL = "manual"` 后新增：
```python
FEISHU = "feishu"
```

**Step 2: 验证**

```bash
pytest pipeline/tests/test_models.py -v
```

**Step 3: 提交**

```bash
git add pipeline/models.py
git commit -m "feat: add ArticleSource.FEISHU enum for Feishu document extraction"
```

---

### Task 2: 新增 FeishuConfig 配置类

**涉及文件：**
- 修改: `pipeline/config.py`

**Step 1: 添加 FeishuConfig 数据类**

在 `ModelConfig` 类后面新增：
```python
@dataclass
class FeishuConfig:
    app_id: str = ""
    app_secret: str = ""
```

**Step 2: 在 PipelineConfig 中添加字段**

```python
feishu: FeishuConfig = field(default_factory=FeishuConfig)
```

**Step 3: 在 `__post_init__` 中加载环境变量**

```python
if not self.feishu.app_id:
    self.feishu.app_id = os.getenv('FEISHU_APP_ID', '')
if not self.feishu.app_secret:
    self.feishu.app_secret = os.getenv('FEISHU_APP_SECRET', '')
```

**Step 4: 验证**

```bash
pytest pipeline/tests/test_config.py -v
```

**Step 5: 提交**

```bash
git add pipeline/config.py
git commit -m "feat: add FeishuConfig to PipelineConfig with env var loading"
```

---

### Task 3: 编写飞书提取器测试

**涉及文件：**
- 新建: `pipeline/tests/test_feishu_extractor.py`

**Step 1: 写 URL 解析测试**

```python
import pytest
from pipeline.extractors.feishu_extractor import parse_feishu_doc_id

def test_parse_wiki_url():
    url = "https://oigi8odzc5w.feishu.cn/wiki/WBMfwiNkfi6uNFkRtXdcavDzn0e"
    assert parse_feishu_doc_id(url) == "WBMfwiNkfi6uNFkRtXdcavDzn0e"

def test_parse_docx_url():
    url = "https://test.feishu.cn/docx/ABCD1234"
    assert parse_feishu_doc_id(url) == "ABCD1234"

def test_parse_with_query_params():
    url = "https://test.feishu.cn/wiki/DOCID?from=from_copylink"
    assert parse_feishu_doc_id(url) == "DOCID"

def test_parse_invalid_url():
    assert parse_feishu_doc_id("https://google.com") is None
```

**Step 2: 写 FeishuClient 测试（mock HTTP）**

```python
from pipeline.extractors.feishu_extractor import FeishuClient, FeishuConfig

def test_get_token(mocker):
    mock_post = mocker.patch('httpx.Client.post')
    mock_post.return_value.json.return_value = {
        "code": 0,
        "tenant_access_token": "t-xxx",
        "expire": 7200,
    }
    client = FeishuClient(FeishuConfig(app_id="test", app_secret="secret"))
    token = client._get_token()
    assert token == "t-xxx"

def test_get_raw_content(mocker):
    # Mock token
    mocker.patch.object(FeishuClient, '_get_token', return_value='t-xxx')
    mock_get = mocker.patch('httpx.Client.get')
    mock_get.return_value.json.return_value = {
        "code": 0,
        "data": {
            "content": "## Hello World\\n\\nThis is a test document.",
        },
    }
    client = FeishuClient(FeishuConfig(app_id="test", app_secret="secret"))
    content = client.get_raw_content("DOCID")
    assert "Hello World" in content

def test_extract_feishu_doc(mocker):
    mocker.patch.object(FeishuClient, 'get_raw_content', return_value="# Test Doc\nContent here.")
    config = FeishuConfig(app_id="test", app_secret="secret")
    article = extract_feishu_doc("https://test.feishu.cn/wiki/DOCID", config)
    assert article is not None
    assert article.source == ArticleSource.FEISHU
    assert article.title == "Test Doc"
    assert article.content_raw == "# Test Doc\nContent here."
```

**Step 3: 运行确认失败**

```bash
pytest pipeline/tests/test_feishu_extractor.py -v
```
期望：全部 FAIL（模块不存在）

---

### Task 4: 实现飞书提取器

**涉及文件：**
- 新建: `pipeline/extractors/feishu_extractor.py`

**Step 1: 创建文件，实现 parse_feishu_doc_id()**

```python
from __future__ import annotations

import re
from urllib.parse import urlparse


def parse_feishu_doc_id(url: str) -> Optional[str]:
    """从飞书文档 URL 中提取 document_id。"""
    try:
        parsed = urlparse(url)
        if 'feishu.cn' not in parsed.netloc:
            return None
        # 路径格式: /wiki/{doc_id} 或 /docx/{doc_id}
        match = re.match(r'/(?:wiki|docx|docs)/([^/?]+)', parsed.path)
        return match.group(1) if match else None
    except Exception:
        return None
```

**Step 2: 实现 FeishuClient 类**

完整实现 token 获取、缓存、raw_content 获取、blocks→markdown 转换。

**Step 3: 运行测试**

```bash
pytest pipeline/tests/test_feishu_extractor.py -v
```
期望：全部 PASS

**Step 4: 提交**

```bash
git add pipeline/extractors/feishu_extractor.py pipeline/tests/test_feishu_extractor.py
git commit -m "feat: add Feishu document extractor with token management and API client"
```

---

### Task 5: 更新 SOURCE_DIRS 和 main.py 调度

**涉及文件：**
- 修改: `pipeline/formatters/obsidian_writer.py`
- 修改: `pipeline/main.py`
- 修改: `pipeline/tests/test_main.py`
- 修改: `pipeline/tests/test_obsidian_writer.py`

**Step 1: SOURCE_DIRS 添加飞书映射**

```python
SOURCE_DIRS = {
    ...
    ArticleSource.FEISHU: "2-Articles",
}
```

**Step 2: main.py 添加 --source feishu --feishu-url**

在 argparse 中新增参数，在 `main()` 中调度：
```python
parser.add_argument(
    "--feishu-url", type=str, default=None,
    help="Feishu document URL (with --source feishu)"
)

# 调度逻辑
elif args.source == "feishu":
    if not args.feishu_url:
        logger.error("--feishu-url required when --source feishu")
        return []
    from pipeline.extractors.feishu_extractor import extract_feishu_doc
    article = extract_feishu_doc(args.feishu_url, config.feishu)
    articles = [article] if article else []
```

同时更新 `_extract()` 方法中 source 为 "feishu" 时的处理。

**Step 3: 更新已有测试**

- `test_main.py`: 添加 `feishu` 到 source choices、更新 mock_config 包含 FeishuConfig
- `test_obsidian_writer.py`: 添加 FEISHU 源文章写目录的断言

**Step 4: 运行全量测试**

```bash
pytest pipeline/tests/ -v
```
期望：全部 PASS

**Step 5: 提交**

```bash
git add pipeline/formatters/obsidian_writer.py pipeline/main.py pipeline/tests/
git commit -m "feat: wire Feishu extractor into main pipeline with --source feishu"
```

---

### Task 6: 更新文档和 README

**涉及文件：**
- 修改: `README.md`

**Step 1: 更新 README**

- 来源类型表新增 `FEISHU` → `2-Articles/`
- 快速开始新增飞书配置说明
- 命令行参数表新增 `--feishu-url`
- 环境变量表新增 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`

**Step 2: 提交**

```bash
git add README.md
git commit -m "docs: add Feishu extractor documentation to README"
```

---

### Task 7: 端到端验证

**前置条件：** 在 `.env` 中配置 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`

```bash
source pipeline/.venv/bin/activate
python -m pipeline.main --source feishu \
  --feishu-url "https://oigi8odzc5w.feishu.cn/wiki/WBMfwiNkfi6uNFkRtXdcavDzn0e"
```

**验证项：**
1. Token 获取成功（日志中无认证错误）
2. 文档内容提取成功（content_raw 非空）
3. L1 评分输出
4. L2 摘要生成
5. 文件写入 `2-Articles/YYYY-MM-DD/` 目录
6. 文件名含评分前缀 `[SX]`

---

## 五、总结

| 指标 | 值 |
|------|-----|
| 新增文件 | `extractors/feishu_extractor.py`, `tests/test_feishu_extractor.py` |
| 修改文件 | `models.py`, `config.py`, `main.py`, `obsidian_writer.py`, `README.md` |
| 新增测试 | ~8 个 |
| 新增环境变量 | `FEISHU_APP_ID`, `FEISHU_APP_SECRET` |
| 新增 CLI 参数 | `--source feishu --feishu-url` |
| 预估总工作量 | 7 个任务，约 1 小时 |

**未来扩展（Phase 2）：**
- 用户 Token 鉴权（跨组织分享文档）
- 飞书知识库（Wiki Space）批量导入
- Bitable 数据表提取

---

## 六、前置准备（用户操作）

在用管线提取飞书文档之前，需要先完成：

1. 访问 [飞书开发者后台](https://open.feishu.cn/app) → 创建企业自建应用
2. 获取 `App ID` 和 `App Secret`
3. 在 `.env` 中配置：
   ```
   FEISHU_APP_ID=cli_xxxxxxxxxxxx
   FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx
   ```
