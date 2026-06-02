from __future__ import annotations

import gzip
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import pandas as pd

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - exercised only when rapidfuzz is absent
    fuzz = None


DOI_PREFIX_RE = re.compile(r"^(https?://(dx\.)?doi\.org/|doi:)", re.I)
ARXIV_RE = re.compile(
    r"(?:arxiv[:/ ]|abs/|pdf/)?(?P<id>(?:\d{4}\.\d{4,5})(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)",
    re.I,
)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def normalize_doi(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    doi = str(value).strip()
    if not doi:
        return None
    doi = DOI_PREFIX_RE.sub("", doi).strip().strip(".").lower()
    return doi or None


def normalize_title(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).lower()
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_arxiv_id(*values: Any) -> str | None:
    for value in values:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            continue
        match = ARXIV_RE.search(str(value))
        if match:
            return match.group("id").lower().replace(".pdf", "")
    return None


def reconstruct_abstract(index: dict[str, list[int]] | None) -> str | None:
    if not index:
        return None
    positions: list[tuple[int, str]] = []
    for token, offsets in index.items():
        for offset in offsets:
            positions.append((int(offset), token))
    if not positions:
        return None
    return " ".join(token for _, token in sorted(positions))


def title_similarity(a: Any, b: Any) -> float:
    na = normalize_title(a)
    nb = normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if fuzz is not None:
        token_score = float(fuzz.token_set_ratio(na, nb)) / 100.0
        aset = set(na.split())
        bset = set(nb.split())
        containment = len(aset & bset) / max(1, min(len(aset), len(bset)))
        return max(token_score, containment)
    aset = set(na.split())
    bset = set(nb.split())
    jaccard = len(aset & bset) / max(1, len(aset | bset))
    containment = len(aset & bset) / max(1, min(len(aset), len(bset)))
    return max(jaccard, containment)


def parse_github_url(url: Any) -> tuple[str | None, str | None]:
    if url is None or (isinstance(url, float) and pd.isna(url)):
        return None, None
    raw = str(url).strip()
    if not raw:
        return None, None
    if raw.startswith("git@github.com:"):
        raw = "https://github.com/" + raw.split(":", 1)[1]
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return None, None
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        return None, None
    owner = parts[0]
    repo = re.sub(r"\.git$", "", parts[1])
    if not owner or not repo:
        return None, None
    return owner, repo


def canonical_repo_url(owner: str | None, repo: str | None) -> str | None:
    if not owner or not repo:
        return None
    return f"https://github.com/{owner}/{repo}"


def read_json(path: str | Path) -> Any:
    p = Path(path)
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with open(p, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False, default=str)


def read_table(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    if p.suffix == ".parquet":
        return pd.read_parquet(p)
    if p.suffix == ".json":
        return pd.read_json(p)
    return pd.read_csv(p)


def _parquet_safe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    nested_types = (dict, list, tuple, set)
    for col in out.columns:
        if out[col].dtype != "object":
            continue
        has_nested = out[col].map(lambda value: isinstance(value, nested_types)).any()
        if has_nested:
            out[col] = out[col].map(
                lambda value: json.dumps(value, ensure_ascii=False, default=str)
                if isinstance(value, nested_types)
                else value
            )
    return out


def write_table(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    if p.suffix == ".parquet":
        _parquet_safe(df).to_parquet(p, index=False)
    elif p.suffix == ".json":
        df.to_json(p, orient="records", indent=2, force_ascii=False)
    else:
        df.to_csv(p, index=False)


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def chunked(values: list[Any], size: int) -> Iterable[list[Any]]:
    for i in range(0, len(values), size):
        yield values[i : i + size]


def sleep_with_backoff(base_seconds: float, attempt: int) -> None:
    time.sleep(base_seconds * (2 ** max(0, attempt - 1)))


def flatten_list(value: Any) -> list[Any]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return value
    return [value]
