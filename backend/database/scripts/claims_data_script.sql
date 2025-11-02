-- ============================================================================
-- PostgreSQL One-Shot Explorer for hackathon.claims
-- Produces a single JSON report aggregating many analyses in one execution.
-- ============================================================================
SET search_path TO hackathon, public;

WITH
-- --------------------------------------------------------------------------
-- SECTION 0: Metadata helpers
-- --------------------------------------------------------------------------
columns_info AS (
  SELECT
    c.ordinal_position,
    c.column_name,
    c.data_type,
    c.is_nullable,
    c.column_default
  FROM information_schema.columns c
  WHERE c.table_schema = 'hackathon' AND c.table_name = 'claims'
  ORDER BY c.ordinal_position
),
approx_rows AS (
  SELECT reltuples::bigint AS approx_rows
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE c.relname = 'claims' AND n.nspname = 'hackathon'
),
exact_rows AS (
  SELECT COUNT(*)::bigint AS exact_rows FROM hackathon.claims
),
table_size AS (
  SELECT pg_size_pretty(pg_total_relation_size('hackathon.claims')) AS table_size
),
indexes AS (
  SELECT indexname, indexdef
  FROM pg_indexes
  WHERE schemaname = 'hackathon' AND tablename = 'claims'
),

-- --------------------------------------------------------------------------
-- SECTION 1: Samples
-- --------------------------------------------------------------------------
sample_first10 AS (
  SELECT * FROM hackathon.claims LIMIT 10
),
sample_random20 AS (
  SELECT * FROM hackathon.claims ORDER BY RANDOM() LIMIT 20
),

-- --------------------------------------------------------------------------
-- SECTION 2: Distincts & Cardinality
-- --------------------------------------------------------------------------
distinct_counts AS (
  SELECT
    COUNT(DISTINCT product_category) AS n_product_category,
    COUNT(DISTINCT product_name)     AS n_product_name,
    COUNT(DISTINCT claim_status)     AS n_claim_status,
    COUNT(DISTINCT loss_type)        AS n_loss_type,
    COUNT(DISTINCT destination)      AS n_destination
  FROM hackathon.claims
),
distinct_values_status AS (
  SELECT DISTINCT claim_status FROM hackathon.claims
),
top_loss_types AS (
  SELECT loss_type, COUNT(*) AS n
  FROM hackathon.claims
  GROUP BY loss_type
  ORDER BY n DESC
  LIMIT 20
),
top_destinations AS (
  SELECT destination, COUNT(*) AS n
  FROM hackathon.claims
  GROUP BY destination
  ORDER BY n DESC
  LIMIT 20
),
claims_by_status AS (
  SELECT claim_status, COUNT(*) AS n
  FROM hackathon.claims
  GROUP BY claim_status
  ORDER BY n DESC
),

