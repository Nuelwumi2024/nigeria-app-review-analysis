"""Load the raw review files, clean them and write data/processed/reviews_clean.csv."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from themes import scrub

ROOT = Path(__file__).resolve().parents[1]
RAW, PROCESSED = ROOT / "data" / "raw", ROOT / "data" / "processed"
MIN_CHARS = 12  # shorter reviews ("nice", "ok") carry no theme and are kept out of theme shares


def load_raw(raw: Path = RAW) -> pd.DataFrame:
    files = sorted(raw.glob("reviews_*.csv"))
    if not files:
        raise FileNotFoundError("No review files in data/raw. Run: python src/scrape.py")
    return pd.concat((pd.read_csv(f) for f in files), ignore_index=True)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d["month"] = d["date"].dt.to_period("M").dt.to_timestamp()
    d = d.dropna(subset=["text", "rating"])
    d["rating"] = d["rating"].astype(int)
    d["text_clean"] = d["text"].map(scrub).str.replace(r"\s+", " ", regex=True).str.strip()
    d = d[d.text_clean.str.len() >= MIN_CHARS]
    d = d.drop_duplicates(["app", "text_clean"])
    return d.drop(columns=["text"]).reset_index(drop=True)


def main() -> pd.DataFrame:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    raw = load_raw()
    d = clean(raw)
    d.to_csv(PROCESSED / "reviews_clean.csv", index=False)
    print(f"raw {len(raw):,} -> clean {len(d):,} reviews, {d.app.nunique()} apps, "
          f"{d.date.min():%Y-%m-%d} to {d.date.max():%Y-%m-%d}")
    return d


if __name__ == "__main__":
    main()
