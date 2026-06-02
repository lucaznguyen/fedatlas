# Methodology

FedAtlas uses a broad-first, filter-later workflow. The crawler queries OpenAlex Works by Federated Learning keywords and year chunks from 2016 through the configured end year. Raw API responses are cached under `data/raw/openalex`, and the consolidated raw record stream is stored under `data/interim`.

## Deduplication

Records are deduplicated in this order:

1. OpenAlex work ID.
2. Normalized DOI.
3. arXiv ID.
4. Exact normalized title.

Weak fuzzy title matches are not merged in the OpenAlex deduplication step. PWC matching uses high-threshold fuzzy title matching only after DOI, arXiv, and exact title matching fail.

## Venue Quality

The crawler stores all venues. The dashboard defaults to A*/A/Q1 when those labels are available, but Unknown venues remain in the data and can be included. FedAtlas does not invent venue labels. Use `scripts/import_venue_quality.py` to convert a legally usable CORE, ERA, SCImago, JCR-style, or manually curated CSV into `config/venue_quality.csv`.

## Topic Classification

Topic groups combine OpenAlex topics with transparent keyword rules. Every paper receives a `topic_group` and `topic_method` so the classification remains auditable.

## Research-to-Code Score

For each group and year:

```text
research_to_code_score = papers_with_at_least_one_github_repo / total_papers
```

Paper-level `code_score` is:

```text
log1p(total_stars)
+ 0.5 * log1p(total_forks)
+ 0.25 * log1p(total_contributors)
+ activity_bonus
```

`activity_bonus` is 0.5 when the latest repository push is within 365 days, 0.25 within 730 days, and 0 otherwise.

## Network Metrics

FedAtlas builds a heterogeneous graph with paper, author, institution, country, topic, venue, GitHub repository, and contributor nodes. It computes degree, weighted degree, betweenness, closeness, PageRank, greedy modularity communities, and a bridge score based on normalized betweenness and degree.
