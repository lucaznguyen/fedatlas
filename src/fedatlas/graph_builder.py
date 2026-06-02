from __future__ import annotations

from itertools import combinations
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd


def _add_edge(rows: list[dict[str, Any]], source: Any, target: Any, relation: str, directed: bool, year: Any = None, source_type: str | None = None, target_type: str | None = None, weight: float = 1.0) -> None:
    if pd.isna(source) or pd.isna(target) or source == target:
        return
    rows.append({
        "source": str(source),
        "target": str(target),
        "relation": relation,
        "directed": directed,
        "weight": weight,
        "year": year,
        "source_type": source_type,
        "target_type": target_type,
        "extra_json": "{}",
    })


def country_collaboration_edges(paper_countries: pd.DataFrame, papers: pd.DataFrame | None = None) -> pd.DataFrame:
    if paper_countries.empty:
        return pd.DataFrame(columns=["source", "target", "weight", "year"])
    pc = paper_countries.dropna(subset=["work_id", "country_code"]).drop_duplicates(["work_id", "country_code"])
    if papers is not None and not papers.empty and "publication_year" in papers:
        pc = pc.merge(papers[["work_id", "publication_year"]], on="work_id", how="left")
    rows = []
    for work_id, group in pc.groupby("work_id"):
        countries = sorted(group["country_code"].dropna().astype(str).unique())
        year = group["publication_year"].dropna().iloc[0] if "publication_year" in group and group["publication_year"].notna().any() else None
        for a, b in combinations(countries, 2):
            rows.append({"source": a, "target": b, "weight": 1, "year": year})
    if not rows:
        return pd.DataFrame(columns=["source", "target", "weight", "year"])
    return pd.DataFrame(rows).groupby(["source", "target", "year"], dropna=False)["weight"].sum().reset_index()


def author_collaboration_edges(paper_authors: pd.DataFrame, papers: pd.DataFrame | None = None) -> pd.DataFrame:
    if paper_authors.empty:
        return pd.DataFrame(columns=["source", "target", "weight", "year"])
    pa = paper_authors.dropna(subset=["work_id", "author_id"]).drop_duplicates(["work_id", "author_id"])
    if papers is not None and not papers.empty and "publication_year" in papers:
        pa = pa.merge(papers[["work_id", "publication_year"]], on="work_id", how="left")
    rows = []
    for _, group in pa.groupby("work_id"):
        authors = sorted(group["author_id"].dropna().astype(str).unique())
        year = group["publication_year"].dropna().iloc[0] if "publication_year" in group and group["publication_year"].notna().any() else None
        for a, b in combinations(authors, 2):
            rows.append({"source": a, "target": b, "weight": 1, "year": year})
    if not rows:
        return pd.DataFrame(columns=["source", "target", "weight", "year"])
    return pd.DataFrame(rows).groupby(["source", "target", "year"], dropna=False)["weight"].sum().reset_index()


def topic_cooccurrence_edges(paper_topics: pd.DataFrame, papers: pd.DataFrame | None = None) -> pd.DataFrame:
    if paper_topics.empty:
        return pd.DataFrame(columns=["source", "target", "weight", "year"])
    pt = paper_topics.dropna(subset=["work_id", "topic_group"]).drop_duplicates(["work_id", "topic_group"])
    if papers is not None and not papers.empty and "publication_year" in papers:
        pt = pt.merge(papers[["work_id", "publication_year"]], on="work_id", how="left")
    rows = []
    for _, group in pt.groupby("work_id"):
        topics = sorted(group["topic_group"].dropna().astype(str).unique())
        year = group["publication_year"].dropna().iloc[0] if "publication_year" in group and group["publication_year"].notna().any() else None
        for a, b in combinations(topics, 2):
            rows.append({"source": a, "target": b, "weight": 1, "year": year})
    if not rows:
        return pd.DataFrame(columns=["source", "target", "weight", "year"])
    return pd.DataFrame(rows).groupby(["source", "target", "year"], dropna=False)["weight"].sum().reset_index()


