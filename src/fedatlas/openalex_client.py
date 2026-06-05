from __future__ import annotations

import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any

import requests

from .config import Settings
from .utils import ensure_dir, sleep_with_backoff, write_json

LOGGER = logging.getLogger(__name__)

OPENALEX_WORKS_URL = "https://api.openalex.org/works"

WORK_SELECT_FIELDS = [
    "id",
    "doi",
    "display_name",
    "title",
    "abstract_inverted_index",
    "publication_year",
    "publication_date",
    "type",
    "language",
    "cited_by_count",
    "fwci",
    "referenced_works",
    "related_works",
    "authorships",
    "primary_location",
    "locations",
    "open_access",
    "concepts",
    "topics",
    "primary_topic",
    "keywords",
    "awards",
    "funders",
    "ids",
]


class OpenAlexClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = requests.Session()
        self.retry_max = int(settings.config.get("openalex", {}).get("retry_max", 6))
        self.backoff = float(settings.config.get("openalex", {}).get("retry_backoff_seconds", 2))

    def _params(self, query: str, year: int, cursor: str = "*") -> dict[str, Any]:
        params: dict[str, Any] = {
            "search": query,
            "filter": f"publication_year:{year},type:article|preprint|book-chapter|conference-paper|proceedings-article",
            "per-page": int(self.settings.config.get("openalex", {}).get("per_page", 100)),
            "cursor": cursor,
            "select": ",".join(WORK_SELECT_FIELDS),
        }
        if self.settings.openalex_mailto:
            params["mailto"] = self.settings.openalex_mailto
        if self.settings.openalex_api_key:
            params["api_key"] = self.settings.openalex_api_key
        return params

    def request_page(self, query: str, year: int, cursor: str = "*") -> dict[str, Any]:
        params = self._params(query, year, cursor)
        last_error: Exception | None = None
        for attempt in range(1, self.retry_max + 1):
            try:
                response = self.session.get(OPENALEX_WORKS_URL, params=params, timeout=60)
            except requests.RequestException as exc:
                last_error = exc
                LOGGER.warning("OpenAlex request error on attempt %s for query=%r year=%s: %s", attempt, query, year, exc)
                sleep_with_backoff(self.backoff, attempt)
                continue
            if response.status_code == 200:
                return response.json()
            if response.status_code in {429, 500, 502, 503, 504}:
                LOGGER.warning("OpenAlex retryable status %s on attempt %s", response.status_code, attempt)
                sleep_with_backoff(self.backoff, attempt)
                continue
            response.raise_for_status()
        detail = f": {last_error}" if last_error else ""
        raise RuntimeError(f"OpenAlex failed after {self.retry_max} retries for query={query!r}, year={year}{detail}")

    def crawl_query_year(self, query: str, year: int, remaining: int | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        records: list[dict[str, Any]] = []
        cursor = "*"
        page = 0
        raw_dir = ensure_dir(self.settings.raw_dir / "openalex" / f"year={year}")
        manifest: dict[str, Any] = {
            "query": query,
            "year": year,
            "pages": 0,
            "records": 0,
            "errors": [],
            "exhausted": False,
        }
        while cursor:
            page += 1
            try:
                payload = self.request_page(query, year, cursor)
            except Exception as exc:
                LOGGER.warning("Stopping OpenAlex batch query=%r year=%s page=%s after error: %s", query, year, page, exc)
                manifest["errors"].append({"page": page, "message": str(exc)})
                manifest["exhausted"] = False
                break
            result_records = payload.get("results", [])
            page_hash = hashlib.sha1(f"{query}-{year}-{page}".encode("utf-8")).hexdigest()[:12]
            write_json(raw_dir / f"{page_hash}.json", payload)
            for row in result_records:
                row["_fedatlas_query"] = query
                row["_fedatlas_query_year"] = year
            records.extend(result_records)
            manifest["pages"] = page
            manifest["records"] = len(records)
            if remaining is not None and len(records) >= remaining:
                records = records[:remaining]
                manifest["exhausted"] = False
                break
            next_cursor = payload.get("meta", {}).get("next_cursor")
            if not next_cursor or not result_records:
                manifest["exhausted"] = True
                break
            cursor = next_cursor
        return records, manifest


def query_year_batches(settings: Settings, broad_sample: bool = False) -> list[tuple[int, str]]:
    years = list(range(settings.start_year, settings.end_year + 1))
    if broad_sample:
        return [(year, query) for query in settings.queries for year in years]
    return [(year, query) for year in years for query in settings.queries]


def crawl_openalex(settings: Settings, sample_size: int | None = None) -> list[dict[str, Any]]:
    client = OpenAlexClient(settings)
    max_papers = sample_size if sample_size is not None else settings.max_papers
    limit = None if max_papers == 0 else int(max_papers)
    batches = query_year_batches(settings, broad_sample=limit is not None)
    per_batch_limit = None if limit is None else max(1, math.ceil(limit / max(1, len(batches))))
    all_records: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for year, query in batches:
        remaining = None if limit is None else max(0, min(per_batch_limit, limit - len(all_records)))
        if remaining == 0:
            break
        LOGGER.info("Crawling OpenAlex query=%r year=%s", query, year)
        records, manifest = client.crawl_query_year(query, year, remaining=remaining)
        manifest["batch_limit"] = remaining
        all_records.extend(records)
        manifests.append(manifest)
    ensure_dir(settings.interim_dir)
    jsonl_path = settings.interim_dir / "openalex_works.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as handle:
        for row in all_records:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_json(settings.manifest_dir / "openalex_manifest.json", {"batches": manifests, "records": len(all_records)})
    return all_records


def load_cached_openalex(settings: Settings) -> list[dict[str, Any]]:
    path = settings.interim_dir / "openalex_works.jsonl"
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records
