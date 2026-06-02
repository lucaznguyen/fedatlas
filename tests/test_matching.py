import pandas as pd

from fedatlas.matching import match_papers_with_code
from fedatlas.utils import extract_arxiv_id, normalize_title, parse_github_url, title_similarity


def test_extract_arxiv_id():
    assert extract_arxiv_id("https://arxiv.org/abs/1602.05629v3") == "1602.05629v3"


def test_parse_github_url():
    assert parse_github_url("https://github.com/openai/example.git") == ("openai", "example")
    assert parse_github_url("git@github.com:owner/repo.git") == ("owner", "repo")


def test_title_normalization_and_fuzzy_threshold():
    a = "Federated Learning: Privacy and Robustness!"
    b = "Federated learning privacy robustness"
    assert normalize_title(a) == "federated learning privacy and robustness"
    assert title_similarity(a, b) >= 0.85


def test_pwc_matching_by_doi():
    papers = pd.DataFrame([{"work_id": "W1", "doi": "10.1/test", "title": "A Federated Learning Paper", "arxiv_id": None}])
    pwc_papers = pd.DataFrame([{"id": "P1", "title": "A Federated Learning Paper", "doi": "https://doi.org/10.1/test"}])
    links = pd.DataFrame([{"paper_id": "P1", "repo_url": "https://github.com/acme/fed", "is_official": True}])
    out = match_papers_with_code(papers, pwc_papers, links)
    assert len(out) == 1
    assert out.iloc[0]["repo_owner"] == "acme"
    assert out.iloc[0]["match_method"] == "doi_exact"


def test_pwc_matching_huggingface_schema_by_arxiv():
    papers = pd.DataFrame([{"work_id": "W2", "doi": None, "title": "FedAvg for Everyone", "arxiv_id": "1602.05629"}])
    pwc_papers = pd.DataFrame([
        {
            "paper_url": "https://paperswithcode.com/paper/fedavg-for-everyone",
            "arxiv_id": "1602.05629",
            "title": "FedAvg for Everyone",
            "url_abs": "https://arxiv.org/abs/1602.05629",
        }
    ])
    links = pd.DataFrame([
        {
            "paper_url": "https://paperswithcode.com/paper/fedavg-for-everyone",
            "paper_arxiv_id": "1602.05629",
            "repo_url": "https://github.com/acme/fedavg",
            "is_official": True,
        }
    ])
    out = match_papers_with_code(papers, pwc_papers, links)
    assert len(out) == 1
    assert out.iloc[0]["repo_name"] == "fedavg"
    assert out.iloc[0]["match_method"] == "arxiv_exact"
