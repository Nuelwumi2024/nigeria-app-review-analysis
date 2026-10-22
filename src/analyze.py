"""Theme prevalence, rating penalties, trends, spikes and a ranked fix list per app."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import themes as th

ROOT = Path(__file__).resolve().parents[1]
PROCESSED, RESULTS = ROOT / "data" / "processed", ROOT / "results"
MIN_MONTH_N = 150     # minimum reviews in an app-month to trust a monthly share
MIN_VERSION_N = 100   # minimum reviews to judge an app version


def overview(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby(["app", "sector"])
    out = g.agg(reviews=("rating", "size"), mean_rating=("rating", "mean"),
                first=("date", "min"), last=("date", "max")).reset_index()
    out["pct_1_2_star"] = g.rating.apply(lambda r: (r <= 2).mean() * 100).values
    out["pct_4_5_star"] = g.rating.apply(lambda r: (r >= 4).mean() * 100).values
    return out


def prevalence(d: pd.DataFrame) -> pd.DataFrame:
    neg = d[d.rating <= 2]
    rows = []
    for app, g in d.groupby("app"):
        gn = neg[neg.app == app]
        for t in th.THEME_NAMES:
            rows.append((app, g.sector.iloc[0], t, g[t].mean() * 100, gn[t].mean() * 100, int(gn[t].sum()), len(gn)))
    return pd.DataFrame(rows, columns=["app", "sector", "theme", "share_all_pct", "share_of_negative_pct",
                                       "negative_with_theme", "negative_reviews"])


def penalty(d: pd.DataFrame, by_app: bool = False) -> pd.DataFrame:
    """Mean rating without minus with a theme, with a 95% interval (Welch). Association only."""
    rows = []
    groups = d.groupby("app") if by_app else [("All apps", d)]
    for app, g in groups:
        for t in th.THEME_NAMES:
            a, b = g.loc[g[t], "rating"], g.loc[~g[t], "rating"]
            if len(a) < 30 or len(b) < 30:
                continue
            diff = b.mean() - a.mean()
            se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
            rows.append((app, t, len(a), a.mean(), b.mean(), diff, diff - 1.96 * se, diff + 1.96 * se))
    return pd.DataFrame(rows, columns=["app", "theme", "n_with", "mean_with", "mean_without",
                                       "rating_penalty", "ci_low", "ci_high"])


def monthly(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby(["app", "month"])
    out = g.agg(reviews=("rating", "size"), mean_rating=("rating", "mean")).reset_index()
    out["pct_1_2_star"] = g.rating.apply(lambda r: (r <= 2).mean() * 100).values
    for t in th.THEME_NAMES:
        out[t] = g[t].mean().values * 100
    return out


def spikes(m: pd.DataFrame, theme: str = "Failed or delayed transactions", z: float = 2.0) -> pd.DataFrame:
    rows = []
    for app, g in m[m.reviews >= MIN_MONTH_N].groupby("app"):
        if len(g) < 6:
            continue
        zs = (g[theme] - g[theme].mean()) / g[theme].std(ddof=1)
        for _, r in g[zs >= z].iterrows():
            rows.append((app, r.month, theme, r[theme], g[theme].mean(), (r[theme] - g[theme].mean()) / g[theme].std(ddof=1)))
    return pd.DataFrame(rows, columns=["app", "month", "theme", "share_pct", "app_mean_pct", "z"])


def version_effect(d: pd.DataFrame) -> pd.DataFrame:
    v = d.dropna(subset=["app_version"]).groupby(["app", "app_version"]).agg(
        reviews=("rating", "size"), mean_rating=("rating", "mean"), first_seen=("date", "min")).reset_index()
    v = v[v.reviews >= MIN_VERSION_N].copy()
    base = d.groupby("app").rating.mean()
    v["vs_app_mean"] = v.mean_rating - v.app.map(base)
    return v.sort_values("vs_app_mean")


def fix_list(d: pd.DataFrame, prev: pd.DataFrame, pen: pd.DataFrame) -> pd.DataFrame:
    p = pen.set_index("theme").rating_penalty
    f = prev.assign(rating_penalty=prev.theme.map(p))
    f["priority"] = f.share_of_negative_pct * f.rating_penalty.clip(lower=0)
    f = f.sort_values(["app", "priority"], ascending=[True, False])
    f["rank"] = f.groupby("app").cumcount() + 1
    return f[f["rank"] <= 3][["app", "sector", "rank", "theme", "share_of_negative_pct", "rating_penalty", "priority"]]


def main() -> dict:
    RESULTS.mkdir(exist_ok=True)
    d = th.tag(pd.read_csv(PROCESSED / "reviews_clean.csv", parse_dates=["date", "month"]))
    ov, prev = overview(d), prevalence(d)
    # Apps cover different periods (OPay ~5 weeks, myMTN ~18 months), so cross-app comparisons
    # use the window every app has reviews for.
    common_start = d.groupby("app").date.min().max().normalize()
    dc = d[d.date >= common_start]
    ov_c, prev_c = overview(dc), prevalence(dc)
    pen, pen_app = penalty(d), penalty(d, by_app=True)
    m = monthly(d)
    sp, ve, fl = spikes(m), version_effect(d), fix_list(d, prev, pen)
    for name, df in [("app_overview", ov), ("app_overview_common_window", ov_c), ("theme_prevalence_common_window", prev_c), ("theme_prevalence", prev), ("theme_penalty", pen),
                     ("theme_penalty_by_app", pen_app), ("monthly", m), ("spikes", sp),
                     ("version_effect", ve), ("fix_list", fl)]:
        df.to_csv(RESULTS / f"{name}.csv", index=False, float_format="%.4f")

    neg = d[d.rating <= 2]
    top = pen.sort_values("rating_penalty", ascending=False)
    comp = prev.groupby("theme").negative_with_theme.sum() / prev.groupby("app").negative_reviews.first().sum() * 100
    s = {
        "reviews": len(d), "apps": int(d.app.nunique()), "first": f"{d.date.min():%Y-%m-%d}", "last": f"{d.date.max():%Y-%m-%d}",
        "pct_negative": float((d.rating <= 2).mean() * 100), "pct_positive": float((d.rating >= 4).mean() * 100),
        "pct_negative_any_theme": float(neg[th.THEME_NAMES].any(axis=1).mean() * 100),
        "pct_all_any_theme": float(d[th.THEME_NAMES].any(axis=1).mean() * 100),
        "top_complaint_theme": comp.idxmax(), "top_complaint_share_of_negative": float(comp.max()),
        "complaint_share_of_negative": {k: float(v) for k, v in comp.sort_values(ascending=False).items()},
        "largest_penalty_theme": top.theme.iloc[0], "largest_penalty": float(top.rating_penalty.iloc[0]),
        "penalty_by_theme": {r.theme: float(r.rating_penalty) for r in pen.itertuples()},
        "sector_mean_rating": {k: float(v) for k, v in d.groupby("sector").rating.mean().items()},
        "spikes": len(sp), "common_window_start": f"{common_start:%Y-%m-%d}", "common_window_reviews": len(dc),
        "common_window_mean_rating": {r.app: float(r.mean_rating) for r in ov_c.itertuples()},
    }
    (RESULTS / "summary.json").write_text(json.dumps(s, indent=2))
    return s


if __name__ == "__main__":
    for k, v in main().items():
        print(f"{k:36s} {v:,.2f}" if isinstance(v, float) else f"{k:36s} {v}")
