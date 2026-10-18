"""Multivariate model at the county x payer x care-timing cell level (the closest this dataset gets to a logistic-regression risk-factor model): does Medicaid, a small-county location, or later prenatal care predict lower birth weight and shorter gestation when all are considered together?"""
import sqlite3
import numpy as np
import pandas as pd
from scipy import stats

con = sqlite3.connect("data/natality.db")
d = pd.read_sql("SELECT * FROM births_cell", con)

# keep Medicaid vs private insurance, known care timing, known outcomes
d = d[d.payer.isin(["Medicaid", "Private Insurance"]) & (d.pnc_month != 99) & (d.pnc_month <= 9)].copy()
d["is_medicaid"] = (d.payer == "Medicaid").astype(float)
d["is_small_county"] = d.small_county_pool.astype(float)
d["no_prenatal_care"] = (d.pnc_month == 0).astype(float)
# month care began, 1-9 (no care is its own flag, set to 0 here)
d["month_care_began"] = np.where(d.pnc_month == 0, 0, d.pnc_month).astype(float)
d["medicaid_x_small"] = d.is_medicaid * d.is_small_county

def fit(df, y, xs, fe_state=False):
    """Births-weighted least squares, standard errors clustered by county."""
    df = df.dropna(subset=[y]).copy()
    X = df[xs].copy()
    X.insert(0, "const", 1.0)
    if fe_state:
        X = pd.concat([X, pd.get_dummies(df.state, drop_first=True, dtype=float)], axis=1)
    w = np.sqrt(df.births.values)
    Xw, yw = X.values * w[:, None], df[y].values * w
    beta = np.linalg.lstsq(Xw, yw, rcond=None)[0]
    e = yw - Xw @ beta
    XtXi = np.linalg.pinv(Xw.T @ Xw)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for _, idx in df.groupby("county").indices.items():
        s = Xw[idx].T @ e[idx]
        meat += np.outer(s, s)
    G, n, k = df.county.nunique(), len(df), X.shape[1]
    cov = XtXi @ meat @ XtXi * (G / (G - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(cov))
    p = 2 * (1 - stats.t.cdf(np.abs(beta / se), G - 1))
    out = pd.DataFrame({"coef": beta, "se": se, "p": p}, index=X.columns).loc[["const"] + xs]
    return out, n, G

xs = ["is_medicaid", "is_small_county", "medicaid_x_small", "no_prenatal_care", "month_care_began"]
rows = []
for y, unit in [("avg_bw_g", "grams"), ("avg_ga_weeks", "weeks")]:
    for fe, name in [(False, "No state effects"), (True, "With state effects")]:
        res, n, G = fit(d, y, xs, fe)
        print(f"\n{y} ({unit}) | {name} | {n:,} cells, {G} counties")
        print(res.round(4))
        for v in xs:
            rows.append({"outcome": y, "model": name, "predictor": v, "coef": res.loc[v, "coef"],
                         "se": res.loc[v, "se"], "p": res.loc[v, "p"], "cells": n, "clusters": G})
pd.DataFrame(rows).to_csv("output/multivariate_model_results.csv", index=False)