-- --------------------------------------------------------------------------
-- SECTION 3: Missing values
-- --------------------------------------------------------------------------
rowcount AS (SELECT COUNT(*)::numeric AS n FROM hackathon.claims),
null_counts AS (
  SELECT
    SUM((claim_number     IS NULL)::int) AS null_claim_number,
    SUM((product_category IS NULL)::int) AS null_product_category,
    SUM((product_name     IS NULL)::int) AS null_product_name,
    SUM((claim_status     IS NULL)::int) AS null_claim_status,
    SUM((accident_date    IS NULL)::int) AS null_accident_date,
    SUM((report_date      IS NULL)::int) AS null_report_date,
    SUM((closed_date      IS NULL)::int) AS null_closed_date,
    SUM((destination      IS NULL)::int) AS null_destination,
    SUM((claim_type       IS NULL)::int) AS null_claim_type,
    SUM((cause_of_loss    IS NULL)::int) AS null_cause_of_loss,
    SUM((loss_type        IS NULL)::int) AS null_loss_type,
    SUM((gross_incurred   IS NULL)::int) AS null_gross_incurred,
    SUM((gross_paid       IS NULL)::int) AS null_gross_paid,
    SUM((gross_reserve    IS NULL)::int) AS null_gross_reserve,
    SUM((net_incurred     IS NULL)::int) AS null_net_incurred,
    SUM((net_paid         IS NULL)::int) AS null_net_paid,
    SUM((net_reserve      IS NULL)::int) AS null_net_reserve
  FROM hackathon.claims
),
null_pct AS (
  SELECT
    jsonb_agg(obj) AS pct_by_column
  FROM (
    SELECT jsonb_build_object('column','claim_status','pct_null', (100 * SUM((claim_status IS NULL)::int) / MAX(n))) AS obj
    FROM hackathon.claims, rowcount
    UNION ALL
    SELECT jsonb_build_object('column','closed_date','pct_null', (100 * SUM((closed_date IS NULL)::int) / MAX(n))) FROM hackathon.claims, rowcount
    UNION ALL
    SELECT jsonb_build_object('column','destination','pct_null', (100 * SUM((destination IS NULL)::int) / MAX(n))) FROM hackathon.claims, rowcount
  ) t
),

-- --------------------------------------------------------------------------
-- SECTION 4: Financial stats
-- --------------------------------------------------------------------------
overall_stats AS (
  SELECT
    COUNT(*)                                     AS n_claims,
    SUM(gross_incurred)                          AS sum_gross_incurred,
    SUM(gross_paid)                              AS sum_gross_paid,
    SUM(gross_reserve)                           AS sum_gross_reserve,
    SUM(net_incurred)                            AS sum_net_incurred,
    SUM(net_paid)                                AS sum_net_paid,
    SUM(net_reserve)                             AS sum_net_reserve,
    AVG(net_paid)                                AS avg_net_paid,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY COALESCE(net_paid,0)) AS p50_net_paid,
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY COALESCE(net_paid,0)) AS p90_net_paid
  FROM hackathon.claims
),
stats_by_loss_type AS (
  SELECT loss_type,
         COUNT(*) AS n,
         AVG(net_paid) AS avg_net_paid,
         PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY net_paid) AS p50,
         PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY net_paid) AS p90,
         SUM(net_paid) AS sum_net_paid
  FROM hackathon.claims
  GROUP BY loss_type
  ORDER BY sum_net_paid DESC NULLS LAST
),

-- --------------------------------------------------------------------------
-- SECTION 5: Time coverage & monthly aggregates
-- --------------------------------------------------------------------------
coverage_period AS (
  SELECT MIN(accident_date) AS min_accident_date,
         MAX(accident_date) AS max_accident_date,
         MIN(report_date)   AS min_report_date,
         MAX(report_date)   AS max_report_date,
         MIN(closed_date)   AS min_closed_date,
         MAX(closed_date)   AS max_closed_date
  FROM hackathon.claims
),
monthly_claims AS (
  SELECT DATE_TRUNC('month', report_date) AS month,
         COUNT(*) AS n_claims
  FROM hackathon.claims
  GROUP BY month
  ORDER BY month
),
monthly_paid_incurred AS (
  SELECT DATE_TRUNC('month', report_date) AS month,
         SUM(net_paid)     AS sum_net_paid,
         SUM(net_incurred) AS sum_net_incurred
  FROM hackathon.claims
  GROUP BY month
  ORDER BY month
),

-- --------------------------------------------------------------------------
-- SECTION 6: Durations / lifecycle
-- --------------------------------------------------------------------------
durations_sample AS (
  SELECT
    claim_number,
    accident_date,
    report_date,
    closed_date,
    (report_date - accident_date) AS days_to_report,
    (closed_date - report_date)   AS days_to_close
  FROM hackathon.claims
  WHERE accident_date IS NOT NULL AND report_date IS NOT NULL
  ORDER BY days_to_report DESC
  LIMIT 50
),
durations_by_loss_type AS (
  SELECT loss_type,
         AVG((report_date - accident_date)) AS avg_days_to_report,
         AVG((closed_date - report_date))   AS avg_days_to_close
  FROM hackathon.claims
  WHERE report_date IS NOT NULL AND accident_date IS NOT NULL
  GROUP BY loss_type
  ORDER BY avg_days_to_close DESC NULLS LAST
),

