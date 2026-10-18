"""County-level analysis of prenatal care access, Medicaid reliance and birth outcomes (gestational age, birth weight). Prints results and exports the CSVs used in Tableau."""
import sqlite3
import numpy as np
import pandas as pd
from scipy import stats

pd.set_option("display.width", 220, "display.max_columns", 30)
con = sqlite3.connect("data/natality.db")
cty = pd.read_sql("SELECT * FROM county_summary", con)
cell = pd.read_sql("SELECT * FROM births_cell", con)

# no-care % is hidden when a county has under 10 such births, so use "no first-trimester care" instead
cty["pct_not_early_pnc"] = (100 - cty["pct_early_pnc"]).round(2)
cty["log_births"] = np.log(cty["births_all"])
cty["county_type"] = np.where(cty["small_county_pool"] == 1, "Small counties (<100k, pooled)", "Larger county (100k+)")

# helpers
def wavg(x, w):
    m = x.notna()
    return (x[m] * w[m]).sum() / w[m].sum()

def wls(df, y, xs, fe=None):
    """Births-weighted least squares with robust standard errors; predictors are z-scored (effect of +1 SD)."""
    d = df.dropna(subset=[y] + xs).copy()
    X = d[xs].apply(lambda s: (s - s.mean()) / s.std())
    X.insert(0, "const", 1.0)
    if fe:
        X = pd.concat([X, pd.get_dummies(d[fe], drop_first=True, dtype=float)], axis=1)
    w = d["births_all"].values
    Xv, yv = X.values, d[y].values
    W = np.sqrt(w)
    Xw, yw = Xv * W[:, None], yv * W
    beta = np.linalg.lstsq(Xw, yw, rcond=None)[0]
    resid = yw - Xw @ beta
    XtXi = np.linalg.pinv(Xw.T @ Xw)
    meat = (Xw * resid[:, None]).T @ (Xw * resid[:, None])
    n, k = Xw.shape
    cov = XtXi @ meat @ XtXi * n / (n - k)
    se = np.sqrt(np.diag(cov))
    p = 2 * (1 - stats.t.cdf(np.abs(beta / se), n - k))
    ss_res = (resid ** 2).sum()
    ss_tot = (((yv - np.average(yv, weights=w)) ** 2) * w).sum()
    out = pd.DataFrame({"coef_per_1SD": beta, "se": se, "p": p}, index=X.columns)
    return out.loc[["const"] + xs], 1 - ss_res / ss_tot, n

# headline numbers
print("\n=== 1. Headline ===")
print(f"Counties/pools: {len(cty)}, births: {cty.births_all.sum():,}")
for c in ["avg_ga_weeks", "avg_bw_g", "pct_medicaid", "pct_not_early_pnc"]:
    print(f"{c}: weighted mean {wavg(cty[c], cty.births_all):.2f}, county range {cty[c].min():.2f} to {cty[c].max():.2f}")

# correlations
print("\n=== 2. Correlations (county level, Spearman) ===")
vars_ = ["pct_medicaid", "pct_self_pay", "pct_not_early_pnc", "pct_no_pnc", "small_county_pool", "avg_ga_weeks", "avg_bw_g", "sd_ga_weeks"]
corr = cty[vars_].corr(method="spearman").round(2)
print(corr.loc[["pct_medicaid", "pct_self_pay", "pct_not_early_pnc", "pct_no_pnc", "small_county_pool"], ["avg_ga_weeks", "avg_bw_g", "sd_ga_weeks"]])

