from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd

from .schemas import SCHEMAS, ensure_columns
from .topic_classifier import classify_topic
from .utils import extract_arxiv_id, normalize_doi, normalize_title, reconstruct_abstract
from .venue_quality import load_venue_quality, tag_venue_quality

LOGGER = logging.getLogger(__name__)


def _source_from_location(location: dict[str, Any] | None) -> dict[str, Any]:
    if not location:
        return {}
    source = location.get("source") or {}
    return source or {}


def _country_name(country_code: str | None, institution: dict[str, Any] | None = None) -> str | None:
    if institution:
        geo = institution.get("geo") or {}
        if geo.get("country"):
            return geo.get("country")
    return country_code


def deduplicate_works(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen_work: dict[str, dict[str, Any]] = {}
    seen_doi: dict[str, str] = {}
    seen_arxiv: dict[str, str] = {}
    seen_title: dict[str, str] = {}
    removed = 0

    for rec in records:
        work_id = rec.get("id")
        doi = normalize_doi(rec.get("doi") or (rec.get("ids") or {}).get("doi"))
        arxiv = extract_arxiv_id(json.dumps(rec.get("ids", {})), rec.get("doi"), rec.get("display_name"))
        title_norm = normalize_title(rec.get("display_name") or rec.get("title"))
        key = None
        confidence = 1.0
        source = None
        if work_id and work_id in seen_work:
            key = work_id
            source = "work_id"
        elif doi and doi in seen_doi:
            key = seen_doi[doi]
            source = "doi"
        elif arxiv and arxiv in seen_arxiv:
            key = seen_arxiv[arxiv]
            source = "arxiv"
        elif title_norm and title_norm in seen_title:
            key = seen_title[title_norm]
            source = "title_exact"
            confidence = 0.95

        if key and key in seen_work:
            existing = seen_work[key]
            ids = set(existing.get("_merge_source_ids", []))
            ids.add(work_id or doi or title_norm)
            existing["_merge_source_ids"] = sorted(ids)
            existing["_dedup_confidence"] = max(float(existing.get("_dedup_confidence", 0.0)), confidence)
            existing["_dedup_source"] = source
            removed += 1
            continue

        canonical = work_id or doi or arxiv or title_norm
        rec["_merge_source_ids"] = [v for v in [work_id, doi, arxiv] if v]
        rec["_dedup_confidence"] = confidence
        seen_work[canonical] = rec
        if work_id:
            seen_work[work_id] = rec
        if doi:
            seen_doi[doi] = canonical
        if arxiv:
            seen_arxiv[arxiv] = canonical
        if title_norm:
            seen_title[title_norm] = canonical
    unique = []
    emitted = set()
    for rec in seen_work.values():
        obj_id = id(rec)
        if obj_id not in emitted:
            unique.append(rec)
            emitted.add(obj_id)
    return unique, removed


def normalize_openalex(records: list[dict[str, Any]], venue_quality_path: str | None = None) -> dict[str, pd.DataFrame]:
    records, duplicate_removed = deduplicate_works(records)
    paper_rows: list[dict[str, Any]] = []
    author_rows: list[dict[str, Any]] = []
    institution_rows: list[dict[str, Any]] = []
    country_rows: list[dict[str, Any]] = []
    venue_rows: list[dict[str, Any]] = []
    topic_rows: list[dict[str, Any]] = []
    paper_author_rows: list[dict[str, Any]] = []
    paper_institution_rows: list[dict[str, Any]] = []
    paper_country_rows: list[dict[str, Any]] = []
    paper_topic_rows: list[dict[str, Any]] = []
    reference_rows: list[dict[str, Any]] = []

    for rec in records:
        work_id = rec.get("id")
        ids = rec.get("ids") or {}
        title = rec.get("display_name") or rec.get("title")
        abstract = reconstruct_abstract(rec.get("abstract_inverted_index"))
        source = _source_from_location(rec.get("primary_location"))
        openalex_topics = rec.get("topics") or []
        topic_group, topic_method = classify_topic(title, abstract, openalex_topics)
        doi = normalize_doi(rec.get("doi") or ids.get("doi"))
        arxiv_id = extract_arxiv_id(json.dumps(ids), rec.get("doi"), rec.get("display_name"))
        venue_id = source.get("id")
        paper_rows.append({
            "work_id": work_id,
            "doi": doi,
            "title": title,
            "abstract": abstract,
            "publication_year": rec.get("publication_year"),
            "publication_date": rec.get("publication_date"),
            "type": rec.get("type"),
            "language": rec.get("language"),
            "cited_by_count": rec.get("cited_by_count", 0),
            "fwci": rec.get("fwci"),
            "venue_id": venue_id,
            "venue_name": source.get("display_name"),
            "venue_type": source.get("type"),
            "publisher": source.get("host_organization_name") or source.get("publisher"),
            "issn_l": source.get("issn_l"),
            "is_oa": (rec.get("open_access") or {}).get("is_oa"),
            "landing_page_url": (rec.get("primary_location") or {}).get("landing_page_url"),
            "openalex_url": work_id,
            "doi_url": f"https://doi.org/{doi}" if doi else None,
            "arxiv_id": arxiv_id,
            "topic_group": topic_group,
            "topic_method": topic_method,
            "merge_source_ids": json.dumps(rec.get("_merge_source_ids", [])),
            "dedup_confidence": rec.get("_dedup_confidence", 1.0),
        })
        if venue_id or source.get("display_name"):
            venue_rows.append({
                "venue_id": venue_id,
                "venue_name": source.get("display_name"),
                "venue_type": source.get("type"),
                "publisher": source.get("host_organization_name") or source.get("publisher"),
                "issn_l": source.get("issn_l"),
            })
        for ref in rec.get("referenced_works") or []:
            reference_rows.append({"work_id": work_id, "referenced_work_id": ref})
        for pos, authorship in enumerate(rec.get("authorships") or [], start=1):
            author = authorship.get("author") or {}
            author_id = author.get("id")
            author_rows.append({"author_id": author_id, "author_name": author.get("display_name"), "orcid": author.get("orcid")})
            paper_author_rows.append({
                "work_id": work_id,
                "author_id": author_id,
                "author_name": author.get("display_name"),
                "author_position": authorship.get("author_position"),
                "position": pos,
            })
            for inst in authorship.get("institutions") or []:
                institution_rows.append({
                    "institution_id": inst.get("id"),
                    "institution_name": inst.get("display_name"),
                    "country_code": inst.get("country_code"),
                    "country_name": _country_name(inst.get("country_code"), inst),
                })
                paper_institution_rows.append({
                    "work_id": work_id,
                    "institution_id": inst.get("id"),
                    "institution_name": inst.get("display_name"),
                })
                if inst.get("country_code"):
                    country_rows.append({"country_code": inst.get("country_code"), "country_name": _country_name(inst.get("country_code"), inst)})
                    paper_country_rows.append({"work_id": work_id, "country_code": inst.get("country_code"), "country_name": _country_name(inst.get("country_code"), inst)})
        topic_candidates = openalex_topics or ([rec.get("primary_topic")] if rec.get("primary_topic") else [])
        for topic in topic_candidates:
            if not topic:
                continue
            topic_id = topic.get("id")
            topic_name = topic.get("display_name")
            subfield = topic.get("subfield") or {}
            field = topic.get("field") or {}
            domain = topic.get("domain") or {}
            topic_rows.append({
                "topic_id": topic_id,
                "topic_name": topic_name,
                "subfield": subfield.get("display_name"),
                "field": field.get("display_name"),
                "domain": domain.get("display_name"),
            })
            paper_topic_rows.append({
                "work_id": work_id,
                "topic_id": topic_id,
                "topic_name": topic_name,
                "topic_group": topic_group,
                "score": topic.get("score"),
            })
        if not topic_candidates:
            paper_topic_rows.append({"work_id": work_id, "topic_id": topic_group, "topic_name": topic_group, "topic_group": topic_group, "score": 1.0})
            topic_rows.append({"topic_id": topic_group, "topic_name": topic_group, "subfield": None, "field": None, "domain": None})

    tables = {
        "papers": pd.DataFrame(paper_rows),
        "authors": pd.DataFrame(author_rows).drop_duplicates(subset=["author_id"], keep="first") if author_rows else pd.DataFrame(),
        "institutions": pd.DataFrame(institution_rows).drop_duplicates(subset=["institution_id"], keep="first") if institution_rows else pd.DataFrame(),
        "countries": pd.DataFrame(country_rows).drop_duplicates(subset=["country_code"], keep="first") if country_rows else pd.DataFrame(),
        "venues": pd.DataFrame(venue_rows).drop_duplicates(subset=["venue_id", "venue_name"], keep="first") if venue_rows else pd.DataFrame(),
        "topics": pd.DataFrame(topic_rows).drop_duplicates(subset=["topic_id", "topic_name"], keep="first") if topic_rows else pd.DataFrame(),
        "paper_authors": pd.DataFrame(paper_author_rows).drop_duplicates(),
        "paper_institutions": pd.DataFrame(paper_institution_rows).drop_duplicates(),
        "paper_countries": pd.DataFrame(paper_country_rows).drop_duplicates(),
        "paper_topics": pd.DataFrame(paper_topic_rows).drop_duplicates(),
        "paper_references": pd.DataFrame(reference_rows).drop_duplicates(),
    }

    if venue_quality_path:
        quality = load_venue_quality(venue_quality_path)
        tables["papers"], tables["venues"] = tag_venue_quality(tables["papers"], tables["venues"], quality)
        tables["quality_venues"] = quality.drop(columns=[c for c in ["venue_name_norm"] if c in quality.columns], errors="ignore")
    else:
        tables["papers"]["quality_label"] = "Unknown"
        tables["venues"]["quality_label"] = "Unknown"
        tables["quality_venues"] = pd.DataFrame()
    for name, cols in SCHEMAS.items():
        if name in tables:
            tables[name] = ensure_columns(tables[name], cols)
    tables["metrics_summary"] = pd.DataFrame([
        {"metric": "duplicates_removed", "value": duplicate_removed},
        {"metric": "normalized_papers", "value": len(tables["papers"])},
    ])
    return tables