-- --------------------------------------------------------------------------
-- SECTION 7: Data quality checks
-- --------------------------------------------------------------------------
anomalies_neg_amounts AS (
  SELECT *
  FROM hackathon.claims
  WHERE COALESCE(net_paid,0) < 0
     OR COALESCE(net_incurred,0) < 0
     OR COALESCE(net_reserve,0) < 0
  LIMIT 100
),
closed_with_reserve AS (
  SELECT *
  FROM hackathon.claims
  WHERE claim_status ILIKE 'closed%'
    AND COALESCE(net_reserve,0) > 0
  LIMIT 100
),
report_before_accident AS (
  SELECT *
  FROM hackathon.claims
  WHERE report_date < accident_date
),

-- --------------------------------------------------------------------------
-- SECTION 8: Rankings & Top-N
-- --------------------------------------------------------------------------
top_claims_net_paid AS (
  SELECT claim_number, product_name, loss_type, destination, net_paid
  FROM hackathon.claims
  ORDER BY net_paid DESC NULLS LAST
  LIMIT 20
),
top_destinations_by_net_paid AS (
  SELECT destination, SUM(net_paid) AS sum_net_paid, COUNT(*) AS n
  FROM hackathon.claims
  GROUP BY destination
  ORDER BY sum_net_paid DESC NULLS LAST
  LIMIT 10
),

-- --------------------------------------------------------------------------
-- SECTION 9: Crosstabs / distributions
-- --------------------------------------------------------------------------
loss_type_status_matrix AS (
  SELECT loss_type,
         SUM(CASE WHEN claim_status ILIKE 'open%'   THEN 1 ELSE 0 END) AS open_cnt,
         SUM(CASE WHEN claim_status ILIKE 'closed%' THEN 1 ELSE 0 END) AS closed_cnt,
         COUNT(*) AS total
  FROM hackathon.claims
  GROUP BY loss_type
  ORDER BY total DESC
),
hist_net_paid AS (
  SELECT
    width_bucket(net_paid, 0, 10000, 10) AS bucket,
    MIN(net_paid) AS bucket_min,
    MAX(net_paid) AS bucket_max,
    COUNT(*) AS n
  FROM hackathon.claims
  WHERE net_paid IS NOT NULL
  GROUP BY bucket
  ORDER BY bucket
),
p99_outliers AS (
  WITH p AS (
    SELECT PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY net_paid) AS p99
    FROM hackathon.claims
  )
  SELECT c.*
  FROM hackathon.claims c, p
  WHERE c.net_paid > p.p99
  ORDER BY c.net_paid DESC
  LIMIT 100
),

-- --------------------------------------------------------------------------
-- SECTION 10: Ratios & adequacy
-- --------------------------------------------------------------------------
ratio_paid_incurred AS (
  SELECT
    AVG(NULLIF(net_paid,0) / NULLIF(net_incurred,0)) AS avg_paid_to_incurred_ratio
  FROM hackathon.claims
  WHERE net_paid IS NOT NULL AND net_incurred IS NOT NULL
),
reserve_adequacy_by_loss_type AS (
  SELECT loss_type,
         SUM(net_incurred) AS incurred,
         SUM(net_paid)     AS paid,
         SUM(net_reserve)  AS reserve,
         CASE WHEN SUM(net_incurred) > 0
              THEN SUM(net_reserve) / SUM(net_incurred)
              ELSE NULL END AS reserve_to_incurred_ratio
  FROM hackathon.claims
  GROUP BY loss_type
  ORDER BY incurred DESC NULLS LAST
),

