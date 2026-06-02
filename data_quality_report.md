# FedAtlas Data Quality Report

- crawl timestamp: 2026-06-02T10:54:59+00:00
- configured year range: 2016-2026
- paper count: 3012
- author count: 11455
- institution count: 2618
- country count: 102
- venue count: 709
- topic count: 756
- repo count: 444
- Papers With Code match count: 665
- venue quality coverage: {'Unknown': 3012}
- missing DOI rate: 0.04714475431606906
- missing abstract rate: 0.16600265604249667

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
