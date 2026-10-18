"""Loads the CDC WONDER 2024 natality CSV into a SQLite database (data/natality.db) so it can be queried with SQL."""
import sqlite3
import pandas as pd

RAW = "data/raw/natality_2024.csv"
DB = "data/natality.db"

df = pd.read_csv(RAW)

# footnote rows at the bottom of the export have no Births value
df = df[df["Births"].notna()].copy()

df = df.rename(columns={
    "County of Residence": "county",
    "County of Residence Code": "fips",
    "Source of Payment for Delivery": "payer",
    "Source of Payment for Delivery Code": "payer_code",
    "Month Prenatal Care Began": "pnc_month_label",
    "Month Prenatal Care Began Code": "pnc_month",
    "Births": "births",
    "Average OE Gestational Age (weeks)": "avg_ga_weeks",
    "Standard Deviation for Average OE Gestational Age": "sd_ga_weeks",
    "Average Birth Weight (grams)": "avg_bw_g",
}).drop(columns=["Notes"])

# "Not Applicable" becomes NULL
for c in ["avg_ga_weeks", "sd_ga_weeks", "avg_bw_g"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

for c in ["fips", "births", "pnc_month", "payer_code"]:
    df[c] = df[c].astype(int)

df["state"] = df["county"].str[-2:]
# counties under 100k people are pooled by state as "Unidentified Counties"
df["small_county_pool"] = df["county"].str.startswith("Unidentified").astype(int)

con = sqlite3.connect(DB)
df.to_sql("births_cell", con, if_exists="replace", index=False)
con.close()
print(f"Loaded {len(df):,} rows, {df.births.sum():,} births -> {DB}")
