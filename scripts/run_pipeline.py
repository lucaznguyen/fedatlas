from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
import pandas as pd

from fedatlas.config import load_settings
from fedatlas.country_codes import country_alpha3, country_display_name
from fedatlas.data_quality import generate_report
from fedatlas.github_client import enrich_github_repos
from fedatlas.graph_builder import build_graph_tables
from fedatlas.logging_utils import setup_logging
from fedatlas.matching import match_papers_with_code
from fedatlas.metrics import compute_code_scores, metrics_summary, paper_code_metrics, research_to_code_scores
from fedatlas.normalize import normalize_openalex
from fedatlas.openalex_client import crawl_openalex, load_cached_openalex
from fedatlas.pwc_client import download_pwc, load_pwc
from fedatlas.schemas import SCHEMAS, ensure_columns, fail_if_production_empty
from fedatlas.utils import ensure_dir, read_json, write_table


LOGGER = setup_logging()


def _empty(name: str) -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMAS.get(name, []))


def load_demo_records(root: Path) -> list[dict]:
    fixture = root / "tests" / "fixtures" / "openalex_sample.json"
    if not fixture.exists():
        return []
    payload = read_json(fixture)
    return payload if isinstance(payload, list) else payload.get("results", [])


def write_core_tables(settings, tables: dict[str, pd.DataFrame]) -> None:
    ensure_dir(settings.processed_dir)
    for name, df in tables.items():
        if name in {"nodes", "edges"}:
            continue
        if isinstance(df, pd.DataFrame):
            write_table(df, settings.processed_dir / f"{name}.parquet")


def add_repo_counts(repos: pd.DataFrame, repo_contributors: pd.DataFrame) -> pd.DataFrame:
    if repos.empty:
        return ensure_columns(repos, SCHEMAS["repos"])
    out = repos.copy()
    if "github_status" in out.columns:
        out["_status_rank"] = (pd.to_numeric(out["github_status"], errors="coerce") == 200).astype(int)
        out = out.sort_values("_status_rank", ascending=False).drop(columns=["_status_rank"])
    if "repo_full_name" in out.columns:
        out = out.drop_duplicates(subset=["repo_full_name"], keep="first")
    if not repo_contributors.empty:
        counts = repo_contributors.groupby("repo_full_name")["contributor_id"].nunique().reset_index(name="contributors_count")
        out = out.merge(counts, on="repo_full_name", how="left")
    else:
        out["contributors_count"] = 0
    out = compute_code_scores(out)
    return ensure_columns(out, SCHEMAS["repos"])


