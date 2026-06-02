import pandas as pd

from fedatlas.metrics import paper_code_metrics, research_to_code_scores


def test_research_to_code_score_calculation():
    papers = pd.DataFrame([
        {"work_id": "W1", "publication_year": 2020, "topic_group": "Privacy", "venue_name": "Venue", "cited_by_count": 10, "title": "A", "quality_label": "Q1"},
        {"work_id": "W2", "publication_year": 2020, "topic_group": "Privacy", "venue_name": "Venue", "cited_by_count": 5, "title": "B", "quality_label": "Q1"},
    ])
    links = pd.DataFrame([{"work_id": "W1", "repo_owner": "o", "repo_name": "r"}])
    repos = pd.DataFrame([{"repo_full_name": "o/r", "stargazers_count": 10, "forks_count": 2, "pushed_at": "2026-01-01T00:00:00Z", "code_score": 3.0}])
    paper_metrics = paper_code_metrics(papers, links, repos)
    rtc = research_to_code_scores(papers, paper_metrics)
    row = rtc[(rtc["group_type"] == "topic") & (rtc["group_value"] == "Privacy")].iloc[0]
    assert row["research_to_code_score"] == 0.5


def test_paper_code_metrics_handles_missing_repo_dates():
    papers = pd.DataFrame([
        {"work_id": "W1", "publication_year": 2020, "topic_group": "Privacy", "venue_name": "Venue", "cited_by_count": 10, "title": "A", "quality_label": "Q1"},
    ])
    links = pd.DataFrame([
        {"work_id": "W1", "repo_owner": "o", "repo_name": "r1"},
        {"work_id": "W1", "repo_owner": "o", "repo_name": "r2"},
    ])
    repos = pd.DataFrame([
        {"repo_full_name": "o/r1", "stargazers_count": "5", "forks_count": "1", "pushed_at": "2026-01-01T00:00:00Z", "code_score": "2.0"},
        {"repo_full_name": "o/r2", "stargazers_count": pd.NA, "forks_count": pd.NA, "pushed_at": pd.NA, "code_score": pd.NA},
    ])
    out = paper_code_metrics(papers, links, repos)
    assert out.iloc[0]["has_code"]
    assert out.iloc[0]["repo_count_per_paper"] == 2
    assert out.iloc[0]["total_stars_per_paper"] == 5
