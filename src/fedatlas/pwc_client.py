from __future__ import annotations

import gzip
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
import requests

from .config import Settings
from .utils import ensure_dir, read_json, write_json

LOGGER = logging.getLogger(__name__)

LEGACY_PWC_URLS = {
    "papers_with_abstracts": "https://production-media.paperswithcode.com/about/papers-with-abstracts.json.gz",
    "links_between_papers_and_code": "https://production-media.paperswithcode.com/about/links-between-papers-and-code.json.gz",
}

HF_DATASETS = {
    "papers_with_abstracts": "pwc-archive/papers-with-abstracts",
    "links_between_papers_and_code": "pwc-archive/links-between-paper-and-code",
}

PWC_PAPER_COLUMNS = [
    "paper_url",
    "arxiv_id",
    "title",
    "abstract",
    "url_abs",
    "url_pdf",
    "date",
    "conference",
    "proceeding",
]

PWC_LINK_COLUMNS = [
    "paper_url",
    "paper_title",
    "paper_arxiv_id",
    "paper_url_abs",
    "paper_url_pdf",
    "repo_url",
    "is_official",
    "mentioned_in_paper",
    "mentioned_in_github",
    "framework",
]


def download_file(url: str, path: Path, force: bool = False) -> Path:
    ensure_dir(path.parent)
    if path.exists() and not force:
        return path
    LOGGER.info("Downloading %s", url)
    headers = {"User-Agent": "FedAtlas/0.1 research data pipeline"}
    with requests.get(url, stream=True, timeout=120, headers=headers) as response:
        response.raise_for_status()
        with open(path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return path


def _hf_dataset_files(repo_id: str) -> list[str]:
    url = f"https://huggingface.co/api/datasets/{repo_id}"
    response = requests.get(url, timeout=60, headers={"User-Agent": "FedAtlas/0.1 research data pipeline"})
    response.raise_for_status()
    payload = response.json()
    return sorted(
        sibling["rfilename"]
        for sibling in payload.get("siblings", [])
        if str(sibling.get("rfilename", "")).endswith(".parquet")
    )


def _download_hf_dataset(repo_id: str, out_dir: Path, force: bool = False) -> list[Path]:
    paths: list[Path] = []
    ensure_dir(out_dir)
    for filename in _hf_dataset_files(repo_id):
        url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{filename}"
        path = out_dir / Path(filename).name
        paths.append(download_file(url, path, force=force))
    return paths


def _download_legacy_json(name: str, out_dir: Path, force: bool = False) -> Path | None:
    url = LEGACY_PWC_URLS[name]
    try:
        return download_file(url, out_dir / f"{name}.json.gz", force=force)
    except Exception as exc:
        LOGGER.warning("Could not download legacy Papers With Code dump %s: %s", name, exc)
        return None


def download_pwc(settings: Settings) -> dict[str, Path]:
    out_dir = ensure_dir(settings.raw_dir / "paperswithcode")
    paths: dict[str, Path | list[Path]] = {}
    for name, repo_id in HF_DATASETS.items():
        try:
            dataset_dir = out_dir / name
            hf_paths = _download_hf_dataset(repo_id, dataset_dir, force=settings.force_refresh)
            if hf_paths:
                paths[name] = hf_paths
                continue
        except Exception as exc:
            LOGGER.warning("Could not download Hugging Face Papers With Code dataset %s: %s", repo_id, exc)
        legacy_path = _download_legacy_json(name, out_dir, force=settings.force_refresh)
        if legacy_path:
            paths[name] = legacy_path
    write_json(settings.manifest_dir / "pwc_manifest.json", {k: [str(p) for p in v] if isinstance(v, list) else str(v) for k, v in paths.items()})
    return {k: v[0] if isinstance(v, list) and v else v for k, v in paths.items() if v}


def _read_parquet_dir(path: Path, columns: list[str]) -> pd.DataFrame:
    files = sorted(path.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
    frames: list[pd.DataFrame] = []
    for file in files:
        available = set(pq.ParquetFile(file).schema_arrow.names)
        selected = [col for col in columns if col in available]
        if selected:
            frames.append(pd.read_parquet(file, columns=selected))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _read_gz_json(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        import json

        return json.load(handle)


def load_pwc(settings: Settings) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = settings.raw_dir / "paperswithcode"
    parquet_papers = _read_parquet_dir(base / "papers_with_abstracts", PWC_PAPER_COLUMNS)
    parquet_links = _read_parquet_dir(base / "links_between_papers_and_code", PWC_LINK_COLUMNS)
    if not parquet_papers.empty and not parquet_links.empty:
        return parquet_papers, parquet_links

    papers_path = base / "papers_with_abstracts.json.gz"
    links_path = base / "links_between_papers_and_code.json.gz"
    if not papers_path.exists() or not links_path.exists():
        return pd.DataFrame(), pd.DataFrame()
    papers = pd.DataFrame(_read_gz_json(papers_path))
    links = pd.DataFrame(_read_gz_json(links_path))
    return papers, links