def build_graph_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    papers = tables.get("papers", pd.DataFrame())
    authors = tables.get("authors", pd.DataFrame())
    institutions = tables.get("institutions", pd.DataFrame())
    countries = tables.get("countries", pd.DataFrame())
    venues = tables.get("venues", pd.DataFrame())
    topics = tables.get("topics", pd.DataFrame())
    code_links = tables.get("paper_code_links", pd.DataFrame())
    repos = tables.get("repos", pd.DataFrame())
    contributors = tables.get("contributors", pd.DataFrame())
    repo_contributors = tables.get("repo_contributors", pd.DataFrame())

    node_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    for _, p in papers.iterrows():
        node_rows.append({"node_id": p.get("work_id"), "node_type": "Paper", "label": p.get("title"), "display_label": p.get("title"), "year": p.get("publication_year"), "country": None, "topic": p.get("topic_group"), "venue_quality": p.get("quality_label"), "size_metric": p.get("cited_by_count", 0), "color_group": "Paper", "community": None, "url": p.get("doi_url") or p.get("openalex_url"), "extra_json": "{}"})
        _add_edge(edge_rows, p.get("work_id"), p.get("venue_id"), "published_in", True, p.get("publication_year"), "Paper", "Venue")
    for _, a in authors.iterrows():
        node_rows.append({"node_id": a.get("author_id"), "node_type": "Author", "label": a.get("author_name"), "display_label": a.get("author_name"), "year": None, "country": None, "topic": None, "venue_quality": None, "size_metric": 1, "color_group": "Author", "community": None, "url": a.get("orcid"), "extra_json": "{}"})
    for _, i in institutions.iterrows():
        node_rows.append({"node_id": i.get("institution_id"), "node_type": "Institution", "label": i.get("institution_name"), "display_label": i.get("institution_name"), "year": None, "country": i.get("country_code"), "topic": None, "venue_quality": None, "size_metric": 1, "color_group": "Institution", "community": None, "url": None, "extra_json": "{}"})
        _add_edge(edge_rows, i.get("institution_id"), i.get("country_code"), "located_in", True, None, "Institution", "Country")
    for _, c in countries.iterrows():
        node_rows.append({"node_id": c.get("country_code"), "node_type": "Country", "label": c.get("country_name") or c.get("country_code"), "display_label": c.get("country_name") or c.get("country_code"), "year": None, "country": c.get("country_code"), "topic": None, "venue_quality": None, "size_metric": 1, "color_group": "Country", "community": None, "url": None, "extra_json": "{}"})
    for _, v in venues.iterrows():
        node_rows.append({"node_id": v.get("venue_id") or v.get("venue_name"), "node_type": "Venue", "label": v.get("venue_name"), "display_label": v.get("venue_name"), "year": None, "country": None, "topic": None, "venue_quality": v.get("quality_label"), "size_metric": 1, "color_group": "Venue", "community": None, "url": None, "extra_json": "{}"})
    for _, t in topics.iterrows():
        node_rows.append({"node_id": t.get("topic_id") or t.get("topic_name"), "node_type": "Topic", "label": t.get("topic_name"), "display_label": t.get("topic_name"), "year": None, "country": None, "topic": t.get("topic_name"), "venue_quality": None, "size_metric": 1, "color_group": "Topic", "community": None, "url": None, "extra_json": "{}"})
    for _, r in repos.iterrows():
        node_rows.append({"node_id": r.get("repo_full_name"), "node_type": "GitHubRepo", "label": r.get("repo_full_name"), "display_label": r.get("repo_full_name"), "year": pd.to_datetime(r.get("created_at"), errors="coerce").year if pd.notna(r.get("created_at")) else None, "country": None, "topic": None, "venue_quality": None, "size_metric": r.get("stargazers_count", 0), "color_group": "GitHubRepo", "community": None, "url": r.get("repo_url"), "extra_json": "{}"})
    for _, c in contributors.iterrows():
        node_rows.append({"node_id": c.get("contributor_id"), "node_type": "Contributor", "label": c.get("login"), "display_label": c.get("login"), "year": None, "country": None, "topic": None, "venue_quality": None, "size_metric": 1, "color_group": "Contributor", "community": None, "url": c.get("html_url"), "extra_json": "{}"})

    for _, row in tables.get("paper_authors", pd.DataFrame()).iterrows():
        year = papers.set_index("work_id").get("publication_year", pd.Series()).get(row.get("work_id")) if not papers.empty else None
        _add_edge(edge_rows, row.get("author_id"), row.get("work_id"), "writes", True, year, "Author", "Paper")
    for _, row in tables.get("paper_institutions", pd.DataFrame()).iterrows():
        _add_edge(edge_rows, row.get("institution_id"), row.get("work_id"), "affiliated_with_paper", True, None, "Institution", "Paper")
    for _, row in tables.get("paper_topics", pd.DataFrame()).iterrows():
        _add_edge(edge_rows, row.get("work_id"), row.get("topic_id") or row.get("topic_group"), "has_topic", True, None, "Paper", "Topic")
    for _, row in tables.get("paper_references", pd.DataFrame()).iterrows():
        _add_edge(edge_rows, row.get("work_id"), row.get("referenced_work_id"), "cites", True, None, "Paper", "Paper")
    if not code_links.empty:
        for _, row in code_links.iterrows():
            full = f"{row.get('repo_owner')}/{row.get('repo_name')}"
            _add_edge(edge_rows, row.get("work_id"), full, "has_implementation", True, None, "Paper", "GitHubRepo")
    if not repo_contributors.empty:
        for _, row in repo_contributors.iterrows():
            _add_edge(edge_rows, row.get("contributor_id"), row.get("repo_full_name"), "contributes_to", True, None, "Contributor", "GitHubRepo", row.get("contributions", 1))

    country_edges = country_collaboration_edges(tables.get("paper_countries", pd.DataFrame()), papers)
    author_edges = author_collaboration_edges(tables.get("paper_authors", pd.DataFrame()), papers)
    topic_edges = topic_cooccurrence_edges(tables.get("paper_topics", pd.DataFrame()), papers)
    for df, rel, stype, ttype in [(country_edges, "collaborates_with", "Country", "Country"), (author_edges, "coauthors", "Author", "Author"), (topic_edges, "co_occurs", "Topic", "Topic")]:
        for _, row in df.iterrows():
            _add_edge(edge_rows, row["source"], row["target"], rel, False, row.get("year"), stype, ttype, row.get("weight", 1))

    node_columns = ["node_id", "node_type", "label", "display_label", "year", "country", "topic", "venue_quality", "size_metric", "color_group", "community", "url", "extra_json"]
    edge_columns = ["source", "target", "relation", "directed", "weight", "year", "source_type", "target_type", "extra_json"]
    nodes = pd.DataFrame(node_rows, columns=node_columns)
    edges = pd.DataFrame(edge_rows, columns=edge_columns)
    if not nodes.empty:
        nodes = nodes.dropna(subset=["node_id"]).drop_duplicates(subset=["node_id"])
    if not edges.empty:
        edges = edges.dropna(subset=["source", "target"])
    nodes = add_network_metrics(nodes, edges)
    return {
        "nodes": nodes,
        "edges": edges,
        "country_collaboration": country_edges,
        "author_collaboration": author_edges,
        "topic_cooccurrence": topic_edges,
    }


