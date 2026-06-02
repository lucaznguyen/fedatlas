from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .utils import env_flag, env_int


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    root: Path
    config: dict[str, Any]
    queries: list[str]
    start_year: int
    end_year: int
    max_papers: int
    use_demo_data: bool
    run_github_enrichment: bool
    run_pwc_matching: bool
    force_refresh: bool
    openalex_api_key: str | None
    openalex_mailto: str | None
    github_token: str | None
    venue_quality_path: Path

    @property
    def raw_dir(self) -> Path:
        return self.root / self.config["cache"]["raw_dir"]

    @property
    def processed_dir(self) -> Path:
        return self.root / self.config["cache"]["processed_dir"]

    @property
    def manifest_dir(self) -> Path:
        return self.root / self.config["cache"]["manifest_dir"]

    @property
    def interim_dir(self) -> Path:
        return self.root / "data" / "interim"


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def load_settings(root: str | Path | None = None) -> Settings:
    project_root = Path(root).resolve() if root else ROOT.resolve()
    load_dotenv(project_root / ".env", override=False)
    cfg = _load_yaml(project_root / "config" / "config.yaml")
    queries_cfg = _load_yaml(project_root / "config" / "search_queries.yaml")
    start_year = env_int("START_YEAR", int(cfg.get("start_year", 2016)))
    end_year = env_int("END_YEAR", int(cfg.get("end_year", 2026)))
    max_papers = env_int("MAX_PAPERS", int(cfg.get("max_papers", 0)))
    venue_quality_path = Path(os.getenv("VENUE_QUALITY_PATH", "config/venue_quality.csv"))
    if not venue_quality_path.is_absolute():
        venue_quality_path = project_root / venue_quality_path
    return Settings(
        root=project_root,
        config=cfg,
        queries=list(queries_cfg.get("queries", [])),
        start_year=start_year,
        end_year=end_year,
        max_papers=max_papers,
        use_demo_data=env_flag("USE_DEMO_DATA", False),
        run_github_enrichment=env_flag("RUN_GITHUB_ENRICHMENT", True),
        run_pwc_matching=env_flag("RUN_PWC_MATCHING", True),
        force_refresh=env_flag("FORCE_REFRESH", False),
        openalex_api_key=os.getenv("OPENALEX_API_KEY") or None,
        openalex_mailto=os.getenv("OPENALEX_MAILTO") or None,
        github_token=os.getenv("GITHUB_TOKEN") or None,
        venue_quality_path=venue_quality_path,
    )
