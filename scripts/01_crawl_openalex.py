from __future__ import annotations

import _bootstrap  # noqa: F401

from fedatlas.config import load_settings
from fedatlas.logging_utils import setup_logging
from fedatlas.openalex_client import crawl_openalex

LOGGER = setup_logging()


if __name__ == "__main__":
    settings = load_settings()
    records = crawl_openalex(settings)
    LOGGER.info("Crawled %s OpenAlex records before deduplication.", len(records))
