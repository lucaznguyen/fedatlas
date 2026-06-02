from __future__ import annotations

import _bootstrap  # noqa: F401

from fedatlas.config import load_settings
from fedatlas.logging_utils import setup_logging
from fedatlas.pwc_client import download_pwc

LOGGER = setup_logging()


if __name__ == "__main__":
    paths = download_pwc(load_settings())
    LOGGER.info("Papers With Code files: %s", paths)
