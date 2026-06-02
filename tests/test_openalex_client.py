from types import SimpleNamespace

from fedatlas.openalex_client import query_year_batches


def test_query_year_batches_broad_sample_prioritizes_year_coverage():
    settings = SimpleNamespace(start_year=2020, end_year=2022, queries=["q1", "q2"])
    batches = query_year_batches(settings, broad_sample=True)
    assert batches[:3] == [(2020, "q1"), (2021, "q1"), (2022, "q1")]


def test_query_year_batches_full_crawl_uses_year_chunks():
    settings = SimpleNamespace(start_year=2020, end_year=2021, queries=["q1", "q2"])
    batches = query_year_batches(settings, broad_sample=False)
    assert batches == [(2020, "q1"), (2020, "q2"), (2021, "q1"), (2021, "q2")]
