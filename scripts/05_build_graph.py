from __future__ import annotations

import _bootstrap  # noqa: F401

from fedatlas.config import load_settings
from fedatlas.graph_builder import build_graph_tables
from fedatlas.utils import read_table, write_table


if __name__ == "__main__":
    settings = load_settings()
    names = ["papers", "authors", "institutions", "countries", "venues", "topics", "paper_authors", "paper_institutions", "paper_countries", "paper_topics", "paper_references", "paper_code_links", "repos", "contributors", "repo_contributors"]
    tables = {name: read_table(settings.processed_dir / f"{name}.parquet") for name in names}
    graph = build_graph_tables(tables)
    for name, df in graph.items():
        suffix = ".csv" if name in {"nodes", "edges"} else ".parquet"
        write_table(df, settings.processed_dir / f"{name}{suffix}")
    print(f"Wrote {len(graph['nodes'])} nodes and {len(graph['edges'])} edges")