-- --------------------------------------------------------------------------
-- SECTION 11: Duplicates & keys
-- --------------------------------------------------------------------------
duplicate_claim_numbers AS (
  SELECT claim_number, COUNT(*) AS n
  FROM hackathon.claims
  GROUP BY claim_number
  HAVING COUNT(*) > 1
  ORDER BY n DESC
),
exact_duplicates AS (
  SELECT product_category, product_name, claim_status, accident_date, destination, loss_type,
         COUNT(*) AS n
  FROM hackathon.claims
  GROUP BY 1,2,3,4,5,6
  HAVING COUNT(*) > 1
  ORDER BY n DESC
  LIMIT 50
),

-- --------------------------------------------------------------------------
-- SECTION 12: Slices by product / destination
-- --------------------------------------------------------------------------
kpis_by_product_name AS (
  SELECT product_name,
         COUNT(*) AS n_claims,
         SUM(net_paid) AS sum_net_paid,
         AVG(net_paid) AS avg_net_paid
  FROM hackathon.claims
  GROUP BY product_name
  ORDER BY sum_net_paid DESC NULLS LAST
),
dest_loss_heat AS (
  SELECT destination, loss_type, COUNT(*) AS n
  FROM hackathon.claims
  GROUP BY destination, loss_type
  ORDER BY n DESC
  LIMIT 200
),

-- --------------------------------------------------------------------------
-- SECTION 13: Open vs closed dynamics
-- --------------------------------------------------------------------------
open_closed_monthly AS (
  SELECT DATE_TRUNC('month', COALESCE(closed_date, report_date)) AS month,
         SUM(CASE WHEN claim_status ILIKE 'open%'   THEN 1 ELSE 0 END) AS open_cnt,
         SUM(CASE WHEN claim_status ILIKE 'closed%' THEN 1 ELSE 0 END) AS closed_cnt
  FROM hackathon.claims
  GROUP BY month
  ORDER BY month
),
triage_open_high_reserve AS (
  SELECT claim_number, product_name, loss_type, destination, net_reserve
  FROM hackathon.claims
  WHERE claim_status ILIKE 'open%' AND COALESCE(net_reserve,0) > 0
  ORDER BY net_reserve DESC
  LIMIT 50
)