def add_network_metrics(nodes: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    if nodes.empty:
        for col in ["degree", "weighted_degree", "betweenness", "pagerank", "closeness", "bridge_score"]:
            nodes[col] = pd.Series(dtype="float64")
        return nodes
    graph = nx.Graph()
    node_ids = set(nodes["node_id"].astype(str))
    for _, node in nodes.iterrows():
        graph.add_node(str(node["node_id"]))
    for _, edge in edges.iterrows():
        source = str(edge["source"])
        target = str(edge["target"])
        # Citation edges can point to external OpenAlex works that are not part
        # of the current node table. Keep those edges in exports, but exclude
        # them from centrality computation so PageRank does not balloon.
        if source in node_ids and target in node_ids:
            graph.add_edge(source, target, weight=float(edge.get("weight", 1) or 1))
    degree = dict(graph.degree())
    weighted_degree = dict(graph.degree(weight="weight"))
    if graph.number_of_nodes() <= 1500 and graph.number_of_edges() <= 10000:
        betweenness = nx.betweenness_centrality(graph, weight="weight", normalized=True)
        closeness = nx.closeness_centrality(graph)
    else:
        betweenness = {n: 0.0 for n in graph.nodes}
        closeness = {n: 0.0 for n in graph.nodes}
    if graph.number_of_edges() and graph.number_of_nodes() <= 5000 and graph.number_of_edges() <= 20000:
        pagerank = nx.pagerank(graph, weight="weight")
    else:
        pagerank = {n: 0.0 for n in graph.nodes}
    try:
        communities = nx.algorithms.community.greedy_modularity_communities(graph, weight="weight")
        community_map = {node: idx for idx, comm in enumerate(communities) for node in comm}
    except Exception:
        community_map = {n: 0 for n in graph.nodes}
    out = nodes.copy()
    out["degree"] = out["node_id"].astype(str).map(degree).fillna(0)
    out["weighted_degree"] = out["node_id"].astype(str).map(weighted_degree).fillna(0)
    out["betweenness"] = out["node_id"].astype(str).map(betweenness).fillna(0.0)
    out["closeness"] = out["node_id"].astype(str).map(closeness).fillna(0.0)
    out["pagerank"] = out["node_id"].astype(str).map(pagerank).fillna(0.0)
    out["community"] = out["node_id"].astype(str).map(community_map).fillna(-1).astype(int)
    if out["betweenness"].max() > 0:
        normalized_b = out["betweenness"] / out["betweenness"].max()
    else:
        normalized_b = 0
    if out["degree"].max() > 0:
        normalized_d = out["degree"] / out["degree"].max()
    else:
        normalized_d = 0
    out["bridge_score"] = np.asarray(normalized_b) * 0.7 + np.asarray(normalized_d) * 0.3
    return out
