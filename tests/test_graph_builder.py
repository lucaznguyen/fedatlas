import pandas as pd

from fedatlas.graph_builder import author_collaboration_edges, build_graph_tables, country_collaboration_edges, topic_cooccurrence_edges


def test_country_pair_collaboration_edge_creation():
    pc = pd.DataFrame([
        {"work_id": "W1", "country_code": "US"},
        {"work_id": "W1", "country_code": "GB"},
        {"work_id": "W2", "country_code": "US"},
    ])
    edges = country_collaboration_edges(pc)
    assert len(edges) == 1
    assert set(edges.iloc[0][["source", "target"]]) == {"GB", "US"}


def test_author_coauthor_edge_creation():
    pa = pd.DataFrame([
        {"work_id": "W1", "author_id": "A1"},
        {"work_id": "W1", "author_id": "A2"},
    ])
    edges = author_collaboration_edges(pa)
    assert len(edges) == 1
    assert edges.iloc[0]["weight"] == 1


def test_topic_cooccurrence_edge_creation():
    pt = pd.DataFrame([
        {"work_id": "W1", "topic_group": "Privacy"},
        {"work_id": "W1", "topic_group": "Security & Robustness"},
    ])
    edges = topic_cooccurrence_edges(pt)
    assert len(edges) == 1


def test_graph_node_edge_schema_empty_safe():
    graph = build_graph_tables({"papers": pd.DataFrame(), "authors": pd.DataFrame()})
    assert "nodes" in graph
    assert "edges" in graph
