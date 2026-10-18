"""Builds three Tableau-style dashboard PNGs from the CSVs in output/ and saves them to dashboards/.
Run after analysis.py and multivariate_model.py."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.colors import LinearSegmentedColormap, Normalize

os.makedirs("dashboards", exist_ok=True)

# ---------- load the stuff we already made ----------
raw = pd.read_csv("data/raw/natality_2024.csv")
timing = pd.read_csv("output/medicaid_by_care_timing.csv")
model = pd.read_csv("output/multivariate_model_results.csv")
gaps = pd.read_csv("output/medicaid_vs_private_gap_by_county.csv")
cells = pd.read_csv("output/tableau_cells.csv")
med_state = pd.read_csv("output/tableau_medicaid_state.csv")
med_cty = pd.read_csv("output/tableau_medicaid_county.csv")

# ---------- tableau-ish colors and fonts ----------
BLUE, ORANGE, RED, TEAL, GREY = "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#BAB0AC"
DARK, MID, LIGHT = "#333333", "#6b6b6b", "#e6e6e6"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": DARK,
    "axes.edgecolor": LIGHT, "axes.labelcolor": MID, "xtick.color": MID, "ytick.color": MID,
    "axes.spines.top": False, "axes.spines.right": False,
})


def weighted(x, w):
    return np.average(x, weights=w)


def new_dashboard(title, subtitle):
    """blank white canvas with a title bar on top, like a tableau dashboard"""
    fig = plt.figure(figsize=(16, 9), dpi=110, facecolor="white")
    fig.add_artist(Rectangle((0, 0.915), 1, 0.085, transform=fig.transFigure, color="#f3f3f3", zorder=0))
    fig.add_artist(Rectangle((0, 0.913), 1, 0.003, transform=fig.transFigure, color=BLUE, zorder=1))
    fig.text(0.02, 0.962, title, fontsize=19, fontweight="bold", va="center")
    fig.text(0.02, 0.928, subtitle, fontsize=10.5, color=MID, va="center")
    fig.text(0.98, 0.012, "Source: CDC WONDER Natality 2024. Averages by county, payer and month care began. Association, not cause.",
             ha="right", fontsize=8, color=MID)
    return fig


def kpi(fig, x, y, w, h, big, small, color):
    """a kpi tile (big number + label)"""
    ax = fig.add_axes([x, y, w, h])
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.04", fc="white",
                                ec=LIGHT, lw=1.2, transform=ax.transAxes))
    ax.add_patch(Rectangle((0, 0), 0.015, 1, color=color, transform=ax.transAxes))
    ax.text(0.5, 0.60, big, ha="center", va="center", fontsize=26, fontweight="bold", color=color, transform=ax.transAxes)
    ax.text(0.5, 0.20, small, ha="center", va="center", fontsize=9.5, color=MID, transform=ax.transAxes, linespacing=1.3)


def panel(ax, title):
    """sheet title with a grey underline"""
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color=DARK, pad=10)
    ax.grid(axis="y", color="#efefef", lw=0.8)
    ax.set_axisbelow(True)


def coef(outcome, predictor, which="No state effects"):
    r = model[(model.outcome == outcome) & (model.model == which) & (model.predictor == predictor)]
    return float(r.coef.iloc[0])


# ---------- numbers used on the dashboards ----------
# share with no first-trimester care by payer (known timing only, months 1-3 = early)
r = raw[raw.Births.notna() & raw["Source of Payment for Delivery"].isin(["Medicaid", "Private Insurance", "Self Pay"])]
r = r[r["Month Prenatal Care Began"] != "Unknown or Not Stated"]
r = r.assign(early=r["Month Prenatal Care Began"].isin(["1st month", "2nd month", "3rd month"]))
late = r.groupby("Source of Payment for Delivery").apply(
    lambda g: 100 * (1 - g.loc[g.early, "Births"].sum() / g.Births.sum()), include_groups=False)

no_care_bw = coef("avg_bw_g", "no_prenatal_care")
no_care_ga = coef("avg_ga_weeks", "no_prenatal_care")
medicaid_bw = coef("avg_bw_g", "is_medicaid")

# within-county gap, medicaid minus private (all births)
gap_bw = weighted(gaps.bw_gap, gaps.w)
gap_ga = weighted(gaps.ga_gap, gaps.w)
share_lower = 100 * (gaps.bw_gap < 0).mean()

# same comparison but only births where care started in month 1-3
e = cells[cells.pnc_month.between(1, 3) & cells.payer.isin(["Medicaid", "Private Insurance"])]
p = e.pivot_table(index=["county", "pnc_month"], columns="payer", values=["avg_bw_g", "births"]).dropna()
early_gap = weighted(p["avg_bw_g"]["Medicaid"] - p["avg_bw_g"]["Private Insurance"], p["births"].min(axis=1))

print(f"no-early-care share: {late.round(1).to_dict()}")
print(f"no care: {no_care_bw:.0f} g, {no_care_ga:.2f} wks | medicaid gap {gap_bw:.0f} g, {gap_ga:.2f} wks, "
      f"{share_lower:.0f}% of counties | early-care gap {early_gap:.0f} g")

# =====================================================================
# DASHBOARD 1: who misses care and what it goes with
# =====================================================================
fig = new_dashboard("Dashboard 1: Medicaid Mothers Miss Early Care, and No Care Is the Biggest Risk Signal",
                    "Births in 2024 | outcomes are average birth weight and gestational age, not preterm or low-birth-weight rates")
kpi(fig, 0.02, 0.74, 0.225, 0.14, f"{late['Medicaid']:.1f}%", "of Medicaid births had NO\nfirst-trimester care", ORANGE)
kpi(fig, 0.265, 0.74, 0.225, 0.14, f"{late['Private Insurance']:.1f}%", "of privately insured births had NO\nfirst-trimester care", BLUE)
kpi(fig, 0.51, 0.74, 0.225, 0.14, f"{no_care_bw:.0f} g", "lighter births with no prenatal care\n(vs births with care)", RED)
kpi(fig, 0.755, 0.74, 0.225, 0.14, f"{no_care_ga:.2f} wk", "shorter gestation with no prenatal care\n(vs births with care)", RED)

# sheet 1: no first-trimester care by payer
ax = fig.add_axes([0.05, 0.10, 0.25, 0.54])
order = ["Private Insurance", "Medicaid", "Self Pay"]
vals = [late[o] for o in order]
bars = ax.bar(["Private", "Medicaid", "Self-pay"], vals, color=[BLUE, ORANGE, GREY], width=0.6)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}%", ha="center", fontweight="bold")
ax.set_ylim(0, 55)
ax.set_ylabel("% of births")
panel(ax, "No first-trimester care, by payer")

# sheet 2: medicaid birth weight by care timing
ax = fig.add_axes([0.38, 0.10, 0.27, 0.54])
cols = [RED, BLUE, BLUE, BLUE]
bars = ax.bar(timing.timing, timing.avg_bw_g, color=cols, width=0.6)
for b, v in zip(bars, timing.avg_bw_g):
    ax.text(b.get_x() + b.get_width() / 2, v + 6, f"{v:,.0f} g", ha="center", fontweight="bold")
ax.set_ylim(2800, 3300)
ax.set_ylabel("Average birth weight (g), axis starts at 2,800")
panel(ax, "Medicaid births: birth weight by when care began")

# sheet 3: medicaid gestation spread by care timing
ax = fig.add_axes([0.73, 0.10, 0.25, 0.54])
bars = ax.bar(timing.timing, timing.sd_ga_weeks, color=cols, width=0.6)
for b, v in zip(bars, timing.sd_ga_weeks):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.2f}", ha="center", fontweight="bold")
ax.set_ylim(0, 4.2)
ax.set_ylabel("Spread of gestational age (SD, weeks)")
panel(ax, "Medicaid births: gestation spread (SD)")
fig.savefig("dashboards/care_access_gap.png")
plt.close(fig)

# =====================================================================
# DASHBOARD 2: medicaid gap is not just late care
# =====================================================================
fig = new_dashboard("Dashboard 2: Medicaid Births Are Lighter Than Private Births in the Same County",
                    "Comparing Medicaid and privately insured births inside each county so place is held constant")
kpi(fig, 0.02, 0.74, 0.225, 0.14, f"{gap_bw:.0f} g", "average Medicaid-vs-private gap\nwithin the same county", RED)
kpi(fig, 0.265, 0.74, 0.225, 0.14, f"{share_lower:.0f}%", "of counties where Medicaid births\nare lighter", ORANGE)
kpi(fig, 0.51, 0.74, 0.225, 0.14, f"{early_gap:.0f} g", "gap among births with care\nstarted in months 1-3", BLUE)
kpi(fig, 0.755, 0.74, 0.225, 0.14, f"{gap_ga:.2f} wk", "average gestational-age gap\n(Medicaid minus private)", TEAL)

# sheet 1: histogram of county gaps
ax = fig.add_axes([0.05, 0.10, 0.42, 0.54])
g = gaps[(gaps.n_med >= 30) & (gaps.n_priv >= 30)]
ax.hist(g.bw_gap.clip(-500, 300), bins=40, color=BLUE, edgecolor="white")
ax.axvline(0, color=DARK, lw=1.2)
ax.axvline(gap_bw, color=RED, lw=2, ls="--")
ax.text(gap_bw - 8, ax.get_ylim()[1] * 0.92, f"average {gap_bw:.0f} g", color=RED, ha="right", fontweight="bold")
ax.set_xlabel("Medicaid minus private birth weight in the county (g)")
ax.set_ylabel("Number of counties")
panel(ax, "Distribution of the within-county gap (each bar = group of counties)")

# sheet 2: gap by care timing group, same method (county x timing, weighted by smaller group)
rows = []
for name, lo, hi in [("Months 1-3", 1, 3), ("Months 4-6", 4, 6), ("Months 7+", 7, 9)]:
    d = cells[cells.pnc_month.between(lo, hi) & cells.payer.isin(["Medicaid", "Private Insurance"])]
    pv = d.pivot_table(index=["county", "pnc_month"], columns="payer", values=["avg_bw_g", "births"]).dropna()
    rows.append((name, weighted(pv["avg_bw_g"]["Medicaid"] - pv["avg_bw_g"]["Private Insurance"], pv["births"].min(axis=1))))
ax = fig.add_axes([0.56, 0.10, 0.40, 0.54])
bars = ax.barh([r_[0] for r_ in rows][::-1], [r_[1] for r_ in rows][::-1], color=ORANGE, height=0.5)
for b, v in zip(bars, [r_[1] for r_ in rows][::-1]):
    ax.text(v - 3, b.get_y() + b.get_height() / 2, f"{v:.0f} g", va="center", ha="right", fontweight="bold", color=DARK)
ax.set_xlim(-170, 0)
ax.set_xlabel("Medicaid minus private birth weight (g), same county and same care-start group")
ax.grid(axis="x", color="#efefef")
ax.grid(axis="y", visible=False)
panel(ax, "The gap shows up whether care started early or late")
fig.savefig("dashboards/medicaid_vs_private_gap.png")
plt.close(fig)

# =====================================================================
# DASHBOARD 3: geography
# =====================================================================
fig = new_dashboard("Dashboard 3: The Same Payer Fares Very Differently Depending on the State",
                    "Medicaid-paid births only | average birth weight by state and by county access to early prenatal care")

# state tile grid map (rows, cols), so we don't need map files
grid = {"AK": (0, 0), "ME": (0, 10), "VT": (1, 9), "NH": (1, 10), "WA": (2, 0), "ID": (2, 1), "MT": (2, 2), "ND": (2, 3),
        "MN": (2, 4), "IL": (2, 5), "WI": (2, 6), "MI": (2, 7), "NY": (2, 8), "RI": (2, 9), "MA": (2, 10),
        "OR": (3, 0), "NV": (3, 1), "WY": (3, 2), "SD": (3, 3), "IA": (3, 4), "IN": (3, 5), "OH": (3, 6), "PA": (3, 7),
        "NJ": (3, 8), "CT": (3, 9), "CA": (4, 0), "UT": (4, 1), "CO": (4, 2), "NE": (4, 3), "MO": (4, 4), "KY": (4, 5),
        "WV": (4, 6), "VA": (4, 7), "MD": (4, 8), "DE": (4, 9), "AZ": (5, 1), "NM": (5, 2), "KS": (5, 3), "AR": (5, 4),
        "TN": (5, 5), "NC": (5, 6), "SC": (5, 7), "DC": (5, 8), "OK": (6, 3), "LA": (6, 4), "MS": (6, 5), "AL": (6, 6),
        "GA": (6, 7), "HI": (7, 0), "TX": (7, 3), "FL": (7, 8)}
st = med_state[med_state.medicaid_births >= 3000].set_index("state")
cmap = LinearSegmentedColormap.from_list("tab", ["#E15759", "#F4A582", "#FDEBD0", "#A9C6DE", "#4E79A7"])
norm = Normalize(st.avg_bw_g.min(), st.avg_bw_g.max())

ax = fig.add_axes([0.02, 0.08, 0.40, 0.80])
ax.set_xlim(-0.2, 11.2)
ax.set_ylim(7.9, -0.3)
ax.set_aspect("equal")
ax.axis("off")
for s, (rr, cc) in grid.items():
    if s in st.index:
        col = cmap(norm(st.loc[s, "avg_bw_g"]))
        txt = "white" if norm(st.loc[s, "avg_bw_g"]) < 0.15 or norm(st.loc[s, "avg_bw_g"]) > 0.8 else DARK
    else:
        col, txt = "#f0f0f0", "#aaaaaa"  # not enough medicaid births to show
    ax.add_patch(Rectangle((cc, rr), 0.92, 0.92, fc=col, ec="white"))
    ax.text(cc + 0.46, rr + 0.46, s, ha="center", va="center", fontsize=8.5, fontweight="bold", color=txt)
ax.set_title("Average Medicaid birth weight by state (grey = under 3,000 Medicaid births)", loc="left", fontsize=11,
             fontweight="bold", pad=6)
cax = fig.add_axes([0.05, 0.06, 0.25, 0.015])
cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="horizontal")
cb.set_label("grams", fontsize=8)
cb.outline.set_visible(False)

# ranked bars: 5 lowest and 5 highest
ranked = st.sort_values("avg_bw_g")
show = pd.concat([ranked.head(5), ranked.tail(5)])
ax = fig.add_axes([0.52, 0.52, 0.45, 0.36])
colors = [RED] * 5 + [BLUE] * 5
bars = ax.barh(show.index[::-1], show.avg_bw_g[::-1], color=colors[::-1], height=0.65)
for b, v in zip(bars, show.avg_bw_g[::-1]):
    ax.text(v + 3, b.get_y() + b.get_height() / 2, f"{v:,.0f} g", va="center", fontsize=9, fontweight="bold")
ax.set_xlim(2900, 3400)
ax.set_xlabel("Average Medicaid birth weight (g), axis starts at 2,900")
ax.grid(axis="x", color="#efefef")
ax.grid(axis="y", visible=False)
panel(ax, f"Five lowest and five highest states ({show.avg_bw_g.max() - show.avg_bw_g.min():.0f} g spread)")

# scatter: county early-care access vs medicaid birth weight
ax = fig.add_axes([0.54, 0.09, 0.43, 0.32])
c = med_cty[(med_cty.medicaid_births >= 300) & med_cty.pct_not_early_pnc.notna()]
ax.scatter(c.pct_not_early_pnc, c.avg_bw_g, s=np.sqrt(c.medicaid_births) * 0.9, alpha=0.45, color=ORANGE, edgecolor="white", lw=0.4)
m, b0 = np.polyfit(c.pct_not_early_pnc, c.avg_bw_g, 1, w=np.sqrt(c.medicaid_births))
xs = np.array([c.pct_not_early_pnc.min(), c.pct_not_early_pnc.max()])
ax.plot(xs, m * xs + b0, color=DARK, lw=1.6, ls="--")
ax.set_xlabel("% of Medicaid births with no first-trimester care (county)")
ax.set_ylabel("Avg Medicaid birth weight (g)")
ax.grid(color="#efefef")
panel(ax, "Counties with weaker early-care access (dot size = Medicaid births)")
fig.savefig("dashboards/geography.png")
plt.close(fig)
print("saved 3 dashboards to dashboards/")
