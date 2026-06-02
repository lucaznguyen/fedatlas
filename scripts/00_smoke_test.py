from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

import _bootstrap  # noqa: F401

from fedatlas.config import load_settings
from fedatlas.logging_utils import setup_logging
from fedatlas.openalex_client import OpenAlexClient

LOGGER = setup_logging()


def check_setup() -> None:
    settings = load_settings()
    LOGGER.info("Project root: %s", settings.root)
    LOGGER.info("Configured years: %s-%s", settings.start_year, settings.end_year)
    missing = []
    for package in ["pandas", "requests", "yaml", "networkx", "pyarrow"]:
        try:
            __import__(package)
        except Exception:
            missing.append(package)
    if missing:
        raise RuntimeError(f"Missing Python packages: {missing}. Run make setup.")
    if not shutil.which("Rscript"):
        LOGGER.warning("Rscript is not available; dashboard launch cannot be verified on this machine.")
    if not settings.openalex_mailto:
        LOGGER.warning("OPENALEX_MAILTO is empty. OpenAlex works without it, but polite pool usage needs a contact email.")


def openalex_sample(sample_size: int) -> None:
    settings = load_settings()
    client = OpenAlexClient(settings)
    query = settings.queries[0]
    year = settings.end_year
    payload = client.request_page(query, year)
    count = len(payload.get("results", [])[:sample_size])
    if count == 0:
        raise RuntimeError("OpenAlex connectivity succeeded but returned zero sample records.")
    LOGGER.info("OpenAlex sample returned %s records for %r in %s", count, query, year)


def r_check() -> None:
    if not shutil.which("Rscript"):
        LOGGER.warning("Rscript is not available; skipping R package sanity check.")
        return
    subprocess.check_call([
        "Rscript",
        "-e",
        "pkgs <- c('shiny','bslib','plotly','DT','visNetwork','dplyr','readr'); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly=TRUE)]; if(length(missing)) stop(paste('Missing R packages:', paste(missing, collapse=', ')))",
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-setup", action="store_true")
    parser.add_argument("--sample-size", type=int, default=0)
    parser.add_argument("--r-check", action="store_true")
    args = parser.parse_args()
    check_setup()
    if args.r_check:
        r_check()
    if args.sample_size:
        openalex_sample(args.sample_size)


if __name__ == "__main__":
    main()
