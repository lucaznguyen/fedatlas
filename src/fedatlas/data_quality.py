from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .config import load_settings
from .utils import now_utc_iso, read_table


def _metric(name: str, value: Any) -> str:
    return f"- {name}: {value}"


def generate_report(processed_dir: str | Path | None = None, output_path: str | Path | None = None) -> Path:
    settings = load_settings()
    processed = Path(processed_dir) if processed_dir else settings.processed_dir
    output = Path(output_path) if output_path else settings.root / "data_quality_report.md"
    tables = {}
    for name in ["papers", "authors", "institutions", "countries", "venues", "topics", "repos", "paper_code_links"]:
        tables[name] = read_table(processed / f"{name}.parquet")
    papers = tables["papers"]
    quality = papers.get("quality_label", pd.Series(dtype="object")).fillna("Unknown") if not papers.empty else pd.Series(dtype="object")
    missing_doi_rate = float(papers.get("doi", pd.Series(dtype="object")).isna().mean()) if not papers.empty and "doi" in papers else None
    missing_abs_rate = float(papers.get("abstract", pd.Series(dtype="object")).isna().mean()) if not papers.empty and "abstract" in papers else None
    lines = [
        "# FedAtlas Data Quality Report",
        "",
        _metric("crawl timestamp", now_utc_iso()),
        _metric("configured year range", f"{settings.start_year}-{settings.end_year}"),
        _metric("paper count", len(tables["papers"])),
        _metric("author count", len(tables["authors"])),
        _metric("institution count", len(tables["institutions"])),
        _metric("country count", len(tables["countries"])),
        _metric("venue count", len(tables["venues"])),
        _metric("topic count", len(tables["topics"])),
        _metric("repo count", len(tables["repos"])),
        _metric("Papers With Code match count", len(tables["paper_code_links"])),
        _metric("venue quality coverage", quality.value_counts(dropna=False).to_dict()),
        _metric("missing DOI rate", missing_doi_rate),
        _metric("missing abstract rate", missing_abs_rate),
        "",
        "## Warnings",
        "",
    ]
    if not settings.github_token:
        lines.append("- GITHUB_TOKEN is not configured; unauthenticated GitHub enrichment is rate-limited.")
    if not settings.openalex_mailto:
        lines.append("- OPENALEX_MAILTO is not configured; set it for polite OpenAlex API usage.")
    if not papers.empty and (quality == "Unknown").mean() > 0.5:
        lines.append("- More than half of venues are Unknown quality; import a licensed venue quality file for A*/A/Q1 filtering.")
    if not lines[-1].startswith("- "):
        lines.append("- No major warnings were generated.")
    lines.extend([
        "",
        "## Reproducibility Commands",
        "",
        "```bash",
        "make setup",
        "make smoke",
        "make crawl",
        "make build",
        "make dashboard",
        "```",
    ])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    print(generate_report())
