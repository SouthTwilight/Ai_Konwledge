"""Knowledge Base Pipeline — Main entry point.

Usage:
    python -m pipeline.main --source rss [--dry-run] [--limit N]
    python -m pipeline.main --source url --url https://example.com/article
    python -m pipeline.main --source feishu --feishu-url https://feishu.cn/docx/xxx
    python -m pipeline.main --source github [--github-repos user/repo1 user/repo2]
    python -m pipeline.main --source email
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pipeline.config import PipelineConfig, load_config, PIPELINE_DIR
from pipeline.models import Article, ArticleSource
from pipeline.extractors.rss_fetcher import fetch_all_rss
from pipeline.extractors.web_extractor import extract_url
from pipeline.utils.dedup import DedupStore
from pipeline.processors.l1_filter import L1Filter
from pipeline.processors.l2_summarizer import L2Summarizer
from pipeline.processors.l3_analyzer import L3Analyzer
from pipeline.formatters.obsidian_writer import ObsidianWriter

logger = logging.getLogger("pipeline")

# Logs directory
LOGS_DIR = PIPELINE_DIR / 'logs'


def setup_logging(level: str = "INFO"):
    """Configure logging with both console and file output."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger config
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler — always DEBUG level for complete log capture
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_filename = datetime.now().strftime("pipeline_%Y%m%d_%H%M%S.log")
    log_path = LOGS_DIR / log_filename

    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root_logger.addHandler(file_handler)

    # Also create a 'latest' symlink / copy for easy access
    latest_path = LOGS_DIR / 'pipeline_latest.log'
    try:
        if latest_path.exists() or latest_path.is_symlink():
            latest_path.unlink()
        latest_path.symlink_to(log_path)
    except OSError:
        # Windows/some FS may not support symlinks — just copy
        import shutil
        shutil.copy2(log_path, latest_path)

    logger.info(f"Log file: {log_path}")
    return log_path


