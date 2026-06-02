from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import requests

from .config import Settings
from .utils import canonical_repo_url, ensure_dir, read_json, sleep_with_backoff, write_json

LOGGER = logging.getLogger(__name__)


class GitHubClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = requests.Session()
        self.retry_max = int(settings.config.get("github", {}).get("retry_max", 5))
        self.backoff = float(settings.config.get("github", {}).get("retry_backoff_seconds", 3))
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        self.session.headers.update(headers)

    def get(self, url: str) -> tuple[int, Any]:
        for attempt in range(1, self.retry_max + 1):
            response = self.session.get(url, timeout=60)
            if response.status_code == 200:
                return response.status_code, response.json()
            if response.status_code == 202:
                sleep_with_backoff(self.backoff, attempt)
                continue
            if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
                return response.status_code, {"message": "GitHub rate limit exhausted"}
            if response.status_code in {403, 429, 500, 502, 503, 504}:
                LOGGER.warning("GitHub retryable status %s for %s", response.status_code, url)
                sleep_with_backoff(self.backoff, attempt)
                continue
            return response.status_code, {"message": response.text}
        return response.status_code, {"message": "retry limit reached"}

    def core_rate_remaining(self) -> int | None:
        try:
            status, payload = self.get("https://api.github.com/rate_limit")
        except Exception:
            return None
        if status != 200 or not isinstance(payload, dict):
            return None
        core = payload.get("resources", {}).get("core", {})
        remaining = core.get("remaining")
        return int(remaining) if remaining is not None else None

    def fetch_repo(self, owner: str, repo: str) -> dict[str, Any]:
        status, payload = self.get(f"https://api.github.com/repos/{owner}/{repo}")
        return {"status": status, "payload": payload}

    def fetch_contributors(self, owner: str, repo: str) -> dict[str, Any]:
        status, payload = self.get(f"https://api.github.com/repos/{owner}/{repo}/contributors?per_page=100")
        return {"status": status, "payload": payload}

    def fetch_languages(self, owner: str, repo: str) -> dict[str, Any]:
        status, payload = self.get(f"https://api.github.com/repos/{owner}/{repo}/languages")
        return {"status": status, "payload": payload}

    def fetch_commit_activity(self, owner: str, repo: str) -> dict[str, Any]:
        status, payload = self.get(f"https://api.github.com/repos/{owner}/{repo}/stats/commit_activity")
        return {"status": status, "payload": payload}


