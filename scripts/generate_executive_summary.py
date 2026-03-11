from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
REPORT_DIR = BASE_DIR / "reports"
ASSET_DIR = REPORT_DIR / "executive_summary_assets"
REPORT_PATH = REPORT_DIR / "executive_summary.md"


plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["figure.dpi"] = 160
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.titleweight"] = "bold"


COLORS = {
    "navy": "#16324f",
    "teal": "#2a9d8f",
    "blue": "#2f6690",
    "gold": "#e9c46a",
    "orange": "#f4a261",
    "red": "#e76f51",
    "green": "#52796f",
    "gray": "#6b7280",
    "light_gray": "#dbe4ee",
}


def money_b(value: float) -> str:
    return f"${value / 1e9:,.2f}B"


def money_m(value: float) -> str:
    return f"${value / 1e6:,.0f}M"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def cagr(first: float, last: float, year_span: int) -> float:
    return (last / first) ** (1 / year_span) - 1


def normalize_items(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["line_item_norm"] = out["line_item"].astype(str).str.strip().str.upper()
    return out


def exact_series(combined: pd.DataFrame, fund: str, line_item: str) -> pd.Series:
    return (
        combined[
            (combined["fund"] == fund)
            & (combined["line_item_norm"] == line_item.upper())
        ]
        .sort_values("fiscal_year")
        .set_index("fiscal_year")["amount"]
    )


def clean_revenue_mix(combined: pd.DataFrame) -> pd.DataFrame:
    revenue = combined[
        (combined["fund"] == "General Fund")
        & (combined["section"] == "revenue")
        & (~combined["line_item_norm"].isin({"SUBTOTAL REVENUES", "TOTAL REVENUES"}))
        & (~combined["line_item_norm"].str.contains("TRANSFER", na=False))
        & (~combined["line_item_norm"].str.contains("AVAILABLE FUNDS", na=False))
    ][["fiscal_year", "line_item", "amount"]].copy()

    revenue["line_item"] = revenue["line_item"].replace(
        {
            "Fines and Forfeits": "Fines & Forfeits",
        }
    )

    return (
        revenue.groupby(["fiscal_year", "line_item"], as_index=False)["amount"]
        .sum()
        .pivot(index="fiscal_year", columns="line_item", values="amount")
        .fillna(0)
        .sort_index()
    )


def clean_spending_mix(combined: pd.DataFrame) -> pd.DataFrame:
    spending = combined[
        (combined["fund"] == "Total All Funds")
        & (combined["section"] == "appropriation")
        & (~combined["line_item_norm"].isin({"SUBTOTAL APPROPRIATIONS", "TOTAL APPROPRIATIONS"}))
        & (~combined["line_item_norm"].str.contains("TRANSFER|RESERVE|GROSS|FINANCIAL|AMEND", na=False))
    ][["fiscal_year", "line_item", "amount"]].copy()

    spending["line_item"] = spending["line_item"].replace(
        {
            "Health and Human Services": "Health & Human Services",
            "Parks and Recreation": "Parks & Recreation",
            "Streets and Infrastructure": "Streets & Infrastructure",
            "Economic Development & Development Svcs": "Economic Development",
        }
    )

    return (
        spending.groupby(["fiscal_year", "line_item"], as_index=False)["amount"]
        .sum()
        .pivot(index="fiscal_year", columns="line_item", values="amount")
        .fillna(0)
        .sort_index()
    )


def fold_small_categories(pivot: pd.DataFrame, keep_count: int) -> pd.DataFrame:
    latest = pivot.iloc[-1].sort_values(ascending=False)
    keep = list(latest.head(keep_count).index)
    folded = pivot[keep].copy()
    other_cols = [col for col in pivot.columns if col not in keep]
    if other_cols:
        folded["Other"] = pivot[other_cols].sum(axis=1)
    return folded


def budget_execution(acfr: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    revenue = acfr[
        (acfr["section"] == "revenue")
        & (acfr["line_item"] == "Amounts Available for Appropriation")
    ].copy()
    expenditure = acfr[
        (acfr["section"] == "expenditure")
        & (acfr["line_item"] == "Total Charges to Appropriations")
    ].copy()

    revenue["variance_pct"] = revenue["variance"] / revenue["final_budget"] * 100
    expenditure["variance_pct"] = expenditure["variance"] / expenditure["final_budget"] * 100
    return revenue.sort_values("fiscal_year"), expenditure.sort_values("fiscal_year")


def save_budget_trends(
    all_rev: pd.Series,
    all_app: pd.Series,
    gf_rev: pd.Series,
    gf_app: pd.Series,
) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    pairs = [
        ("All Funds Official Totals", all_rev, all_app, COLORS["navy"], COLORS["orange"]),
        ("General Fund Official Totals", gf_rev, gf_app, COLORS["blue"], COLORS["red"]),
    ]

    for ax, (title, rev, app, rev_color, app_color) in zip(axes, pairs):
        years = rev.index
        ax.plot(years, rev.values / 1e9, color=rev_color, linewidth=2.6, marker="o", label="Revenue")
        ax.plot(years, app.values / 1e9, color=app_color, linewidth=2.6, marker="s", label="Appropriations")
        ax.fill_between(
            years,
            rev.values / 1e9,
            app.values / 1e9,
            color=COLORS["light_gray"],
            alpha=0.4,
        )
        ax.set_title(title)
        ax.set_xlabel("Fiscal year")
        ax.set_ylabel("Billions")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.1f}B"))
        ax.legend(frameon=False)
        ax.text(
            0.02,
            0.98,
            f"FY {years[-1]} revenue: {money_b(rev.iloc[-1])}\n"
            f"FY {years[-1]} appropriations: {money_b(app.iloc[-1])}\n"
            f"Gap: {money_m(app.iloc[-1] - rev.iloc[-1])}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": COLORS["light_gray"], "boxstyle": "round,pad=0.35"},
        )

    fig.suptitle("San Antonio Budget Scale, FY 2008-2026", y=1.02, fontsize=15, fontweight="bold")
    fig.tight_layout()
    path = ASSET_DIR / "budget_trends.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.name


