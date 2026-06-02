import json
from pathlib import Path

from fedatlas.normalize import normalize_openalex
from fedatlas.utils import normalize_doi, reconstruct_abstract


def test_reconstruct_abstract_inverted_index():
    assert reconstruct_abstract({"hello": [1], "world": [0]}) == "world hello"


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1000/ABC.") == "10.1000/abc"
    assert normalize_doi("doi:10.5555/Test") == "10.5555/test"


def test_normalize_openalex_fixture():
    records = json.loads(Path("tests/fixtures/openalex_sample.json").read_text(encoding="utf-8"))
    tables = normalize_openalex(records, "config/venue_quality.csv")
    assert len(tables["papers"]) == 2
    assert len(tables["authors"]) == 4
    assert len(tables["countries"]) == 2
    assert "quality_label" in tables["papers"].columns