def export_dashboard_data(settings, tables: dict[str, pd.DataFrame]) -> None:
    out_dir = ensure_dir(settings.processed_dir)
    papers = tables.get("papers", _empty("papers"))
    authors = tables.get("authors", _empty("authors"))
    institutions = tables.get("institutions", _empty("institutions"))
    countries = tables.get("countries", _empty("countries"))
    venues = tables.get("venues", _empty("venues"))
    repos = tables.get("repos", _empty("repos"))
    code_links = tables.get("paper_code_links", _empty("paper_code_links"))
    paper_metrics = tables.get("research_to_code_papers", pd.DataFrame())
    nodes = tables.get("nodes", pd.DataFrame())
    edges = tables.get("edges", pd.DataFrame())
    paper_countries = tables.get("paper_countries", pd.DataFrame())

    has_code_ids = set(code_links.get("work_id", pd.Series(dtype="object")).dropna().astype(str))
    total_papers = len(papers)
    kpis = pd.DataFrame([
        {"metric": "Papers", "value": total_papers},
        {"metric": "Authors", "value": len(authors)},
        {"metric": "Institutions", "value": len(institutions)},
        {"metric": "Countries", "value": len(countries)},
        {"metric": "Venues", "value": len(venues)},
        {"metric": "GitHub Repos", "value": len(repos)},
        {"metric": "Total Citations", "value": pd.to_numeric(papers.get("cited_by_count", 0), errors="coerce").fillna(0).sum() if not papers.empty else 0},
        {"metric": "Total GitHub Stars", "value": pd.to_numeric(repos.get("stargazers_count", 0), errors="coerce").fillna(0).sum() if not repos.empty else 0},
        {"metric": "Research-to-Code Score", "value": (len(set(has_code_ids)) / total_papers) if total_papers else 0},
    ])
    write_table(kpis, out_dir / "dashboard_kpis.csv")

    if not papers.empty:
        ts = papers.assign(has_code=papers["work_id"].astype(str).isin(has_code_ids))
        timeseries = ts.groupby("publication_year").agg(
            papers=("work_id", "nunique"),
            citations=("cited_by_count", "sum"),
            github_linked_papers=("has_code", "sum"),
        ).reset_index().rename(columns={"publication_year": "year"})
        topic_year = ts.groupby(["publication_year", "topic_group"]).size().reset_index(name="papers").rename(columns={"publication_year": "year"})
        code_gap = paper_metrics if not paper_metrics.empty else ts[["work_id", "title", "publication_year", "cited_by_count", "topic_group", "venue_name", "quality_label", "has_code"]]
    else:
        timeseries = pd.DataFrame(columns=["year", "papers", "citations", "github_linked_papers"])
        topic_year = pd.DataFrame(columns=["year", "topic_group", "papers"])
        code_gap = pd.DataFrame()
    write_table(timeseries, out_dir / "dashboard_timeseries.csv")
    write_table(topic_year, out_dir / "dashboard_topic_year.csv")
    write_table(code_gap, out_dir / "dashboard_code_gap.csv")

    if not paper_countries.empty:
        paper_country_base = papers[["work_id", "cited_by_count"]] if not papers.empty else pd.DataFrame()
        if not paper_country_base.empty:
            paper_country_base = paper_country_base.assign(has_code=paper_country_base["work_id"].astype(str).isin(has_code_ids))
        country_map = paper_countries.merge(paper_country_base, on="work_id", how="left")
        country_map = country_map.groupby(["country_code", "country_name"]).agg(
            paper_count=("work_id", "nunique"),
            citations=("cited_by_count", "sum"),
            github_linked_papers=("has_code", "sum"),
        ).reset_index()
        country_map["country_iso3"] = country_map["country_code"].map(country_alpha3)
        country_map["country_name"] = country_map.apply(
            lambda row: country_display_name(row["country_code"]) or row["country_name"],
            axis=1,
        )
        country_map = country_map.dropna(subset=["country_iso3"])
        country_map["research_to_code_score"] = country_map["github_linked_papers"] / country_map["paper_count"].replace(0, pd.NA)
        if not nodes.empty and {"node_type", "node_id", "bridge_score", "degree"}.issubset(nodes.columns):
            country_nodes = nodes[nodes["node_type"] == "Country"][["node_id", "bridge_score", "degree"]]
            country_map = country_map.merge(country_nodes, left_on="country_code", right_on="node_id", how="left").drop(columns=["node_id"], errors="ignore")
    else:
        country_map = pd.DataFrame(columns=["country_code", "country_iso3", "country_name", "paper_count", "citations", "github_linked_papers", "research_to_code_score", "bridge_score", "degree"])
    write_table(country_map, out_dir / "dashboard_country_map.csv")
    write_table(tables.get("country_collaboration", pd.DataFrame()), out_dir / "dashboard_country_edges.csv")

    if not nodes.empty:
        write_table(nodes, out_dir / "nodes.csv")
        write_table(nodes, out_dir / "dashboard_network_nodes.csv")
    else:
        write_table(pd.DataFrame(columns=["node_id", "node_type", "label"]), out_dir / "nodes.csv")
        write_table(pd.DataFrame(columns=["node_id", "node_type", "label"]), out_dir / "dashboard_network_nodes.csv")
    if not edges.empty:
        write_table(edges, out_dir / "edges.csv")
        write_table(edges, out_dir / "dashboard_network_edges.csv")
    else:
        write_table(pd.DataFrame(columns=["source", "target", "relation", "weight"]), out_dir / "edges.csv")
        write_table(pd.DataFrame(columns=["source", "target", "relation", "weight"]), out_dir / "dashboard_network_edges.csv")

    sankey_rows = []
    if not code_links.empty and not paper_countries.empty and not papers.empty:
        country_labels = paper_countries[["work_id", "country_name", "country_code"]].drop_duplicates()
        country_labels["country_label"] = country_labels["country_name"].fillna(country_labels["country_code"])
        sankey_base = code_links.merge(papers[["work_id", "title", "topic_group"]], on="work_id", how="left").merge(country_labels[["work_id", "country_label"]], on="work_id", how="left")
        for _, row in sankey_base.dropna(subset=["country_label", "topic_group", "title", "repo_owner", "repo_name"]).head(500).iterrows():
            repo_label = f"{row['repo_owner']}/{row['repo_name']}"
            sankey_rows.extend([
                {"source": row["country_label"], "target": row["topic_group"], "value": 1, "level": "country_to_topic"},
                {"source": row["topic_group"], "target": row["title"], "value": 1, "level": "topic_to_paper"},
                {"source": row["title"], "target": repo_label, "value": 1, "level": "paper_to_repo"},
            ])
    sankey = pd.DataFrame(sankey_rows).groupby(["source", "target", "level"], as_index=False)["value"].sum() if sankey_rows else pd.DataFrame(columns=["source", "target", "value", "level"])
    rtc = tables.get("research_to_code", _empty("research_to_code"))
    write_table(rtc, out_dir / "research_to_code.parquet")
    write_table(sankey, out_dir / "dashboard_sankey.csv")


