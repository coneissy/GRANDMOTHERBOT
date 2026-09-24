from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _save(fig, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def plot_gross_return_curve(curve, path, title="Gross Return curve"):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    xs = list(curve.keys())
    ys = [float(value) for value in curve.values()]
    ax.plot([float(x) for x in xs], ys, marker="o", linewidth=1)
    ax.set_xlabel("Markout horizon (s)")
    ax.set_ylabel("Gross return")
    ax.set_title(title)
    ax.axvline(float(max(curve, key=curve.get)), linestyle="--", linewidth=1)
    _save(fig, path)


def plot_weekly_hhi(hhi_by_week, path, title="Weekly HHI"):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    xs = list(hhi_by_week.keys())
    ys = [float(value) for value in hhi_by_week.values()]
    ax.plot(range(len(xs)), ys, linewidth=1)
    ax.set_xlabel("Week")
    ax.set_ylabel("HHI")
    ax.set_title(title)
    _save(fig, path)


def plot_section5_trade_size_return(frame: pd.DataFrame, path):
    fig, ax = plt.subplots(figsize=(8, 5))
    for pattern, group in frame.groupby("pattern"):
        ax.scatter(
            group["median_trade_volume_usd"],
            group["median_gross_return_bps"],
            s=(group["estimated_revenue_usd"].clip(lower=0).fillna(0) + 1) ** 0.5,
            label=f"Pattern {pattern}",
        )
        for _, row in group.iterrows():
            ax.annotate(
                str(row.searcher_label),
                (row.median_trade_volume_usd, row.median_gross_return_bps),
                fontsize=7,
            )
    ax.set_xlabel("Median trade volume (USD)")
    ax.set_ylabel("Median gross return (bps)")
    ax.set_title("Figure 4(a): Trade size and gross return")
    ax.legend()
    _save(fig, path)


def plot_section5_gross_return_cdf(frame: pd.DataFrame, path):
    fig, ax = plt.subplots(figsize=(8, 5))
    for pattern, group in frame.groupby("pattern"):
        ordered = group.sort_values("gross_return_bps")
        ax.plot(
            ordered["gross_return_bps"],
            ordered["cdf"],
            linewidth=1,
            label=f"Pattern {pattern}",
        )
    ax.set_xlabel("Gross return (bps)")
    ax.set_ylabel("Cumulative probability")
    ax.set_title("Figure 4(b): Gross return CDF")
    ax.legend()
    _save(fig, path)


def plot_section5_hedge_correlation(
    frame: pd.DataFrame,
    path: str,
    x_column: str,
    title: str,
):
    fig, ax = plt.subplots(figsize=(8, 5))
    for pattern, group in frame.groupby("pattern"):
        ax.scatter(
            group[x_column],
            group["decline_3s"],
            label=f"Pattern {pattern}",
        )
    ax.set_xlabel("Major-Major share")
    ax.set_ylabel("3-second decline in median gross return")
    ax.set_title(title)
    ax.legend()
    _save(fig, path)
