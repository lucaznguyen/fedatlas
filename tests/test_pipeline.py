import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_pipeline import add_repo_counts


def test_add_repo_counts_deduplicates_canonical_repo_names():
    repos = pd.DataFrame([
        {"repo_full_name": "owner/repo", "repo_owner": "owner", "repo_name": "repo", "github_status": 0},
        {"repo_full_name": "owner/repo", "repo_owner": "Owner", "repo_name": "repo", "github_status": 200, "stargazers_count": 5, "forks_count": 1},
    ])
    out = add_repo_counts(repos, pd.DataFrame())
    assert len(out) == 1
    assert out.iloc[0]["github_status"] == 200