def run(skip_crawl: bool = False, sample_size: int | None = None) -> dict[str, pd.DataFrame]:
    settings = load_settings()
    if skip_crawl:
        records = load_cached_openalex(settings)
    else:
        records = crawl_openalex(settings, sample_size=sample_size)
    if not records and settings.use_demo_data:
        LOGGER.warning("Using demo fixture records because USE_DEMO_DATA=1.")
        records = load_demo_records(settings.root)
    if not records:
        raise RuntimeError("No OpenAlex records are available. Run make crawl, set USE_DEMO_DATA=1 for fixtures, or check network/API access.")

    tables = normalize_openalex(records, str(settings.venue_quality_path))
    fail_if_production_empty("papers", tables["papers"], production=not settings.use_demo_data)
    fail_if_production_empty("authors", tables["authors"], production=not settings.use_demo_data)
    fail_if_production_empty("countries", tables["countries"], production=not settings.use_demo_data)

    if settings.run_pwc_matching:
        download_pwc(settings)
        pwc_papers, pwc_links = load_pwc(settings)
        code_links = match_papers_with_code(tables["papers"], pwc_papers, pwc_links)
    else:
        code_links = _empty("paper_code_links")
    tables["paper_code_links"] = ensure_columns(code_links, SCHEMAS["paper_code_links"])

    repos, contributors, repo_contributors = enrich_github_repos(settings, tables["paper_code_links"])
    tables["contributors"] = ensure_columns(contributors, SCHEMAS["contributors"])
    tables["repo_contributors"] = ensure_columns(repo_contributors, SCHEMAS["repo_contributors"])
    tables["repos"] = add_repo_counts(repos, tables["repo_contributors"])

    paper_metrics = paper_code_metrics(tables["papers"], tables["paper_code_links"], tables["repos"])
    tables["research_to_code_papers"] = paper_metrics
    tables["research_to_code"] = research_to_code_scores(tables["papers"], paper_metrics, tables.get("paper_countries"))
    graph_tables = build_graph_tables(tables)
    tables.update(graph_tables)
    tables["metrics_summary"] = pd.concat([tables.get("metrics_summary", pd.DataFrame()), metrics_summary(tables)], ignore_index=True)

    write_core_tables(settings, tables)
    export_dashboard_data(settings, tables)
    generate_report(settings.processed_dir, settings.root / "data_quality_report.md")
    LOGGER.info("Pipeline complete. Processed tables written to %s", settings.processed_dir)
    return tables


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-crawl", action="store_true", help="Use cached data/interim/openalex_works.jsonl")
    parser.add_argument("--sample-size", type=int, default=None, help="Limit OpenAlex crawl for smoke/demo runs")
    args = parser.parse_args()
    run(skip_crawl=args.skip_crawl, sample_size=args.sample_size)


if __name__ == "__main__":
    main()
