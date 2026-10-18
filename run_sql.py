"""Runs a .sql file against the database and prints each result set."""
import sqlite3, sys, re
import pandas as pd
pd.set_option("display.width", 220, "display.max_columns", 30)
con = sqlite3.connect("data/natality.db")
text = open(sys.argv[1]).read()
for stmt in [s.strip() for s in text.split(";") if s.strip()]:
    body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
    if not body:
        continue
    head = stmt.splitlines()[0]
    if body.upper().startswith("SELECT") or body.upper().startswith("WITH"):
        print(f"\n{head}")
        print(pd.read_sql(body, con).to_string(index=False))
    else:
        con.execute(body); con.commit()