def save_revenue_mix(revenue_mix: pd.DataFrame) -> str:
    folded = fold_small_categories(revenue_mix, keep_count=5)
    latest = revenue_mix.iloc[-1].sort_values(ascending=True)
    latest = latest[latest > 0]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={"width_ratios": [1.5, 1]})
    colors = [COLORS["navy"], COLORS["teal"], COLORS["gold"], COLORS["orange"], COLORS["red"], COLORS["gray"]]

    folded.plot.area(ax=axes[0], color=colors[: len(folded.columns)], alpha=0.9)
    axes[0].set_title("General Fund Revenue Mix Over Time")
    axes[0].set_xlabel("Fiscal year")
    axes[0].set_ylabel("Millions")
    axes[0].yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x / 1e6:,.0f}M"))
    axes[0].legend(frameon=False, fontsize=8, loc="upper left", ncol=2)

    bars = axes[1].barh(latest.index, latest.values / 1e6, color=COLORS["teal"])
    axes[1].set_title("FY 2026 Revenue Sources")
    axes[1].set_xlabel("Millions")
    axes[1].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.0f}M"))
    total = latest.sum()
    for bar, value in zip(bars, latest.values):
        axes[1].text(
            bar.get_width() + 6,
            bar.get_y() + bar.get_height() / 2,
            f"{value / total * 100:.1f}%",
            va="center",
            fontsize=9,
        )

    fig.tight_layout()
    path = ASSET_DIR / "general_fund_revenue_mix.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.name


