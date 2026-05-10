"""Exponential-backoff retry helper for LLM API calls."""
from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_MAX_RETRIES = 2
DEFAULT_BASE_DELAY = 2.0  # seconds


def retry_with_backoff(
    fn: Callable[[], T],
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    label: str = "API call",
) -> T:
    """Call *fn* with exponential-backoff retry on any exception.

    Args:
        fn: Zero-arg callable to execute.
        max_retries: Maximum number of retries (total attempts = max_retries + 1).
        base_delay: Base delay in seconds; each retry multiplies by 2.
        label: Human-readable label for log messages.

    Returns:
        The return value of *fn*.

    Raises:
        The last exception if all attempts fail.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                    label, attempt + 1, max_retries + 1, e, delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "%s failed after %d attempts: %s",
                    label, max_retries + 1, e,
                )
    raise last_exc  # type: ignore[misc]
