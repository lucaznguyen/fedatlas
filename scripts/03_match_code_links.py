from __future__ import annotations

import _bootstrap  # noqa: F401

from fedatlas.config import load_settings
from fedatlas.matching import match_papers_with_code
from fedatlas.pwc_client import load_pwc
from fedatlas.schemas import SCHEMAS, ensure_columns
from fedatlas.utils import read_table, write_table


if __name__ == "__main__":
    settings = load_settings()
    papers = read_table(settings.processed_dir / "papers.parquet")
    pwc_papers, pwc_links = load_pwc(settings)
    matches = ensure_columns(match_papers_with_code(papers, pwc_papers, pwc_links), SCHEMAS["paper_code_links"])
    write_table(matches, settings.processed_dir / "paper_code_links.parquet")
    print(f"Wrote {len(matches)} code links")
