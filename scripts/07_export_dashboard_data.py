from __future__ import annotations

import _bootstrap  # noqa: F401

from run_pipeline import export_dashboard_data

from fedatlas.config import load_settings
from fedatlas.utils import read_table


if __name__ == "__main__":
    settings = load_settings()
    names = ["papers", "authors", "institutions", "countries", "venues", "repos", "paper_code_links", "paper_countries", "country_collaboration", "research_to_code"]
    tables = {name: read_table(settings.processed_dir / f"{name}.parquet") for name in names}
    tables["nodes"] = read_table(settings.processed_dir / "nodes.csv")
    tables["edges"] = read_table(settings.processed_dir / "edges.csv")
    export_dashboard_data(settings, tables)
    print("Dashboard exports written")
