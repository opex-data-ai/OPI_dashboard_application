WITH country_base_data AS (
    SELECT 
        *    
    FROM country_summary
    WHERE event_date BETWEEN ? AND ?
)

SELECT
  country,
  SUM(IF(page_title like 'RegTech365%', unique_users, 0)) AS RegTech365,
  SUM(IF(page_title = 'Regport', unique_users, 0)) AS RegPort,
  SUM(IF(page_title = 'RegWatch', unique_users, 0)) AS RegWatch
FROM country_base_data
GROUP BY country
ORDER BY country;