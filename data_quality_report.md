# FedAtlas Data Quality Report

- crawl timestamp: 2026-06-05T09:35:59+00:00
- configured year range: 2016-2026
- paper count: 10699
- author count: 45191
- institution count: 7840
- country count: 170
- venue count: 2355
- topic count: 2111
- repo count: 845
- Papers With Code match count: 1114
- venue quality coverage: {'Unknown': 10699}
- missing DOI rate: 0.020843069445742594
- missing abstract rate: 0.1404804187307225

## Warnings

- GITHUB_TOKEN is not configured; unauthenticated GitHub enrichment is rate-limited.
- OPENALEX_MAILTO is not configured; set it for polite OpenAlex API usage.
- More than half of venues are Unknown quality; import a licensed venue quality file for A*/A/Q1 filtering.

## Reproducibility Commands

```bash
make setup
make smoke
make crawl
make build
make dashboard
```
