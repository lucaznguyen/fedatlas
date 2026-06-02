from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from fedatlas.venue_quality import import_quality_csv


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("--output", default="config/venue_quality.csv")
    args = parser.parse_args()
    df = import_quality_csv(args.input_csv, args.output)
    print(f"Imported {len(df)} venue quality rows into {args.output}")
