# Data Dictionary

FedAtlas writes normalized parquet tables to `data/processed` and dashboard-ready CSV files to the same directory.

## Core Tables

`papers.parquet`: one row per deduplicated OpenAlex work. Key fields include `work_id`, `doi`, `title`, `abstract`, `publication_year`, `cited_by_count`, `venue_id`, `venue_name`, `topic_group`, `quality_label`, `merge_source_ids`, and `dedup_confidence`.

`authors.parquet`, `institutions.parquet`, `countries.parquet`, `venues.parquet`, `topics.parquet`: dimension tables extracted from OpenAlex.

`paper_authors.parquet`, `paper_institutions.parquet`, `paper_countries.parquet`, `paper_topics.parquet`, `paper_references.parquet`: relational tables connecting papers to authors, institutions, countries, topics, and references.

`paper_code_links.parquet`: Papers With Code matches to GitHub repositories. It stores `work_id`, PWC IDs, repository URL, owner/name, match method, and match confidence.

`repos.parquet`, `contributors.parquet`, `repo_contributors.parquet`: GitHub public metadata and contributor links.

`nodes.csv` and `edges.csv`: heterogeneous graph export for papers, authors, institutions, countries, topics, venues, GitHub repositories, and contributors.

## Dashboard CSVs

`dashboard_kpis.csv`: KPI card values.

`dashboard_timeseries.csv`: papers, citations, and GitHub-linked papers by year.

`dashboard_topic_year.csv`: topic group counts by year.

`dashboard_country_map.csv` and `dashboard_country_edges.csv`: country summary and collaboration edges.

`dashboard_network_nodes.csv` and `dashboard_network_edges.csv`: filtered graph inputs for Shiny.

`dashboard_code_gap.csv`: paper-level research-to-code metrics.

`dashboard_sankey.csv`: research-to-code grouping export, currently topic/year rows.