# quartiles
def quartile_table(col, label):
    d = cty.dropna(subset=[col]).copy()
    d["q"] = pd.qcut(d[col], 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"])
    rows = []
    for q, g in d.groupby("q", observed=True):
        rows.append({"measure": label, "quartile": q, "counties": len(g), "births": g.births_all.sum(),
                     "range": f"{g[col].min():.1f}-{g[col].max():.1f}",
                     "avg_ga_weeks": wavg(g.avg_ga_weeks, g.births_all),
                     "avg_bw_g": wavg(g.avg_bw_g, g.births_all),
                     "sd_ga_weeks": wavg(g.sd_ga_weeks, g.births_all)})
    return pd.DataFrame(rows)

quart = pd.concat([quartile_table("pct_medicaid", "Medicaid share"),
                   quartile_table("pct_not_early_pnc", "No first-trimester care share"),
                   quartile_table("pct_self_pay", "Self-pay (uninsured proxy) share")])
print("\n=== 3. Outcomes by quartile of each vulnerability measure ===")
print(quart.round(2).to_string(index=False))

# regressions
print("\n=== 4. Regressions (births-weighted, predictors in SD units) ===")
xs = ["pct_medicaid", "pct_not_early_pnc", "pct_self_pay", "small_county_pool", "log_births"]
reg_rows = []
for y in ["avg_bw_g", "avg_ga_weeks", "sd_ga_weeks"]:
    for fe, name in [(None, "No state effects"), ("state", "With state effects")]:
        res, r2, n = wls(cty, y, xs, fe)
        print(f"\n{y} | {name} | n={n} | R2={r2:.2f}")
        print(res.round(4))
        for v in xs:
            reg_rows.append({"outcome": y, "model": name, "predictor": v, "coef_per_1SD": res.loc[v, "coef_per_1SD"],
                             "se": res.loc[v, "se"], "p": res.loc[v, "p"], "r2": r2, "n": n})

# who bears the burden?
print("\n=== 5. Burden concentration ===")
cut = cty.avg_bw_g.quantile(0.20)
cty["bottom_fifth_bw"] = cty.avg_bw_g <= cut
hi_med = cty.pct_medicaid >= cty.pct_medicaid.quantile(0.75)
hi_late = cty.pct_not_early_pnc >= cty.pct_not_early_pnc.quantile(0.75)
for label, mask in [("Top-quartile Medicaid counties", hi_med), ("Top-quartile no-early-care counties", hi_late),
                    ("Both", hi_med & hi_late), ("Small-county pools", cty.small_county_pool == 1)]:
    share_births = cty.loc[mask, "births_all"].sum() / cty.births_all.sum()
    in_bottom = cty.loc[mask & cty.bottom_fifth_bw, "births_all"].sum() / cty.loc[cty.bottom_fifth_bw, "births_all"].sum()
    print(f"{label}: {mask.sum()} counties, {share_births:.1%} of births, {in_bottom:.1%} of births in the lowest-birth-weight fifth of counties")
cty["both_flag"] = np.select([hi_med & hi_late, hi_med, hi_late], ["High Medicaid + low early care", "High Medicaid only", "Low early care only"], "Neither")
both = cty.groupby("both_flag").apply(lambda g: pd.Series({
    "counties": len(g), "births": g.births_all.sum(),
    "avg_ga_weeks": wavg(g.avg_ga_weeks, g.births_all), "avg_bw_g": wavg(g.avg_bw_g, g.births_all),
    "sd_ga_weeks": wavg(g.sd_ga_weeks, g.births_all)}), include_groups=False)
print(both.round(2))
both.to_csv("output/risk_group_summary.csv")

# small counties vs larger
print("\n=== 6. Small-county pools vs larger counties ===")
print(cty.groupby("county_type").apply(lambda g: pd.Series({
    "units": len(g), "births": g.births_all.sum(), "pct_medicaid": wavg(g.pct_medicaid, g.births_all),
    "pct_not_early_pnc": wavg(g.pct_not_early_pnc, g.births_all),
    "avg_ga_weeks": wavg(g.avg_ga_weeks, g.births_all), "avg_bw_g": wavg(g.avg_bw_g, g.births_all)}), include_groups=False).round(2))

# payer gap inside the same county
print("\n=== 7. Medicaid vs Private gap WITHIN the same county ===")
cell["avg_bw_x"] = cell.avg_bw_g * cell.births
cell["avg_ga_x"] = cell.avg_ga_weeks * cell.births
cell["bw_n"] = cell.births.where(cell.avg_bw_g.notna(), 0)
cell["ga_n"] = cell.births.where(cell.avg_ga_weeks.notna(), 0)
pc = cell[cell.payer.isin(["Medicaid", "Private Insurance"])].groupby(["county", "state", "small_county_pool", "payer"]).agg(
    bw_x=("avg_bw_x", "sum"), bw_n=("bw_n", "sum"), ga_x=("avg_ga_x", "sum"), ga_n=("ga_n", "sum"), births=("births", "sum")).reset_index()
pc["bw"] = pc.bw_x / pc.bw_n
pc["ga"] = pc.ga_x / pc.ga_n
wide = pc.pivot(index=["county", "state", "small_county_pool"], columns="payer", values=["bw", "ga", "births"]).dropna().reset_index()
wide.columns = ["county", "state", "small_county_pool", "bw_med", "bw_priv", "ga_med", "ga_priv", "n_med", "n_priv"]
wide["bw_gap"] = wide.bw_med - wide.bw_priv
wide["ga_gap"] = wide.ga_med - wide.ga_priv
wide["w"] = wide.n_med + wide.n_priv
wide = wide[(wide.n_med >= 30) & (wide.n_priv >= 30)]
print(f"counties with both groups (30+ births each): {len(wide)}")
print(f"avg Medicaid-minus-private gap: {wavg(wide.bw_gap, wide.w):.0f} g, {wavg(wide.ga_gap, wide.w):.2f} weeks")
print(f"counties where Medicaid is lower on birth weight: {(wide.bw_gap < 0).mean():.1%}")
print(wide.groupby("small_county_pool").apply(lambda g: pd.Series({
    "counties": len(g), "bw_gap_g": wavg(g.bw_gap, g.w), "ga_gap_wks": wavg(g.ga_gap, g.w)}), include_groups=False).round(2))
wide.sort_values("bw_gap").to_csv("output/medicaid_vs_private_gap_by_county.csv", index=False)
print("Largest gaps (counties with 300+ Medicaid births):")
print(wide[wide.n_med >= 300].sort_values("bw_gap").head(8)[["county", "bw_med", "bw_priv", "bw_gap", "n_med"]].round(0).to_string(index=False))

# care timing groups
print("\n=== 8. Care timing and payer ===")
cell["timing"] = np.select([cell.pnc_month == 0, cell.pnc_month.between(1, 3), cell.pnc_month.between(4, 6), cell.pnc_month >= 7 ],
                           ["No care", "Months 1-3", "Months 4-6", "Months 7+"], "Unknown")
def pooled_sd(g):
    g = g.dropna(subset=["avg_ga_weeks", "sd_ga_weeks"])
    M = (g.births * g.avg_ga_weeks).sum() / g.births.sum()
    return np.sqrt((g.births * (g.sd_ga_weeks ** 2 + (g.avg_ga_weeks - M) ** 2)).sum() / g.births.sum())
timing = cell[cell.timing != "Unknown"].groupby("timing").apply(lambda g: pd.Series({
    "births": g.births.sum(), "avg_ga_weeks": wavg(g.avg_ga_weeks, g.births),
    "avg_bw_g": wavg(g.avg_bw_g, g.births), "sd_ga_weeks": pooled_sd(g)}), include_groups=False)
print(timing.round(2))
payer_sd = cell[cell.payer != "Unknown or Not Stated"].groupby("payer").apply(lambda g: pd.Series({
    "births": g.births.sum(), "avg_ga_weeks": wavg(g.avg_ga_weeks, g.births), "avg_bw_g": wavg(g.avg_bw_g, g.births),
    "sd_ga_weeks": pooled_sd(g)}), include_groups=False)
print(payer_sd.round(2))

# state table + extreme counties
state = cty.groupby("state").apply(lambda g: pd.Series({
    "births": g.births_all.sum(), "pct_medicaid": wavg(g.pct_medicaid, g.births_all),
    "pct_not_early_pnc": wavg(g.pct_not_early_pnc, g.births_all),
    "avg_ga_weeks": wavg(g.avg_ga_weeks, g.births_all), "avg_bw_g": wavg(g.avg_bw_g, g.births_all),
    "sd_ga_weeks": wavg(g.sd_ga_weeks, g.births_all)}), include_groups=False).reset_index()
print("\n=== 9. Lowest / highest birth-weight states ===")
print(state.sort_values("avg_bw_g").head(5).round(1).to_string(index=False))
print(state.sort_values("avg_bw_g").tail(5).round(1).to_string(index=False))
big = cty[(cty.births_all >= 2000) & (cty.small_county_pool == 0)]
print("\nLowest birth-weight counties (2,000+ births):")
print(big.sort_values("avg_bw_g").head(8)[["county", "births_all", "pct_medicaid", "pct_not_early_pnc", "avg_ga_weeks", "avg_bw_g"]].round(1).to_string(index=False))
print("Highest:")
print(big.sort_values("avg_bw_g").tail(5)[["county", "births_all", "pct_medicaid", "pct_not_early_pnc", "avg_ga_weeks", "avg_bw_g"]].round(1).to_string(index=False))

# exports for Tableau
cty["fips5"] = cty.fips.astype(str).str.zfill(5)
cty["county_name"] = cty.county.str.rsplit(",", n=1).str[0]
cty["mappable"] = np.where(cty.small_county_pool == 1, "No (pooled)", "Yes")
cty["risk_group"] = cty["both_flag"]
labels = ["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"]
cty["medicaid_quartile"] = pd.qcut(cty.pct_medicaid, 4, labels=labels)
cty["no_early_care_quartile"] = pd.qcut(cty.pct_not_early_pnc, 4, labels=labels)
cty.drop(columns=["both_flag", "bottom_fifth_bw", "log_births"]).to_csv("output/tableau_county.csv", index=False)
state.to_csv("output/tableau_state.csv", index=False)
cell_out = cell[["county", "state", "small_county_pool", "payer", "pnc_month", "pnc_month_label", "timing", "births", "avg_ga_weeks", "sd_ga_weeks", "avg_bw_g"]]
cell_out.to_csv("output/tableau_cells.csv", index=False)
quart.to_csv("output/quartile_table.csv", index=False)
timing.to_csv("output/care_timing_summary.csv")

# Medicaid-reliant births only (payer = Medicaid)
print("\n=== 10. Medicaid-paid births only ===")
med = cell[cell.payer == "Medicaid"].copy()
known = med[med.pnc_month != 99]

adequacy = known.groupby("timing").apply(lambda g: pd.Series({
    "medicaid_births": g.births.sum(), "pct_of_medicaid_births": 100 * g.births.sum() / known.births.sum(),
    "avg_ga_weeks": wavg(g.avg_ga_weeks, g.births), "avg_bw_g": wavg(g.avg_bw_g, g.births),
    "sd_ga_weeks": pooled_sd(g)}), include_groups=False).loc[["No care", "Months 1-3", "Months 4-6", "Months 7+"]]
print(adequacy.round(2))
adequacy.to_csv("output/medicaid_by_care_timing.csv")

def med_summary(g):
    k = g[g.pnc_month != 99]
    return pd.Series({
        "medicaid_births": g.births.sum(),
        "pct_not_early_pnc": 100 * k[~k.pnc_month.between(1, 3)].births.sum() / k.births.sum(),
        "pct_no_pnc": 100 * k[k.pnc_month == 0].births.sum() / k.births.sum(),
        "avg_ga_weeks": wavg(g.avg_ga_weeks, g.births), "avg_bw_g": wavg(g.avg_bw_g, g.births)})

geo = med.groupby("small_county_pool").apply(med_summary, include_groups=False)
geo.index = ["Larger counties (100k+)", "Small-county pools"]
print(geo.round(2))

med_state = med.groupby("state").apply(med_summary, include_groups=False).reset_index()
med_state.to_csv("output/tableau_medicaid_state.csv", index=False)
ms = med_state[med_state.medicaid_births > 3000].sort_values("avg_bw_g")
print(f"State range for Medicaid births: {ms.avg_bw_g.min():.0f} g ({ms.iloc[0].state}) to {ms.avg_bw_g.max():.0f} g ({ms.iloc[-1].state})")

med_cty = med.groupby(["county", "state", "small_county_pool"]).apply(med_summary, include_groups=False).reset_index()
med_cty = med_cty.merge(cty[["county", "fips5", "county_name", "mappable", "pct_medicaid", "births_all"]], on="county")
med_cty = med_cty.rename(columns={"pct_medicaid": "county_medicaid_share"})
med_cty = med_cty[med_cty.medicaid_births >= 100].copy()
med_cty["access_quartile"] = pd.qcut(med_cty.pct_not_early_pnc, 4, labels=["Q1 (best access)", "Q2", "Q3", "Q4 (worst access)"])
med_cty["community_medicaid_quartile"] = pd.qcut(med_cty.county_medicaid_share, 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"])
med_cty.to_csv("output/tableau_medicaid_county.csv", index=False)

rows = []
for col, label in [("access_quartile", "County prenatal-care access (Medicaid births)"), ("community_medicaid_quartile", "County Medicaid concentration")]:
    for q, g in med_cty.groupby(col, observed=True):
        rows.append({"grouping": label, "quartile": q, "counties": len(g), "medicaid_births": g.medicaid_births.sum(),
                     "pct_not_early_pnc": wavg(g.pct_not_early_pnc, g.medicaid_births),
                     "avg_ga_weeks": wavg(g.avg_ga_weeks, g.medicaid_births), "avg_bw_g": wavg(g.avg_bw_g, g.medicaid_births)})
medq = pd.DataFrame(rows)
print(medq.round(2).to_string(index=False))

# regression on Medicaid births only: does county care adequacy / community context predict their outcomes?
med_cty["births_all"] = med_cty["medicaid_births"]
med_cty["log_med_births"] = np.log(med_cty.medicaid_births)
xs_med = ["pct_not_early_pnc", "county_medicaid_share", "small_county_pool", "log_med_births"]
mrows = []
for y in ["avg_bw_g", "avg_ga_weeks"]:
    for fe, name in [(None, "No state effects"), ("state", "With state effects")]:
        res, r2, n = wls(med_cty, y, xs_med, fe)
        print(f"\nMedicaid births | {y} | {name} | n={n} | R2={r2:.2f}")
        print(res.round(4))
        for v in xs_med:
            mrows.append({"outcome": y, "model": name, "predictor": v, "coef_per_1SD": res.loc[v, "coef_per_1SD"],
                          "se": res.loc[v, "se"], "p": res.loc[v, "p"], "r2": r2, "n": n})
pd.DataFrame(mrows).to_csv("output/medicaid_regression_results.csv", index=False)

print("\nDone. Files written to output/")
