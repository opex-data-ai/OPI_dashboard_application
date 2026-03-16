WITH date_base_data AS (
    SELECT 
        event_date,
        user_pseudo_id,
        user_id,
        page_title
    FROM kpi_metrics
    WHERE event_date BETWEEN ? AND ?
),
user_metrics AS (
    SELECT
        event_date,
        -- RegTech365 (including RegTech365 Audit Management)
        COUNT(DISTINCT CASE WHEN page_title LIKE 'RegTech365%' THEN user_pseudo_id END) AS RegTech365_total_users,
        COUNT(DISTINCT CASE WHEN page_title LIKE 'RegTech365%' AND user_id IS NOT NULL AND user_id != '' THEN user_pseudo_id END) AS RegTech365_signed_in_users,
        
        -- Regport
        COUNT(DISTINCT CASE WHEN page_title = 'Regport' THEN user_pseudo_id END) AS Regport_total_users,
        COUNT(DISTINCT CASE WHEN page_title = 'Regport' AND user_id IS NOT NULL AND user_id != '' THEN user_pseudo_id END) AS Regport_signed_in_users,
        
        -- RegWatch
        COUNT(DISTINCT CASE WHEN page_title = 'RegWatch' THEN user_pseudo_id END) AS RegWatch_total_users,
        COUNT(DISTINCT CASE WHEN page_title = 'RegWatch' AND user_id IS NOT NULL AND user_id != '' THEN user_pseudo_id END) AS RegWatch_signed_in_users
    FROM date_base_data
    GROUP BY event_date
)
SELECT
    event_date,
    RegTech365_total_users,
    RegTech365_signed_in_users,
    Regport_total_users,
    Regport_signed_in_users,
    RegWatch_total_users,
    RegWatch_signed_in_users
FROM user_metrics
ORDER BY event_date;