def save_spending_mix(spending_mix: pd.DataFrame) -> str:
    folded = fold_small_categories(spending_mix, keep_count=6)
    latest = spending_mix.iloc[-1].sort_values(ascending=True)
    latest = latest[latest > 0]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [1.5, 1]})
    colors = [COLORS["navy"], COLORS["blue"], COLORS["teal"], COLORS["green"], COLORS["gold"], COLORS["orange"], COLORS["gray"]]

    folded.plot.area(ax=axes[0], color=colors[: len(folded.columns)], alpha=0.88)
    axes[0].set_title("Core Service Categories Over Time")
    axes[0].set_xlabel("Fiscal year")
    axes[0].set_ylabel("Billions")
    axes[0].yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x / 1e9:,.1f}B"))
    axes[0].legend(frameon=False, fontsize=8, loc="upper left", ncol=2)

    bars = axes[1].barh(latest.index, latest.values / 1e6, color=COLORS["navy"])
    axes[1].set_title("FY 2026 Core Service Mix")
    axes[1].set_xlabel("Millions")
    axes[1].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.0f}M"))
    total = latest.sum()
    for bar, value in zip(bars, latest.values):
        axes[1].text(
            bar.get_width() + 8,
            bar.get_y() + bar.get_height() / 2,
            f"{value / total * 100:.1f}%",
            va="center",
            fontsize=9,
        )

    fig.tight_layout()
    path = ASSET_DIR / "spending_mix.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.name


def save_budget_execution(revenue_exec: pd.DataFrame, expenditure_exec: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(11.5, 4.8))
    ax.plot(
        revenue_exec["fiscal_year"],
        revenue_exec["variance_pct"],
        color=COLORS["teal"],
        linewidth=2.5,
        marker="o",
        label="Revenue above final budget",
    )
    ax.plot(
        expenditure_exec["fiscal_year"],
        expenditure_exec["variance_pct"],
        color=COLORS["red"],
        linewidth=2.5,
        marker="s",
        label="Expenditures below final budget",
    )
    ax.axhline(0, color=COLORS["gray"], linewidth=1)
    ax.set_title("General Fund Budget Execution from ACFRs")
    ax.set_xlabel("Fiscal year")
    ax.set_ylabel("Variance vs. final budget")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    ax.legend(frameon=False)
    ax.text(
        0.99,
        0.03,
        "Coverage: FY 2010 and FY 2015-2024\nFY 2011-2014 ACFR tables were not text-extractable",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8.5,
        bbox={"facecolor": "white", "edgecolor": COLORS["light_gray"], "boxstyle": "round,pad=0.35"},
    )

    fig.tight_layout()
    path = ASSET_DIR / "budget_execution.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.name


