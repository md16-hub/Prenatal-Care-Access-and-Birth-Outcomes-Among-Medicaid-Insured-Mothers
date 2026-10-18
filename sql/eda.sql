-- eda.sql : exploratory queries on births_cell
-- Unit of the table: one row = county x payer x prenatal-care-start month (2024 births)

-- Q1: size of the data
SELECT COUNT(*) AS rows_n,
       COUNT(DISTINCT county) AS geographies,
       SUM(small_county_pool) AS rows_in_small_county_pools,
       SUM(births) AS total_births
FROM births_cell;

-- Q2: missing values in the outcome columns (all from Unknown/Not Stated groups)
SELECT SUM(avg_ga_weeks IS NULL) AS missing_ga,
       SUM(avg_bw_g IS NULL)     AS missing_bw,
       SUM(sd_ga_weeks IS NULL)  AS missing_sd
FROM births_cell;

-- Q3: births by payer, with share and outcome averages (weighted by births)
SELECT payer,
       SUM(births) AS births,
       ROUND(100.0 * SUM(births) / (SELECT SUM(births) FROM births_cell), 1) AS pct_of_births,
       ROUND(SUM(births * avg_ga_weeks) / SUM(CASE WHEN avg_ga_weeks IS NOT NULL THEN births END), 2) AS avg_ga_weeks,
       ROUND(SUM(births * avg_bw_g)     / SUM(CASE WHEN avg_bw_g     IS NOT NULL THEN births END), 0) AS avg_bw_g
FROM births_cell
GROUP BY payer
ORDER BY births DESC;

-- Q4: births by month prenatal care began
SELECT pnc_month_label, pnc_month,
       SUM(births) AS births,
       ROUND(100.0 * SUM(births) / (SELECT SUM(births) FROM births_cell), 1) AS pct_of_births,
       ROUND(SUM(births * avg_ga_weeks) / SUM(CASE WHEN avg_ga_weeks IS NOT NULL THEN births END), 2) AS avg_ga_weeks,
       ROUND(SUM(births * avg_bw_g)     / SUM(CASE WHEN avg_bw_g     IS NOT NULL THEN births END), 0) AS avg_bw_g
FROM births_cell
GROUP BY pnc_month_label, pnc_month
ORDER BY pnc_month;

-- Q5: who gets no prenatal care? (share of births with NO care, by payer)
SELECT payer,
       SUM(births) AS births,
       ROUND(100.0 * SUM(CASE WHEN pnc_month = 0 THEN births END) / SUM(births), 2) AS pct_no_prenatal_care
FROM births_cell
WHERE pnc_month <> 99
GROUP BY payer
ORDER BY pct_no_prenatal_care DESC;

-- Q6: small-county pools (<100k pop) vs. larger counties
SELECT CASE small_county_pool WHEN 1 THEN 'Small counties (<100k, pooled)' ELSE 'Larger counties (100k+)' END AS group_label,
       SUM(births) AS births,
       ROUND(100.0 * SUM(CASE WHEN payer = 'Medicaid' THEN births END) / SUM(births), 1) AS pct_medicaid,
       ROUND(100.0 * SUM(CASE WHEN payer = 'Self Pay' THEN births END) / SUM(births), 1) AS pct_self_pay,
       ROUND(100.0 * SUM(CASE WHEN pnc_month = 0 THEN births END) / SUM(CASE WHEN pnc_month <> 99 THEN births END), 2) AS pct_no_pnc,
       ROUND(SUM(births * avg_ga_weeks) / SUM(CASE WHEN avg_ga_weeks IS NOT NULL THEN births END), 3) AS avg_ga_weeks,
       ROUND(SUM(births * avg_bw_g)     / SUM(CASE WHEN avg_bw_g     IS NOT NULL THEN births END), 1) AS avg_bw_g
FROM births_cell
GROUP BY small_county_pool;

-- Q7: payer gap WITHIN prenatal-care timing (is Medicaid worse even at the same care timing?)
SELECT CASE WHEN pnc_month BETWEEN 1 AND 3 THEN 'Early care (months 1-3)'
            WHEN pnc_month = 0 THEN 'No care' ELSE 'Care from month 4+' END AS care_timing,
       payer,
       SUM(births) AS births,
       ROUND(SUM(births * avg_bw_g) / SUM(births), 0) AS avg_bw_g
FROM births_cell
WHERE payer IN ('Medicaid', 'Private Insurance', 'Self Pay')
  AND pnc_month <> 99 AND avg_bw_g IS NOT NULL
GROUP BY care_timing, payer
ORDER BY care_timing, payer;

-- Q8: 10 largest and 10 smallest-birth geographies (sanity check on spread)
SELECT county, SUM(births) AS births FROM births_cell GROUP BY county ORDER BY births DESC LIMIT 10;