class Pipeline:
    """End-to-end knowledge base processing pipeline."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.dedup = DedupStore(config.dedup_db_path)
        self.l1 = L1Filter(config.model)
        self.l2 = L2Summarizer(config.model)
        self.l3 = L3Analyzer(config.model) if config.l3_enabled else None
        self.writer = ObsidianWriter(config.vault_path)

    def run(
        self,
        source: str = "rss",
        url: Optional[str] = None,
        feishu_url: Optional[str] = None,
        github_repos: Optional[list] = None,
        dry_run: bool = False,
        limit: Optional[int] = None,
    ) -> dict:
        """Execute the full pipeline.

        Args:
            source: Content source type ("rss", "url", "feishu", "github", "email")
            url: Single URL to process (for --source url)
            feishu_url: Feishu document URL (for --source feishu)
            github_repos: Specific GitHub repos to check (for --source github)
            dry_run: If True, skip writing files and LLM calls
            limit: Max articles to process

        Returns:
            Summary dict with stats
        """
        stats = {
            "fetched": 0,
            "new": 0,
            "l1_passed": 0,
            "l2_summarized": 0,
            "written": 0,
            "errors": 0,
        }

        start_time = time.time()

        # Step 1: Extract
        logger.info(f"=== Pipeline start: source={source} dry_run={dry_run} ===")
        logger.info(f"Model config: L1={self.config.model.l1_model}, "
                     f"L2={self.config.model.l2_model}, "
                     f"api_base={self.config.model.api_base}")
        articles = self._extract(source, url, feishu_url, github_repos)
        stats["fetched"] = len(articles)

        if limit:
            articles = articles[:limit]
            logger.info(f"Limited to {limit} articles")

        # Step 2: Deduplicate
        articles = self.dedup.filter_new(articles)
        stats["new"] = len(articles)

        if not articles:
            logger.info("No new articles to process")
            self.dedup.close()
            return stats

        if dry_run:
            logger.info(f"[DRY RUN] Would process {len(articles)} articles:")
            for a in articles:
                logger.info(f"  - {a.title} ({a.url})")
            self.dedup.close()
            return stats

        # Step 3: L1 Filter
        logger.info(f"Starting L1 filter on {len(articles)} articles "
                     f"(discard<={self.config.tier_discard_max}, compressed<={self.config.tier_compressed_max})")
        articles = self.l1.filter_batch(articles, config=self.config)
        stats["l1_passed"] = len(articles)

        if not articles:
            logger.info("No articles passed L1 filter")
            self.dedup.close()
            return stats

        # Step 4: L2 Summarize
        logger.info(f"Starting L2 summarization on {len(articles)} articles")
        articles = self.l2.summarize_batch(articles)
        stats["l2_summarized"] = len(articles)

        # Step 4.5: L3 Deep Analysis (optional, only for high-score detailed articles)
        if self.l3:
            l3_articles = [
                a for a in articles
                if a.relevance_score >= self.config.l3_min_score
                and a.content_tier == "detailed"
            ]
            if l3_articles:
                logger.info(f"Starting L3 deep analysis on {len(l3_articles)} articles "
                            f"(score >= {self.config.l3_min_score})")
                self.l3.analyze_batch(l3_articles)
            else:
                logger.info("No articles eligible for L3 analysis")

        # Step 5: Write to Obsidian
        logger.info(f"Writing {len(articles)} articles to Obsidian vault")
        paths = self.writer.write_batch(articles)
        stats["written"] = len(paths)

        elapsed = time.time() - start_time
        logger.info(
            f"=== Pipeline complete in {elapsed:.1f}s: "
            f"{stats['fetched']} fetched -> {stats['new']} new -> "
            f"{stats['l1_passed']} L1 passed -> {stats['l2_summarized']} L2 -> "
            f"{stats['written']} written ==="
        )

        self.dedup.close()
        return stats

    def _extract(self, source: str, url: Optional[str], feishu_url: Optional[str] = None, github_repos: Optional[list] = None) -> List[Article]:
        """Extract articles from the specified source."""
        if source == "rss":
            logger.info(f"Fetching from {len(self.config.rss_sources)} RSS sources")
            return fetch_all_rss(self.config.rss_sources)

        elif source == "url":
            if not url:
                logger.error("--url required when --source url")
                return []
            article = extract_url(url)
            return [article] if article else []

        elif source == "feishu":
            if not feishu_url:
                logger.error("--feishu-url required when --source feishu")
                return []
            from pipeline.extractors.feishu_extractor import extract_feishu_doc
            article = extract_feishu_doc(feishu_url, self.config.feishu)
            return [article] if article else []

        elif source == "github":
            from pipeline.extractors.github_extractor import extract_github_projects
            return extract_github_projects(repos=github_repos)

        elif source == "email":
            from pipeline.extractors.email_extractor import extract_emails
            return extract_emails(
                imap_server=self.config.email.imap_server,
                imap_port=self.config.email.imap_port,
                username=self.config.email.username,
                app_password=self.config.email.app_password,
                sender_whitelist=self.config.email.sender_whitelist,
                max_emails=self.config.email.max_emails,
                mark_as_read=self.config.email.mark_as_read,
            )

        else:
            logger.error(f"Unknown source: {source}")
            return []


def main():
    parser = argparse.ArgumentParser(
        description="Personal AI Knowledge Base Pipeline"
    )
    parser.add_argument(
        "--source", choices=["rss", "url", "feishu", "github", "email"], default="rss",
        help="Content source type"
    )
    parser.add_argument("--url", help="Single URL to process (with --source url)")
    parser.add_argument(
        "--feishu-url", type=str, default=None,
        help="Feishu document URL (with --source feishu)"
    )
    parser.add_argument(
        "--github-repos", nargs="+", default=None,
        help="Specific GitHub repos to check (with --source github). E.g. --github-repos user/repo1 user/repo2"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Extract and dedup only, skip LLM calls and file writes"
    )
    parser.add_argument("--limit", type=int, help="Max articles to process")
    parser.add_argument(
        "--config", type=str, default=None,
        help="YAML config file for RSS sources (default: pipeline/configs/default.yaml)"
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    args = parser.parse_args()

    log_path = setup_logging(args.log_level)

    config = load_config(args.config)
    if args.source == "rss":
        logger.info(f"Loaded {len(config.rss_sources)} RSS source(s) from config")

    pipeline = Pipeline(config)
    stats = pipeline.run(
        source=args.source,
        url=args.url,
        feishu_url=args.feishu_url,
        github_repos=args.github_repos,
        dry_run=args.dry_run,
        limit=args.limit,
    )

    # Print summary
    print(f"\n{'='*50}")
    print(f"Pipeline Summary:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"  Log: {log_path}")
    print(f"{'='*50}\n")

    sys.exit(0 if stats["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
