-- county_summary.sql : builds one row per county for the analysis + Tableau
-- Access proxies come only from this dataset: prenatal-care timing, payer mix,
-- and county size (small_county_pool).

DROP TABLE IF EXISTS county_summary;

CREATE TABLE county_summary AS
WITH base AS (
    SELECT county, fips, state, small_county_pool,
           SUM(births) AS births_all,

           -- payer shares use births with a known payer
           SUM(CASE WHEN payer <> 'Unknown or Not Stated' THEN births END) AS births_payer_known,
           SUM(CASE WHEN payer = 'Medicaid' THEN births END)  AS births_medicaid,
           SUM(CASE WHEN payer = 'Self Pay' THEN births END)  AS births_selfpay,

           -- prenatal-care shares use births with a known start month
           SUM(CASE WHEN pnc_month <> 99 THEN births END)                    AS births_pnc_known,
           SUM(CASE WHEN pnc_month = 0 THEN births END)                      AS births_no_pnc,
           SUM(CASE WHEN pnc_month BETWEEN 1 AND 3 THEN births END)          AS births_early_pnc,
           SUM(CASE WHEN pnc_month >= 7 AND pnc_month <> 99 THEN births END) AS births_late_pnc,

           -- outcome averages (weighted by births)
           SUM(CASE WHEN avg_ga_weeks IS NOT NULL THEN births END) AS n_ga,
           SUM(births * avg_ga_weeks)                              AS sum_ga,
           SUM(CASE WHEN avg_bw_g IS NOT NULL THEN births END)     AS n_bw,
           SUM(births * avg_bw_g)                                  AS sum_bw
    FROM births_cell
    GROUP BY county, fips, state, small_county_pool
),
-- pooled variance of gestational age: within-cell variance + between-cell variance
var_calc AS (
    SELECT c.county,
           SUM(c.births * (c.sd_ga_weeks * c.sd_ga_weeks
               + (c.avg_ga_weeks - b.sum_ga / b.n_ga) * (c.avg_ga_weeks - b.sum_ga / b.n_ga))) / b.n_ga AS ga_var
    FROM births_cell c
    JOIN base b ON b.county = c.county
    WHERE c.avg_ga_weeks IS NOT NULL AND c.sd_ga_weeks IS NOT NULL
    GROUP BY c.county, b.n_ga, b.sum_ga
)
SELECT b.county, b.fips, b.state, b.small_county_pool, b.births_all,
       ROUND(100.0 * b.births_medicaid / b.births_payer_known, 2) AS pct_medicaid,
       ROUND(100.0 * b.births_selfpay  / b.births_payer_known, 2) AS pct_self_pay,
       ROUND(100.0 * b.births_no_pnc    / b.births_pnc_known, 2)  AS pct_no_pnc,
       ROUND(100.0 * b.births_early_pnc / b.births_pnc_known, 2)  AS pct_early_pnc,
       ROUND(100.0 * b.births_late_pnc  / b.births_pnc_known, 2)  AS pct_late_pnc,
       ROUND(b.sum_ga / b.n_ga, 3) AS avg_ga_weeks,
       ROUND(b.sum_bw / b.n_bw, 1) AS avg_bw_g,
       ROUND(SQRT(v.ga_var), 3)    AS sd_ga_weeks
FROM base b
LEFT JOIN var_calc v ON v.county = b.county;

SELECT COUNT(*) AS counties_built FROM county_summary;
