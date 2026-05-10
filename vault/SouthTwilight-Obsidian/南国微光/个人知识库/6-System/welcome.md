---
type: system
date: 2026-05-07
tags: [system]
---

# AI Knowledge Base

Managed by Hermes Agent + Python Pipeline.

## Directory Layout
| Dir | Purpose |
|-----|---------|
| 0-Inbox | Unprocessed |
| 1-Daily | Daily notes |
| 2-Articles | AI-processed articles |
| 3-GitHub | Repo activity |
| 4-Newsletters | Email newsletters |
| 5-Topics | Topic MOCs |
| 6-Permanent | Permanent notes |

## Pipeline
RSS/URL -> Extractor -> L1(filter) -> L2(summary) -> Obsidian
