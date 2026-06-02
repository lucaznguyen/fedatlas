from __future__ import annotations

import _bootstrap  # noqa: F401

from fedatlas.config import load_settings
from fedatlas.github_client import enrich_github_repos
from fedatlas.schemas import SCHEMAS, ensure_columns
from fedatlas.utils import read_table, write_table


if __name__ == "__main__":
    settings = load_settings()
    code_links = read_table(settings.processed_dir / "paper_code_links.parquet")
    repos, contributors, repo_contributors = enrich_github_repos(settings, code_links)
    write_table(ensure_columns(repos, SCHEMAS["repos"]), settings.processed_dir / "repos.parquet")
    write_table(ensure_columns(contributors, SCHEMAS["contributors"]), settings.processed_dir / "contributors.parquet")
    write_table(ensure_columns(repo_contributors, SCHEMAS["repo_contributors"]), settings.processed_dir / "repo_contributors.parquet")
    print(f"Wrote {len(repos)} repos")