def save_capital_program(
    cip_categories: pd.DataFrame,
    cip_revenue: pd.DataFrame,
    bond_status: pd.DataFrame,
) -> str:
    annual = (
        cip_categories[cip_categories["category"] != "Total"].pivot_table(
            index="fiscal_year",
            columns="category",
            values="fy_amount",
            aggfunc="sum",
            fill_value=0,
        )
        .sort_index()
    )
    latest_year = int(annual.index.max())
    airport = annual["Air Transportation"] if "Air Transportation" in annual.columns else pd.Series(0, index=annual.index)
    non_airport = annual.drop(columns=["Air Transportation"], errors="ignore").sum(axis=1)

    latest_rev = (
        cip_revenue[cip_revenue["fiscal_year"] == latest_year]
        .copy()
        .dropna(subset=["multiyear_amount"])
    )
    latest_rev = latest_rev[latest_rev["source"] != "Total"].sort_values("multiyear_amount", ascending=True)

    bond_cycles = (
        bond_status[bond_status["proposition"] == "Total"]
        .groupby("bond_program", as_index=False)["authorized"]
        .max()
        .sort_values("authorized")
    )
    latest_unissued = (
        bond_status[
            (bond_status["bond_program"] == "2022 G.O. Bonds")
            & (bond_status["proposition"] == "Total")
        ]
        .sort_values("fiscal_year")
        .iloc[-1]["unissued"]
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [1.35, 1]})

    axes[0].bar(non_airport.index, non_airport.values / 1e6, color=COLORS["blue"], label="Non-airport CIP")
    axes[0].bar(non_airport.index, airport.values / 1e6, bottom=non_airport.values / 1e6, color=COLORS["gold"], label="Air Transportation")
    axes[0].set_title("Annual Capital Program")
    axes[0].set_xlabel("Fiscal year")
    axes[0].set_ylabel("Millions")
    axes[0].yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.0f}M"))
    axes[0].legend(frameon=False)

    bars = axes[1].barh(
        latest_rev["source"],
        latest_rev["multiyear_amount"] / 1e6,
        color=COLORS["teal"],
    )
    axes[1].set_title(f"FY {latest_year} Multi-Year Funding Sources")
    axes[1].set_xlabel("Millions")
    axes[1].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.0f}M"))
    for bar, value in zip(bars, latest_rev["multiyear_amount"]):
        axes[1].text(
            bar.get_width() + 8,
            bar.get_y() + bar.get_height() / 2,
            money_m(value),
            va="center",
            fontsize=8.5,
        )

    fig.suptitle("Capital Program Snapshot", y=1.03, fontsize=14, fontweight="bold")
    fig.text(
        0.5,
        0.965,
        "Bond cycle authorizations: "
        + ", ".join(
            f"{row.bond_program.replace(' G.O. Bonds', '')} {row.authorized / 1e6:,.0f}M"
            for row in bond_cycles.itertuples()
        )
        + f"; 2022 bonds still unissued: {latest_unissued / 1e6:,.0f}M",
        ha="center",
        fontsize=10,
    )
    fig.tight_layout()
    path = ASSET_DIR / "capital_program.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.name


