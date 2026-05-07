"""Knowledge Base Pipeline — Main entry point.

Usage:
    python -m pipeline.main --source rss [--dry-run] [--limit N]
    python -m pipeline.main --source url --url https://example.com/article
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

from pipeline.config import PipelineConfig, load_config
from pipeline.models import Article, ArticleSource
from pipeline.extractors.rss_fetcher import fetch_all_rss
from pipeline.extractors.web_extractor import extract_url
from pipeline.utils.dedup import DedupStore
from pipeline.processors.l1_filter import L1Filter
from pipeline.processors.l2_summarizer import L2Summarizer
from pipeline.formatters.obsidian_writer import ObsidianWriter

logger = logging.getLogger("pipeline")


def setup_logging(level: str = "INFO"):
    """Configure logging for the pipeline."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


class Pipeline:
    """End-to-end knowledge base processing pipeline."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.dedup = DedupStore(config.dedup_db_path)
        self.l1 = L1Filter(config.model)
        self.l2 = L2Summarizer(config.model)
        self.writer = ObsidianWriter(config.vault_path)

    def run(
        self,
        source: str = "rss",
        url: Optional[str] = None,
        dry_run: bool = False,
        limit: Optional[int] = None,
    ) -> dict:
        """Execute the full pipeline.

        Args:
            source: Content source type ("rss" or "url")
            url: Single URL to process (for --source url)
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
        articles = self._extract(source, url)
        stats["fetched"] = len(articles)

        if limit:
            articles = articles[:limit]

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
        articles = self.l1.filter_batch(articles, threshold=self.config.relevance_threshold)
        stats["l1_passed"] = len(articles)

        if not articles:
            logger.info("No articles passed L1 filter")
            self.dedup.close()
            return stats

        # Step 4: L2 Summarize
        articles = self.l2.summarize_batch(articles)
        stats["l2_summarized"] = len(articles)

        # Step 5: Write to Obsidian
        paths = self.writer.write_batch(articles)
        stats["written"] = len(paths)

        elapsed = time.time() - start_time
        logger.info(
            f"=== Pipeline complete in {elapsed:.1f}s: "
            f"{stats['fetched']} fetched → {stats['new']} new → "
            f"{stats['l1_passed']} L1 passed → {stats['l2_summarized']} L2 → "
            f"{stats['written']} written ==="
        )

        self.dedup.close()
        return stats

    def _extract(self, source: str, url: Optional[str]) -> List[Article]:
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

        else:
            logger.error(f"Unknown source: {source}")
            return []


def main():
    parser = argparse.ArgumentParser(
        description="Personal AI Knowledge Base Pipeline"
    )
    parser.add_argument(
        "--source", choices=["rss", "url"], default="rss",
        help="Content source type"
    )
    parser.add_argument("--url", help="Single URL to process (with --source url)")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Extract and dedup only, skip LLM calls and file writes"
    )
    parser.add_argument("--limit", type=int, help="Max articles to process")
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    args = parser.parse_args()

    setup_logging(args.log_level)

    config = load_config()
    pipeline = Pipeline(config)
    stats = pipeline.run(
        source=args.source,
        url=args.url,
        dry_run=args.dry_run,
        limit=args.limit,
    )

    # Print summary
    print(f"\n{'='*50}")
    print(f"Pipeline Summary:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"{'='*50}\n")

    sys.exit(0 if stats["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
