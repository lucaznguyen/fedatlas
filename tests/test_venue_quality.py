from pathlib import Path

import pandas as pd

from fedatlas.venue_quality import import_quality_csv, load_venue_quality, tag_venue_quality


def test_venue_quality_matching(tmp_path: Path):
    csv = tmp_path / "quality.csv"
    csv.write_text("venue_id,venue_name,venue_type,issn,issn_l,eissn,quality_label,quality_source,source_year,notes\nS1,Test Journal,journal,,1234-5678,,Q1,manual,2025,\n", encoding="utf-8")
    quality = load_venue_quality(csv)
    papers = pd.DataFrame([{"work_id": "W1", "venue_id": "S1", "venue_name": "Test Journal", "issn_l": "1234-5678"}])
    venues = pd.DataFrame([{"venue_id": "S1", "venue_name": "Test Journal", "issn_l": "1234-5678"}])
    tagged_papers, tagged_venues = tag_venue_quality(papers, venues, quality)
    assert tagged_papers.iloc[0]["quality_label"] == "Q1"
    assert tagged_venues.iloc[0]["quality_label"] == "Q1"


def test_import_quality_csv_invalid_label_to_unknown(tmp_path: Path):
    source = tmp_path / "source.csv"
    output = tmp_path / "out.csv"
    source.write_text("venue_name,quality_label\nVenue,B\n", encoding="utf-8")
    out = import_quality_csv(source, output)
    assert out.iloc[0]["quality_label"] == "Unknown"
