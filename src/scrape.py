"""Collect public Google Play reviews for the apps in apps.py.

Only review text, star rating, date, app version and thumbs-up count are kept. Reviewer names,
IDs and avatars are dropped at collection time. The raw files stay on your machine (data/ is
git-ignored): this repo publishes the code and aggregated results, not the review text.

Check Google Play's terms of service before running this at scale, and keep the request
rate low. Usage:  python src/scrape.py [--since 2025-01-01] [--cap 8000]
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from google_play_scraper import Sort, reviews

from apps import APPS

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def collect(app_id: str, since: datetime, cap: int, pause: float = 1.0) -> pd.DataFrame:
    out, token = [], None
    while len(out) < cap:
        batch, token = reviews(app_id, lang="en", country="ng", sort=Sort.NEWEST, count=200,
                               continuation_token=token)
        if not batch:
            break
        out += batch
        if batch[-1]["at"] < since or token is None:
            break
        time.sleep(pause)
    df = pd.DataFrame(out)
    if df.empty:
        return df
    df = df.rename(columns={"at": "date", "score": "rating", "content": "text", "thumbsUpCount": "thumbs_up",
                            "appVersion": "app_version"})
    df = df[["date", "rating", "text", "thumbs_up", "app_version"]]
    return df[df.date >= since].drop_duplicates(["date", "text"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2025-01-01")
    ap.add_argument("--cap", type=int, default=8000)
    ap.add_argument("--refresh", action="store_true", help="re-collect apps that already have a file")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    since = datetime.fromisoformat(a.since)
    for name, (app_id, sector) in APPS.items():
        if (RAW / f"reviews_{app_id}.csv").exists() and not a.refresh:
            print(f"{name:12s} already collected, skipping", flush=True)
            continue
        df = collect(app_id, since, a.cap)
        df.insert(0, "app", name)
        df.insert(1, "sector", sector)
        df.to_csv(RAW / f"reviews_{app_id}.csv", index=False)
        rng = f"{df.date.min():%Y-%m-%d} to {df.date.max():%Y-%m-%d}" if len(df) else "none"
        print(f"{name:12s} {len(df):>6,} reviews  {rng}", flush=True)


if __name__ == "__main__":
    main()
