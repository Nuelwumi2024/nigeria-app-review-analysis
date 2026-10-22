"""Charts for the README. One message per chart; titles state the finding."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
INK, MUTED, GRID = "#1f2933", "#6b7280", "#e5e7eb"
BLUE, ORANGE, GREY = "#0072B2", "#D55E00", "#b6bbc4"
SEQ = LinearSegmentedColormap.from_list("seq", ["#f1f6fb", "#0072B2"])
SRC = "Public Google Play reviews (English, Nigeria storefront), collected Oct 2026. Author's analysis."

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
                     "axes.axisbelow": True, "figure.dpi": 140, "axes.titleweight": "bold",
                     "axes.titlesize": 12.5, "axes.titlelocation": "left"})


def _finish(fig, ax, title, subtitle, name, pad=22, sub_y=1.02):
    ax.set_title(title, color=INK, pad=pad)
    ax.text(0, sub_y, subtitle, transform=ax.transAxes, color=MUTED, fontsize=9)
    fig.text(0.01, 0.01, SRC, color=MUTED, fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / name, bbox_inches="tight")
    plt.close(fig)


def ratings(ov, start):
    o = ov.sort_values("mean_rating")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.barh(o.app, o.mean_rating, color=[ORANGE if a == "myMTN NG" else BLUE for a in o.app], height=0.6)
    for i, r in enumerate(o.itertuples()):
        ax.text(r.mean_rating + 0.05, i, f"{r.mean_rating:.2f}★   {r.pct_1_2_star:.0f}% negative   (n={r.reviews:,})",
                va="center", fontsize=8.5, color=INK)
    ax.set_xlim(0, 7.2); ax.set_xticks(range(0, 6)); ax.grid(axis="y", visible=False)
    ax.set_xlabel("Average star rating")
    _finish(fig, ax, "myMTN NG is the outlier: its average rating is roughly half that of the fintech apps",
            f"Reviews from {pd.Timestamp(start):%d %b %Y} to 20 Oct 2026, the window all seven apps share", "01_ratings.png")


def heatmap(prev):
    p = prev.pivot(index="app", columns="theme", values="share_of_negative_pct")
    order = p.mean().sort_values(ascending=False).index
    p = p[order]
    p = p.loc[p.sum(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.imshow(p.values, cmap=SEQ, aspect="auto", vmin=0, vmax=25)
    short = {"Login, OTP and verification": "Login / OTP", "App performance and downtime": "App stability",
             "Customer support": "Support", "Loans and credit": "Loans", "Data, airtime and bundles": "Data / airtime",
             "Fraud and security": "Fraud", "Fees and charges": "Fees", "Failed or delayed transactions": "Failed txns",
             "Account restriction or freeze": "Restrictions"}
    ax.set_xticks(range(p.shape[1])); ax.set_xticklabels([short[c] for c in p.columns], fontsize=8.5)
    ax.set_yticks(range(p.shape[0])); ax.set_yticklabels(p.index); ax.grid(False)
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            v = p.values[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8.5, color="white" if v > 14 else INK)
    ax.xaxis.tick_top()
    _finish(fig, ax, "Login problems and app stability lead complaints in most apps",
            "% of 1-2 star reviews mentioning each theme (a review can mention several)", "02_complaint_heatmap.png",
            pad=52, sub_y=1.11)


def penalty(pen):
    p = pen.sort_values("rating_penalty")
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.hlines(p.theme, p.ci_low, p.ci_high, color=GREY, lw=3)
    ax.plot(p.rating_penalty, p.theme, "o", color=BLUE, ms=7)
    for y, r in zip(p.theme, p.rating_penalty):
        ax.text(r, y, f"  -{r:.1f}", va="center", fontsize=8.5, color=INK)
    ax.set_xlim(0, 2.7); ax.grid(axis="y", visible=False)
    ax.set_xlabel("Stars lost when a review mentions the theme (with 95% interval)")
    _finish(fig, ax, "Fraud, login and stability problems cost the most stars",
            "Average rating without the theme minus with it, all 34k reviews. Association, not proof of cause.", "03_rating_penalty.png")


def mtn_trend(m):
    x = m[(m.app == "myMTN NG") & (m.reviews >= 100)].copy()
    x["month"] = pd.to_datetime(x.month)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(x.month, x.mean_rating, color=BLUE, lw=2.2, marker="o", ms=4)
    hi, lo = x.loc[x.mean_rating.idxmax()], x.iloc[-1]
    for r in (hi, lo):
        ax.annotate(f"{r.mean_rating:.1f}", (r.month, r.mean_rating), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=9, color=INK)
    ax.set_ylim(1, 4); ax.set_ylabel("Average star rating (monthly)")
    _finish(fig, ax, "myMTN NG recovered from 1.7 to 3.3 stars by Feb 2026, then slid back to 2.1",
            "Monthly average rating (months with 100+ reviews). It is the only app with 12+ months of reviews in the sample.",
            "04_mtn_trend.png")


def main():
    FIG.mkdir(exist_ok=True)
    s = json.loads((RES / "summary.json").read_text())
    rd = lambda n: pd.read_csv(RES / f"{n}.csv")
    ratings(rd("app_overview_common_window"), s["common_window_start"])
    heatmap(rd("theme_prevalence_common_window"))
    penalty(rd("theme_penalty"))
    mtn_trend(rd("monthly"))


if __name__ == "__main__":
    main()
