from __future__ import annotations

from pathlib import Path

import pandas as pd

from .utils import normalize_title, write_table

ALLOWED_QUALITY = {"A*", "A", "Q1", "Unknown", "Not_Target"}


def load_venue_quality(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame(columns=["venue_id", "venue_name", "venue_type", "issn", "issn_l", "eissn", "quality_label", "quality_source", "source_year", "notes"])
    df = pd.read_csv(p, dtype=str).fillna("")
    if "quality_label" not in df.columns:
        df["quality_label"] = "Unknown"
    df["quality_label"] = df["quality_label"].where(df["quality_label"].isin(ALLOWED_QUALITY), "Unknown")
    df["venue_name_norm"] = df.get("venue_name", "").map(normalize_title)
    return df


def tag_venue_quality(papers: pd.DataFrame, venues: pd.DataFrame, quality: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    papers_out = papers.copy()
    venues_out = venues.copy()
    if papers_out.empty:
        papers_out["quality_label"] = pd.Series(dtype="object")
        return papers_out, venues_out
    if quality.empty:
        papers_out["quality_label"] = "Unknown"
        venues_out["quality_label"] = "Unknown"
        return papers_out, venues_out

    q_by_id = quality.dropna(subset=["venue_id"]).set_index("venue_id")["quality_label"].to_dict() if "venue_id" in quality else {}
    q_by_issn = quality.dropna(subset=["issn_l"]).set_index("issn_l")["quality_label"].to_dict() if "issn_l" in quality else {}
    q_by_name = quality.dropna(subset=["venue_name_norm"]).set_index("venue_name_norm")["quality_label"].to_dict() if "venue_name_norm" in quality else {}

    def label(row: pd.Series) -> str:
        for key, mapping in [
            (row.get("venue_id"), q_by_id),
            (row.get("issn_l"), q_by_issn),
            (normalize_title(row.get("venue_name")), q_by_name),
        ]:
            if key and key in mapping and mapping[key]:
                return mapping[key]
        return "Unknown"

    papers_out["quality_label"] = papers_out.apply(label, axis=1)
    if not venues_out.empty:
        venues_out["quality_label"] = venues_out.apply(label, axis=1)
    return papers_out, venues_out


def import_quality_csv(input_path: str | Path, output_path: str | Path) -> pd.DataFrame:
    source = pd.read_csv(input_path, dtype=str).fillna("")
    canonical = ["venue_id", "venue_name", "venue_type", "issn", "issn_l", "eissn", "quality_label", "quality_source", "source_year", "notes"]
    out = pd.DataFrame()
    for col in canonical:
        if col in source.columns:
            out[col] = source[col]
        else:
            out[col] = ""
    out["quality_label"] = out["quality_label"].where(out["quality_label"].isin(ALLOWED_QUALITY), "Unknown")
    write_table(out, output_path)
    return out