def enrich_github_repos(settings: Settings, code_links: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if code_links.empty or not settings.run_github_enrichment:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    client = GitHubClient(settings)
    unique = (
        code_links[["repo_url", "repo_owner", "repo_name"]]
        .dropna(subset=["repo_owner", "repo_name"])
        .drop_duplicates()
        .to_dict("records")
    )
    repo_rows: list[dict[str, Any]] = []
    contributor_rows: list[dict[str, Any]] = []
    repo_contrib_rows: list[dict[str, Any]] = []
    raw_dir = ensure_dir(settings.raw_dir / "github")
    minimal_mode = not bool(settings.github_token)
    remaining_budget = client.core_rate_remaining() if minimal_mode else None
    if minimal_mode:
        LOGGER.warning("GITHUB_TOKEN is not configured; fetching repo metadata only within unauthenticated rate limits.")
    for row in unique:
        owner = row["repo_owner"]
        repo = row["repo_name"]
        full_name = f"{owner}/{repo}"
        cache_path = raw_dir / f"{owner}__{repo}.json"
        LOGGER.info("Enriching GitHub repo %s", full_name)
        cached = read_json(cache_path) if cache_path.exists() and not settings.force_refresh else None
        use_cache = bool(cached) and (minimal_mode or cached.get("repo", {}).get("status") == 200)
        if use_cache:
            repo_resp = cached.get("repo", {"status": 0, "payload": {}})
            contrib_resp = cached.get("contributors", {"status": 0, "payload": []})
            lang_resp = cached.get("languages", {"status": 0, "payload": {}})
            stats_resp = cached.get("commit_activity", {"status": 0, "payload": {}})
        elif minimal_mode and remaining_budget is not None and remaining_budget <= 2:
            repo_resp = {"status": 0, "payload": {"message": "skipped: unauthenticated GitHub rate budget exhausted"}}
            contrib_resp = {"status": 0, "payload": []}
            lang_resp = {"status": 0, "payload": {}}
            stats_resp = {"status": 0, "payload": {}}
            write_json(cache_path, {
                "repo": repo_resp,
                "contributors": contrib_resp,
                "languages": lang_resp,
                "commit_activity": stats_resp,
            })
        else:
            repo_resp = client.fetch_repo(owner, repo)
            if minimal_mode and remaining_budget is not None:
                remaining_budget -= 1
            if minimal_mode:
                contrib_resp = {"status": 0, "payload": []}
                lang_resp = {"status": 0, "payload": {}}
                stats_resp = {"status": 0, "payload": {}}
            else:
                contrib_resp = client.fetch_contributors(owner, repo)
                lang_resp = client.fetch_languages(owner, repo)
                stats_resp = client.fetch_commit_activity(owner, repo)
            write_json(cache_path, {
                "repo": repo_resp,
                "contributors": contrib_resp,
                "languages": lang_resp,
                "commit_activity": stats_resp,
            })
        if repo_resp["status"] != 200 or not isinstance(repo_resp["payload"], dict):
            repo_rows.append({
                "repo_full_name": full_name,
                "repo_owner": owner,
                "repo_name": repo,
                "repo_url": canonical_repo_url(owner, repo),
                "github_status": repo_resp["status"],
            })
            continue
        payload = repo_resp["payload"]
        license_payload = payload.get("license") or {}
        repo_rows.append({
            "repo_id": payload.get("id"),
            "repo_full_name": payload.get("full_name", full_name),
            "repo_url": payload.get("html_url") or canonical_repo_url(owner, repo),
            "description": payload.get("description"),
            "repo_owner": owner,
            "repo_name": repo,
            "owner_type": (payload.get("owner") or {}).get("type"),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
            "pushed_at": payload.get("pushed_at"),
            "archived": payload.get("archived"),
            "disabled": payload.get("disabled"),
            "fork": payload.get("fork"),
            "stargazers_count": payload.get("stargazers_count", 0),
            "forks_count": payload.get("forks_count", 0),
            "watchers_count": payload.get("watchers_count", 0),
            "open_issues_count": payload.get("open_issues_count", 0),
            "subscribers_count": payload.get("subscribers_count"),
            "language": payload.get("language"),
            "license": license_payload.get("spdx_id") or license_payload.get("name"),
            "topics": payload.get("topics", []),
            "default_branch": payload.get("default_branch"),
            "size": payload.get("size"),
            "homepage": payload.get("homepage"),
            "languages": lang_resp["payload"] if lang_resp["status"] == 200 else {},
            "commit_activity_status": stats_resp["status"],
            "github_status": repo_resp["status"],
        })
        contributors = contrib_resp["payload"] if contrib_resp["status"] == 200 and isinstance(contrib_resp["payload"], list) else []
        for c in contributors:
            cid = c.get("id") or c.get("login")
            contributor_rows.append({
                "contributor_id": cid,
                "login": c.get("login"),
                "type": c.get("type"),
                "avatar_url": c.get("avatar_url"),
                "html_url": c.get("html_url"),
            })
            repo_contrib_rows.append({
                "repo_full_name": payload.get("full_name", full_name),
                "contributor_id": cid,
                "login": c.get("login"),
                "contributions": c.get("contributions", 0),
            })
    repos = pd.DataFrame(repo_rows)
    contributors = pd.DataFrame(contributor_rows).drop_duplicates(subset=["contributor_id"]) if contributor_rows else pd.DataFrame()
    repo_contributors = pd.DataFrame(repo_contrib_rows)
    return repos, contributors, repo_contributors