-- --------------------------------------------------------------------------
-- FINAL SELECT: Build a single JSON report containing every section
-- --------------------------------------------------------------------------
SELECT jsonb_build_object(
  'meta', jsonb_build_object(
    'columns',      (SELECT jsonb_agg(to_jsonb(columns_info)) FROM columns_info),
    'approx_rows',  (SELECT approx_rows FROM approx_rows),
    'exact_rows',   (SELECT exact_rows  FROM exact_rows),
    'table_size',   (SELECT table_size  FROM table_size),
    'indexes',      (SELECT jsonb_agg(to_jsonb(indexes)) FROM indexes)
  ),

  'samples', jsonb_build_object(
    'first10',      (SELECT jsonb_agg(to_jsonb(sample_first10))  FROM sample_first10),
    'random20',     (SELECT jsonb_agg(to_jsonb(sample_random20)) FROM sample_random20)
  ),

  'distincts', jsonb_build_object(
    'counts',       (SELECT to_jsonb(distinct_counts) FROM distinct_counts),
    'claim_status_values', (SELECT jsonb_agg(to_jsonb(distinct_values_status)) FROM distinct_values_status),
    'top_loss_types',      (SELECT jsonb_agg(to_jsonb(top_loss_types)) FROM top_loss_types),
    'top_destinations',    (SELECT jsonb_agg(to_jsonb(top_destinations)) FROM top_destinations),
    'claims_by_status',    (SELECT jsonb_agg(to_jsonb(claims_by_status)) FROM claims_by_status)
  ),

  'missing_values', jsonb_build_object(
    'null_counts',  (SELECT to_jsonb(null_counts) FROM null_counts),
    'null_pct_subset', (SELECT pct_by_column FROM null_pct)
  ),

  'financials', jsonb_build_object(
    'overall',      (SELECT to_jsonb(overall_stats) FROM overall_stats),
    'by_loss_type', (SELECT jsonb_agg(to_jsonb(stats_by_loss_type)) FROM stats_by_loss_type)
  ),

  'time', jsonb_build_object(
    'coverage_period',        (SELECT to_jsonb(coverage_period) FROM coverage_period),
    'monthly_claims',         (SELECT jsonb_agg(to_jsonb(monthly_claims)) FROM monthly_claims),
    'monthly_paid_incurred',  (SELECT jsonb_agg(to_jsonb(monthly_paid_incurred)) FROM monthly_paid_incurred)
  ),

  'durations', jsonb_build_object(
    'sample',         (SELECT jsonb_agg(to_jsonb(durations_sample)) FROM durations_sample),
    'by_loss_type',   (SELECT jsonb_agg(to_jsonb(durations_by_loss_type)) FROM durations_by_loss_type)
  ),

  'data_quality', jsonb_build_object(
    'negative_amounts',        (SELECT jsonb_agg(to_jsonb(anomalies_neg_amounts)) FROM anomalies_neg_amounts),
    'closed_with_reserve',     (SELECT jsonb_agg(to_jsonb(closed_with_reserve)) FROM closed_with_reserve),
    'report_before_accident',  (SELECT jsonb_agg(to_jsonb(report_before_accident)) FROM report_before_accident)
  ),

  'rankings', jsonb_build_object(
    'top_claims_net_paid',         (SELECT jsonb_agg(to_jsonb(top_claims_net_paid)) FROM top_claims_net_paid),
    'top_destinations_by_net_paid',(SELECT jsonb_agg(to_jsonb(top_destinations_by_net_paid)) FROM top_destinations_by_net_paid)
  ),

  'distributions', jsonb_build_object(
    'loss_type_status_matrix', (SELECT jsonb_agg(to_jsonb(loss_type_status_matrix)) FROM loss_type_status_matrix),
    'hist_net_paid',           (SELECT jsonb_agg(to_jsonb(hist_net_paid)) FROM hist_net_paid),
    'p99_outliers',            (SELECT jsonb_agg(to_jsonb(p99_outliers)) FROM p99_outliers)
  ),

  'ratios', jsonb_build_object(
    'avg_paid_to_incurred_ratio', (SELECT to_jsonb(ratio_paid_incurred) FROM ratio_paid_incurred),
    'reserve_adequacy_by_loss_type', (SELECT jsonb_agg(to_jsonb(reserve_adequacy_by_loss_type)) FROM reserve_adequacy_by_loss_type)
  ),

  'duplicates', jsonb_build_object(
    'duplicate_claim_numbers', (SELECT jsonb_agg(to_jsonb(duplicate_claim_numbers)) FROM duplicate_claim_numbers),
    'exact_duplicates_subset', (SELECT jsonb_agg(to_jsonb(exact_duplicates)) FROM exact_duplicates)
  ),

  'slices', jsonb_build_object(
    'kpis_by_product_name', (SELECT jsonb_agg(to_jsonb(kpis_by_product_name)) FROM kpis_by_product_name),
    'dest_loss_heat_subset', (SELECT jsonb_agg(to_jsonb(dest_loss_heat)) FROM dest_loss_heat)
  ),

  'open_closed', jsonb_build_object(
    'monthly_open_vs_closed', (SELECT jsonb_agg(to_jsonb(open_closed_monthly)) FROM open_closed_monthly),
    'triage_open_high_reserve',(SELECT jsonb_agg(to_jsonb(triage_open_high_reserve)) FROM triage_open_high_reserve)
  )
) AS claims_exploration_report;
