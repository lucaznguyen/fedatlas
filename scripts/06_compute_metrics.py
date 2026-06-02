from __future__ import annotations

import _bootstrap  # noqa: F401

from fedatlas.config import load_settings
from fedatlas.metrics import metrics_summary, paper_code_metrics, research_to_code_scores
from fedatlas.utils import read_table, write_table


if __name__ == "__main__":
    settings = load_settings()
    papers = read_table(settings.processed_dir / "papers.parquet")
    links = read_table(settings.processed_dir / "paper_code_links.parquet")
    repos = read_table(settings.processed_dir / "repos.parquet")
    countries = read_table(settings.processed_dir / "paper_countries.parquet")
    paper_metrics = paper_code_metrics(papers, links, repos)
    rtc = research_to_code_scores(papers, paper_metrics, countries)
    write_table(paper_metrics, settings.processed_dir / "research_to_code_papers.parquet")
    write_table(rtc, settings.processed_dir / "research_to_code.parquet")
    write_table(metrics_summary({"papers": papers, "paper_code_links": links, "repos": repos}), settings.processed_dir / "metrics_summary.parquet")
    print("Metrics written")
