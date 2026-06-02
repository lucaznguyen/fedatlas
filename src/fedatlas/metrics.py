from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd


def compute_code_scores(repos: pd.DataFrame, today: datetime | None = None) -> pd.DataFrame:
    if repos.empty:
        return repos.assign(code_score=pd.Series(dtype="float64"))
    out = repos.copy()
    today = today or datetime.now(timezone.utc)
    pushed_source = out["pushed_at"] if "pushed_at" in out.columns else pd.Series(pd.NaT, index=out.index)
    pushed = pd.to_datetime(pushed_source, errors="coerce", utc=True)
    recency_days = (today - pushed).dt.days
    out["repo_activity_recency_days"] = recency_days
    stars = pd.to_numeric(out.get("stargazers_count", 0), errors="coerce").fillna(0)
    forks = pd.to_numeric(out.get("forks_count", 0), errors="coerce").fillna(0)
    contributors = pd.to_numeric(out.get("contributors_count", 0), errors="coerce").fillna(0) if "contributors_count" in out else 0
    activity_bonus = np.where(recency_days <= 365, 0.5, np.where(recency_days <= 730, 0.25, 0.0))
    activity_bonus = np.where(recency_days.isna(), 0.0, activity_bonus)
    out["code_score"] = np.log1p(stars) + 0.5 * np.log1p(forks) + 0.25 * np.log1p(contributors) + activity_bonus
    return out


def paper_code_metrics(papers: pd.DataFrame, code_links: pd.DataFrame, repos: pd.DataFrame) -> pd.DataFrame:
    if papers.empty:
        return pd.DataFrame()
    out = papers[["work_id", "publication_year", "title", "cited_by_count", "topic_group", "venue_name", "quality_label"]].copy()
    if code_links.empty:
        out["has_code"] = False
        out["repo_count_per_paper"] = 0
        out["total_stars_per_paper"] = 0
        out["total_forks_per_paper"] = 0
        out["total_contributors_per_paper"] = 0
        out["latest_repo_push_date"] = pd.NaT
        out["repo_activity_recency_days"] = pd.NA
        out["code_score"] = 0.0
        return out
    repo_meta = repos.copy()
    if "repo_full_name" not in repo_meta and {"repo_owner", "repo_name"}.issubset(repo_meta.columns):
        repo_meta["repo_full_name"] = repo_meta["repo_owner"].astype(str) + "/" + repo_meta["repo_name"].astype(str)
    for col in ["stargazers_count", "forks_count", "code_score"]:
        if col not in repo_meta.columns:
            repo_meta[col] = 0
        repo_meta[col] = pd.to_numeric(repo_meta[col], errors="coerce").fillna(0)
    if "pushed_at" not in repo_meta.columns:
        repo_meta["pushed_at"] = pd.NaT
    repo_meta["pushed_at"] = pd.to_datetime(repo_meta["pushed_at"], errors="coerce", utc=True)
    links = code_links.copy()
    links["repo_full_name"] = links["repo_owner"].astype(str) + "/" + links["repo_name"].astype(str)
    joined = links.merge(repo_meta, on="repo_full_name", how="left", suffixes=("", "_repo"))
    grouped = joined.groupby("work_id").agg(
        repo_count_per_paper=("repo_full_name", "nunique"),
        total_stars_per_paper=("stargazers_count", "sum"),
        total_forks_per_paper=("forks_count", "sum"),
        latest_repo_push_date=("pushed_at", "max"),
        code_score=("code_score", "sum"),
    ).reset_index()
    out = out.merge(grouped, on="work_id", how="left")
    out["has_code"] = out["repo_count_per_paper"].fillna(0) > 0
    for col in ["repo_count_per_paper", "total_stars_per_paper", "total_forks_per_paper", "code_score"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    out["latest_repo_push_date"] = pd.to_datetime(out["latest_repo_push_date"], errors="coerce", utc=True)
    today = datetime.now(timezone.utc)
    out["repo_activity_recency_days"] = (today - out["latest_repo_push_date"]).dt.days
    out["total_contributors_per_paper"] = 0
    return out


def research_to_code_scores(papers: pd.DataFrame, paper_metrics: pd.DataFrame, paper_countries: pd.DataFrame | None = None) -> pd.DataFrame:
    if papers.empty:
        return pd.DataFrame(columns=["group_type", "group_value", "year", "total_papers", "papers_with_code", "research_to_code_score"])
    metrics = paper_metrics[["work_id", "has_code"]].copy() if not paper_metrics.empty else pd.DataFrame({"work_id": papers["work_id"], "has_code": False})
    base = papers.merge(metrics, on="work_id", how="left")
    base["has_code"] = base["has_code"].fillna(False)
    groups = {
        "topic": "topic_group",
        "venue": "venue_name",
        "year": "publication_year",
    }
    rows = []
    for group_type, col in groups.items():
        if col is None or col not in base.columns:
            continue
        group_cols = [col] if col == "publication_year" else [col, "publication_year"]
        temp = base.dropna(subset=[col]).groupby(group_cols).agg(
            total_papers=("work_id", "nunique"),
            papers_with_code=("has_code", "sum"),
        ).reset_index()
        temp["group_type"] = group_type
        temp["group_value"] = temp[col].astype(str)
        temp["year"] = temp["publication_year"] if "publication_year" in temp.columns else temp[col]
        temp["research_to_code_score"] = temp["papers_with_code"] / temp["total_papers"].replace(0, np.nan)
        rows.append(temp[["group_type", "group_value", "year", "total_papers", "papers_with_code", "research_to_code_score"]])
    if paper_countries is not None and not paper_countries.empty:
        country_base = paper_countries[["work_id", "country_code", "country_name"]].drop_duplicates().merge(
            base[["work_id", "publication_year", "has_code"]],
            on="work_id",
            how="left",
        )
        country_base["country_label"] = country_base["country_name"].fillna(country_base["country_code"])
        temp = country_base.dropna(subset=["country_label"]).groupby(["country_label", "publication_year"]).agg(
            total_papers=("work_id", "nunique"),
            papers_with_code=("has_code", "sum"),
        ).reset_index()
        if not temp.empty:
            temp["group_type"] = "country"
            temp["group_value"] = temp["country_label"].astype(str)
            temp["year"] = temp["publication_year"]
            temp["research_to_code_score"] = temp["papers_with_code"] / temp["total_papers"].replace(0, np.nan)
            rows.append(temp[["group_type", "group_value", "year", "total_papers", "papers_with_code", "research_to_code_score"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["group_type", "group_value", "year", "total_papers", "papers_with_code", "research_to_code_score"])


def metrics_summary(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    papers = tables.get("papers", pd.DataFrame())
    repos = tables.get("repos", pd.DataFrame())
    code_links = tables.get("paper_code_links", pd.DataFrame())
    rows = [
        ("papers", len(papers)),
        ("authors", len(tables.get("authors", pd.DataFrame()))),
        ("institutions", len(tables.get("institutions", pd.DataFrame()))),
        ("countries", len(tables.get("countries", pd.DataFrame()))),
        ("venues", len(tables.get("venues", pd.DataFrame()))),
        ("topics", len(tables.get("topics", pd.DataFrame()))),
        ("github_repos", len(repos)),
        ("pwc_matches", len(code_links)),
        ("total_citations", pd.to_numeric(papers.get("cited_by_count", 0), errors="coerce").fillna(0).sum() if not papers.empty else 0),
        ("total_github_stars", pd.to_numeric(repos.get("stargazers_count", 0), errors="coerce").fillna(0).sum() if not repos.empty else 0),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])
