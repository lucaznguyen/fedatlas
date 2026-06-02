from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


SCHEMAS: dict[str, list[str]] = {
    "papers": [
        "work_id",
        "doi",
        "title",
        "abstract",
        "publication_year",
        "publication_date",
        "type",
        "language",
        "cited_by_count",
        "venue_id",
        "venue_name",
        "venue_type",
        "publisher",
        "is_oa",
        "landing_page_url",
        "openalex_url",
        "doi_url",
        "arxiv_id",
        "topic_group",
        "quality_label",
        "merge_source_ids",
        "dedup_confidence",
    ],
    "authors": ["author_id", "author_name", "orcid"],
    "institutions": ["institution_id", "institution_name", "country_code", "country_name"],
    "countries": ["country_code", "country_name"],
    "venues": ["venue_id", "venue_name", "venue_type", "publisher", "issn_l", "quality_label"],
    "topics": ["topic_id", "topic_name", "subfield", "field", "domain"],
    "paper_authors": ["work_id", "author_id", "author_name", "author_position", "position"],
    "paper_institutions": ["work_id", "institution_id", "institution_name"],
    "paper_countries": ["work_id", "country_code", "country_name"],
    "paper_topics": ["work_id", "topic_id", "topic_name", "topic_group", "score"],
    "paper_references": ["work_id", "referenced_work_id"],
    "paper_code_links": ["work_id", "pwc_paper_id", "pwc_title", "repo_url", "repo_owner", "repo_name", "is_official", "match_method", "match_confidence", "source_method"],
    "repos": ["repo_full_name", "repo_url", "repo_owner", "repo_name", "stargazers_count", "forks_count", "language", "license", "topics", "pushed_at", "code_score"],
    "contributors": ["contributor_id", "login", "type", "avatar_url", "html_url"],
    "repo_contributors": ["repo_full_name", "contributor_id", "login", "contributions"],
    "quality_venues": ["venue_id", "venue_name", "venue_type", "issn", "issn_l", "eissn", "quality_label", "quality_source", "source_year", "notes"],
    "country_collaboration": ["source", "target", "weight", "year"],
    "author_collaboration": ["source", "target", "weight", "year"],
    "topic_cooccurrence": ["source", "target", "weight", "year"],
    "metrics_summary": ["metric", "value"],
    "research_to_code": ["group_type", "group_value", "year", "total_papers", "papers_with_code", "research_to_code_score"],
}


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def required_columns(table_name: str) -> list[str]:
    return SCHEMAS.get(table_name, [])


def validate_columns(table_name: str, df: pd.DataFrame) -> ValidationResult:
    required = required_columns(table_name)
    missing = [col for col in required if col not in df.columns]
    return ValidationResult(ok=not missing, errors=[f"{table_name}: missing columns {missing}"] if missing else [], warnings=[])


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA
    return out[columns + [c for c in out.columns if c not in columns]]


def fail_if_production_empty(table_name: str, df: pd.DataFrame, production: bool = True) -> None:
    if production and df.empty:
        raise ValueError(f"Production mode produced empty required table: {table_name}")