def write_report(
    assets: dict[str, str],
    metrics: dict[str, object],
) -> None:
    report = dedent(
        f"""\
        # San Antonio Budget Data Executive Summary

        Generated from the current project outputs on 2026-03-11.

        San Antonio does not publish the core budget and financial statements in machine-readable tabular form. The operating budget, capital program, and ACFR figures used here were reconstructed from adopted budget PDFs and ACFR PDFs by custom scrapers in this project.

        ## Headline findings

        - Core all-funds appropriations rose from {money_b(metrics["all_core_app_start"])} in FY 2008 to {money_b(metrics["all_core_app_end"])} in FY 2026, a {metrics["all_core_app_growth"]:.0f}% increase ({metrics["all_core_app_cagr"]:.1f}% CAGR).
        - The General Fund remains structurally concentrated: CPS Energy, property tax, and sales tax account for {metrics["gf_pillar_share"]:.1f}% of FY 2026 core revenue categories.
        - Public Safety is still the dominant service area at {metrics["public_safety_share"]:.1f}% of FY 2026 core appropriations, with debt service the next-largest category at {metrics["debt_service_share"]:.1f}%.
        - Budget execution is tight in every usable ACFR year: actual General Fund revenue beat final budget by an average of {metrics["avg_rev_var_pct"]:.1f}%, while actual expenditures finished {metrics["avg_exp_var_pct"]:.1f}% below final budget on average.
        - The capital program has expanded from {money_b(metrics["cip_start"])} annually in FY 2008 to {money_b(metrics["cip_end"])} in FY 2026. In the current six-year plan, aviation alone represents {metrics["airport_share"]:.1f}% of multi-year capital spending, and the 2022 bond program still has {money_m(metrics["unissued_2022_bonds"])} unissued.

        ## Visuals

        ![Budget trends](executive_summary_assets/{assets["budget_trends"]})

        Official totals from the adopted budget tables. The FY 2026 gap between revenues and appropriations represents planned use of transfers, balances, and reserves rather than an ACFR-style actual deficit.

        ![General Fund revenue mix](executive_summary_assets/{assets["revenue_mix"]})

        The General Fund is unusually dependent on utility revenue: CPS Energy alone is {metrics["cps_share"]:.1f}% of FY 2026 core revenue, and CPS plus SAWS together contribute {metrics["utilities_share"]:.1f}%.

        ![Spending mix](executive_summary_assets/{assets["spending_mix"]})

        Service-category charts exclude transfer, reserve, and ending-balance rows so category shares are not distorted by bookkeeping lines.

        ![Budget execution](executive_summary_assets/{assets["budget_execution"]})

        The ACFR extract is the cleanest evidence of execution quality, but it only covers FY 2010 and FY 2015-FY 2024 because FY 2011-FY 2014 ACFR tables were not text-extractable.

        ![Capital program](executive_summary_assets/{assets["capital_program"]})

        The capital plan is now airport-led. Excluding aviation, streets, parks, and drainage still account for {metrics["core_non_airport_share"]:.1f}% of the remaining FY 2026 multi-year CIP. Annual CIP bars are built from direct category sums because a few annual `Total` rows are inconsistent.

        ## Data review

        | Dataset | Coverage | Used in this brief | Review note |
        | --- | --- | --- | --- |
        | `combined_budget_summary.csv` | FY 2008-FY 2026 | Yes | Reconstructed from adopted budget PDFs. Strongest operating-budget file once transfers and reserve rows are separated from service categories. |
        | `acfr_budget_vs_actual.csv` | FY 2010 and FY 2015-FY 2024 | Yes | Reconstructed from ACFR PDFs. Good execution dataset within coverage, but FY 2011-FY 2014 tables were not text-extractable. |
        | `cip_categories.csv`, `cip_revenue_sources.csv`, `bond_status.csv` | FY 2008-FY 2026 / FY 2011-FY 2026 / FY 2015-FY 2026 | Yes | Reconstructed from budget PDFs. Strong enough for capital trends. Bond-cycle transitions need `max authorized` logic, and a few annual CIP `Total` rows are cleaner when rebuilt from category sums. |
        | `general_fund_departments.csv` | FY 2008-FY 2026 | No | Reconstructed from budget PDFs, but not reliable enough for headline use. Total rows fail reconciliation against the combined summary in many years, and FY 2024 plus FY 2026 contain obvious non-department artifacts. |
        | `all_funds_revenue.csv` | FY 2008-FY 2026 | No | Reconstructed from budget PDFs. Useful for exploration only after normalization; fund labels are inconsistent, and some latest-year fund totals appear incomplete. |
        | `Check Disbursements_03_10_2026.csv` | Mixed fiscal coverage | No | Raw export with a preamble row and incomplete period coverage. The project notebook notes FY 2025 is the only complete fiscal year in that file. |

        ## Recommendations

        - Add row-level validation and cross-file reconciliation tests to the PDF scrapers so totals in `general_fund_departments.csv` and `all_funds_revenue.csv` are checked automatically against `combined_budget_summary.csv`.
        - Treat `combined_budget_summary.csv` as the canonical source for executive trend reporting until the department and granular-revenue scrapes are hardened.
        - Convert the disbursement export into a processed table with a fixed schema, completeness flags by fiscal year, and documented exclusions so transaction-level analysis can join cleanly to the budget data.
        """
    )
    REPORT_PATH.write_text(report)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    combined = normalize_items(pd.read_csv(DATA_DIR / "combined_budget_summary.csv"))
    acfr = pd.read_csv(DATA_DIR / "acfr_budget_vs_actual.csv")
    cip_categories = pd.read_csv(DATA_DIR / "cip_categories.csv")
    cip_revenue = pd.read_csv(DATA_DIR / "cip_revenue_sources.csv")
    bond_status = pd.read_csv(DATA_DIR / "bond_status.csv")

    all_rev = exact_series(combined, "Total All Funds", "TOTAL REVENUES")
    all_app = exact_series(combined, "Total All Funds", "TOTAL APPROPRIATIONS")
    gf_rev_totals = exact_series(combined, "General Fund", "TOTAL REVENUES")
    gf_app = exact_series(combined, "General Fund", "TOTAL APPROPRIATIONS")

    revenue_mix = clean_revenue_mix(combined)
    spending_mix = clean_spending_mix(combined)
    revenue_exec, expenditure_exec = budget_execution(acfr)

    latest_fy = int(revenue_mix.index.max())
    latest_revenue = revenue_mix.loc[latest_fy]
    latest_spending = spending_mix.loc[latest_fy]

    all_core_app = exact_series(combined, "Total All Funds", "SUBTOTAL APPROPRIATIONS")
    cip_total = (
        cip_categories[cip_categories["category"] != "Total"]
        .groupby("fiscal_year")["fy_amount"]
        .sum()
        .sort_index()
    )
    latest_cip = cip_categories[cip_categories["fiscal_year"] == latest_fy]
    latest_cip_rev = cip_revenue[cip_revenue["fiscal_year"] == latest_fy]

    assets = {
        "budget_trends": save_budget_trends(all_rev, all_app, gf_rev_totals, gf_app),
        "revenue_mix": save_revenue_mix(revenue_mix),
        "spending_mix": save_spending_mix(spending_mix),
        "budget_execution": save_budget_execution(revenue_exec, expenditure_exec),
        "capital_program": save_capital_program(cip_categories, cip_revenue, bond_status),
    }

    metrics = {
        "all_core_app_start": float(all_core_app.iloc[0]),
        "all_core_app_end": float(all_core_app.iloc[-1]),
        "all_core_app_growth": (all_core_app.iloc[-1] / all_core_app.iloc[0] - 1) * 100,
        "all_core_app_cagr": cagr(all_core_app.iloc[0], all_core_app.iloc[-1], int(all_core_app.index[-1] - all_core_app.index[0])) * 100,
        "gf_pillar_share": float(
            latest_revenue[["CPS Energy", "Property Tax", "Sales Tax"]].sum() / latest_revenue.sum() * 100
        ),
        "cps_share": float(latest_revenue["CPS Energy"] / latest_revenue.sum() * 100),
        "utilities_share": float(
            latest_revenue[["CPS Energy", "San Antonio Water System"]].sum() / latest_revenue.sum() * 100
        ),
        "public_safety_share": float(latest_spending["Public Safety"] / latest_spending.sum() * 100),
        "debt_service_share": float(latest_spending["Debt Service"] / latest_spending.sum() * 100),
        "avg_rev_var_pct": float(revenue_exec["variance_pct"].mean()),
        "avg_exp_var_pct": float(expenditure_exec["variance_pct"].mean()),
        "cip_start": float(cip_total.iloc[0]),
        "cip_end": float(cip_total.iloc[-1]),
        "airport_share": float(
            latest_cip.loc[latest_cip["category"] == "Air Transportation", "multiyear_amount"].sum()
            / latest_cip.loc[latest_cip["category"] != "Total", "multiyear_amount"].sum()
            * 100
        ),
        "core_non_airport_share": float(
            latest_cip.loc[
                latest_cip["category"].isin(["Streets", "Parks", "Drainage"]),
                "multiyear_amount",
            ].sum()
            / latest_cip.loc[
                ~latest_cip["category"].isin(["Total", "Air Transportation"]),
                "multiyear_amount",
            ].sum()
            * 100
        ),
        "unissued_2022_bonds": float(
            bond_status[
                (bond_status["bond_program"] == "2022 G.O. Bonds")
                & (bond_status["proposition"] == "Total")
            ]
            .sort_values("fiscal_year")
            .iloc[-1]["unissued"]
        ),
    }

    write_report(assets, metrics)
    print(f"Wrote {REPORT_PATH.relative_to(BASE_DIR)}")
    for name in assets.values():
        print(f"Wrote {ASSET_DIR.relative_to(BASE_DIR) / name}")


if __name__ == "__main__":
    main()
