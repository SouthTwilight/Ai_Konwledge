"""Tests for Obsidian Writer formatter."""
import pytest
from datetime import datetime
from pathlib import Path

from pipeline.models import Article, ArticleSource, ProcessingLevel
from pipeline.formatters.obsidian_writer import ObsidianWriter, _slugify


@pytest.fixture
def processed_article():
    return Article(
        url="https://example.com/gpt5-released",
        title="GPT-5 Released with Major Improvements",
        source=ArticleSource.RSS,
        content_raw="OpenAI has released GPT-5. " * 50,
        content_summary="**TL;DR:** GPT-5 is here.\n\nFull summary of the release.",
        author="John Doe",
        published_at=datetime(2026, 5, 1),
        source_name="TechNews",
        relevance_score=9,
        tags=["ai", "llm", "openai"],
        key_points=["10x reasoning", "1M context", "Tool use"],
        related_topics=["LLM", "OpenAI"],
        processing_level=ProcessingLevel.L2_SUMMARIZED,
        content_hash="abc123",
        content_tier="compressed",
    )


@pytest.fixture
def writer(tmp_path):
    return ObsidianWriter(tmp_path)


class TestSlugify:

    def test_basic(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert _slugify("What's new in AI/ML? (2026)") == "whats-new-in-aiml-2026"

    def test_long_title(self):
        slug = _slugify("A" * 200)
        assert len(slug) <= 80


class TestObsidianWriter:

    def test_format_has_frontmatter(self, writer, processed_article):
        _, content = writer.format_article(processed_article)
        assert content.startswith("---\n")
        # Second --- for frontmatter close
        parts = content.split("---\n")
        assert len(parts) >= 3  # frontmatter open, body

    def test_format_has_title(self, writer, processed_article):
        _, content = writer.format_article(processed_article)
        assert "# GPT-5 Released" in content

    def test_format_has_wikilinks(self, writer, processed_article):
        _, content = writer.format_article(processed_article)
        assert "[[LLM]]" in content
        assert "[[OpenAI]]" in content

    def test_format_has_tags(self, writer, processed_article):
        _, content = writer.format_article(processed_article)
        assert "#ai" in content
        assert "#llm" in content

    def test_format_has_key_points(self, writer, processed_article):
        _, content = writer.format_article(processed_article)
        assert "- 10x reasoning" in content

    def test_write_creates_file(self, writer, processed_article):
        path = writer.write_article(processed_article)
        assert path is not None
        assert path.exists()
        assert path.suffix == ".md"

    def test_write_uses_correct_directory(self, writer, processed_article):
        path = writer.write_article(processed_article)
        assert "2-Articles" in str(path)

    def test_write_github_article(self, writer):
        article = Article(
            url="https://github.com/test/repo",
            title="Test Repo Release",
            source=ArticleSource.GITHUB,
            tags=["open-source"],
            processing_level=ProcessingLevel.L2_SUMMARIZED,
        )
        path = writer.write_article(article)
        assert "3-GitHub" in str(path)

    def test_write_handles_collision(self, writer, processed_article):
        # Write same article twice
        path1 = writer.write_article(processed_article)
        # Reset obsidian_path to simulate new article
        processed_article.obsidian_path = ""
        path2 = writer.write_article(processed_article)
        assert path1 != path2

    def test_batch_write(self, writer):
        articles = [
            Article(url=f"https://example.com/{i}", title=f"Article {i}",
                    source=ArticleSource.RSS, tags=["test"])
            for i in range(3)
        ]
        paths = writer.write_batch(articles)
        assert len(paths) == 3
        for p in paths:
            assert p.exists()

    def test_preview_no_file(self, writer, processed_article):
        content = writer.preview(processed_article)
        assert "# GPT-5" in content
        # Should not create any files
        written_files = list(writer.vault_path.rglob("*.md"))
        assert len(written_files) == 0

    def test_date_subfolder_in_path(self, writer, processed_article):
        """Articles should be written under a YYYY-MM-DD date subfolder."""
        path = writer.write_article(processed_article)
        parts = Path(str(path)).parts
        assert "2-Articles" in parts
        # Find date part (YYYY-MM-DD format)
        date_parts = [p for p in parts if len(p) == 10 and p[4] == '-' and p[7] == '-']
        assert len(date_parts) >= 1, f"Expected date folder like 2026-05-08 in {path}"

    def test_detailed_article_has_raw_content_section(self, writer, processed_article):
        processed_article.content_tier = "detailed"
        _, content = writer.format_article(processed_article)
        assert "## 原文内容" in content

    def test_compressed_article_no_raw_content_section(self, writer, processed_article):
        processed_article.content_tier = "compressed"
        _, content = writer.format_article(processed_article)
        assert "## 原文内容" not in content

    def test_filename_has_score_prefix(self, writer, processed_article):
        filename, _ = writer.format_article(processed_article)
        assert filename.startswith("[S"), f"Expected score prefix like [S9], got: {filename}"
        assert f"[S{processed_article.relevance_score}]" in filename

    def test_filename_no_score_when_zero(self, writer):
        article = Article(
            url="https://example.com/test",
            title="Test Article",
            source=ArticleSource.RSS,
            relevance_score=0,
            content_tier="compressed",
        )
        filename, _ = writer.format_article(article)
        assert not filename.startswith("[S"), f"Zero score should have no prefix, got: {filename}"
