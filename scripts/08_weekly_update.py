from __future__ import annotations

import os

import _bootstrap  # noqa: F401

from fedatlas.logging_utils import setup_logging
from run_pipeline import run

LOGGER = setup_logging()


if __name__ == "__main__":
    # OpenAlex premium supports from_updated_date. Without it, this conservative
    # update recrawls the current configured range with cache reuse and rebuilds
    # all normalized outputs, which is reliable for weekly class-sized updates.
    os.environ.setdefault("FORCE_REFRESH", "0")
    LOGGER.info("Starting weekly update. Secrets are read from environment variables.")
    run(skip_crawl=False)
