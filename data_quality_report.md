# FedAtlas Data Quality Report

- crawl timestamp: 2026-06-05T20:24:01+00:00
- configured year range: 2016-2026
- paper count: 6431
- author count: 22874
- institution count: 4267
- country count: 124
- venue count: 1318
- topic count: 1190
- repo count: 716
- Papers With Code match count: 1000
- venue quality coverage: {'Unknown': 6431}
- missing DOI rate: 0.04851500544238843
- missing abstract rate: 0.16902503498678276

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
