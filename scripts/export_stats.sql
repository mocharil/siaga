-- SIAGA Operational Metrics Snapshot Export Script (T28)
-- Generates authoritative snapshot of all operational data from siaga.db

.headers on
.mode column

SELECT '==================================================' AS title;
SELECT 'SIAGA OPERATIONAL METRICS SNAPSHOT' AS title;
SELECT 'Snapshot Date: ' || datetime('now', '+7 hours') || ' WIB' AS title;
SELECT '==================================================' AS title;

SELECT '1. TOTAL COUNTS BY TABLE' AS section;
SELECT 'ct_raw' AS table_name, COUNT(*) AS row_count FROM ct_raw
UNION ALL
SELECT 'collector_runs', COUNT(*) FROM collector_runs
UNION ALL
SELECT 'domain_findings', COUNT(*) FROM domain_findings
UNION ALL
SELECT 'campaigns', COUNT(*) FROM campaigns
UNION ALL
SELECT 'daily_stats', COUNT(*) FROM daily_stats
UNION ALL
SELECT 'rdap_cache', COUNT(*) FROM rdap_cache
UNION ALL
SELECT 'blacklist_cache', COUNT(*) FROM blacklist_cache;

SELECT '2. CT RAW DOMAINS COLLECTED PER DAY' AS section;
SELECT date(first_seen) AS date_seen,
       COUNT(*) AS total_domains,
       COUNT(DISTINCT domain) AS unique_domains,
       COUNT(CASE WHEN source = 'ctlogs_id' THEN 1 END) AS ctlogs_id_count
FROM ct_raw
GROUP BY 1
ORDER BY 1;

SELECT '3. COLLECTOR RUNS HISTORY' AS section;
SELECT id, started_at, finished_at, source, fetched, inserted_new, status
FROM collector_runs
ORDER BY id DESC
LIMIT 10;

SELECT '4. DOMAIN FINDINGS SUMMARY' AS section;
SELECT risk_level,
       COUNT(*) AS count,
       ROUND(AVG(risk_score), 1) AS avg_score,
       COUNT(CASE WHEN is_live = 1 THEN 1 END) AS live_count,
       COUNT(CASE WHEN in_public_blacklist_at_detection = 1 THEN 1 END) AS in_blacklist_at_detection
FROM domain_findings
GROUP BY 1
ORDER BY avg_score DESC;

SELECT '5. TOP TARGETED BRANDS IN FINDINGS' AS section;
SELECT matched_brand,
       COUNT(*) AS occurrences,
       MAX(risk_score) AS max_risk_score,
       ROUND(AVG(risk_score), 1) AS avg_risk_score
FROM domain_findings
WHERE matched_brand IS NOT NULL
GROUP BY 1
ORDER BY occurrences DESC
LIMIT 10;
