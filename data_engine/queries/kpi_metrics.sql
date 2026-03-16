-- kpi_metrics.sql
-- Optimizing to use a CTE for filtering and shared session_id calculation
WITH base_data AS (
    SELECT 
        *, 
        CONCAT(user_pseudo_id, CAST(ga_session_number AS STRING)) AS session_id
    FROM kpi_metrics
    WHERE event_date BETWEEN ? AND ?
)
SELECT 'total_sessions' AS metric,
       COUNT(DISTINCT IF(page_title LIKE 'RegTech365%', session_id, NULL)) AS RegTech365,
       COUNT(DISTINCT IF(page_title = 'Regport', session_id, NULL)) AS RegPort,
       COUNT(DISTINCT IF(page_title = 'RegWatch', session_id, NULL)) AS RegWatch
FROM base_data

UNION ALL

SELECT 'engaged_sessions' AS metric,
       COUNT(DISTINCT IF(page_title LIKE 'RegTech365%' AND (engagement_time_msec >= 10000 OR pageviews_in_session >= 2), session_id, NULL)) AS RegTech365,
       COUNT(DISTINCT IF(page_title = 'Regport' AND (engagement_time_msec >= 10000 OR pageviews_in_session >= 2), session_id, NULL)) AS RegPort,
       COUNT(DISTINCT IF(page_title = 'RegWatch' AND (engagement_time_msec >= 10000 OR pageviews_in_session >= 2), session_id, NULL)) AS RegWatch
FROM base_data

UNION ALL

SELECT 'new_visitors' AS metric,
       COUNT(DISTINCT IF(page_title LIKE 'RegTech365%' AND ga_session_number = 1, user_pseudo_id, NULL)) AS RegTech365,
       COUNT(DISTINCT IF(page_title = 'Regport' AND ga_session_number = 1, user_pseudo_id, NULL)) AS RegPort,
       COUNT(DISTINCT IF(page_title = 'RegWatch' AND ga_session_number = 1, user_pseudo_id, NULL)) AS RegWatch
FROM base_data

UNION ALL

SELECT 'returning_visitors' AS metric,
       COUNT(DISTINCT IF(page_title LIKE 'RegTech365%' AND ga_session_number > 1, user_pseudo_id, NULL)) AS RegTech365,
       COUNT(DISTINCT IF(page_title = 'Regport' AND ga_session_number > 1, user_pseudo_id, NULL)) AS RegPort,
       COUNT(DISTINCT IF(page_title = 'RegWatch' AND ga_session_number > 1, user_pseudo_id, NULL)) AS RegWatch
FROM base_data

UNION ALL

SELECT 'active_visitors' AS metric,
       COUNT(DISTINCT IF(page_title LIKE 'RegTech365%' AND is_active_user = true, user_pseudo_id, NULL)) AS RegTech365,
       COUNT(DISTINCT IF(page_title = 'Regport' AND is_active_user = true, user_pseudo_id, NULL)) AS RegPort,
       COUNT(DISTINCT IF(page_title = 'RegWatch' AND is_active_user = true, user_pseudo_id, NULL)) AS RegWatch
FROM base_data

UNION ALL

SELECT 'total_visitors' AS metric,
       COUNT(DISTINCT IF(page_title LIKE 'RegTech365%', user_pseudo_id, NULL)) AS RegTech365,
       COUNT(DISTINCT IF(page_title = 'Regport', user_pseudo_id, NULL)) AS RegPort,
       COUNT(DISTINCT IF(page_title = 'RegWatch', user_pseudo_id, NULL)) AS RegWatch
FROM base_data;