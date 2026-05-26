"""
Query Store - Repository of SQL queries as Python variables.
Used to decouple SQL logic from data loading and service layers.
"""

#For 1. Total Organization
#    2. Total Platform
ORGANIZATION_BY_PLATFORM_QUERY = """
SELECT
  COUNT(DISTINCT email_domain) AS total_orgs,
  platform
FROM all_organizations
  GROUP BY platform;
"""
#For 1. Total Users
USER_BY_PLATFORM_QUERY = """
SELECT
  COUNT(DISTINCT user_id) AS total_users,
  platform
FROM all_users
  GROUP BY platform;
"""

#For 3. Multiplatform adoption rate
#    4. Ecosystem adoption rate
ECOSYSTEM_ADOPTION_RATE_QUERY = """
WITH org_platforms AS (
  SELECT
    email_domain,
    COUNT(DISTINCT platform) AS platform_count
  FROM all_organizations
  GROUP BY email_domain
),
total_platforms AS (
  SELECT
    COUNT(DISTINCT platform) AS total_platform
  FROM all_organizations
)
SELECT
  COUNTIF(platform_count > 1) AS multi_platform_orgs_count,
  COUNTIF(platform_count = total_platform) AS full_ecosystem_orgs_count,
  COUNT(*) AS total_orgs,
  MAX(total_platform) AS total_platforms,
  COUNTIF(platform_count > 1) / COUNT(*) AS multi_platform_adoption_rate,
  COUNTIF(platform_count = total_platform) / COUNT(*) AS full_ecosystem_adoption_rate
FROM
  org_platforms,
  (SELECT total_platform FROM total_platforms) AS tp;
"""

MULTIPLATFORM_ORGANIZATION_QUERY = """
SELECT
  COUNT(*) AS multi_platform_organization_count
FROM (
  SELECT
    email_domain,
    COUNT(DISTINCT platform) AS platform_count
  FROM all_organizations
  --WHERE user_type = 'external'
  GROUP BY email_domain
  HAVING platform_count > 1
);
"""

#-- ============================================================================
#-- COMBINED QUERY: Platform by Organization Count + User Count
#-- Output: platform, organization_count, signed_in_users, total_visitors
#-- ============================================================================
PLATFORM_ORGANIZATION_USER_COUNT = """
WITH time_params AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date
)
SELECT
  p.platform,
  p.organization_count,
  u.signed_in_users,
  u.total_visitors
FROM (
  -- Organization Count by Platform
  SELECT
    dom.platform,
    COUNT(DISTINCT dom.organization_id) AS organization_count
  FROM daily_organization_metrics dom
  CROSS JOIN time_params
  WHERE dom.date::DATE BETWEEN time_params.start_date AND time_params.end_date
  GROUP BY dom.platform
) p
JOIN (
  -- User Count by Platform
  SELECT
    dum.platform,
    COUNT(DISTINCT dum.user_id) AS signed_in_users,
    COUNT(DISTINCT dum.user_pseudo_id) AS total_visitors
  FROM daily_user_metrics dum
  CROSS JOIN time_params
  WHERE dum.date::DATE BETWEEN time_params.start_date AND time_params.end_date
  GROUP BY dum.platform
) u
ON p.platform = u.platform
ORDER BY u.total_visitors DESC;
"""

#-- ============================================================================
#-- QUERY 1.7: Column Chart - Platform by Rate Metrics
#-- Output: platform, growth_rate, churn_rate, engagement_rate
#-- ============================================================================
PLATFORM_RATE_METRICS = """
WITH time_params AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date
),
current_period_users AS (
  SELECT
    dum.platform,
    COUNT(DISTINCT dum.user_pseudo_id) AS current_active_users
  FROM daily_user_metrics dum
  CROSS JOIN time_params
  WHERE dum.date::DATE BETWEEN time_params.start_date AND time_params.end_date
    AND CAST(dum.is_signed_in AS INTEGER) = 1
  GROUP BY dum.platform
),
prior_period_users AS (
  SELECT
    dum.platform,
    COUNT(DISTINCT dum.user_pseudo_id) AS prior_active_users
  FROM daily_user_metrics dum
  CROSS JOIN time_params
  WHERE dum.date::DATE BETWEEN 
    (time_params.start_date - ((time_params.end_date - time_params.start_date + 1) * INTERVAL 1 DAY))
    AND (time_params.start_date - INTERVAL 1 DAY)
    AND CAST(dum.is_signed_in AS INTEGER) = 1
  GROUP BY dum.platform
),
churned_users AS (
  SELECT
    prior_users.platform,
    COUNT(DISTINCT prior_users.user_pseudo_id) AS churned_user_count
  FROM (
    SELECT DISTINCT dum.platform, dum.user_pseudo_id
    FROM daily_user_metrics dum
    CROSS JOIN time_params
    WHERE dum.date::DATE BETWEEN 
      (time_params.start_date - ((time_params.end_date - time_params.start_date + 1) * INTERVAL 1 DAY))
      AND (time_params.start_date - INTERVAL 1 DAY)
      AND CAST(dum.is_signed_in AS INTEGER) = 1
  ) prior_users
  WHERE NOT EXISTS (
    SELECT 1
    FROM daily_user_metrics current_users
    CROSS JOIN time_params
    WHERE current_users.platform = prior_users.platform
      AND current_users.user_pseudo_id = prior_users.user_pseudo_id
      AND current_users.date::DATE BETWEEN time_params.start_date AND time_params.end_date
      AND CAST(current_users.is_signed_in AS INTEGER) = 1
  )
  GROUP BY prior_users.platform
),
session_engagement AS (
  SELECT
    dsm.platform,
    COUNT(DISTINCT dsm.ga_session_id) AS total_sessions,
    COUNT(DISTINCT CASE WHEN CAST(dsm.is_engaged_session AS VARCHAR) = 'true' THEN dsm.ga_session_id END) AS engaged_sessions
  FROM daily_session_metrics dsm
  CROSS JOIN time_params
  WHERE dsm.date::DATE BETWEEN time_params.start_date AND time_params.end_date
  GROUP BY dsm.platform
)
SELECT
  c.platform,
  ROUND(
    100.0 * (c.current_active_users - COALESCE(p.prior_active_users, 0)) / 
    NULLIF(p.prior_active_users, 0),
    2
  ) AS growth_rate_pct, 
  ROUND(
    100.0 * COALESCE(ch.churned_user_count, 0) / 
    NULLIF(p.prior_active_users, 0),
    2
  ) AS churn_rate_pct,
  ROUND(
    100.0 * COALESCE(e.engaged_sessions, 0) / 
    NULLIF(e.total_sessions, 0),
    2
  ) AS engagement_rate_pct
FROM current_period_users c
LEFT JOIN prior_period_users p USING (platform)
LEFT JOIN churned_users ch USING (platform)
LEFT JOIN session_engagement e USING (platform)
--WHERE p.prior_active_users > 0
ORDER BY growth_rate_pct DESC;
"""

#-- ============================================================================
#-- TOP ORGANIZATION PER PLATFORM BY ENGAGEMENT (Overview Tab)
#-- ============================================================================
TOP_ORG_PER_PLATFORM = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date
),

org_metrics AS (
  SELECT
    dsm.platform,
    org.organizationName,
    org.email_domain,
    org.organization_start_date,
    COUNT(DISTINCT dsm.ga_session_id) AS total_sessions,
    COUNT(DISTINCT dsm.ga_session_id)
      FILTER (WHERE CAST(dsm.is_engaged_session AS VARCHAR) = 'true')
      AS engaged_sessions
  FROM daily_session_metrics dsm
  JOIN all_organizations org
    ON dsm.organization_id = org.organization_id
  CROSS JOIN vars
  WHERE dsm.date::DATE BETWEEN vars.start_date AND vars.end_date
  GROUP BY 1, 2, 3, 4
)
--Returns only the top org by total_sessions per platform
SELECT
  *,
  ROUND(
    100.0 * engaged_sessions / NULLIF(total_sessions, 0),
    2
  ) AS engagement_rate_pct
FROM org_metrics
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY platform
  ORDER BY total_sessions DESC, engaged_sessions DESC
) = 1;
"""

#-- ============================================================================
#-- PRODUCT DASHBOARD QUERIES (Overview Tab)
#-- ============================================================================

PRODUCT_KPI_ACTIVE_ORG_COUNT = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  COUNT(DISTINCT dom.organization_id) AS active_organization_count
FROM daily_organization_metrics dom, vars v
WHERE dom.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dom.platform) = LOWER(v.platform);
"""

PRODUCT_KPI_ACTIVE_SIGNED_IN_USERS = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  COUNT(DISTINCT dum.user_id) AS active_signed_in_users
FROM daily_user_metrics dum, vars v
WHERE dum.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dum.platform) = LOWER(v.platform)
  AND dum.user_id IS NOT NULL
  AND dum.email IS NOT NULL;
"""

PRODUCT_KPI_CHURN_RATE = """
WITH org_monthly_presence AS (
  SELECT DISTINCT
    DATE_TRUNC('month', m.date::DATE) AS month,
    m.platform,
    m.email_domain
  FROM daily_organization_metrics m
  WHERE EXTRACT(YEAR FROM m.date::DATE) IN (?::INTEGER - 1, ?::INTEGER)
),
churned AS (
  SELECT
    curr.month,
    curr.platform,
    COUNT(DISTINCT prev.email_domain) AS prior_orgs,
    COUNT(DISTINCT CASE WHEN curr.email_domain IS NULL
          THEN prev.email_domain END) AS churned_orgs
  FROM org_monthly_presence prev
  LEFT JOIN org_monthly_presence curr
    ON  prev.email_domain = curr.email_domain
    AND curr.month = DATE_TRUNC('month', prev.month + INTERVAL '1 month')
    AND prev.platform = curr.platform
  GROUP BY 1, 2
)
SELECT
  month,
  platform,
  prior_orgs,
  churned_orgs,
  ROUND(
    100.0 * churned_orgs / NULLIF(prior_orgs, 0),
    2
  ) AS churn_rate_pct
FROM churned
WHERE month IS NOT NULL
ORDER BY platform, month;
"""

PRODUCT_KPI_GROWTH_RATE = """
WITH monthly_new_orgs AS (
  SELECT
    DATE_TRUNC('month', m.date::DATE) AS month,
    m.platform,
    COUNT(DISTINCT m.email_domain) AS new_orgs
  FROM daily_organization_metrics m
  WHERE m.date::DATE = m.organization_start_date::DATE
    AND EXTRACT(YEAR FROM m.date::DATE) = ?::INTEGER
  GROUP BY 1, 2
),
monthly_with_cumulative AS (
  SELECT
    month,
    platform,
    new_orgs,
    SUM(new_orgs) OVER (PARTITION BY platform ORDER BY month) AS total_orgs
  FROM monthly_new_orgs
)
SELECT
  month,
  platform,
  new_orgs,
  total_orgs,
  ROUND(
    100.0 * (total_orgs - LAG(total_orgs) OVER (PARTITION BY platform ORDER BY month))
    / NULLIF(LAG(total_orgs) OVER (PARTITION BY platform ORDER BY month), 0),
    2
  ) AS mom_growth_rate_pct
FROM monthly_with_cumulative
ORDER BY platform, month;
"""


PRODUCT_KPI_ANONYMOUS_USERS_PCT = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  ROUND(
    100.0 * COUNT(DISTINCT CASE WHEN dum.user_id IS NULL THEN dum.user_pseudo_id END) / 
    NULLIF(COUNT(DISTINCT dum.user_pseudo_id), 0), 
    2
  ) AS anonymous_users_pct,
  COUNT(DISTINCT CASE WHEN dum.user_id IS NOT NULL THEN dum.user_pseudo_id END) AS signed_in_visitors,
 COUNT(DISTINCT CASE WHEN dum.user_id IS NULL THEN dum.user_pseudo_id END) AS anonymous_visitors
FROM daily_user_metrics dum, vars v
WHERE dum.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dum.platform) = LOWER(v.platform)
;
"""

PRODUCT_KPI_AVAILABLE_YEARS = """
SELECT DISTINCT EXTRACT(YEAR FROM date::DATE)::INTEGER AS year
FROM daily_organization_metrics
WHERE date IS NOT NULL
ORDER BY year DESC;
"""

# Engagement Rate: % of engaged sessions for a specific platform
PRODUCT_KPI_ENGAGEMENT_RATE = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  COUNT(DISTINCT dsm.ga_session_id) AS total_sessions,
  COUNT(DISTINCT CASE WHEN CAST(dsm.is_engaged_session AS VARCHAR) = 'true' THEN dsm.ga_session_id END) AS engaged_sessions,
  ROUND(
    100.0 * COUNT(DISTINCT CASE WHEN CAST(dsm.is_engaged_session AS VARCHAR) = 'true' THEN dsm.ga_session_id END) / 
    NULLIF(COUNT(DISTINCT dsm.ga_session_id), 0),
    2
  ) AS engagement_rate_pct
FROM daily_session_metrics dsm, vars v
WHERE dsm.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dsm.platform) = LOWER(v.platform);
"""

# User Acquisition Trend: Daily breakdown of visitors by type
PRODUCT_USER_ACQUISITION_TREND = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  dum.date::DATE AS date,
  COUNT(DISTINCT dum.user_pseudo_id) AS total_visitors,
  COUNT(DISTINCT dum.user_id) AS signed_in_users,
  COUNT(DISTINCT CASE WHEN dum.user_id IS NULL THEN dum.user_pseudo_id END) AS anonymous_users
FROM daily_user_metrics dum, vars v
WHERE dum.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dum.platform) = LOWER(v.platform)
GROUP BY dum.date::DATE
ORDER BY date;
"""

# Geographic Metrics: Country-level user distribution
PRODUCT_GEOGRAPHIC_METRICS = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  dgm.country,
  dgm.city,
  SUM(CAST(dgm.total_visitors AS INTEGER)) AS total_visitors,
  SUM(CAST(dgm.signed_in_users AS INTEGER)) AS signed_in_users,
  --SUM(CAST(dgm.external_users AS INTEGER)) AS external_users,
  SUM(CAST(dgm.sessions AS INTEGER)) AS sessions,
  SUM(CAST(dgm.page_views AS INTEGER)) AS page_views
FROM daily_geographic_metrics dgm, vars v
WHERE dgm.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dgm.platform) = LOWER(v.platform)
GROUP BY dgm.country, dgm.city
ORDER BY total_visitors DESC;
"""

# User Stickiness: DAU/WAU, DAU/MAU, WAU/MAU ratios
PRODUCT_STICKINESS = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
),
daily_actives AS (
  SELECT
    m.date::DATE AS date,
    COUNT(DISTINCT m.user_pseudo_id) AS dau
  FROM daily_user_metrics m, vars v
  WHERE LOWER(m.platform) = LOWER(v.platform)
  GROUP BY m.date::DATE
),
weekly_window AS (
  SELECT
    date,
    SUM(dau) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS wau
  FROM daily_actives
),
monthly_window AS (
  SELECT
    date,
    SUM(dau) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS mau
  FROM daily_actives
)
SELECT
  d.date,
  ROUND(CAST(d.dau AS FLOAT) / NULLIF(w.wau, 0), 4) AS dau_wau_ratio,
  ROUND(CAST(d.dau AS FLOAT) / NULLIF(m.mau, 0), 4) AS dau_mau_ratio,
  ROUND(CAST(w.wau AS FLOAT) / NULLIF(m.mau, 0), 4) AS wau_mau_ratio
FROM daily_actives d
JOIN weekly_window w USING (date)
JOIN monthly_window m USING (date), vars v
WHERE d.date BETWEEN v.start_date AND v.end_date
ORDER BY d.date;
"""


#-- ============================================================================
#-- QUERY 2.12: Acquisition Tab - New Users by Primary Medium & Source
#-- Output: acquisition_source, acquisition_medium, new_visitors, sessions
#-- ============================================================================
PRODUCT_TRAFFIC_SOURCE_METRICS = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  dtsm.acquisition_source,
  dtsm.acquisition_medium,
  SUM(dtsm.new_visitors) AS new_visitors,
  SUM(dtsm.new_signed_in_users) AS new_signed_in_users,
  SUM(dtsm.sessions) AS sessions
FROM daily_traffic_source_metrics dtsm, vars v
WHERE dtsm.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dtsm.platform) = LOWER(v.platform)
GROUP BY dtsm.acquisition_source, dtsm.acquisition_medium
ORDER BY new_visitors DESC;
"""


#-- ============================================================================
#-- QUERY 2.13: Acquisition Tab - Session Traffic by Primary Medium & Source
#-- Output: session_source, session_medium, session_count
#-- ============================================================================
PRODUCT_SESSION_TRAFFIC_METRICS = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  dtsm.session_source,
  dtsm.session_medium,
  dtsm.session_campaign,
  SUM(dtsm.sessions) AS session_count,
  COUNT(DISTINCT dtsm.date) AS days_tracked
FROM daily_traffic_source_metrics dtsm, vars v
WHERE dtsm.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dtsm.platform) = LOWER(v.platform)
GROUP BY dtsm.session_source, dtsm.session_medium, dtsm.session_campaign
ORDER BY session_count DESC;
"""


#-- ============================================================================
#-- PRODUCT DASHBOARD QUERIES (Conversion Tab)
#-- ============================================================================

PRODUCT_KPI_AVG_PAGES_PER_SESSION = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  ROUND(AVG(distinct_pages), 2) AS avg_pages_per_session,
  MAX(distinct_pages)           AS max_pages_in_session,
  MIN(distinct_pages)           AS min_pages_in_session
FROM daily_session_metrics dsm, vars v
WHERE dsm.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dsm.platform) = LOWER(v.platform);
"""

PRODUCT_KPI_TIME_TO_SIGNUP = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
),
signup_users AS (
  SELECT
    dsm.user_pseudo_id,
    MIN(dsm.date::DATE) AS first_signup_date
  FROM daily_session_metrics dsm
  CROSS JOIN vars v
  WHERE CAST(dsm.sign_up_events AS INTEGER) > 0
    AND LOWER(dsm.platform) = LOWER(v.platform)
  GROUP BY dsm.user_pseudo_id
  HAVING MIN(dsm.date::DATE) BETWEEN (SELECT start_date FROM vars) AND (SELECT end_date FROM vars)
),
engagement_summary AS (
  SELECT
    dsm.user_pseudo_id,
    SUM(COALESCE(CAST(dsm.total_engagement_time_msec AS BIGINT), 0)) AS time_to_signup_msec
  FROM daily_session_metrics dsm
  JOIN signup_users su ON dsm.user_pseudo_id = su.user_pseudo_id
  CROSS JOIN vars v
  WHERE dsm.date::DATE <= su.first_signup_date
    AND LOWER(dsm.platform) = LOWER(v.platform)
  GROUP BY dsm.user_pseudo_id
)
SELECT
  ROUND(AVG(time_to_signup_msec), 2) AS avg_time_to_first_signup_msec,
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time_to_signup_msec), 2) AS median_time_to_first_signup_msec
FROM engagement_summary;
"""


PRODUCT_KPI_EXIT_RATE_LANDING = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
),
session_level AS (
  SELECT
    dsm.ga_session_id,
    dsm.distinct_pages AS pages_visited
  FROM daily_session_metrics dsm, vars v
  WHERE dsm.date::DATE BETWEEN v.start_date AND v.end_date
    AND LOWER(dsm.platform) = LOWER(v.platform)
)
SELECT
  COUNT(*)                                                AS total_sessions,
  SUM(CASE WHEN pages_visited = 1 THEN 1 ELSE 0 END)     AS exit_on_landing_sessions,
  ROUND(
    100.0 * SUM(CASE WHEN pages_visited = 1 THEN 1 ELSE 0 END)
    / NULLIF(COUNT(*), 0),
    2
  )  AS exit_rate_pct
FROM session_level;
"""


PRODUCT_USER_CONVERSION_PATH = """
WITH vars AS (
    SELECT
        ?::DATE AS start_date,
        ?::DATE AS end_date,
        ?       AS platform
),

total_users AS (
    -- denominator for user_pct: total active user-days in the period
    SELECT COUNT(*) AS total
    FROM   daily_user_metrics dum
    CROSS JOIN vars v
    WHERE  dum.date::DATE BETWEEN v.start_date AND v.end_date
      AND  LOWER(dum.platform) = LOWER(v.platform)
),

paths AS (
    SELECT
        dcpm.conversion_path,
        SUM(dcpm.path_occurrence_count)   AS path_occurrence_count,
        AVG(dcpm.path_percentage)         AS path_percentage,
        MAX(dcpm.num_pages)               AS num_pages,
        MAX(dcpm.unique_pages)            AS unique_pages,
        SUM(dcpm.unique_users_count)      AS unique_users_count
    FROM   daily_conversion_path_metrics dcpm
    CROSS JOIN vars v
    WHERE  dcpm.date::DATE BETWEEN v.start_date AND v.end_date
      AND  LOWER(dcpm.platform) = LOWER(v.platform)
      AND  dcpm.unique_pages    >= 3        -- minimum depth filter
      AND  dcpm.num_pages       >= 3        -- exclude trivial single-redirects
    GROUP BY dcpm.conversion_path
)

SELECT
    p.conversion_path,
    ROUND(p.path_percentage, 2)                                   AS path_percentage,
    p.path_occurrence_count,
    p.num_pages,
    p.unique_pages,
    p.unique_users_count,
    ROUND(100.0 * p.unique_users_count / NULLIF(tu.total, 0), 2) AS user_pct
FROM   paths p
CROSS JOIN total_users tu
ORDER BY
    user_pct             DESC,   -- highest reach first
    unique_pages         DESC,   -- then deepest
    path_occurrence_count DESC   -- then most frequent
LIMIT 20;                        -- fetch 20; UI shows 5 + "load more"
"""


PRODUCT_LANDING_PAGE_FUNNEL = r"""
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
),
page_sequences AS (
  SELECT
    dsm.ga_session_id,
    dsm.user_id,
    split_part(REGEXP_REPLACE(dsm.page_location, '^https{0,1}://[^/]+', ''), CHR(63), 1) AS current_page,
    LEAD(split_part(REGEXP_REPLACE(dsm.page_location, '^https{0,1}://[^/]+', ''), CHR(63), 1)) OVER (
      PARTITION BY dsm.ga_session_id
      ORDER BY dsm.date
    ) AS next_page
  FROM daily_session_metrics dsm, vars v
  WHERE dsm.date::DATE BETWEEN v.start_date AND v.end_date
    AND LOWER(dsm.platform) = LOWER(v.platform)
    AND dsm.page_location IS NOT NULL
    AND dsm.page_location NOT LIKE '%client%'
    AND dsm.page_location NOT LIKE '%localhost%'
)
SELECT
  current_page AS landing_page,
  next_page AS next_common_action,
  COUNT(DISTINCT user_id) AS user_count,
  ROUND(
    100.0 * COUNT(DISTINCT user_id) / 
    SUM(COUNT(DISTINCT user_id)) OVER (PARTITION BY current_page),
    2
  ) AS pct_users
FROM page_sequences
WHERE next_page IS NOT NULL
GROUP BY current_page, next_page
ORDER BY user_count DESC, pct_users DESC, landing_page ASC
LIMIT 50;
"""

PRODUCT_ENGAGED_VS_CHURNED_METRICS = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
),
params AS (
  SELECT
    start_date,
    end_date,
    platform,
    (end_date - start_date + 1) AS window_days
  FROM vars
),
session_pages AS (
  SELECT
    dsm.ga_session_id,
    dsm.user_pseudo_id,
    dsm.is_engaged_session,
    dsm.distinct_pages,
    MAX(CAST(dsm.key_events AS INTEGER))                                           AS had_key_event,
    SUM(COALESCE(CAST(dsm.total_engagement_time_msec AS BIGINT), 0))               AS engagement_time
  FROM daily_session_metrics dsm, params p
  WHERE dsm.date::DATE BETWEEN p.start_date AND p.end_date
    AND LOWER(dsm.platform) = LOWER(p.platform)
  GROUP BY dsm.ga_session_id, dsm.user_pseudo_id, dsm.is_engaged_session,dsm.distinct_pages
),
engaged_users AS (
  SELECT
    ROUND(AVG(engagement_time), 2)  AS avg_engagement_time,
    ROUND(AVG(distinct_pages), 2) AS avg_pages,
    ROUND(AVG(had_key_event), 2)    AS avg_key_events
  FROM session_pages
  WHERE LOWER(CAST(is_engaged_session AS VARCHAR)) = 'true'
),
churned_users AS (
  SELECT
    ROUND(AVG(engagement_time), 2)  AS avg_engagement_time,
    ROUND(AVG(distinct_pages), 2) AS avg_pages,
    ROUND(AVG(had_key_event), 2)    AS avg_key_events
  FROM session_pages
  WHERE LOWER(CAST(is_engaged_session AS VARCHAR)) = 'false'
)
SELECT
  'avg_engagement_time_msec' AS metric,
  e.avg_engagement_time      AS engaged_value,
  c.avg_engagement_time      AS churned_value
FROM engaged_users e, churned_users c
UNION ALL
SELECT
  'avg_pages_per_session',
  e.avg_pages,
  c.avg_pages
FROM engaged_users e, churned_users c
UNION ALL
SELECT
  'avg_key_events',
  e.avg_key_events,
  c.avg_key_events
FROM engaged_users e, churned_users c;
"""

PRODUCT_ENGAGEMENT_KPIS = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  ROUND(
    AVG(CASE WHEN is_engaged_session THEN total_engagement_time_msec ELSE NULL END),
    2
  ) AS avg_engaged_duration_msec,
  COUNT(DISTINCT CASE WHEN is_engaged_session THEN ga_session_id ELSE NULL END) AS engaged_sessions,
  ROUND(
    100.0 * COUNT(DISTINCT CASE WHEN is_engaged_session THEN ga_session_id ELSE NULL END)
    / NULLIF(COUNT(DISTINCT ga_session_id), 0),
    2
  ) AS engagement_rate,
  SUM(total_events) AS total_event_count,
  SUM(key_events) AS key_event_count,
  SUM(page_views) AS total_page_views
FROM daily_session_metrics dsm, vars v
WHERE dsm.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dsm.platform) = LOWER(v.platform);
"""

PRODUCT_PAGE_ENGAGEMENT_TABLE = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  page_path_level_1,
  SUM(page_views) AS page_views,
  SUM(anonymous_visitors) AS anonymous_visitors,
  SUM(signed_in_users) AS signed_in_users,
  ROUND(AVG(avg_engagement_time_msec), 2) AS avg_engagement_time_msec,
  SUM(key_events) AS key_events,
  ROUND(AVG(avg_percent_scrolled), 2) AS avg_scroll_depth
FROM daily_page_metrics dpm, vars v
WHERE dpm.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dpm.platform) = LOWER(v.platform)
GROUP BY
  page_title,
  page_path_level_1
ORDER BY page_views DESC;
"""

PRODUCT_ORG_ENGAGEMENT_TABLE = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
  organization_id,
  organizationName,
  SUM(anonymous_visitors) AS anonymous_visitors,
  SUM(signed_in_users) AS signed_in_users,
  SUM(sessions) AS sessions,
  SUM(key_events) AS key_events,
  ROUND(
    100.0 * SUM(engaged_sessions) / NULLIF(SUM(sessions), 0),
    2
  ) AS engagement_rate,
  ROUND(AVG(avg_engagement_time_msec), 2) AS avg_engagement_time_msec
FROM daily_organization_metrics dom, vars v
WHERE dom.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dom.platform) = LOWER(v.platform)
  --AND user_type = 'external'
GROUP BY organization_id, organizationName
ORDER BY key_events DESC;
"""

REGCOMPLY_ORG_DEEP_DIVE_DETAILS = """
WITH member_count AS (
    SELECT
        organization_id,
        COUNT(*) FILTER (WHERE isDeleted = 'false') AS total_members,
        MAX(TRY_CAST(lastActive AS TIMESTAMP)) AS last_member_active
    FROM regcomply_users
    WHERE organization_id = ?
    GROUP BY organization_id
)
SELECT
    o.organization_id,
    o.organizationName,
    o.email,
    o.industry,
    o.country_name,
    o.subscriptionPlan,
    o.subscriptionStatus,
    o.upgrade,
    (TRY_CAST(o.createdAt AS TIMESTAMP))::DATE AS member_since,
    (TRY_CAST(o.updatedAt AS TIMESTAMP))::DATE AS last_org_updated,
    COALESCE(m.total_members, 0) AS total_members,
    m.last_member_active
FROM regcomply_organizations o
LEFT JOIN member_count m ON o.organization_id = m.organization_id
WHERE o.organization_id = ?
LIMIT 1;
"""

REGCOMPLY_ORG_CONVERSION_MILESTONES = """
WITH audit_base AS (
    SELECT *
    FROM regcomply_audit
    WHERE organization_id = ?
      AND TRY_CAST(startDate AS TIMESTAMP)::DATE BETWEEN ?::DATE AND ?::DATE
),
org_info AS (
    SELECT subscriptionPlan, subscriptionStatus
    FROM regcomply_organizations
    WHERE organization_id = ?
    LIMIT 1
)
SELECT
    o.subscriptionPlan,
    o.subscriptionStatus,
    MIN(TRY_CAST(a.createdAt AS TIMESTAMP))::DATE              AS first_audit_created,
    COUNT(*)                                                    AS total_audits,
    COUNT(*) FILTER (WHERE a.status IN ('completed','audited','approved')) AS completed_audits,
    COUNT(*) FILTER (WHERE a.status IN ('ongoing','pending','request'))    AS active_audits,
    COUNT(*) FILTER (WHERE a.status = 'declined')              AS declined_audits,
    ROUND(AVG(date_diff('day',
        TRY_CAST(a.startDate AS TIMESTAMP),
        TRY_CAST(a.endDate AS TIMESTAMP))), 1)                 AS avg_planned_days,
    COUNT(*) FILTER (WHERE a.useCheckList = 'true')            AS checklist_used,
    COUNT(*) FILTER (WHERE a.requestExtension = 'true')        AS extensions_requested
FROM org_info o, audit_base a
GROUP BY o.subscriptionPlan, o.subscriptionStatus;
"""

REGCOMPLY_ORG_AUDIT_FUNNEL = """
WITH base AS (
    SELECT *
    FROM regcomply_audit
    WHERE organization_id = ?
      AND TRY_CAST(startDate AS TIMESTAMP)::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT 'Created'       AS stage, 1 AS stage_order, COUNT(*)                              AS count FROM base
UNION ALL
SELECT 'Approved'      AS stage, 2,  COUNT(*) FILTER (WHERE approvedAt IS NOT NULL)       FROM base
UNION ALL
SELECT 'Questions Set' AS stage, 3,  COUNT(*) FILTER (WHERE questionsSetAt IS NOT NULL)   FROM base
UNION ALL
SELECT 'Responded'     AS stage, 4,  COUNT(*) FILTER (WHERE respondedAt IS NOT NULL)      FROM base
UNION ALL
SELECT 'Audited'       AS stage, 5,  COUNT(*) FILTER (WHERE auditedAt IS NOT NULL)        FROM base
UNION ALL
SELECT 'Completed'     AS stage, 6,  COUNT(*) FILTER (WHERE completedAt IS NOT NULL)      FROM base
ORDER BY stage_order;
"""

REGCOMPLY_ORG_MODULE_DEEPDIVE = """
WITH base AS (
    SELECT *
    FROM regcomply_audit
    WHERE organization_id = ?
      AND TRY_CAST(startDate AS TIMESTAMP)::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
    standardName,
    auditType,
    COUNT(*)                                                                AS total_audits,
    COUNT(*) FILTER (WHERE status IN ('completed','audited','approved'))    AS completed_audits,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status IN ('completed','audited','approved'))
          / NULLIF(COUNT(*), 0), 1)                                         AS completion_rate,
    ROUND(100.0 * (1 - COUNT(*) FILTER (WHERE status IN ('completed','audited','approved')) * 1.0
          / NULLIF(COUNT(*), 0)), 1)                                         AS drop_off_rate,
    ROUND(AVG(date_diff('day',
        TRY_CAST(startDate AS TIMESTAMP),
        TRY_CAST(endDate AS TIMESTAMP))), 1)                                AS avg_planned_days,
    ROUND(AVG(date_diff('day',
        TRY_CAST(createdAt AS TIMESTAMP),
        COALESCE(
            TRY_CAST(completedAt AS TIMESTAMP),
            TRY_CAST(auditedAt AS TIMESTAMP),
            TRY_CAST(respondedAt AS TIMESTAMP),
            now()
        ))), 1)                                                             AS avg_actual_days,
    COUNT(*) FILTER (WHERE useCheckList = 'true')                           AS checklist_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE useCheckList = 'true')
          / NULLIF(COUNT(*), 0), 1)                                         AS checklist_pct,
    AVG(date_diff('hour',
        TRY_CAST(questionsSetAt AS TIMESTAMP),
        TRY_CAST(respondedAt AS TIMESTAMP)))                                AS avg_hrs_to_respond
FROM base
GROUP BY standardName, auditType
ORDER BY total_audits DESC;
"""

REGCOMPLY_ORG_STAGE_BOTTLENECK = """
WITH base AS (
    SELECT *
    FROM regcomply_audit
    WHERE organization_id = ?
      AND TRY_CAST(startDate AS TIMESTAMP)::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
    ROUND(AVG(date_diff('hour',
        TRY_CAST(createdAt AS TIMESTAMP),
        TRY_CAST(approvedAt AS TIMESTAMP))) / 24.0, 2)          AS days_creation_to_approval,
    ROUND(AVG(date_diff('hour',
        TRY_CAST(approvedAt AS TIMESTAMP),
        TRY_CAST(questionsSetAt AS TIMESTAMP))) / 24.0, 2)      AS days_approval_to_questions,
    ROUND(AVG(date_diff('hour',
        TRY_CAST(questionsSetAt AS TIMESTAMP),
        TRY_CAST(respondedAt AS TIMESTAMP))) / 24.0, 2)         AS days_questions_to_response,
    ROUND(AVG(date_diff('hour',
        TRY_CAST(respondedAt AS TIMESTAMP),
        TRY_CAST(auditedAt AS TIMESTAMP))) / 24.0, 2)           AS days_response_to_audited,
    ROUND(AVG(date_diff('hour',
        TRY_CAST(auditedAt AS TIMESTAMP),
        TRY_CAST(completedAt AS TIMESTAMP))) / 24.0, 2)         AS days_audited_to_complete
FROM base
WHERE createdAt IS NOT NULL;
"""

REGCOMPLY_ORG_USER_BREAKDOWN = """
WITH user_metrics AS (
    SELECT
        m.user_id,
        SUM(CAST(m.session_count AS INTEGER))      AS sessions,
        SUM(CAST(m.key_event_count AS INTEGER))    AS key_events,
        MAX(m.date::DATE)                          AS last_active_date,
        COUNT(DISTINCT m.date)                     AS active_days
    FROM daily_user_metrics m
    INNER JOIN regcomply_users u ON m.user_id = u.user_id
    WHERE u.organization_id = ?
      AND m.date::DATE BETWEEN ?::DATE AND ?::DATE
    GROUP BY m.user_id
)
SELECT
    u.user_id,
    u.email,
    u.role_name,
    u.status,
    TRY_CAST(u.lastActive AS TIMESTAMP)::DATE   AS last_active,
    TRY_CAST(u.createdAt AS TIMESTAMP)::DATE    AS joined,
    COALESCE(um.sessions, 0)                    AS sessions,
    COALESCE(um.key_events, 0)                  AS key_events,
    COALESCE(um.active_days, 0)                 AS active_days,
    CASE
        WHEN TRY_CAST(u.lastActive AS TIMESTAMP)::DATE >= CURRENT_DATE - 7  THEN 'Active'
        WHEN TRY_CAST(u.lastActive AS TIMESTAMP)::DATE >= CURRENT_DATE - 14 THEN 'Dormant'
        ELSE 'Inactive'
    END AS activity_status
FROM regcomply_users u
LEFT JOIN user_metrics um ON u.user_id = um.user_id
WHERE u.organization_id = ?
  AND u.isDeleted = 'false'
ORDER BY COALESCE(um.sessions, 0) DESC;
"""

#---RegComply Feature Adoption
REGCOMPLY_AUDIT_COUNT = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date
)
SELECT COUNT(*) AS total_audits
FROM regcomply_audit_metrics ram, vars v
WHERE (TRY_CAST(ram.startDate AS TIMESTAMP))::DATE BETWEEN v.start_date AND v.end_date
"""

REGCOMPLY_AUDIT_COMPLETION_RATE = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date
)
SELECT
  ROUND(100.0 * 
        COUNTIF(status IN ('completed','approved','audited')) 
        / COUNT(*), 
        2) AS completion_rate
FROM regcomply_audit_metrics ram, vars v
WHERE (TRY_CAST(ram.startDate AS TIMESTAMP))::DATE BETWEEN v.start_date AND v.end_date
"""

REGCOMPLY_ACTIVE_AUDITS = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date
)
SELECT
  COUNT(*) AS active_audits
FROM regcomply_audit_metrics ram, vars v
WHERE (TRY_CAST(ram.startDate AS TIMESTAMP))::DATE BETWEEN v.start_date AND v.end_date
  AND ram.status IN ('ongoing','pending','request')
"""

REGCOMPLY_AVERAGE_AUDIT_DURATION = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date
)

SELECT
  AVG(date_diff('day', 
    TRY_CAST(ram.startDate AS TIMESTAMP),
    COALESCE(TRY_CAST(ram.completedAt AS TIMESTAMP), now())
  )) AS avg_duration_days
FROM regcomply_audit_metrics ram, vars v
WHERE (TRY_CAST(ram.startDate AS TIMESTAMP))::DATE BETWEEN v.start_date AND v.end_date
  AND ram.startDate IS NOT NULL
"""

RECOMPLY_EXTERNAL_AUDIT_PCT = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date
)
SELECT
  ROUND(100.0 * 
        COUNTIF(auditType = 'external') 
        / COUNT(*), 
        2) AS external_audit_pct
FROM regcomply_audit_metrics ram, vars v
WHERE (TRY_CAST(ram.startDate AS TIMESTAMP))::DATE BETWEEN v.start_date AND v.end_date
"""

REGCOMPLY_AUDIT_FUNNEL = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date
)

SELECT 'Created' AS stage, COUNT(*) AS audits FROM regcomply_audit_metrics ram, vars v
WHERE (TRY_CAST(ram.startDate AS TIMESTAMP))::DATE BETWEEN v.start_date AND v.end_date
UNION ALL
SELECT 'Approved' AS stage, COUNT(*) AS audits FROM regcomply_audit_metrics ram, vars v
WHERE (TRY_CAST(ram.approvedAt AS TIMESTAMP))::DATE BETWEEN v.start_date AND v.end_date
UNION ALL
SELECT 'Questions Set', COUNTIF(questionsSetAt IS NOT NULL) FROM regcomply_audit_metrics ram, vars v
WHERE (TRY_CAST(ram.startDate AS TIMESTAMP))::DATE BETWEEN v.start_date AND v.end_date
UNION ALL
SELECT 'Responded', COUNTIF(respondedAt IS NOT NULL) FROM regcomply_audit_metrics ram, vars v
WHERE (TRY_CAST(ram.startDate AS TIMESTAMP))::DATE BETWEEN v.start_date AND v.end_date
UNION ALL
SELECT 'Audited', COUNTIF(auditedAt IS NOT NULL) FROM regcomply_audit_metrics ram, vars v
WHERE (TRY_CAST(ram.startDate AS TIMESTAMP))::DATE BETWEEN v.start_date AND v.end_date
UNION ALL
SELECT 'Completed', COUNTIF(completedAt IS NOT NULL) FROM regcomply_audit_metrics ram, vars v
WHERE (TRY_CAST(ram.startDate AS TIMESTAMP))::DATE BETWEEN v.start_date AND v.end_date;
"""

REGCOMPLY_STATUS_DISTRIBUTION = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  CASE
    WHEN status IN ('ongoing','pending','request') THEN 'Active'
    WHEN status IN ('completed','approved','audited') THEN 'Completed'
    WHEN status = 'declined' THEN 'Failed'
    ELSE 'Other'
  END AS status_group,
  COUNT(*) AS audits
FROM base
GROUP BY status_group;
"""

REGCOMPLY_AUDIT_TYPE_SPLIT = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  auditType,
  COUNT(*) AS audits
FROM base
GROUP BY auditType;
"""

REGCOMPLY_AUDITS_BY_STANDARD = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  standardName,
  COUNT(*) AS audits
FROM base
GROUP BY standardName
ORDER BY audits DESC;
"""

REGCOMPLY_AUDIT_DURATION_TREND = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  (TRY_CAST(createdAt AS TIMESTAMP))::DATE AS audit_date,
  AVG(date_diff('day', 
    TRY_CAST(startDate AS TIMESTAMP),
    COALESCE(TRY_CAST(completedAt AS TIMESTAMP), now())
  )) AS avg_duration
FROM base
WHERE startDate IS NOT NULL
GROUP BY audit_date
ORDER BY audit_date;
"""

REGCOMPLY_TIME_TO_QUESTIONS = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  AVG(date_diff('hour', TRY_CAST(createdAt AS TIMESTAMP), TRY_CAST(questionsSetAt AS TIMESTAMP))) AS avg_hours_to_questions
FROM base
WHERE questionsSetAt IS NOT NULL;
"""

REGCOMPLY_TIME_TO_RESPOND = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  AVG(date_diff('hour', TRY_CAST(questionsSetAt AS TIMESTAMP), TRY_CAST(respondedAt AS TIMESTAMP))) AS avg_hours_to_respond
FROM base
WHERE respondedAt IS NOT NULL;
"""

REGCOMPLY_TIME_TO_COMPLETE = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  AVG(date_diff('day', TRY_CAST(createdAt AS TIMESTAMP), TRY_CAST(completedAt AS TIMESTAMP))) AS avg_days_to_complete
FROM base
WHERE completedAt IS NOT NULL;
"""

REGCOMPLY_CHECKLIST_ADOPTION = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  useCheckList,
  COUNT(*) AS audits,
  COUNT(*) / SUM(COUNT(*)) OVER() AS pct
FROM base
GROUP BY useCheckList;
"""

REGCOMPLY_SCORING_PATTERN_USAGE = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  scoringPattern,
  COUNT(*) AS usage_count
FROM base
GROUP BY scoringPattern
ORDER BY usage_count DESC;
"""

REGCOMPLY_EXTENSION_RATE = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  COUNT(*) FILTER (WHERE requestExtensionDate IS NOT NULL) / COUNT(*) AS extension_rate
FROM base;
"""

REGCOMPLY_DELAYED_AUDITS = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  COUNT(*) AS delayed_audits
FROM base
WHERE
  endDate IS NOT NULL
  AND (
    TRY_CAST(completedAt AS TIMESTAMP) > TRY_CAST(endDate AS TIMESTAMP)
    OR (completedAt IS NULL AND now() > TRY_CAST(endDate AS TIMESTAMP))
  );
"""

REGCOMPLY_ORG_PERFORMANCE_TABLE = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  organization_id,
  org_name,
  COUNT(*) AS total_audits,
  COUNT(*) FILTER (WHERE status IN ('completed','approved','audited')) / COUNT(*) AS completion_rate,
  AVG(date_diff('day', 
    TRY_CAST(startDate AS TIMESTAMP),
    COALESCE(TRY_CAST(completedAt AS TIMESTAMP), now())
  )) AS avg_duration,
  COUNT(*) FILTER (WHERE status IN ('ongoing','pending')) AS active_audits
FROM base
GROUP BY organization_id, org_name
ORDER BY total_audits DESC;
"""

REGCOMPLY_AUDITS_PER_ORG = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  organization_id,
  COUNT(*) AS audits_per_org
FROM base
GROUP BY organization_id;
"""

REGCOMPLY_LIFECYCLE_DURATION_TABLE = """
WITH base AS (
  SELECT * FROM regcomply_audit_metrics
  WHERE (TRY_CAST(startDate AS TIMESTAMP))::DATE BETWEEN ?::DATE AND ?::DATE
)
SELECT
  auditTitle AS audit_title,
  COUNT(*) AS total_audits,
  COUNT(*) FILTER (WHERE status IN ('audited', 'completed')) AS total_completed_audits,

  -- 1. Creation → Next Stage (secs)
  --AVG(
  --  date_diff('second',
  --    TRY_CAST(createdAt AS TIMESTAMP),
  --    COALESCE(
  --      TRY_CAST(approvedAt AS TIMESTAMP),
  --      TRY_CAST(questionsSetAt AS TIMESTAMP),
  --      TRY_CAST(respondedAt AS TIMESTAMP),
  --      TRY_CAST(auditedAt AS TIMESTAMP),
  --      TRY_CAST(completedAt AS TIMESTAMP)
  --    )
  --  )
  --) AS secs_creation_to_next,

  -- 2. Approval → Next Stage (secs)
  --AVG(
  --  date_diff('second',
  --    TRY_CAST(approvedAt AS TIMESTAMP),
  --    COALESCE(
  --      TRY_CAST(questionsSetAt AS TIMESTAMP),
  --      TRY_CAST(respondedAt AS TIMESTAMP),
  --      TRY_CAST(auditedAt AS TIMESTAMP),
  --      TRY_CAST(completedAt AS TIMESTAMP)
  --    )
  --  )
  --) AS secs_approval_stage,

  -- 3. Question Set → Next Stage (secs)
  --AVG(
  --  date_diff('second',
  --    TRY_CAST(questionsSetAt AS TIMESTAMP),
  --    COALESCE(
  --      TRY_CAST(respondedAt AS TIMESTAMP),
  --      TRY_CAST(auditedAt AS TIMESTAMP),
  --      TRY_CAST(completedAt AS TIMESTAMP)
  --    )
  --  )
  --) AS secs_question_stage,

  -- 4. Response → Next Stage (secs)
  --AVG(
  --  date_diff('second',
  --    TRY_CAST(respondedAt AS TIMESTAMP),
  --    COALESCE(
  --      TRY_CAST(auditedAt AS TIMESTAMP),
  --      TRY_CAST(completedAt AS TIMESTAMP)
  --    )
  --  )
  --) AS secs_response_stage,

  -- 5. Audit Feedback → Completion (secs)
  --AVG(
  --  date_diff('second',
  --    TRY_CAST(auditedAt AS TIMESTAMP),
  --    TRY_CAST(completedAt AS TIMESTAMP)
  --  )
  --) AS secs_feedback_to_completion,

  -- 6. Planned Duration (secs)
  AVG(
    date_diff('second',
      TRY_CAST(startDate AS TIMESTAMP),
      TRY_CAST(endDate AS TIMESTAMP)
    )
  ) AS secs_planned_duration,

  -- 7. Actual Duration (secs)
  AVG(
    date_diff('second',
      TRY_CAST(createdAt AS TIMESTAMP),
      COALESCE(
        TRY_CAST(completedAt AS TIMESTAMP),
        TRY_CAST(auditedAt AS TIMESTAMP),
        TRY_CAST(respondedAt AS TIMESTAMP),
        TRY_CAST(questionsSetAt AS TIMESTAMP),
        TRY_CAST(approvedAt AS TIMESTAMP)
      )
    )
  ) AS secs_actual_duration

FROM base
GROUP BY auditTitle
ORDER BY total_audits DESC;
"""

#-- ============================================================================
#-- ORGANIZATION DEEP-DIVE: List of organizations per platform
#-- Output: organization_id, organizationName
#-- ============================================================================
PRODUCT_ORG_LIST = """
SELECT DISTINCT
  organization_id,
  organizationName,
  organization_start_date,
  email_domain
FROM all_organizations
WHERE LOWER(platform) = LOWER(?)
  AND organizationName IS NOT NULL
  AND organizationName NOT LIKE '%<%'
  AND organizationName NOT LIKE '%>%'
  AND LOWER(organizationName) NOT LIKE '%script%'
  AND LOWER(organizationName) NOT LIKE '%iframe%'
ORDER BY organizationName ASC;
"""

#-- ============================================================================
#-- ORGANIZATION DEEP-DIVE: Count unique users for org + platform
#-- Params: organization_id, platform
#-- ============================================================================
PRODUCT_ORG_DEEP_DIVE_USER_COUNT = """
SELECT
  organization_id,
  platform,
  COUNT(DISTINCT user_id) AS user_count
FROM all_users
WHERE organization_id = ?
  AND LOWER(platform) = LOWER(?)
  AND organization_id IS NOT NULL
GROUP BY organization_id, platform;
"""

PRODUCT_ORG_DEEP_DIVE_LAST_ACTIVITY_DATE = """
SELECT
  organization_id,
  MAX(date) AS last_activity_date,
  COUNT(DISTINCT CONCAT(user_pseudo_id, CAST(ga_session_id AS STRING))) AS total_sessions
FROM daily_session_metrics
WHERE organization_id = ?
  AND LOWER(platform) = LOWER(?)
GROUP BY organization_id;
"""


REGWATCH_ASSESSMENT_SUMMARY = """
SELECT
    COUNT(*)                                                            AS total_assessments,
    SUM(CASE WHEN status = 'Completed'   THEN 1 ELSE 0 END)            AS completed,
    SUM(CASE WHEN status = 'Not Started' THEN 1 ELSE 0 END)            AS not_started,
    SUM(CASE WHEN status = 'Expired'     THEN 1 ELSE 0 END)            AS expired,
    ROUND(100.0 * SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 1)                                     AS completion_rate_pct,
    ROUND(AVG(CAST(compliance_percentage AS DOUBLE)), 1)                AS avg_compliance_pct,
    ROUND(AVG(CAST(compliant_count AS DOUBLE)), 1)                      AS avg_compliant_items,
    ROUND(AVG(CAST(non_compliant_count AS DOUBLE)), 1)                  AS avg_non_compliant_items,
    ROUND(AVG(CAST(unanswered_count AS DOUBLE)), 1)                     AS avg_unanswered_items,
    MIN(CAST(started_at AS TIMESTAMP))                                  AS first_assessment_at,
    MAX(CAST(started_at AS TIMESTAMP))                                  AS last_assessment_at,
    COUNT(DISTINCT regulation_id)                                       AS distinct_regulations,
    COUNT(DISTINCT started_by)                                          AS distinct_assessors,
    ROUND(AVG(date_diff('second', CAST(started_at AS TIMESTAMP), CAST(completed_at AS TIMESTAMP))) / 60.0, 1) AS avg_time_to_complete_min
FROM regwatch_pre_assessment
WHERE CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""


REGWATCH_ASSESSMENT_TREND_MONTHLY = """
SELECT
    DATE_TRUNC('month', CAST(started_at AS TIMESTAMP))   AS month,
    COUNT(*)                                              AS total_started,
    SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
    SUM(CASE WHEN status = 'Expired'   THEN 1 ELSE 0 END) AS expired,
    ROUND(AVG(CAST(compliance_percentage AS DOUBLE)), 1)  AS avg_compliance_pct,
    ROUND(AVG(CAST(compliant_count AS DOUBLE)), 1)        AS avg_compliant_items,
    ROUND(AVG(CAST(non_compliant_count AS DOUBLE)), 1)    AS avg_non_compliant_items,
    ROUND(AVG(CAST(unanswered_count AS DOUBLE)), 1)       AS avg_unanswered_items
FROM regwatch_pre_assessment
WHERE CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY month
ORDER BY month ASC;
"""


REGWATCH_ASSESSMENT_STATUS_BREAKDOWN = """
SELECT
    status,
    COUNT(*)                                                          AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)               AS pct,
    ROUND(AVG(CAST(compliance_percentage AS DOUBLE)), 1)              AS avg_compliance_pct
FROM regwatch_pre_assessment
WHERE CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY status
ORDER BY count DESC;
"""


REGWATCH_DEADLINE_ADHERENCE = """
SELECT
    SUM(CASE
        WHEN status = 'Completed'
         AND CAST(completed_at AS TIMESTAMP) <= CAST(deadline AS TIMESTAMP)
        THEN 1 ELSE 0 END)                AS completed_on_time,
    SUM(CASE
        WHEN status = 'Completed'
         AND CAST(completed_at AS TIMESTAMP) > CAST(deadline AS TIMESTAMP)
        THEN 1 ELSE 0 END)                AS completed_late,
    SUM(CASE WHEN status = 'Expired' THEN 1 ELSE 0 END) AS missed_deadline,
    COUNT(*)                              AS total
FROM regwatch_pre_assessment
WHERE CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""


REGWATCH_COMPLIANCE_SCORE_DISTRIBUTION = """
SELECT
    CASE
        WHEN CAST(compliance_percentage AS DOUBLE) = 100  THEN '100%'
        WHEN CAST(compliance_percentage AS DOUBLE) >= 80  THEN '80–99%'
        WHEN CAST(compliance_percentage AS DOUBLE) >= 60  THEN '60–79%'
        WHEN CAST(compliance_percentage AS DOUBLE) >= 40  THEN '40–59%'
        ELSE 'Below 40%'
    END                AS score_band,
    COUNT(*)           AS assessments,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM regwatch_pre_assessment
WHERE status = 'Completed'
  AND CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY score_band
ORDER BY MIN(CAST(compliance_percentage AS DOUBLE)) DESC;
"""


REGWATCH_REGULATORY_AREA_COVERAGE = """
SELECT
    r.regulatory_area,
    COUNT(pa.pre_assessment_id)                                    AS assessments_run,
    SUM(CASE WHEN pa.status = 'Completed' THEN 1 ELSE 0 END)      AS completed,
    COALESCE(ROUND(AVG(CAST(pa.compliance_percentage AS DOUBLE)), 1), 0.0) AS avg_compliance_pct,
    COUNT(DISTINCT pa.regulation_id)                               AS distinct_regulations
FROM regwatch_pre_assessment pa
JOIN regwatch_regulations r ON r.regulation_id = pa.regulation_id
WHERE CAST(pa.started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY r.regulatory_area
ORDER BY assessments_run DESC;
"""


REGWATCH_REPEAT_ASSESSMENT_RATE = """
SELECT
    regulation_id,
    regulation_title,
    COUNT(*) AS times_assessed
FROM regwatch_pre_assessment
WHERE CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY regulation_id, regulation_title
HAVING COUNT(*) > 1
ORDER BY times_assessed DESC;
"""


REGWATCH_REGULATOR_USAGE = """
SELECT
    r.regulator_name,
    r.regulator_code,
    r.regulator_country,
    COUNT(pa.pre_assessment_id)                                    AS assessments_run,
    COUNT(DISTINCT pa.regulation_id)                               AS distinct_regulations,
    COALESCE(ROUND(AVG(CAST(pa.compliance_percentage AS DOUBLE)), 1), 0.0) AS avg_compliance_pct
FROM regwatch_pre_assessment pa
JOIN regwatch_regulations r ON r.regulation_id = pa.regulation_id
WHERE CAST(pa.started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY r.regulator_name, r.regulator_code, r.regulator_country
ORDER BY assessments_run DESC;
"""


REGWATCH_LOW_COMPLIANCE_REGULATIONS = """
SELECT
    pa.regulation_title,
    r.regulatory_area,
    r.risk_level,
    COALESCE(ROUND(AVG(CAST(pa.compliance_percentage AS DOUBLE)), 1), 0.0)  AS avg_compliance_pct,
    COALESCE(ROUND(AVG(CAST(pa.non_compliant_count AS DOUBLE)), 1), 0.0)    AS avg_non_compliant_items,
    COUNT(*)                                                  AS attempts
FROM regwatch_pre_assessment pa
JOIN regwatch_regulations r ON r.regulation_id = pa.regulation_id
WHERE pa.status = 'Completed'
  AND CAST(pa.compliance_percentage AS DOUBLE) < 80
  AND CAST(pa.started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY pa.regulation_title, r.regulatory_area, r.risk_level
ORDER BY avg_compliance_pct ASC
LIMIT 10;
"""


REGWATCH_DEEP_ORG_PROFILE = """
SELECT
    o.organization_id,
    o.organizationName,
    o.email,
    o.emailDomain,
    o.industry,
    o.employeeSize,
    o.description,
    o.services,
    o.country_name,
    o.isActive,
    o.isRegTechOrg,
    o.createdAt                                        AS org_created_at,
    o.updatedAt                                        AS org_updated_at,
    DATEDIFF('day',
        CAST(o.createdAt AS TIMESTAMP),
        CURRENT_TIMESTAMP)                             AS days_since_onboarding,
    DATEDIFF('day',
        CAST(o.createdAt AS TIMESTAMP),
        CAST(o.updatedAt AS TIMESTAMP))                AS days_since_last_profile_update
FROM regwatch_organizations o
WHERE o.organization_id = ?;
"""


REGWATCH_DEEP_GA4_SUMMARY = """
SELECT
    COUNT(DISTINCT date)                                     AS active_days,
    SUM(CAST(sessions AS INTEGER))                           AS total_sessions,
    SUM(CAST(active_users AS INTEGER))                       AS total_active_users,
    SUM(CAST(key_events AS INTEGER))                         AS total_key_events,
    SUM(CAST(total_events AS INTEGER))                       AS total_events,
    SUM(CAST(signed_in_users AS INTEGER))                    AS total_signed_in_users,
    SUM(CAST(anonymous_visitors AS INTEGER))                 AS total_anonymous,
    ROUND(AVG(CAST(active_users AS DOUBLE)), 1)              AS avg_daily_active_users,
    ROUND(SUM(CAST(total_engagement_time_msec AS DOUBLE))
          / 60000.0
          / NULLIF(SUM(CAST(sessions AS INTEGER)), 0), 2)    AS avg_session_engagement_min,
    SUM(CAST(engaged_sessions AS INTEGER))                   AS total_engaged_sessions,
    ROUND(100.0 * SUM(CAST(engaged_sessions AS INTEGER))
          / NULLIF(SUM(CAST(sessions AS INTEGER)), 0), 1)    AS engaged_session_pct,
    MAX(date)                                                AS last_active_date,
    MIN(date)                                                AS first_active_date
FROM daily_organization_metrics
WHERE organization_id = ?
  AND LOWER(platform) = 'regwatch'
  AND CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE);
"""


REGWATCH_DEEP_NORTHSTAR_EVENTS = """
SELECT
    date,
    SUM(CAST(northstar_view_regulation_count AS INTEGER))        AS regulation_views,
    SUM(CAST(northstar_regtech365_login_count AS INTEGER))       AS ecosystem_logins,
    SUM(CAST(northstar_customer_verification_count AS INTEGER))  AS customer_verifications,
    SUM(CAST(key_event_count AS INTEGER))                        AS total_key_events,
    COUNT(DISTINCT user_pseudo_id)                               AS distinct_users
FROM daily_user_metrics
WHERE organization_id = ?
  AND LOWER(platform) = 'regwatch'
  AND CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY date
ORDER BY date ASC;
"""


PRODUCT_DEEP_GA4_WEEKLY_PATTERN = """
SELECT
    DAYOFWEEK(CAST(date AS TIMESTAMP))             AS day_of_week,
    ROUND(AVG(CAST(active_users AS DOUBLE)), 1)    AS avg_active_users,
    ROUND(AVG(CAST(sessions AS DOUBLE)), 1)        AS avg_sessions,
    ROUND(AVG(CAST(key_events AS DOUBLE)), 1)      AS avg_key_events
FROM daily_organization_metrics
WHERE organization_id = ?
  AND LOWER(platform) = LOWER(?)
  AND CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY day_of_week
ORDER BY day_of_week;
"""


PRODUCT_DEEP_TRAFFIC_SOURCE = """
SELECT
    COALESCE(NULLIF(session_traffic_source, '(not set)'), 'Direct') AS source,
    COALESCE(NULLIF(session_traffic_medium, '(not set)'), 'Direct') AS medium,
    COUNT(DISTINCT ga_session_id)                                     AS sessions,
    ROUND(AVG(CAST(total_engagement_time_msec AS DOUBLE)) / 60000.0, 2) AS avg_engagement_min
FROM daily_session_metrics
WHERE organization_id = ?
  AND LOWER(platform) = LOWER(?)
  AND CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY source, medium
ORDER BY sessions DESC
LIMIT 10;
"""




#--- RegPort Feature Adoption (PULSE KPIs)
REGPORT_PULSE_ACTIVE_ORGS = """
SELECT
    COUNT(DISTINCT organizationId) AS active_org_count
FROM regport_audit_trails
WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
  AND organizationId IS NOT NULL;
"""

REGPORT_PULSE_WORKFLOW_COMPLETION = """
WITH params AS (
    SELECT
        TRY_CAST(? AS TIMESTAMP) AS start_date,
        TRY_CAST(? AS TIMESTAMP) + INTERVAL '1 day' AS end_date
),
org_ingestion AS (

    SELECT DISTINCT
        TRIM(CAST(rup.organizationId AS VARCHAR)) AS organizationId
    FROM regport_uploaded_files rup, params p
    WHERE TRY_CAST(rup.createdAt AS TIMESTAMP)
          BETWEEN p.start_date AND p.end_date
      AND rup.organizationId IS NOT NULL

    UNION

    SELECT DISTINCT
        TRIM(CAST(rt.organizationId AS VARCHAR)) AS organizationId
    FROM regport_transactions rt, params p
    WHERE TRY_CAST(rt.transactionCreatedAt AS TIMESTAMP)
          BETWEEN p.start_date AND p.end_date
      AND rt.organizationId IS NOT NULL

    UNION

    SELECT DISTINCT
        TRIM(CAST(rat.organizationId AS VARCHAR)) AS organizationId
    FROM regport_audit_trails rat, params p
    WHERE (LOWER(TRIM(CAST(rat.actionType AS VARCHAR))) = 'batch upload' 
           OR LOWER(TRIM(CAST(rat.action AS VARCHAR))) = 'file uploaded')
      AND TRY_CAST(rat.createdAt AS TIMESTAMP)
          BETWEEN p.start_date AND p.end_date
      AND rat.organizationId IS NOT NULL
),
org_screening AS (

    SELECT DISTINCT
        TRIM(CAST(rs.organizationId AS VARCHAR)) AS organizationId
    FROM regport_screening_results rs, params p
    WHERE TRY_CAST(rs.createdAt AS TIMESTAMP)
          BETWEEN p.start_date AND p.end_date
      AND rs.organizationId IS NOT NULL

    UNION

    SELECT DISTINCT
        TRIM(CAST(vc.organizationId AS VARCHAR)) AS organizationId
    FROM regport_verify_customers vc, params p
    WHERE TRY_CAST(vc.createdAt AS TIMESTAMP)
          BETWEEN p.start_date AND p.end_date
      AND vc.organizationId IS NOT NULL
  
  UNION

    SELECT DISTINCT
        TRIM(CAST(ma.organizationId AS VARCHAR)) AS organizationId
    FROM regport_monitored_accounts ma, params p
    WHERE TRY_CAST(ma.createdAt AS TIMESTAMP)
          BETWEEN p.start_date AND p.end_date
      AND ma.organizationId IS NOT NULL),
org_reporting AS (

    SELECT DISTINCT
        TRIM(CAST(gr.organizationId AS VARCHAR)) AS organizationId
    FROM regport_generated_report gr, params p
    WHERE TRY_CAST(gr.createdAt AS TIMESTAMP)
          BETWEEN p.start_date AND p.end_date
      AND gr.organizationId IS NOT NULL
),
active_orgs AS (

    SELECT DISTINCT
        TRIM(CAST(rat.organizationId AS VARCHAR)) AS organizationId
    FROM regport_audit_trails rat, params p
    WHERE TRY_CAST(rat.createdAt AS TIMESTAMP)
          BETWEEN p.start_date AND p.end_date
      AND rat.organizationId IS NOT NULL
),
completed AS (

    SELECT DISTINCT
        a.organizationId
    FROM active_orgs a
    INNER JOIN org_ingestion i
        ON a.organizationId = i.organizationId
    INNER JOIN org_screening s
        ON a.organizationId = s.organizationId
    INNER JOIN org_reporting r
        ON a.organizationId = r.organizationId
)

SELECT
    COUNT(DISTINCT a.organizationId) AS total_active_orgs,

    COUNT(DISTINCT c.organizationId) AS completed_orgs,

    ROUND(
        (
            COUNT(DISTINCT c.organizationId) * 100.0
        ) / NULLIF(COUNT(DISTINCT a.organizationId), 0),
        1
    ) AS completion_rate_pct

FROM active_orgs a
LEFT JOIN completed c
    ON a.organizationId = c.organizationId;
"""

REGPORT_PULSE_AVG_MODULES = """
WITH module_counts AS (
    SELECT
        organizationId,
        COUNT(DISTINCT module) AS distinct_modules
    FROM regport_audit_trails
    WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
      AND module IS NOT NULL
      AND organizationId IS NOT NULL
    GROUP BY organizationId
)
SELECT
    ROUND(AVG(distinct_modules), 1) AS avg_modules_per_org,
    MIN(distinct_modules) AS min_modules,
    MAX(distinct_modules) AS max_modules
FROM module_counts;
"""

REGPORT_PULSE_FLAG_RESOLUTION = """
WITH flagged AS (
    SELECT COUNT(*) AS total_flagged
    FROM regport_transactions
    WHERE LOWER(CAST(transactionFlagged AS VARCHAR)) = 'true'
      AND LOWER(CAST(transactionIsDeleted AS VARCHAR)) = 'false'
      AND CAST(transactionCreatedAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
),
resolved AS (
    SELECT COUNT(*) AS total_resolved
    FROM regport_audit_trails
    WHERE actionType IN ('Transaction Confirmation', 'Transaction Dismissal', 'Transaction Escalation')
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
)
SELECT
    f.total_flagged,
    r.total_resolved,
    ROUND(r.total_resolved * 100.0 / NULLIF(f.total_flagged, 0), 1) AS resolution_rate_pct
FROM flagged f, resolved r;
"""

REGPORT_PULSE_REPORT_APPROVAL = """
WITH approval_events AS (
    SELECT
        SUM(CASE WHEN actionType = 'Report Approval' THEN 1 ELSE 0 END) AS approved,
        SUM(CASE WHEN actionType = 'Report Rejection' THEN 1 ELSE 0 END) AS rejected
    FROM regport_audit_trails
    WHERE actionType IN ('Report Approval', 'Report Rejection')
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
)
SELECT
    approved,
    rejected,
    approved + rejected AS total,
    ROUND(approved * 100.0 / NULLIF(approved + rejected, 0), 1) AS approval_rate_pct
FROM approval_events;
"""

REGPORT_PULSE_SUPPORT_TOUCH = """
WITH active_orgs AS (
    SELECT COUNT(DISTINCT organizationId) AS total_active
    FROM regport_audit_trails
    WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
),
support_orgs AS (
    SELECT COUNT(DISTINCT organizationId) AS orgs_with_support
    FROM regport_audit_trails
    WHERE actionType IN ('Live Chat Initiated', 'Email Support Accessed', 'Consultation Booking')
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
)
SELECT
    a.total_active,
    s.orgs_with_support,
    ROUND(s.orgs_with_support * 100.0 / NULLIF(a.total_active, 0), 1) AS support_touch_rate_pct
FROM active_orgs a, support_orgs s;
"""

# --- FLAGGED TRANSACTIONS MODULE QUERIES ---

REGPORT_FLAG_RATE_BY_ORG = """
SELECT
    organizationId,
    organizationName,
    COUNT(*) AS total_transactions,
    SUM(CASE WHEN LOWER(CAST(transactionFlagged AS VARCHAR)) = 'true' THEN 1 ELSE 0 END) AS flagged_count,
    ROUND(
        SUM(CASE WHEN LOWER(CAST(transactionFlagged AS VARCHAR)) = 'true' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0),
        2
    ) AS flag_rate_pct
FROM regport_transactions
WHERE LOWER(CAST(transactionIsDeleted AS VARCHAR)) = 'false'
  AND CAST(transactionCreatedAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY organizationId, organizationName
ORDER BY flag_rate_pct DESC;
"""

REGPORT_FLAG_RESOLUTION_FUNNEL = """
SELECT
    actionType,
    COUNT(*) AS event_count,
    COUNT(DISTINCT organizationId) AS org_count
FROM regport_audit_trails
WHERE actionType IN (
    'Dashboard Access',
    'Transaction Monitoring',
    'Transaction Confirmation',
    'Transaction Dismissal',
    'Transaction Escalation',
    'Suspicious Transaction Flagged'
)
AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY actionType
ORDER BY event_count DESC;
"""

REGPORT_RULE_EFFECTIVENESS = """
-- Both CTEs are ALL-TIME (no date filter).
-- The orgs that have resolution events and the orgs that have recent flagged
-- transactions are completely disjoint in the current data.  A date-filtered
-- join always returns 0 resolutions.  Showing all-time gives a meaningful
-- view of which rules trigger flags and how those are resolved overall.
WITH org_resolutions AS (
    SELECT
        organizationId,
        SUM(CASE WHEN actionType = 'Transaction Confirmation' THEN 1 ELSE 0 END) AS confirmed,
        SUM(CASE WHEN actionType = 'Transaction Dismissal'    THEN 1 ELSE 0 END) AS dismissed,
        SUM(CASE WHEN actionType = 'Transaction Escalation'   THEN 1 ELSE 0 END) AS escalated
    FROM regport_audit_trails
    WHERE actionType IN ('Transaction Confirmation', 'Transaction Dismissal', 'Transaction Escalation')
    AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
),
rule_flags AS (
    SELECT
        ruleCode,
        ruleTemplateName,
        organizationId,
        COUNT(DISTINCT transactionId) AS total_flagged
    FROM regport_transactions
    WHERE LOWER(CAST(transactionFlagged AS VARCHAR)) = 'true'
      AND LOWER(CAST(transactionIsDeleted AS VARCHAR)) = 'false'
      AND ruleCode IS NOT NULL
    GROUP BY ruleCode, ruleTemplateName, organizationId
)
SELECT
    rf.ruleCode,
    rf.ruleTemplateName,
    SUM(rf.total_flagged)                        AS total_flagged,
    COALESCE(SUM(r.confirmed), 0)                AS confirmed,
    COALESCE(SUM(r.dismissed), 0)                AS dismissed,
    COALESCE(SUM(r.escalated), 0)                AS escalated,
    ROUND(
        COALESCE(SUM(r.dismissed), 0) * 100.0
        / NULLIF(
            COALESCE(SUM(r.confirmed), 0)
            + COALESCE(SUM(r.dismissed), 0)
            + COALESCE(SUM(r.escalated), 0),
            0
        ),
        1
    ) AS dismissal_rate_pct
FROM rule_flags rf
LEFT JOIN org_resolutions r ON rf.organizationId = r.organizationId
GROUP BY rf.ruleCode, rf.ruleTemplateName
ORDER BY total_flagged DESC;
"""

REGPORT_FLAG_MANUAL_VS_RULE = """
SELECT
    SUM(CASE WHEN actionType = 'Suspicious Transaction Flagged' THEN 1 ELSE 0 END) AS manual_flags,
    SUM(CASE WHEN actionType IN ('Transaction Confirmation', 'Transaction Dismissal', 'Transaction Escalation') THEN 1 ELSE 0 END) AS rule_triggered_actions,
    COUNT(*) AS total_relevant_events
FROM regport_audit_trails
WHERE actionType IN (
    'Suspicious Transaction Flagged',
    'Transaction Confirmation',
    'Transaction Dismissal',
    'Transaction Escalation'
)
AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""

REGPORT_FLAG_DEBIT_CREDIT = """
WITH org_resolutions AS (
    SELECT
        organizationId,
        SUM(CASE WHEN actionType = 'Transaction Confirmation' THEN 1 ELSE 0 END) AS confirmed,
        SUM(CASE WHEN actionType = 'Transaction Dismissal'    THEN 1 ELSE 0 END) AS dismissed,
        SUM(CASE WHEN actionType = 'Transaction Escalation'   THEN 1 ELSE 0 END) AS escalated
    FROM regport_audit_trails
    WHERE actionType IN ('Transaction Confirmation', 'Transaction Dismissal', 'Transaction Escalation')
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
),
type_flags AS (
    SELECT
        transactionType,
        organizationId,
        COUNT(*) AS flagged_count
    FROM regport_transactions
    WHERE LOWER(CAST(transactionFlagged AS VARCHAR)) = 'true'
      AND LOWER(CAST(transactionIsDeleted AS VARCHAR)) = 'false'
    GROUP BY transactionType, organizationId
)
SELECT
    tf.transactionType,
    SUM(tf.flagged_count)                        AS flagged_count,
    COALESCE(SUM(r.confirmed), 0)                AS confirmed,
    COALESCE(SUM(r.dismissed), 0)                AS dismissed,
    COALESCE(SUM(r.escalated), 0)                AS escalated
FROM type_flags tf
LEFT JOIN org_resolutions r ON tf.organizationId = r.organizationId
GROUP BY tf.transactionType;
"""

REGPORT_FLAG_WEEKLY_TREND = """
WITH weekly_flags AS (
    SELECT
        DATE_TRUNC('week', CAST(transactionCreatedAt AS TIMESTAMP)) AS week_start,
        COUNT(*) AS flag_volume
    FROM regport_transactions
    WHERE LOWER(CAST(transactionFlagged AS VARCHAR)) = 'true'
      AND LOWER(CAST(transactionIsDeleted AS VARCHAR)) = 'false'
      AND CAST(transactionCreatedAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY week_start
),
weekly_resolutions AS (
    SELECT
        DATE_TRUNC('week', CAST(createdAt AS TIMESTAMP)) AS week_start,
        COUNT(*) AS resolution_count
    FROM regport_audit_trails
    WHERE actionType IN ('Transaction Confirmation', 'Transaction Dismissal', 'Transaction Escalation')
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY week_start
)
SELECT
    f.week_start,
    f.flag_volume,
    COALESCE(r.resolution_count, 0) AS resolution_count,
    ROUND(COALESCE(r.resolution_count, 0) * 100.0 / NULLIF(f.flag_volume, 0), 1) AS resolution_rate_pct
FROM weekly_flags f
LEFT JOIN weekly_resolutions r ON f.week_start = r.week_start
ORDER BY f.week_start;
"""

REGPORT_ORG_DEEP_DIVE_DETAILS = """
SELECT
    o.organizationId,
    o.organizationName,
    o.email,
    o.industry,
    o.businessCategory,
    o.businessSubCategory,
    o.country_name,
    o.submissionMode,
    o.monitoringDuration,
    o.primaryRegulator,
    o.autoMonitoring,
    o.cddCheckFrequency,
    o.upgrade,
    CASE
      WHEN LOWER(CAST(o.isDeleted AS VARCHAR)) = 'false' THEN 'Active'
      WHEN LOWER(CAST(o.isDeleted AS VARCHAR)) = 'true' THEN 'Inactive'
      ELSE 'Active'
    END AS org_status,
    o.createdAt AS org_created_at,
    o.trialStartData,
    o.trialEndDate,

    date_diff('day', CAST(o.createdAt AS TIMESTAMP), CURRENT_TIMESTAMP) AS days_since_onboarding,

    CASE
        WHEN LOWER(CAST(o.upgrade AS VARCHAR)) = 'true' THEN 'Upgraded'
        WHEN o.trialEndDate IS NOT NULL AND o.trialEndDate != 'NaT' AND CAST(o.trialEndDate AS TIMESTAMP) >= CURRENT_TIMESTAMP THEN 'Trial'
        ELSE 'Standard'
    END AS account_status

FROM regport_organizations o
WHERE o.organizationId = ?;
"""

REGPORT_ORG_DEEP_DIVE_USER_STATS = """
SELECT
    COUNT(*) AS total_users,

    SUM(
        CASE
            WHEN LOWER(CAST(isActive AS VARCHAR)) = 'true' THEN 1
            ELSE 0
        END
    ) AS active_users,

    SUM(
        CASE
            WHEN LOWER(CAST(isActive AS VARCHAR)) = 'false' THEN 1
            ELSE 0
        END
    ) AS inactive_users,

    SUM(
        CASE
            WHEN LOWER(CAST(isSuperAdmin AS VARCHAR)) = 'true' THEN 1
            ELSE 0
        END
    ) AS super_admins,

    SUM(
        CASE
            WHEN LOWER(CAST(isSubAccount AS VARCHAR)) = 'true' THEN 1
            ELSE 0
        END
    ) AS sub_accounts,

    SUM(
        CASE
            WHEN LOWER(CAST(isDeleted AS VARCHAR)) = 'true' THEN 1
            ELSE 0
        END
    ) AS deleted_users,

    MAX(
        CASE
            WHEN lastActive IS NOT NULL
                 AND lastActive != 'NaT'
            THEN CAST(lastActive AS TIMESTAMP)
        END
    ) AS last_team_activity

FROM regport_users
WHERE organizationId = ?;
"""

REGPORT_ORG_ENGAGEMENT_SUMMARY = """
SELECT
    COUNT(DISTINCT date)                             AS active_days,
    SUM(sessions)                                    AS total_sessions,
    SUM(signed_in_users)                                AS total_active_users,
    MAX(signed_in_users)                                AS peak_active_users,
    SUM(key_events)                                  AS total_key_events,
    ROUND(AVG(active_users), 1)                      AS avg_daily_active_users,
    ROUND(SUM(total_engagement_time_msec) / 60000.0 / NULLIF(SUM(sessions),0), 2)
                                                     AS avg_session_engagement_min,
    MAX(date)                                        AS last_active_date,
    SUM(engaged_sessions)                            AS total_engaged_sessions,
    ROUND(100.0 * SUM(engaged_sessions) / NULLIF(SUM(sessions),0), 1)
                                                     AS engaged_session_pct
FROM daily_organization_metrics
WHERE organization_id = ?
  AND LOWER(platform) = LOWER(?)
  AND CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE);
"""

REGPORT_ORG_ENGAGEMENT_DAILY_TREND = """
SELECT
    date,
    SUM(active_users) AS active_users,
    SUM(sessions) AS sessions
FROM daily_organization_metrics
WHERE organization_id = ?
  AND LOWER(platform) = LOWER(?)
  AND CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY date
ORDER BY date ASC;
"""

REGPORT_ORG_SESSION_DEVICE_SPLIT = """
SELECT
    device_category,
    COUNT(DISTINCT ga_session_id) AS session_count,
    ROUND(100.0 * COUNT(DISTINCT ga_session_id) /
          SUM(COUNT(DISTINCT ga_session_id)) OVER (), 1) AS pct
FROM daily_session_metrics
WHERE organization_id = ?
  AND LOWER(platform) = LOWER(?)
  AND CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY device_category
ORDER BY session_count DESC;
"""

REGPORT_ORG_TRAFFIC_SOURCE = """
SELECT
    COALESCE(NULLIF(session_traffic_source,'(not set)'), 'Direct/Unknown') AS source,
    COALESCE(NULLIF(session_traffic_medium,'(not set)'), 'Direct/Unknown') AS medium,
    COUNT(DISTINCT ga_session_id) AS sessions
FROM daily_session_metrics
WHERE organization_id = ?
  AND LOWER(platform) = LOWER(?)
  AND CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY source, medium
ORDER BY sessions DESC
LIMIT 10;
"""

REGPORT_ORG_MODULE_USAGE_FROM_AUDIT = """
SELECT
    module,
    COUNT(*)                                    AS total_actions,
    COUNT(DISTINCT userId)                      AS distinct_users,
    COUNT(DISTINCT CAST(createdAt AS DATE))     AS active_days,
    MAX(CAST(createdAt AS TIMESTAMP))           AS last_used_at
FROM regport_audit_trails
WHERE organizationId = ?
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
  AND module IS NOT NULL
GROUP BY module
ORDER BY total_actions DESC;
"""

REGPORT_ORG_ACTION_TYPE_BREAKDOWN = """
SELECT
    actionType,
    COUNT(*) AS action_count
FROM regport_audit_trails
WHERE organizationId = ?
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY actionType
ORDER BY action_count DESC;
"""

REGPORT_ORG_MODULE_ADOPTION_WEEKLY = """
SELECT
    DATE_TRUNC('week', CAST(createdAt AS TIMESTAMP)) AS week_start,
    module,
    COUNT(*)                                          AS actions
FROM regport_audit_trails
WHERE organizationId = ?
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
  AND module IS NOT NULL
GROUP BY week_start, module
ORDER BY week_start ASC, actions DESC;
"""

REGPORT_ORG_USER_JOURNEY_FIRST_ACTIONS = """
SELECT
    u.user_id,
    u.roleName,
    MIN(CAST(a.createdAt AS TIMESTAMP))  AS first_action_ts,
    FIRST(a.module ORDER BY a.createdAt) AS first_module,
    COUNT(DISTINCT a.module)             AS modules_touched,
    COUNT(*)                             AS total_actions
FROM regport_users u
JOIN regport_audit_trails a
    ON a.userId = u.user_id
   AND a.organizationId = u.organizationId
WHERE u.organizationId = ?
  AND CAST(a.createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY u.user_id, u.roleName
ORDER BY first_action_ts ASC;
"""


ORG_USER_JOURNEY_PATHS = """
WITH vars AS (
    SELECT
        ?::DATE AS start_date,
        ?::DATE AS end_date,
        ?       AS organization_id,
        ?       AS platform
),

total_users AS (
    -- denominator for user_pct: total active user-days in the period for this organization
    SELECT COUNT(*) AS total
    FROM   daily_user_metrics dum
    CROSS JOIN vars v
    WHERE  dum.date::DATE BETWEEN v.start_date AND v.end_date
      AND  LOWER(dum.platform) = LOWER(v.platform)
      AND  dum.organization_id = v.organization_id
),

paths AS (
    SELECT
        dcpm.conversion_path,
        SUM(dcpm.path_occurrence_count)   AS path_occurrence_count,
        AVG(dcpm.path_percentage)         AS path_percentage,
        MAX(dcpm.num_pages)               AS num_pages,
        MAX(dcpm.unique_pages)            AS unique_pages,
        SUM(dcpm.unique_users_count)      AS unique_users_count
    FROM   daily_conversion_path_metrics dcpm
    CROSS JOIN vars v
    WHERE  dcpm.date::DATE BETWEEN v.start_date AND v.end_date
      AND  LOWER(dcpm.platform) = LOWER(v.platform)
      AND  dcpm.organization_id = v.organization_id
      AND  dcpm.organization_id IS NOT NULL
   GROUP BY dcpm.conversion_path
)

SELECT
    p.conversion_path,
    ROUND(p.path_percentage, 2)                                   AS path_percentage,
    p.path_occurrence_count,
    p.num_pages,
    p.unique_pages,
    p.unique_users_count,
    ROUND(100.0 * p.unique_users_count / NULLIF(tu.total, 0), 2) AS user_pct
FROM   paths p
CROSS JOIN total_users tu
ORDER BY
    user_pct             DESC,
    unique_pages         DESC,
    path_occurrence_count DESC
LIMIT 20;
"""


REGPORT_ORG_MODULE_BREADTH = """
SELECT
    COUNT(DISTINCT module) AS modules_used,
    COUNT(DISTINCT userId) AS users_active
FROM regport_audit_trails
WHERE organizationId = ?
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""

REGPORT_ORG_ACTIVITY_HEATMAP = """
SELECT
    DAYOFWEEK(CAST(createdAt AS TIMESTAMP))   AS day_of_week,   -- 0=Sun .. 6=Sat
    HOUR(CAST(createdAt AS TIMESTAMP))        AS hour_of_day,
    COUNT(*)                                  AS action_count
FROM regport_audit_trails
WHERE organizationId = ?
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY day_of_week, hour_of_day
ORDER BY day_of_week, hour_of_day;
"""

REGPORT_ORG_AUDIT_TIMELINE = """
SELECT
    CAST(createdAt AS DATE)  AS action_date,
    COUNT(*)                 AS actions,
    COUNT(DISTINCT userId)   AS distinct_users,
    COUNT(DISTINCT module)   AS modules_touched
FROM regport_audit_trails
WHERE organizationId = ?
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY action_date
ORDER BY action_date ASC;
"""


REGPORT_ORG_TRANSACTION_SUMMARY = """
SELECT
    COUNT(*)                                                    AS total_transactions,
    COUNT(DISTINCT CAST(transaction_date AS DATE))              AS active_days,
    SUM(CAST(transactionAmount AS DOUBLE))                      AS total_amount,
    AVG(CAST(transactionAmount AS DOUBLE))                      AS avg_amount,
    SUM(CASE WHEN transactionFlagged = 'True'  THEN 1 ELSE 0 END) AS flagged_count,
    SUM(CASE WHEN transactionMonitored = 'True' THEN 1 ELSE 0 END) AS monitored_count,
    ROUND(100.0 * SUM(CASE WHEN transactionFlagged = 'True' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 2)                             AS flag_rate_pct,
    MAX(CAST(transaction_date AS TIMESTAMP))                    AS latest_transaction
FROM regport_transactions
WHERE organizationId = ?
  AND CAST(transactionCreatedAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""

REGPORT_ORG_MONITORED_ACCOUNTS_SUMMARY = """
SELECT
    COUNT(*)                                                          AS total_monitored,
    SUM(CASE WHEN monitoredAccountStatus = 'NEW'   THEN 1 ELSE 0 END) AS new_count,
    SUM(CASE WHEN monitoredAccountStatus = 'CLOSED'   THEN 1 ELSE 0 END) AS closed_count,
    SUM(CASE WHEN monitoredAccountStatus = 'UNDER REVIEW' THEN 1 ELSE 0 END) AS review_count,
    SUM(CAST(flaggedTransactionCount AS INTEGER))                     AS total_flagged_txns,
    COUNT(DISTINCT customerType)                                      AS customer_types
FROM regport_monitored_accounts
WHERE organizationId = ?
  AND (isDeleted = FALSE OR isDeleted IS NULL)
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""

REGPORT_ORG_VERIFICATION_DAILY_TREND = """
SELECT
    CAST(createdAt AS DATE) AS check_date,
    verificationType,
    COUNT(*)                AS checks
FROM regport_verify_customers
WHERE organizationId = ?
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY check_date, verificationType
ORDER BY check_date ASC;
"""

REGPORT_ORG_SCREENING_SUMMARY = """
SELECT
    COUNT(*)                                                               AS total_screenings,
    SUM(CAST(sanction_match_count AS INTEGER))                            AS total_sanction_matches,
    SUM(CAST(pep_match_count AS INTEGER))                                 AS total_pep_matches,
    SUM(CASE WHEN CAST(sanction_match_count AS INTEGER) > 0
              OR  CAST(pep_match_count AS INTEGER)      > 0
             THEN 1 ELSE 0 END)                                           AS flagged_screenings,
    ROUND(100.0 * SUM(CASE WHEN CAST(sanction_match_count AS INTEGER) > 0
                            OR  CAST(pep_match_count AS INTEGER)      > 0
                           THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0), 1)   AS flag_rate_pct
FROM regport_screening_results
WHERE organizationId = ?
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""

REGPORT_ORG_BATCH_UPLOAD_SUMMARY = """
SELECT
    COUNT(*)                                     AS total_uploads,
    SUM(CAST(record_count AS INTEGER))           AS total_records,
    SUM(CAST(processed_successfully AS INTEGER)) AS records_ok,
    SUM(CAST(errors_count AS INTEGER))           AS total_errors,
    ROUND(100.0 * SUM(CAST(errors_count AS INTEGER))
          / NULLIF(SUM(CAST(record_count AS INTEGER)),0), 2) AS error_rate_pct,
    COUNT(DISTINCT file_type)                    AS file_types,
    COUNT(DISTINCT template_type)                AS template_types
FROM regport_uploaded_files
WHERE organizationId = ?
  AND (isDeleted = FALSE OR isDeleted IS NULL)
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""

REGPORT_ORG_BATCH_UPLOAD_BY_TEMPLATE = """
SELECT
    template_type,
    file_type,
    COUNT(*)                                     AS uploads,
    SUM(CAST(record_count AS INTEGER))           AS total_records,
    SUM(CAST(errors_count AS INTEGER))           AS total_errors
FROM regport_uploaded_files
WHERE organizationId = ?
  AND (isDeleted = FALSE OR isDeleted IS NULL)
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY template_type, file_type
ORDER BY uploads DESC;
"""


REGPORT_ORG_TRANSACTION_DAILY_TREND = """
SELECT
    CAST(transaction_date AS DATE)                              AS txn_date,
    COUNT(*)                                                    AS txn_count,
    SUM(CAST(transactionAmount AS DOUBLE))                      AS total_amount,
    SUM(CASE WHEN transactionFlagged = 'True' THEN 1 ELSE 0 END) AS flagged_count
FROM regport_transactions
WHERE organizationId = ?
  AND CAST(transactionCreatedAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY txn_date
ORDER BY txn_date ASC;
"""

REGPORT_ORG_TRANSACTION_TYPE_SPLIT = """
SELECT
    transactionType,
    COUNT(*)                            AS count,
    SUM(CAST(transactionAmount AS DOUBLE)) AS total_amount
FROM regport_transactions
WHERE organizationId = ?
  AND CAST(transactionCreatedAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY transactionType
ORDER BY count DESC;
"""

REGPORT_ORG_RULES_BY_CODE = """
SELECT
    ruleCode,
    ruleSecurityLevel,
    COUNT(*) AS rule_count
FROM regport_rules
WHERE organizationId = ?
  AND ruleIsDeleted = 'False'
GROUP BY ruleCode, ruleSecurityLevel
ORDER BY rule_count DESC;
"""

REGPORT_ORG_USERS = """
SELECT user_id, email, RoleName, isSubAccount, isSuperAdmin, isActive, lastActive
FROM regport_users
WHERE organizationId = ?
  AND (isDeleted = FALSE OR isDeleted IS NULL);
"""

REGPORT_ORG_USER_ACTIVITY_BY_ROLE = """
SELECT ru.roleName, COUNT(*) AS user_action_count
FROM regport_audit_trails rat
LEFT JOIN regport_users ru
  ON rat.userId = ru.user_id
WHERE ru.organizationId = ?
  AND CAST(rat.createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
  AND (ru.isDeleted = FALSE OR ru.isDeleted IS NULL)
GROUP BY ru.roleName
ORDER BY user_action_count DESC;
"""
 

REGWATCH_DEEP_ASSESSMENT_SUMMARY = """
SELECT
    COUNT(*)                                                              AS total_assessments,
    SUM(CASE WHEN status = 'Completed'   THEN 1 ELSE 0 END)             AS completed,
    SUM(CASE WHEN status = 'Not Started' THEN 1 ELSE 0 END)             AS not_started,
    SUM(CASE WHEN status = 'Expired'     THEN 1 ELSE 0 END)             AS expired,
    ROUND(100.0 * SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 1)                                      AS completion_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN status = 'Expired' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 1)                                      AS expiry_rate_pct,
    COUNT(DISTINCT regulation_id)                                        AS distinct_regulations,
    COUNT(DISTINCT started_by)                                           AS distinct_assessors,
    MIN(CAST(started_at AS TIMESTAMP))                                   AS first_assessment_at,
    MAX(CAST(started_at AS TIMESTAMP))                                   AS last_assessment_at
FROM regwatch_pre_assessment
WHERE company_id = ?
  AND CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""

REGWATCH_DEEP_ASSESSMENT_MONTHLY = """
SELECT
    DATE_TRUNC('month', CAST(started_at AS TIMESTAMP))    AS month,
    COUNT(*)                                               AS total_started,
    SUM(CASE WHEN status = 'Completed'   THEN 1 ELSE 0 END) AS completed,
    SUM(CASE WHEN status = 'Expired'     THEN 1 ELSE 0 END) AS expired,
    SUM(CASE WHEN status = 'Not Started' THEN 1 ELSE 0 END) AS not_started,
    ROUND(AVG(CAST(compliance_percentage AS DOUBLE)), 1)   AS avg_compliance_pct,
    COUNT(DISTINCT started_by)                             AS active_assessors
FROM regwatch_pre_assessment
WHERE company_id = ?
  AND CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY month
ORDER BY month ASC;
"""

REGWATCH_DEEP_TIME_TO_COMPLETE = """
SELECT
    ROUND(AVG(DATEDIFF('minute',
        CAST(started_at AS TIMESTAMP),
        CAST(completed_at AS TIMESTAMP))), 1)         AS avg_minutes,
    ROUND(MEDIAN(DATEDIFF('minute',
        CAST(started_at AS TIMESTAMP),
        CAST(completed_at AS TIMESTAMP))), 1)         AS median_minutes,
    MIN(DATEDIFF('minute',
        CAST(started_at AS TIMESTAMP),
        CAST(completed_at AS TIMESTAMP)))             AS min_minutes,
    MAX(DATEDIFF('minute',
        CAST(started_at AS TIMESTAMP),
        CAST(completed_at AS TIMESTAMP)))             AS max_minutes,
    COUNT(*)                                          AS completed_count,
    SUM(CASE WHEN DATEDIFF('minute',
                   CAST(started_at AS TIMESTAMP),
                   CAST(completed_at AS TIMESTAMP)) <= 5 THEN 1 ELSE 0 END) AS under_5_min,
    SUM(CASE WHEN DATEDIFF('minute',
                   CAST(started_at AS TIMESTAMP),
                   CAST(completed_at AS TIMESTAMP)) BETWEEN 5 AND 30 THEN 1 ELSE 0 END) AS btw_5_30_min,
    SUM(CASE WHEN DATEDIFF('minute',
                   CAST(started_at AS TIMESTAMP),
                   CAST(completed_at AS TIMESTAMP)) > 30 THEN 1 ELSE 0 END) AS over_30_min
FROM regwatch_pre_assessment
WHERE company_id = ?
  AND status = 'Completed'
  AND completed_at IS NOT NULL
  AND CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""

REGWATCH_DEEP_DEADLINE_ADHERENCE = """
SELECT
    SUM(CASE WHEN status = 'Completed'
              AND CAST(completed_at AS TIMESTAMP) <= CAST(deadline AS TIMESTAMP)
             THEN 1 ELSE 0 END)                AS on_time,
    SUM(CASE WHEN status = 'Completed'
              AND CAST(completed_at AS TIMESTAMP) > CAST(deadline AS TIMESTAMP)
             THEN 1 ELSE 0 END)                AS late,
    SUM(CASE WHEN status = 'Expired'  THEN 1 ELSE 0 END) AS expired_missed,
    SUM(CASE WHEN status = 'Not Started'
              AND CAST(deadline AS TIMESTAMP) < CURRENT_TIMESTAMP
             THEN 1 ELSE 0 END)                AS overdue_not_started,
    COUNT(*)                                   AS total
FROM regwatch_pre_assessment
WHERE company_id = ?
  AND CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""

REGWATCH_DEEP_COMPLIANCE_SCORE_DIST = """
SELECT
    CASE
        WHEN CAST(compliance_percentage AS DOUBLE) = 100    THEN '100%'
        WHEN CAST(compliance_percentage AS DOUBLE) >= 80    THEN '80–99%'
        WHEN CAST(compliance_percentage AS DOUBLE) >= 60    THEN '60–79%'
        WHEN CAST(compliance_percentage AS DOUBLE) >= 40    THEN '40–59%'
        ELSE 'Below 40%'
    END                 AS score_band,
    COUNT(*)            AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM regwatch_pre_assessment
WHERE company_id = ?
  AND status = 'Completed'
  AND CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY score_band
ORDER BY MIN(CAST(compliance_percentage AS DOUBLE)) DESC;
"""

REGWATCH_DEEP_COMPLIANCE_TREND = """
SELECT
    DATE_TRUNC('month', CAST(completed_at AS TIMESTAMP))        AS month,
    ROUND(AVG(CAST(compliance_percentage AS DOUBLE)), 1)        AS avg_compliance_pct,
    ROUND(AVG(CAST(non_compliant_count AS DOUBLE)), 2)          AS avg_non_compliant,
    ROUND(AVG(CAST(unanswered_count AS DOUBLE)), 2)             AS avg_unanswered,
    COUNT(*)                                                     AS completed_count
FROM regwatch_pre_assessment
WHERE company_id = ?
  AND status = 'Completed'
  AND completed_at IS NOT NULL
  AND CAST(completed_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY month
ORDER BY month ASC;
"""

REGWATCH_DEEP_COMPLIANCE_SUMMARY = """
SELECT
    ROUND(AVG(CAST(compliant_count AS DOUBLE)), 1)                   AS avg_compliant_items,
    ROUND(AVG(CAST(non_compliant_count AS DOUBLE)), 1)               AS avg_non_compliant_items,
    ROUND(AVG(CAST(unanswered_count AS DOUBLE)), 1)                  AS avg_unanswered_items,
    COUNT(*)                                                         AS completed_count
FROM regwatch_pre_assessment
WHERE company_id = ?
  AND status = 'Completed'
  AND CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP);
"""


REGWATCH_DEEP_LOW_COMPLIANCE_REGS = """
SELECT
    pa.regulation_title,
    r.regulatory_area,
    r.regulator_name,
    r.risk_level,
    COUNT(*)                                                     AS attempts,
    ROUND(AVG(CAST(pa.compliance_percentage AS DOUBLE)), 1)     AS avg_compliance_pct,
    ROUND(AVG(CAST(pa.non_compliant_count AS DOUBLE)), 1)       AS avg_non_compliant,
    ROUND(AVG(CAST(pa.unanswered_count AS DOUBLE)), 1)          AS avg_unanswered,
    MAX(CAST(pa.started_at AS TIMESTAMP))                       AS last_attempted
FROM regwatch_pre_assessment pa
JOIN regwatch_regulations r ON r.regulation_id = pa.regulation_id
WHERE pa.company_id = ?
  AND pa.status = 'Completed'
  AND CAST(pa.compliance_percentage AS DOUBLE) < 80
  AND CAST(pa.started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY pa.regulation_title, r.regulatory_area, r.regulator_name, r.risk_level
ORDER BY avg_compliance_pct ASC
LIMIT 10;
"""


REGWATCH_DEEP_COMPLIANCE_IMPROVEMENT = """
WITH ranked AS (
    SELECT
        regulation_id,
        regulation_title,
        CAST(compliance_percentage AS DOUBLE) AS compliance_pct,
        CAST(started_at AS TIMESTAMP)         AS started_at,
        ROW_NUMBER() OVER (PARTITION BY regulation_id ORDER BY CAST(started_at AS TIMESTAMP) ASC)  AS rn_first,
        ROW_NUMBER() OVER (PARTITION BY regulation_id ORDER BY CAST(started_at AS TIMESTAMP) DESC) AS rn_last
    FROM regwatch_pre_assessment
    WHERE company_id = ?
      AND status = 'Completed'
      AND CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
)
SELECT
    f.regulation_id,
    f.regulation_title,
    f.compliance_pct                              AS first_score,
    l.compliance_pct                              AS latest_score,
    ROUND(l.compliance_pct - f.compliance_pct, 1) AS improvement_delta
FROM ranked f
JOIN ranked l ON l.regulation_id = f.regulation_id AND l.rn_last = 1
WHERE f.rn_first = 1
  AND f.compliance_pct != l.compliance_pct
ORDER BY improvement_delta DESC;
"""


REGWATCH_DEEP_REGULATORY_AREA = """
SELECT
    r.regulatory_area,
    COUNT(pa.pre_assessment_id)                                     AS assessments_run,
    COUNT(DISTINCT pa.regulation_id)                                AS distinct_regulations,
    SUM(CASE WHEN pa.status = 'Completed' THEN 1 ELSE 0 END)       AS completed,
    SUM(CASE WHEN pa.status = 'Expired'   THEN 1 ELSE 0 END)       AS expired,
    ROUND(AVG(CAST(pa.compliance_percentage AS DOUBLE)), 1)         AS avg_compliance_pct,
    MAX(CAST(pa.started_at AS TIMESTAMP))                           AS last_assessed
FROM regwatch_pre_assessment pa
JOIN regwatch_regulations r ON r.regulation_id = pa.regulation_id
WHERE pa.company_id = ?
  AND CAST(pa.started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY r.regulatory_area
ORDER BY assessments_run DESC;
"""


REGWATCH_DEEP_RISK_LEVEL_PROFILE = """
SELECT
    r.risk_level,
    COUNT(pa.pre_assessment_id) AS assessments
FROM regwatch_pre_assessment pa
JOIN regwatch_regulations r ON r.regulation_id = pa.regulation_id
WHERE pa.company_id = ?
  AND CAST(pa.started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY r.risk_level;
"""


REGWATCH_DEEP_REGULATOR_BREAKDOWN = """
SELECT
    r.regulator_name,
    r.regulator_code,
    COUNT(pa.pre_assessment_id) AS assessments,
    ROUND(AVG(CAST(pa.compliance_percentage AS DOUBLE)), 1) AS avg_compliance_pct
FROM regwatch_pre_assessment pa
JOIN regwatch_regulations r ON r.regulation_id = pa.regulation_id
WHERE pa.company_id = ?
  AND CAST(pa.started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY r.regulator_name, r.regulator_code
ORDER BY assessments DESC;
"""


REGWATCH_DEEP_TOP_REGULATIONS = """
SELECT
    regulation_title,
    COUNT(*) AS times_assessed
FROM regwatch_pre_assessment
WHERE company_id = ?
  AND CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY regulation_title
ORDER BY times_assessed DESC
LIMIT 10;
"""


REGWATCH_DEEP_ASSESSOR_LEADERBOARD = """
SELECT
    started_by                                                      AS user_id,
    started_by_email                                                AS email,
    CONCAT(started_by_firstName, ' ', started_by_lastName)         AS full_name,
    COUNT(*)                                                        AS total_assessments,
    SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END)          AS completed,
    SUM(CASE WHEN status = 'Expired'   THEN 1 ELSE 0 END)          AS expired,
    ROUND(AVG(CAST(compliance_percentage AS DOUBLE)), 1)            AS avg_compliance_pct,
    COUNT(DISTINCT regulation_id)                                   AS distinct_regulations,
    MAX(CAST(started_at AS TIMESTAMP))                              AS last_activity
FROM regwatch_pre_assessment
WHERE company_id = ?
  AND CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY started_by, started_by_email, full_name
ORDER BY total_assessments DESC;
"""


REGWATCH_DEEP_ASSESSOR_MONTHLY_ACTIVITY = """
SELECT
    DATE_TRUNC('month', CAST(started_at AS TIMESTAMP))   AS month,
    started_by_email                                      AS assessor_email,
    COUNT(*)                                              AS assessments
FROM regwatch_pre_assessment
WHERE company_id = ?
  AND CAST(started_at AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY month, assessor_email
ORDER BY month ASC, assessments DESC;
"""


REGPORT_CASE_STATUS_DISTRIBUTION = """
SELECT
    monitoredAccountStatus,
    COUNT(*) AS case_count,
    COUNT(DISTINCT organizationId) AS org_count
FROM regport_monitored_accounts
WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY monitoredAccountStatus
ORDER BY case_count DESC;
"""

REGPORT_CASE_RESOLUTION_TIME = """
SELECT
    organizationId,
    organizationName,
    COUNT(*) AS closed_cases,
    ROUND(
        AVG(
            DATEDIFF('day',
                CAST(createdAt AS TIMESTAMP),
                CAST(updatedAt AS TIMESTAMP)
            )
        ),
        1
    ) AS avg_days_to_close,
    MIN(DATEDIFF('day', CAST(createdAt AS TIMESTAMP), CAST(updatedAt AS TIMESTAMP))) AS min_days,
    MAX(DATEDIFF('day', CAST(createdAt AS TIMESTAMP), CAST(updatedAt AS TIMESTAMP))) AS max_days
FROM regport_monitored_accounts
WHERE monitoredAccountStatus = 'CLOSED'
  AND CAST(updatedAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY organizationId, organizationName
ORDER BY avg_days_to_close DESC;
"""

REGPORT_CASE_ACTION_DEPTH = """
SELECT
    a.organizationId,
    a.organizationName,
    COUNT(DISTINCT a.actionType) AS distinct_action_types,
    COUNT(*) AS total_case_events,
    ROUND(COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT m.monitoredAccountId), 0), 1) AS avg_actions_per_case
FROM regport_audit_trails a
LEFT JOIN regport_monitored_accounts m ON a.organizationId = m.organizationId
WHERE a.actionType IN (
    'Case Assignment',
    'Case Status Update',
    'Case Investigation Note',
    'Investigation'
)
AND CAST(a.createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY a.organizationId, a.organizationName
ORDER BY avg_actions_per_case DESC;
"""

REGPORT_FLAG_TO_CASE_RATIO = """
WITH flag_counts AS (
    SELECT
        organizationId,
        SUM(CAST(flaggedTransactionCount AS INTEGER)) AS total_flags_in_cases
    FROM regport_monitored_accounts
    WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
),
case_counts AS (
    SELECT
        organizationId,
        organizationName,
        COUNT(*) AS total_cases
    FROM regport_monitored_accounts
    WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId, organizationName
)
SELECT
    c.organizationId,
    c.organizationName,
    c.total_cases,
    COALESCE(f.total_flags_in_cases, 0) AS total_flagged_txns,
    CASE
        WHEN c.total_cases = 0 THEN NULL
        ELSE ROUND(COALESCE(f.total_flags_in_cases, 0) * 1.0 / c.total_cases, 1)
    END AS flags_per_case
FROM case_counts c
LEFT JOIN flag_counts f ON c.organizationId = f.organizationId
ORDER BY flags_per_case DESC NULLS LAST;
"""

REGPORT_CASE_AGE_BUCKETS = """
SELECT
    organizationName,
    COUNT(CASE WHEN DATEDIFF('day', CAST(createdAt AS TIMESTAMP), CURRENT_DATE) < 7 THEN 1 END) AS under_7d,
    COUNT(CASE WHEN DATEDIFF('day', CAST(createdAt AS TIMESTAMP), CURRENT_DATE) BETWEEN 7 AND 30 THEN 1 END) AS d7_to_30,
    COUNT(CASE WHEN DATEDIFF('day', CAST(createdAt AS TIMESTAMP), CURRENT_DATE) BETWEEN 31 AND 90 THEN 1 END) AS d31_to_90,
    COUNT(CASE WHEN DATEDIFF('day', CAST(createdAt AS TIMESTAMP), CURRENT_DATE) > 90 THEN 1 END) AS over_90d
FROM regport_monitored_accounts
WHERE monitoredAccountStatus IN ('NEW', 'UNDER REVIEW')
GROUP BY organizationName
ORDER BY over_90d DESC;
"""

REGPORT_VERIFY_PASS_FAIL_BY_SERVICE = """
WITH verify_events AS (
    SELECT
        a.organizationId,
        a.organizationName,
        v.verificationService,
        SUM(CASE WHEN a.action = 'Verification Successful' THEN 1 ELSE 0 END) AS pass_count,
        SUM(CASE WHEN a.action = 'Verification Failed' THEN 1 ELSE 0 END) AS fail_count,
        COUNT(*) AS total_verifications
    FROM regport_verify_customers v
    LEFT JOIN regport_audit_trails a
        ON v.organizationId = a.organizationId
        AND a.actionType = 'Customer Verification'
        AND CAST(a.createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    WHERE CAST(v.createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY a.organizationId, a.organizationName, v.verificationService
)
SELECT
    verificationService,
    SUM(pass_count) AS total_pass,
    SUM(fail_count) AS total_fail,
    SUM(total_verifications) AS total,
    ROUND(SUM(pass_count) * 100.0 / NULLIF(SUM(total_verifications), 0), 1) AS pass_rate_pct
FROM verify_events
WHERE verificationService IS NOT NULL
GROUP BY verificationService
ORDER BY total DESC;
"""

REGPORT_SCREENING_HIT_RATE = """
SELECT
    organizationId,
    organizationName,
    COUNT(*) AS total_screenings,
    SUM(CASE WHEN TRY_CAST(sanction_match_count AS INTEGER) > 0 THEN 1 ELSE 0 END) AS sanction_hits,
    SUM(CASE WHEN TRY_CAST(pep_match_count AS INTEGER) > 0 THEN 1 ELSE 0 END) AS pep_hits,
    SUM(CASE WHEN TRY_CAST(sanction_match_count AS INTEGER) = 0 AND TRY_CAST(pep_match_count AS INTEGER) = 0 THEN 1 ELSE 0 END) AS clean_screenings,
    ROUND(
        SUM(CASE WHEN TRY_CAST(sanction_match_count AS INTEGER) > 0 OR TRY_CAST(pep_match_count AS INTEGER) > 0 THEN 1 ELSE 0 END)
        * 100.0 / NULLIF(COUNT(*), 0),
        2
    ) AS hit_rate_pct
FROM regport_screening_results
WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
  AND TRY_CAST(sanction_match_count AS INTEGER) IS NOT NULL
  AND TRY_CAST(pep_match_count AS INTEGER) IS NOT NULL
GROUP BY organizationId, organizationName
ORDER BY hit_rate_pct DESC;
"""

REGPORT_SCREENING_DEPTH_SCORE = """
WITH individual_screening AS (
    SELECT DISTINCT organizationId, 1 AS has_individual
    FROM regport_audit_trails
    WHERE actionType = 'Screening'
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
),
batch_screening AS (
    SELECT DISTINCT organizationId, 1 AS has_batch
    FROM regport_audit_trails
    WHERE actionType = 'Batch Screening'
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
),
custom_list AS (
    SELECT DISTINCT organizationId, 1 AS has_custom_list
    FROM regport_audit_trails
    WHERE actionType = 'Screening List Creation'
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
),
sanction_check AS (
    SELECT DISTINCT organizationId, 1 AS has_sanction
    FROM regport_screening_results
    WHERE TRY_CAST(sanction_match_count AS INTEGER) >= 0
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
),
pep_check AS (
    SELECT DISTINCT organizationId, 1 AS has_pep
    FROM regport_screening_results
    WHERE TRY_CAST(pep_match_count AS INTEGER) >= 0
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
),
active_orgs AS (
    SELECT DISTINCT organizationId, organizationName
    FROM regport_audit_trails
    WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
)
SELECT
    a.organizationId,
    a.organizationName,
    COALESCE(i.has_individual, 0) AS has_individual,
    COALESCE(b.has_batch, 0) AS has_batch,
    COALESCE(c.has_custom_list, 0) AS has_custom_list,
    COALESCE(s.has_sanction, 0) AS has_sanction,
    COALESCE(p.has_pep, 0) AS has_pep,
    (
        COALESCE(i.has_individual, 0)
        + COALESCE(b.has_batch, 0)
        + COALESCE(c.has_custom_list, 0)
        + COALESCE(s.has_sanction, 0)
        + COALESCE(p.has_pep, 0)
    ) AS depth_score_out_of_5
FROM active_orgs a
LEFT JOIN individual_screening i ON a.organizationId = i.organizationId
LEFT JOIN batch_screening b ON a.organizationId = b.organizationId
LEFT JOIN custom_list c ON a.organizationId = c.organizationId
LEFT JOIN sanction_check s ON a.organizationId = s.organizationId
LEFT JOIN pep_check p ON a.organizationId = p.organizationId
ORDER BY depth_score_out_of_5 DESC;
"""

REGPORT_KYC_KYB_SPLIT = """
SELECT
    organizationId,
    verificationType,
    COUNT(*) AS verification_count
FROM regport_verify_customers
WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
  AND verificationType IS NOT NULL
GROUP BY organizationId, verificationType
ORDER BY organizationId, verificationType;
"""

REGPORT_ADVERSE_MEDIA_LAG = """
WITH flagged_screenings AS (
    SELECT
        organizationId,
        CAST(createdAt AS TIMESTAMP) AS flagged_at
    FROM regport_audit_trails
    WHERE action = 'Screening Completed (Flagged)'
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
),
investigations AS (
    SELECT
        organizationId,
        CAST(createdAt AS TIMESTAMP) AS investigated_at
    FROM regport_audit_trails
    WHERE action = 'Conducted adverse media investigation'
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
)
SELECT
    f.organizationId,
    ROUND(
        AVG(
            DATEDIFF('minute', f.flagged_at, i.investigated_at) / 60.0
        ),
        1
    ) AS avg_lag_hours,
    COUNT(*) AS matched_events
FROM flagged_screenings f
INNER JOIN investigations i
    ON f.organizationId = i.organizationId
    AND i.investigated_at > f.flagged_at
GROUP BY f.organizationId
ORDER BY avg_lag_hours DESC;
"""


REGPORT_REPORT_PIPELINE = """
SELECT
    organizationId,
    organizationName,
    SUM(CASE WHEN actionType = 'Report Generation' THEN 1 ELSE 0 END) AS generated,
    SUM(CASE WHEN actionType = 'Report Approval' THEN 1 ELSE 0 END) AS approved,
    SUM(CASE WHEN actionType = 'Report Rejection' THEN 1 ELSE 0 END) AS rejected,
    SUM(CASE WHEN actionType = 'Report Generation' THEN 1 ELSE 0 END)
        - SUM(CASE WHEN actionType IN ('Report Approval', 'Report Rejection') THEN 1 ELSE 0 END) AS pending,
    ROUND(
        SUM(CASE WHEN actionType = 'Report Approval' THEN 1 ELSE 0 END) * 100.0
        / NULLIF(SUM(CASE WHEN actionType IN ('Report Approval', 'Report Rejection') THEN 1 ELSE 0 END), 0),
        1
    ) AS approval_rate_pct
FROM regport_audit_trails
WHERE actionType IN ('Report Generation', 'Report Approval', 'Report Rejection')
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY organizationId, organizationName
ORDER BY generated DESC;
"""


REGPORT_UPLOAD_QUALITY_BY_ORG = """
SELECT
    organizationId,
    organizationName,
    COUNT(*) AS total_uploads,
    SUM(CAST(record_count AS INTEGER)) AS total_records,
    SUM(CAST(processed_successfully AS INTEGER)) AS total_processed,
    SUM(CAST(errors_count AS INTEGER)) AS total_errors,
    ROUND(
        SUM(CAST(processed_successfully AS INTEGER)) * 100.0
        / NULLIF(SUM(CAST(record_count AS INTEGER)), 0),
        1
    ) AS quality_score_pct
FROM regport_uploaded_files
WHERE isDeleted = 'False'
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY organizationId, organizationName
ORDER BY quality_score_pct DESC;
"""

REGPORT_TEMPLATE_TYPE_COVERAGE = """
SELECT
    organizationId,
    organizationName,
    COUNT(DISTINCT template_type) AS distinct_template_types,
    ARRAY_AGG(DISTINCT template_type) AS template_types_used
FROM regport_uploaded_files
WHERE isDeleted = 'False'
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY organizationId, organizationName
ORDER BY distinct_template_types DESC;
"""

REGPORT_UPLOAD_ERROR_TREND = """
SELECT
    DATE_TRUNC('month', CAST(createdAt AS TIMESTAMP)) AS upload_month,
    organizationId,
    organizationName,
    SUM(CAST(errors_count AS INTEGER)) AS total_errors,
    COUNT(*) AS upload_count,
    ROUND(SUM(CAST(errors_count AS INTEGER)) * 1.0 / NULLIF(COUNT(*), 0), 2) AS avg_errors_per_upload
FROM regport_uploaded_files
WHERE isDeleted = 'False'
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY upload_month, organizationId, organizationName
ORDER BY upload_month, organizationId;
"""

REGPORT_UPLOAD_TO_ACTION_LATENCY = """
WITH uploads AS (
    SELECT
        organizationId,
        CAST(createdAt AS TIMESTAMP) AS upload_time
    FROM regport_audit_trails
    WHERE action = 'File Uploaded'
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
),
next_actions AS (
    SELECT
        a.organizationId,
        u.upload_time,
        MIN(CAST(a.createdAt AS TIMESTAMP)) AS next_action_time
    FROM uploads u
    INNER JOIN regport_audit_trails a
        ON u.organizationId = a.organizationId
        AND CAST(a.createdAt AS TIMESTAMP) > u.upload_time
        AND a.actionType IN (
            'Screening', 'Batch Screening', 'Transaction Monitoring',
            'Report Generation', 'Customer Verification'
        )
    GROUP BY a.organizationId, u.upload_time
)
SELECT
    organizationId,
    ROUND(AVG(DATEDIFF('minute', upload_time, next_action_time) / 60.0), 1) AS avg_latency_hours,
    COUNT(*) AS matched_uploads
FROM next_actions
GROUP BY organizationId
ORDER BY avg_latency_hours ASC;
"""

REGPORT_FILE_TYPE_DISTRIBUTION = """
SELECT
    file_type,
    COUNT(*) AS upload_count,
    COUNT(DISTINCT organizationId) AS org_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM regport_uploaded_files
WHERE isDeleted = 'False'
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY file_type
ORDER BY upload_count DESC;
"""


REGPORT_COMPLIANCE_CHAIN_MAP = """
WITH stage_ingestion AS (
    SELECT organizationId, COUNT(*) AS cnt
    FROM (
        SELECT organizationId FROM regport_audit_trails
        WHERE actionType = 'Batch Upload'
          AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
        UNION ALL
        SELECT organizationId FROM regport_transactions
        WHERE CAST(transactionCreatedAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    )
    GROUP BY organizationId
),
stage_screening AS (
    SELECT organizationId, COUNT(*) AS cnt
    FROM regport_audit_trails
    WHERE actionType IN ('Screening', 'Batch Screening', 'Customer Verification')
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
),
stage_monitoring AS (
    SELECT organizationId, COUNT(*) AS cnt
    FROM regport_audit_trails
    WHERE actionType = 'Transaction Monitoring'
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
),
stage_cases AS (
    SELECT organizationId, COUNT(*) AS cnt
    FROM regport_audit_trails
    WHERE actionType IN ('Case Assignment', 'Case Status Update', 'Investigation')
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
),
stage_reports AS (
    SELECT organizationId, COUNT(*) AS cnt
    FROM regport_audit_trails
    WHERE actionType = 'Report Generation'
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
),
active_orgs AS (
    SELECT DISTINCT organizationId, organizationName
    FROM regport_audit_trails
    WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
)
SELECT
    a.organizationId,
    a.organizationName,
    COALESCE(i.cnt, 0) AS ingestion,
    COALESCE(s.cnt, 0) AS screening,
    COALESCE(m.cnt, 0) AS monitoring,
    COALESCE(c.cnt, 0) AS cases,
    COALESCE(r.cnt, 0) AS reports,
    (
        (CASE WHEN i.cnt IS NOT NULL AND i.cnt > 0 THEN 1 ELSE 0 END) +
        (CASE WHEN s.cnt IS NOT NULL AND s.cnt > 0 THEN 1 ELSE 0 END) +
        (CASE WHEN m.cnt IS NOT NULL AND m.cnt > 0 THEN 1 ELSE 0 END) +
        (CASE WHEN c.cnt IS NOT NULL AND c.cnt > 0 THEN 1 ELSE 0 END) +
        (CASE WHEN r.cnt IS NOT NULL AND r.cnt > 0 THEN 1 ELSE 0 END)
    ) AS stages_completed
FROM active_orgs a
LEFT JOIN stage_ingestion i ON a.organizationId = i.organizationId
LEFT JOIN stage_screening s ON a.organizationId = s.organizationId
LEFT JOIN stage_monitoring m ON a.organizationId = m.organizationId
LEFT JOIN stage_cases c ON a.organizationId = c.organizationId
LEFT JOIN stage_reports r ON a.organizationId = r.organizationId
ORDER BY stages_completed DESC;
"""

REGPORT_MODULE_BREADTH_DISTRIBUTION = """
WITH per_org AS (
    SELECT
        organizationId,
        COUNT(DISTINCT module) AS modules_used
    FROM regport_audit_trails
    WHERE module IS NOT NULL
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
)
SELECT
    modules_used,
    COUNT(*) AS org_count
FROM per_org
GROUP BY modules_used
ORDER BY modules_used;
"""

REGPORT_SUPPORT_SIGNAL_BY_MODULE = """
WITH module_then_support AS (
    SELECT
        a1.organizationId,
        a1.module AS module_before_support,
        COUNT(*) AS support_events
    FROM regport_audit_trails a1
    INNER JOIN regport_audit_trails a2
        ON a1.organizationId = a2.organizationId
        AND a2.actionType IN ('Live Chat Initiated', 'Email Support Accessed', 'Consultation Booking')
        AND CAST(a2.createdAt AS TIMESTAMP) > CAST(a1.createdAt AS TIMESTAMP)
        AND DATEDIFF('minute',
            CAST(a1.createdAt AS TIMESTAMP),
            CAST(a2.createdAt AS TIMESTAMP)
        ) <= 30
    WHERE a1.module IS NOT NULL
      AND CAST(a1.createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY a1.organizationId, a1.module
)
SELECT
    module_before_support,
    SUM(support_events) AS total_support_events,
    COUNT(DISTINCT organizationId) AS orgs_affected
FROM module_then_support
GROUP BY module_before_support
ORDER BY total_support_events DESC;
"""

REGPORT_MODULE_ACTIVITY_VOLUME = """
SELECT
    module,
    COUNT(*) AS total_events,
    COUNT(DISTINCT organizationId) AS active_orgs,
    COUNT(DISTINCT userId) AS active_users,
    ROUND(COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT organizationId), 0), 1) AS events_per_org
FROM regport_audit_trails
WHERE module IS NOT NULL
  AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
GROUP BY module
ORDER BY total_events DESC;
"""

REGPORT_ORG_HEALTH_MATRIX = """
WITH active_orgs AS (
    SELECT
        organizationId,
        organizationName,
        MAX(CAST(createdAt AS TIMESTAMP)) AS last_active,
        DATEDIFF('day', MAX(CAST(createdAt AS TIMESTAMP)), CURRENT_DATE) AS days_since_active,
        COUNT(DISTINCT module) AS modules_used,
        COUNT(*) AS total_events
    FROM regport_audit_trails
    WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId, organizationName
),
flag_resolution AS (
    SELECT
        t.organizationId,
        COUNT(CASE WHEN t.transactionFlagged = 'True' THEN 1 END) AS total_flagged,
        COUNT(CASE WHEN a.actionType IN (
            'Transaction Confirmation', 'Transaction Dismissal', 'Transaction Escalation'
        ) THEN 1 END) AS resolved_flags
    FROM regport_transactions t
    LEFT JOIN regport_audit_trails a
        ON t.organizationId = a.organizationId
        AND a.actionType IN ('Transaction Confirmation', 'Transaction Dismissal', 'Transaction Escalation')
        AND CAST(a.createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    WHERE t.transactionIsDeleted = 'False'
      AND CAST(t.transactionCreatedAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY t.organizationId
),
report_approval AS (
    SELECT
        organizationId,
        SUM(CASE WHEN actionType = 'Report Approval' THEN 1 ELSE 0 END) AS approved,
        SUM(CASE WHEN actionType = 'Report Rejection' THEN 1 ELSE 0 END) AS rejected
    FROM regport_audit_trails
    WHERE actionType IN ('Report Approval', 'Report Rejection')
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
),
upload_quality AS (
    SELECT
        organizationId,
        ROUND(
            SUM(CAST(processed_successfully AS INTEGER)) * 100.0
            / NULLIF(SUM(CAST(record_count AS INTEGER)), 0),
            1
        ) AS quality_pct
    FROM regport_uploaded_files
    WHERE isDeleted = 'False'
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
),
support_touches AS (
    SELECT
        organizationId,
        COUNT(*) AS support_count
    FROM regport_audit_trails
    WHERE actionType IN ('Live Chat Initiated', 'Email Support Accessed', 'Consultation Booking')
      AND CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
),
prior_period_events AS (
    SELECT
        organizationId,
        COUNT(*) AS prior_events
    FROM regport_audit_trails
    WHERE CAST(createdAt AS TIMESTAMP) BETWEEN
        CAST(? AS TIMESTAMP) - INTERVAL '30 days'
        AND CAST(? AS TIMESTAMP) - INTERVAL '1 day'
    GROUP BY organizationId
)
SELECT
    a.organizationId,
    a.organizationName,
    a.last_active,
    a.days_since_active,
    a.modules_used,
    a.total_events AS current_period_events,
    COALESCE(pp.prior_events, 0) AS prior_period_events,
    ROUND(
        (a.total_events - COALESCE(pp.prior_events, 0)) * 100.0
        / NULLIF(COALESCE(pp.prior_events, 0), 0),
        1
    ) AS mom_change_pct,
    COALESCE(f.total_flagged, 0) AS total_flagged,
    COALESCE(f.resolved_flags, 0) AS resolved_flags,
    ROUND(COALESCE(f.resolved_flags, 0) * 100.0 / NULLIF(COALESCE(f.total_flagged, 0), 0), 1) AS flag_resolution_pct,
    COALESCE(r.approved, 0) AS reports_approved,
    COALESCE(r.rejected, 0) AS reports_rejected,
    ROUND(COALESCE(r.approved, 0) * 100.0 / NULLIF(COALESCE(r.approved, 0) + COALESCE(r.rejected, 0), 0), 1) AS report_approval_pct,
    COALESCE(u.quality_pct, NULL) AS upload_quality_pct,
    COALESCE(s.support_count, 0) AS support_touches,
    CASE
        WHEN a.days_since_active > 30 THEN 'dormant'
        WHEN a.days_since_active > 14
            AND (a.total_events - COALESCE(pp.prior_events, 0)) < 0 THEN 'high'
        WHEN a.modules_used < 3
            OR COALESCE(f.resolved_flags, 0) * 100.0 / NULLIF(COALESCE(f.total_flagged, 0), 0) < 40 THEN 'medium'
        ELSE 'low'
    END AS risk_tier
FROM active_orgs a
LEFT JOIN flag_resolution f ON a.organizationId = f.organizationId
LEFT JOIN report_approval r ON a.organizationId = r.organizationId
LEFT JOIN upload_quality u ON a.organizationId = u.organizationId
LEFT JOIN support_touches s ON a.organizationId = s.organizationId
LEFT JOIN prior_period_events pp ON a.organizationId = pp.organizationId
ORDER BY
    CASE
        WHEN a.days_since_active > 30 THEN 4
        WHEN a.days_since_active > 14 THEN 3
        WHEN a.modules_used < 3 THEN 2
        ELSE 1
    END DESC,
    a.days_since_active DESC;
"""

REGPORT_DORMANCY_RISK_LIST = """
WITH prior_activity AS (
    SELECT
        organizationId,
        organizationName,
        COUNT(*) AS prior_weekly_avg_events
    FROM regport_audit_trails
    WHERE CAST(createdAt AS TIMESTAMP) BETWEEN
        CAST(? AS TIMESTAMP) - INTERVAL '60 days'
        AND CAST(? AS TIMESTAMP) - INTERVAL '22 days'
    GROUP BY organizationId, organizationName
    HAVING COUNT(*) > 20
),
recent_silence AS (
    SELECT
        organizationId,
        MAX(CAST(createdAt AS TIMESTAMP)) AS last_event
    FROM regport_audit_trails
    WHERE CAST(createdAt AS TIMESTAMP) BETWEEN
        CAST(? AS TIMESTAMP) - INTERVAL '21 days'
        AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId
)
SELECT
    p.organizationId,
    p.organizationName,
    COALESCE(r.last_event, NULL) AS last_seen,
    DATEDIFF('day', COALESCE(r.last_event, CAST(? AS TIMESTAMP) - INTERVAL '21 days'), CURRENT_DATE) AS days_silent,
    p.prior_weekly_avg_events
FROM prior_activity p
LEFT JOIN recent_silence r ON p.organizationId = r.organizationId
WHERE (r.last_event IS NULL OR DATEDIFF('day', r.last_event, CURRENT_DATE) >= 21)
  AND ? IS NOT NULL;
"""

REGPORT_ORG_TIER_SEGMENTATION = """
WITH org_signals AS (
    SELECT
        organizationId,
        organizationName,
        DATEDIFF('day', MAX(CAST(createdAt AS TIMESTAMP)), CURRENT_DATE) AS days_since_active,
        COUNT(DISTINCT module) AS modules_used,
        COUNT(*) AS total_events
    FROM regport_audit_trails
    WHERE CAST(createdAt AS TIMESTAMP) BETWEEN CAST(? AS TIMESTAMP) AND CAST(? AS TIMESTAMP)
    GROUP BY organizationId, organizationName
)
SELECT
    organizationId,
    organizationName,
    days_since_active,
    modules_used,
    total_events,
    CASE
        WHEN days_since_active <= 7 AND modules_used >= 5 AND total_events >= 100 THEN 'power'
        WHEN days_since_active <= 14 AND modules_used >= 3 THEN 'steady'
        WHEN days_since_active > 30 THEN 'dormant'
        ELSE 'at-risk'
    END AS tier
FROM org_signals
ORDER BY
    CASE WHEN days_since_active <= 7 AND modules_used >= 5 AND total_events >= 100 THEN 1
         WHEN days_since_active <= 14 AND modules_used >= 3 THEN 2
         WHEN days_since_active > 30 THEN 4
         ELSE 3 END;
"""

PRODUCT_ENGAGEMENT_USER_FREQUENCY_SEGMENTS = """
SELECT
    CASE
        WHEN CAST(distinct_session_numbers AS INTEGER) = 1  THEN 'One-time'
        WHEN CAST(distinct_session_numbers AS INTEGER) <= 3  THEN 'Occasional (2–3)'
        WHEN CAST(distinct_session_numbers AS INTEGER) <= 7  THEN 'Regular (4–7)'
        WHEN CAST(distinct_session_numbers AS INTEGER) <= 14 THEN 'Frequent (8–14)'
        ELSE 'Power User (15+)'
    END                                                                  AS frequency_segment,
    COUNT(DISTINCT user_pseudo_id)                                       AS users,
    ROUND(100.0 * COUNT(DISTINCT user_pseudo_id)
          / SUM(COUNT(DISTINCT user_pseudo_id)) OVER (), 1)              AS pct,
    ROUND(AVG(CAST(avg_engagement_time_msec AS DOUBLE)) / 60000.0, 2)   AS avg_eng_min,
    ROUND(AVG(CAST(key_event_count AS DOUBLE)), 1)                       AS avg_key_events
FROM daily_user_metrics
WHERE CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
  AND LOWER(platform) = LOWER(?)
  AND user_pseudo_id IS NOT NULL
GROUP BY frequency_segment
ORDER BY MIN(CAST(distinct_session_numbers AS INTEGER));
"""

PRODUCT_ENGAGEMENT_TIME_BUCKETS = """
SELECT
    CASE
        WHEN CAST(total_engagement_time_msec AS DOUBLE) < 30000   THEN '<30s'
        WHEN CAST(total_engagement_time_msec AS DOUBLE) < 120000  THEN '30s–2m'
        WHEN CAST(total_engagement_time_msec AS DOUBLE) < 300000  THEN '2–5m'
        WHEN CAST(total_engagement_time_msec AS DOUBLE) < 900000  THEN '5–15m'
        ELSE '15m+'
    END                                                                  AS time_bucket,
    COUNT(*)                                                             AS sessions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                  AS pct
FROM daily_session_metrics
WHERE CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
  AND LOWER(platform) = LOWER(?)
GROUP BY time_bucket
ORDER BY MIN(CAST(total_engagement_time_msec AS DOUBLE));
"""

PRODUCT_ENGAGEMENT_SESSION_DEPTH_BUCKETS = """
SELECT
    CASE
        WHEN CAST(distinct_pages AS INTEGER) = 1  THEN '1 page'
        WHEN CAST(distinct_pages AS INTEGER) <= 3  THEN '2–3 pages'
        WHEN CAST(distinct_pages AS INTEGER) <= 7  THEN '4–7 pages'
        WHEN CAST(distinct_pages AS INTEGER) <= 15 THEN '8–15 pages'
        ELSE '16+ pages'
    END                                                                  AS depth_bucket,
    COUNT(*)                                                             AS sessions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                  AS pct,
    ROUND(AVG(CAST(total_engagement_time_msec AS DOUBLE)) / 60000.0, 2) AS avg_eng_min
FROM daily_session_metrics
WHERE CAST(date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
  AND LOWER(platform) = LOWER(?)
GROUP BY depth_bucket
ORDER BY MIN(CAST(distinct_pages AS INTEGER));
"""


PRODUCT_ACQUISITION_KPIS = """
WITH vars AS (
  SELECT CAST(? AS DATE) AS start_date, CAST(? AS DATE) AS end_date, ? AS platform
),
orgs AS (
  SELECT COUNT(DISTINCT o.organization_id) AS new_orgs
  FROM all_organizations o
  WHERE LOWER(o.platform) = LOWER((SELECT platform FROM vars))
    AND CAST(o.organization_start_date AS DATE) BETWEEN (SELECT start_date FROM vars) AND (SELECT end_date FROM vars)
),
users AS (
  SELECT COUNT(DISTINCT u.user_id) AS new_users
  FROM all_users u
  WHERE LOWER(u.platform) = LOWER((SELECT platform FROM vars))
    AND CAST(u.user_start_date AS DATE) BETWEEN (SELECT start_date FROM vars) AND (SELECT end_date FROM vars)
),
traffic AS (
  SELECT 
    COALESCE(SUM(t.new_visitors), 0) AS new_visitors,
    COALESCE(ROUND(SUM(t.signed_in_users) * 100.0 / NULLIF(SUM(t.sessions), 0), 1), 0.0) AS signed_in_rate_pct
  FROM daily_traffic_source_metrics t
  WHERE LOWER(t.platform) = LOWER((SELECT platform FROM vars))
    AND CAST(t.date AS DATE) BETWEEN (SELECT start_date FROM vars) AND (SELECT end_date FROM vars)
),
avg_size AS (
  SELECT 
    COALESCE(ROUND(CAST(COUNT(DISTINCT u.user_id) AS DOUBLE) / NULLIF(COUNT(DISTINCT o.organization_id), 0), 1), 0.0) AS avg_users_per_org
  FROM all_users u
  LEFT JOIN all_organizations o ON u.organization_id = o.organization_id AND LOWER(u.platform) = LOWER(o.platform)
  WHERE LOWER(u.platform) = LOWER((SELECT platform FROM vars))
)
SELECT 
  orgs.new_orgs,
  users.new_users,
  traffic.new_visitors,
  traffic.signed_in_rate_pct,
  avg_size.avg_users_per_org
FROM orgs, users, traffic, avg_size;
"""


PRODUCT_ACQUISITION_NEW_ORGS_TREND = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
    DATE_TRUNC('month', organization_start_date::DATE) AS month,
    COUNT(DISTINCT organization_id)                     AS new_orgs
FROM  all_organizations, vars v
WHERE LOWER(all_organizations.platform) = LOWER(v.platform)
  AND organization_start_date::DATE BETWEEN v.start_date AND v.end_date
GROUP BY month
ORDER BY month;
"""

ACQUISITION_NEW_USERS_TREND = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
    DATE_TRUNC('month', user_start_date::DATE) AS month,
    COUNT(DISTINCT user_id)                     AS new_users
FROM  all_users, vars v
WHERE LOWER(all_users.platform) = LOWER(v.platform)
  AND user_start_date::DATE BETWEEN v.start_date AND v.end_date
GROUP BY month
ORDER BY month;
"""

PRODUCT_ACQUISITION_TOP_SOURCES = """
WITH vars AS (
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
)
SELECT
    COALESCE(session_source, '(direct)')      AS source,
    acquisition_medium                         AS medium,
    SUM(unique_visitors ) AS total_sessions,
    SUM(signed_in_users)                      AS signed_in_sessions,
    SUM(new_signed_in_users)                  AS new_signed_in,
    ROUND(AVG(avg_engagement_time_msec)
          / 60000.0, 1)                       AS avg_engagement_min,
    SUM(key_events)  FROM  daily_traffic_source_metrics, vars v
WHERE LOWER(daily_traffic_source_metrics.platform) = LOWER(v.platform)
  AND date::DATE BETWEEN v.start_date AND v.end_date
  AND session_source NOT IN ('(not set)', '(direct)', '')
GROUP BY source, medium
ORDER BY signed_in_sessions DESC
LIMIT 10;
"""

PRODUCT_ACQ_NEW_VS_RETURNING = """
WITH vars AS (
  SELECT CAST(? AS DATE) AS start_date, CAST(? AS DATE) AS end_date, ? AS platform
)
SELECT
    DATE_TRUNC('week', CAST(date AS TIMESTAMP))                          AS week_start,
    SUM(CASE WHEN CAST(ga_session_number AS INTEGER) = 1
             THEN 1 ELSE 0 END)                                          AS new_users,
    SUM(CASE WHEN CAST(ga_session_number AS INTEGER) > 1
             THEN 1 ELSE 0 END)                                          AS returning_users,
    ROUND(100.0 * SUM(CASE WHEN CAST(ga_session_number AS INTEGER) = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 1)                                      AS new_pct
FROM daily_session_metrics, vars v
WHERE LOWER(daily_session_metrics.platform) = LOWER(v.platform)
  AND date::DATE BETWEEN v.start_date AND v.end_date
GROUP BY week_start
ORDER BY week_start ASC;
"""

PRODUCT_ACQUISITION_GEOGRAPHIC = """
WITH vars AS (
  SELECT CAST(? AS DATE) AS start_date, CAST(? AS DATE) AS end_date, ? AS platform
)
SELECT
    country,
    region,
    SUM(signed_in_users)                      AS signed_in_users,
    SUM(sessions)                             AS sessions,
    SUM(total_visitors)                       AS total_visitors,
    SUM(key_events)                           AS key_events,
    ROUND(AVG(engagement_rate), 1)            AS avg_engagement_rate_pct,
    ROUND(AVG(avg_engagement_time_msec)
          / 60000.0, 1)                       AS avg_engagement_min
FROM  daily_geographic_metrics, vars v
WHERE LOWER(daily_geographic_metrics.platform) = LOWER(v.platform)
  AND date::DATE BETWEEN v.start_date AND v.end_date
GROUP BY country, region
ORDER BY signed_in_users DESC
LIMIT 20;
"""

PRODUCT_ACQUISITION_DEVICE_BROWSER = """
WITH vars AS (
  SELECT CAST(? AS DATE) AS start_date, CAST(? AS DATE) AS end_date, ? AS platform
)
SELECT
    device_category,
    browser,
    COUNT(DISTINCT user_pseudo_id)            AS unique_users,
    COUNT(*)                                  AS total_user_days,
    SUM(session_count)                        AS total_sessions,
    ROUND(AVG(avg_engagement_time_msec)
          / 60000.0, 1)                       AS avg_engagement_min
FROM  daily_user_metrics, vars v
WHERE LOWER(daily_user_metrics.platform) = LOWER(v.platform)
  AND date::DATE BETWEEN v.start_date AND v.end_date
GROUP BY device_category, browser
ORDER BY unique_users DESC;
"""

PRODUCT_CONVERSION_LOGIN_SIGN_UP_TREND = """
SELECT
    DATE_TRUNC('week', CAST(dsm.date AS TIMESTAMP)) AS week_start,
    COALESCE(signups.signups, 0) AS signups,
    SUM(CAST(dsm.login_events AS INTEGER)) AS logins,
    COUNT(DISTINCT dsm.ga_session_id) AS sessions,
    ROUND(
        100.0 * COALESCE(signups.signups, 0)
        / NULLIF(COUNT(DISTINCT dsm.ga_session_id), 0),
        2
    ) AS signup_rate_pct,
    ROUND(
        100.0 * SUM(CAST(dsm.login_events AS INTEGER))
        / NULLIF(COUNT(DISTINCT dsm.ga_session_id), 0),
        2
    ) AS login_rate_pct
FROM daily_session_metrics dsm
LEFT JOIN (
    SELECT
        DATE_TRUNC('week', CAST(organization_start_date AS TIMESTAMP)) AS week_start,
        COUNT(DISTINCT organization_id) AS signups 
    FROM all_organizations 
    WHERE CAST(organization_start_date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
      AND LOWER(platform) = LOWER(?)
    GROUP BY 1
) signups
ON DATE_TRUNC('week', CAST(dsm.date AS TIMESTAMP)) = signups.week_start
WHERE CAST(dsm.date AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
  AND LOWER(dsm.platform) = LOWER(?)
GROUP BY 1, 2
ORDER BY week_start ASC;
"""

REGPORT_CONVERSION_CHURN_SIGNAL = """
WITH vars AS (
  SELECT CAST(? AS DATE) AS start_date, CAST(? AS DATE) AS end_date, ? AS platform
),
recent AS (
    SELECT DISTINCT organization_id
    FROM daily_organization_metrics, vars v
    WHERE LOWER(daily_organization_metrics.platform) = LOWER(v.platform)
      AND CAST(date AS DATE) >= v.end_date - INTERVAL 30 DAY
),
prior AS (
    SELECT DISTINCT organization_id
    FROM daily_organization_metrics, vars v
    WHERE LOWER(daily_organization_metrics.platform) = LOWER(v.platform)
      AND CAST(date AS DATE) BETWEEN v.end_date - INTERVAL 120 DAY
                                 AND v.end_date - INTERVAL 31 DAY
)
SELECT
    p.organization_id,
    MAX(dom.organizationName)                                             AS org_name,
    MAX(dom.date)                                                         AS last_seen,
    DATEDIFF('day', CAST(MAX(dom.date) AS DATE), CURRENT_DATE)                         AS days_dormant
FROM prior p
LEFT JOIN recent r ON r.organization_id = p.organization_id
JOIN daily_organization_metrics dom ON dom.organization_id = p.organization_id
JOIN regport_organizations org ON org.organizationId = p.organization_id
WHERE r.organization_id IS NULL
  AND dom.organization_id IS NOT NULL
GROUP BY p.organization_id
ORDER BY days_dormant DESC
LIMIT 20;
"""

REGCOMPLY_CONVERSION_CHURN_SIGNAL = """
WITH vars AS (
  SELECT CAST(? AS DATE) AS start_date, CAST(? AS DATE) AS end_date, ? AS platform
),
recent AS (
    SELECT DISTINCT organization_id
    FROM daily_organization_metrics, vars v
    WHERE LOWER(daily_organization_metrics.platform) = LOWER(v.platform)
      AND CAST(date AS DATE) >= v.end_date - INTERVAL 30 DAY
),
prior AS (
    SELECT DISTINCT organization_id
    FROM daily_organization_metrics, vars v
    WHERE LOWER(daily_organization_metrics.platform) = LOWER(v.platform)
      AND CAST(date AS DATE) BETWEEN v.end_date - INTERVAL 120 DAY
                                 AND v.end_date - INTERVAL 31 DAY
)
SELECT
    p.organization_id,
    MAX(dom.organizationName)                                             AS org_name,
    MAX(dom.date)                                                         AS last_seen,
    DATEDIFF('day', CAST(MAX(dom.date) AS DATE), CURRENT_DATE)                         AS days_dormant
FROM prior p
LEFT JOIN recent r ON r.organization_id = p.organization_id
JOIN daily_organization_metrics dom ON dom.organization_id = p.organization_id
JOIN regcomply_organizations org ON org.organization_id = p.organization_id
WHERE r.organization_id IS NULL
  AND dom.organization_id IS NOT NULL
GROUP BY p.organization_id
ORDER BY days_dormant DESC
LIMIT 20;
"""

REGWATCH_CONVERSION_CHURN_SIGNAL = """
WITH vars AS (
  SELECT CAST(? AS DATE) AS start_date, CAST(? AS DATE) AS end_date, ? AS platform
),
recent AS (
    SELECT DISTINCT organization_id
    FROM daily_organization_metrics, vars v
    WHERE LOWER(daily_organization_metrics.platform) = LOWER(v.platform)
      AND CAST(date AS DATE) >= v.end_date - INTERVAL 30 DAY
),
prior AS (
    SELECT DISTINCT organization_id
    FROM daily_organization_metrics, vars v
    WHERE LOWER(daily_organization_metrics.platform) = LOWER(v.platform)
      AND CAST(date AS DATE) BETWEEN v.end_date - INTERVAL 120 DAY
                                 AND v.end_date - INTERVAL 31 DAY
)
SELECT
    p.organization_id,
    MAX(dom.organizationName)                                             AS org_name,
    MAX(dom.date)                                                         AS last_seen,
    DATEDIFF('day', CAST(MAX(dom.date) AS DATE), CURRENT_DATE)                         AS days_dormant
FROM prior p
LEFT JOIN recent r ON r.organization_id = p.organization_id
JOIN daily_organization_metrics dom ON dom.organization_id = p.organization_id
JOIN regwatch_organizations org ON org.organization_id = p.organization_id
WHERE r.organization_id IS NULL
  AND dom.organization_id IS NOT NULL
GROUP BY p.organization_id
ORDER BY days_dormant DESC
LIMIT 20;
"""

# Dictionary to map query names to their SQL content
# This allows 'transfering them where needed' in a batch
QUERIES = {
    'product_conversion_login_signup_trend': PRODUCT_CONVERSION_LOGIN_SIGN_UP_TREND,
    'regport_conversion_churn_signal': REGPORT_CONVERSION_CHURN_SIGNAL,
    'regcomply_conversion_churn_signal': REGCOMPLY_CONVERSION_CHURN_SIGNAL,
    'regwatch_conversion_churn_signal': REGWATCH_CONVERSION_CHURN_SIGNAL,
    'product_acq_new_vs_returning': PRODUCT_ACQ_NEW_VS_RETURNING,
    'product_acquisition_geographic': PRODUCT_ACQUISITION_GEOGRAPHIC,
    'product_acquisition_device_browser': PRODUCT_ACQUISITION_DEVICE_BROWSER,
    'product_acquisition_new_orgs_trend': PRODUCT_ACQUISITION_NEW_ORGS_TREND,
    'product_acquisition_new_users_trend': ACQUISITION_NEW_USERS_TREND,
    'product_acquisition_top_sources': PRODUCT_ACQUISITION_TOP_SOURCES,
    'product_acquisition_kpis': PRODUCT_ACQUISITION_KPIS,
    'product_engagement_user_frequency_segments': PRODUCT_ENGAGEMENT_USER_FREQUENCY_SEGMENTS,
    'product_engagement_time_buckets': PRODUCT_ENGAGEMENT_TIME_BUCKETS,
    'product_engagement_session_depth_buckets': PRODUCT_ENGAGEMENT_SESSION_DEPTH_BUCKETS,
    #home page
    'organization_by_platform': ORGANIZATION_BY_PLATFORM_QUERY,
    'user_by_platform': USER_BY_PLATFORM_QUERY,
    'ecosystem_adoption_rate': ECOSYSTEM_ADOPTION_RATE_QUERY,
    'multiplatform_organization': MULTIPLATFORM_ORGANIZATION_QUERY,
    'platform_organization_user_count': PLATFORM_ORGANIZATION_USER_COUNT,
    'platform_rate_metrics': PLATFORM_RATE_METRICS,
    
    # Product specific KPIs
    'product_churn_rate': PRODUCT_KPI_CHURN_RATE,
    'product_growth_rate': PRODUCT_KPI_GROWTH_RATE,
    'product_available_years': PRODUCT_KPI_AVAILABLE_YEARS,
  
    'product_active_org_count': PRODUCT_KPI_ACTIVE_ORG_COUNT,
    'product_active_signed_in_users': PRODUCT_KPI_ACTIVE_SIGNED_IN_USERS,
    'product_anonymous_users_pct': PRODUCT_KPI_ANONYMOUS_USERS_PCT,
    'product_engagement_rate': PRODUCT_KPI_ENGAGEMENT_RATE,
    'product_user_acquisition_trend': PRODUCT_USER_ACQUISITION_TREND,
    'product_geographic_metrics': PRODUCT_GEOGRAPHIC_METRICS,
    'product_stickiness': PRODUCT_STICKINESS,
    'product_traffic_source_metrics': PRODUCT_TRAFFIC_SOURCE_METRICS,
    'product_session_traffic_metrics': PRODUCT_SESSION_TRAFFIC_METRICS,
    'product_avg_pages_per_session': PRODUCT_KPI_AVG_PAGES_PER_SESSION,
    'product_time_to_signup': PRODUCT_KPI_TIME_TO_SIGNUP,
    'product_exit_rate_landing': PRODUCT_KPI_EXIT_RATE_LANDING,
    'product_user_journey': PRODUCT_USER_CONVERSION_PATH,
    'org_user_journey_paths': ORG_USER_JOURNEY_PATHS,
    'product_landing_page_funnel': PRODUCT_LANDING_PAGE_FUNNEL,
    'product_engaged_vs_churned_metrics': PRODUCT_ENGAGED_VS_CHURNED_METRICS,
    'product_engagement_kpis': PRODUCT_ENGAGEMENT_KPIS,
    'product_page_engagement_table': PRODUCT_PAGE_ENGAGEMENT_TABLE,
    'product_org_engagement_table': PRODUCT_ORG_ENGAGEMENT_TABLE,
    'product_deep_ga4_weekly_pattern': PRODUCT_DEEP_GA4_WEEKLY_PATTERN,
    'product_deep_traffic_source': PRODUCT_DEEP_TRAFFIC_SOURCE,
    
    # Top organizations
    'top_org_per_platform': TOP_ORG_PER_PLATFORM,
 
    #RegComply
    'regcomply_audit_count': REGCOMPLY_AUDIT_COUNT,
    'regcomply_audit_completion_rate': REGCOMPLY_AUDIT_COMPLETION_RATE,
    'regcomply_active_audits': REGCOMPLY_ACTIVE_AUDITS,
    'regcomply_average_audit_duration': REGCOMPLY_AVERAGE_AUDIT_DURATION,
    'regcomply_external_audit_pct': RECOMPLY_EXTERNAL_AUDIT_PCT,
    'regcomply_audit_funnel': REGCOMPLY_AUDIT_FUNNEL,
    'regcomply_status_distribution': REGCOMPLY_STATUS_DISTRIBUTION,
    'regcomply_audit_type_split': REGCOMPLY_AUDIT_TYPE_SPLIT,
    'regcomply_audits_by_standard': REGCOMPLY_AUDITS_BY_STANDARD,
    'regcomply_audit_duration_trend': REGCOMPLY_AUDIT_DURATION_TREND,
    'regcomply_time_to_questions': REGCOMPLY_TIME_TO_QUESTIONS,
    'regcomply_time_to_respond': REGCOMPLY_TIME_TO_RESPOND,
    'regcomply_time_to_complete': REGCOMPLY_TIME_TO_COMPLETE,
    'regcomply_checklist_adoption': REGCOMPLY_CHECKLIST_ADOPTION,
    'regcomply_scoring_pattern_usage': REGCOMPLY_SCORING_PATTERN_USAGE,
    'regcomply_extension_rate': REGCOMPLY_EXTENSION_RATE,
    'regcomply_delayed_audits': REGCOMPLY_DELAYED_AUDITS,
    'regcomply_org_performance_table': REGCOMPLY_ORG_PERFORMANCE_TABLE,
    'regcomply_audits_per_org': REGCOMPLY_AUDITS_PER_ORG,
    'regcomply_lifecycle_duration_table': REGCOMPLY_LIFECYCLE_DURATION_TABLE,
 
    # Organization Deep-Dive
    'product_org_list': PRODUCT_ORG_LIST,
    'regcomply_org_deep_dive_details': REGCOMPLY_ORG_DEEP_DIVE_DETAILS,
    'regcomply_org_engagement_summary': REGPORT_ORG_ENGAGEMENT_SUMMARY,
    'regcomply_org_engagement_daily_trend': REGPORT_ORG_ENGAGEMENT_DAILY_TREND,
    'regcomply_org_engagement_session_device_split': REGPORT_ORG_SESSION_DEVICE_SPLIT,
    'regcomply_org_session_device_split': REGPORT_ORG_SESSION_DEVICE_SPLIT,
    'regcomply_org_traffic_source': REGPORT_ORG_TRAFFIC_SOURCE,
    'regcomply_org_conversion_milestones': REGCOMPLY_ORG_CONVERSION_MILESTONES,
    'regcomply_org_audit_funnel': REGCOMPLY_ORG_AUDIT_FUNNEL,
    'regcomply_org_module_deepdive': REGCOMPLY_ORG_MODULE_DEEPDIVE,
    'regcomply_org_stage_bottleneck': REGCOMPLY_ORG_STAGE_BOTTLENECK,
    'regcomply_org_user_breakdown': REGCOMPLY_ORG_USER_BREAKDOWN,
    'product_org_deep_dive_user_count': PRODUCT_ORG_DEEP_DIVE_USER_COUNT,
    'product_org_deep_dive_last_activity_date': PRODUCT_ORG_DEEP_DIVE_LAST_ACTIVITY_DATE,
    'product_org_deep_dive_details': REGPORT_ORG_DEEP_DIVE_DETAILS,
    'product_org_deep_dive_user_stats': REGPORT_ORG_DEEP_DIVE_USER_STATS,
    'regport_org_deep_dive_details': REGPORT_ORG_DEEP_DIVE_DETAILS,
    'regport_org_deep_dive_user_stats': REGPORT_ORG_DEEP_DIVE_USER_STATS,
    'regport_org_engagement_summary': REGPORT_ORG_ENGAGEMENT_SUMMARY,
    'regport_org_engagement_daily_trend': REGPORT_ORG_ENGAGEMENT_DAILY_TREND,
    'regport_org_session_device_split': REGPORT_ORG_SESSION_DEVICE_SPLIT,
    'regport_org_traffic_source': REGPORT_ORG_TRAFFIC_SOURCE,
    'regport_org_module_usage_from_audit': REGPORT_ORG_MODULE_USAGE_FROM_AUDIT,
    'regport_org_action_type_breakdown': REGPORT_ORG_ACTION_TYPE_BREAKDOWN,
    'regport_org_module_adoption_weekly': REGPORT_ORG_MODULE_ADOPTION_WEEKLY,
    'regport_org_user_journey_first_actions': REGPORT_ORG_USER_JOURNEY_FIRST_ACTIONS,
    'regport_org_module_breadth': REGPORT_ORG_MODULE_BREADTH,
    'regport_org_activity_heatmap': REGPORT_ORG_ACTIVITY_HEATMAP,
    'regport_org_audit_timeline': REGPORT_ORG_AUDIT_TIMELINE,
    'regport_org_transaction_summary': REGPORT_ORG_TRANSACTION_SUMMARY,
    'regport_org_monitored_accounts_summary': REGPORT_ORG_MONITORED_ACCOUNTS_SUMMARY,
    'regport_org_verification_daily_trend': REGPORT_ORG_VERIFICATION_DAILY_TREND,
    'regport_org_screening_summary': REGPORT_ORG_SCREENING_SUMMARY,
    'regport_org_batch_upload_summary': REGPORT_ORG_BATCH_UPLOAD_SUMMARY,
    'regport_org_transaction_daily_trend': REGPORT_ORG_TRANSACTION_DAILY_TREND,
    'regport_org_transaction_type_split': REGPORT_ORG_TRANSACTION_TYPE_SPLIT,
    'regport_org_rules_by_code': REGPORT_ORG_RULES_BY_CODE,
    'regport_org_batch_upload_by_template': REGPORT_ORG_BATCH_UPLOAD_BY_TEMPLATE,
    'regport_org_users': REGPORT_ORG_USERS,
    'regport_org_user_activity_by_role': REGPORT_ORG_USER_ACTIVITY_BY_ROLE,

    # RegPort Feature Adoption
    'regport_pulse_active_orgs': REGPORT_PULSE_ACTIVE_ORGS,
    'regport_pulse_workflow_completion': REGPORT_PULSE_WORKFLOW_COMPLETION,
    'regport_pulse_avg_modules': REGPORT_PULSE_AVG_MODULES,
    'regport_pulse_flag_resolution': REGPORT_PULSE_FLAG_RESOLUTION,
    'regport_pulse_report_approval': REGPORT_PULSE_REPORT_APPROVAL,
    'regport_pulse_support_touch': REGPORT_PULSE_SUPPORT_TOUCH,

    # RegPort Flagged Transactions
    'regport_flag_rate_by_org': REGPORT_FLAG_RATE_BY_ORG,
    'regport_flag_resolution_funnel': REGPORT_FLAG_RESOLUTION_FUNNEL,
    'regport_rule_effectiveness': REGPORT_RULE_EFFECTIVENESS,
    'regport_flag_manual_vs_rule': REGPORT_FLAG_MANUAL_VS_RULE,
    'regport_flag_debit_credit': REGPORT_FLAG_DEBIT_CREDIT,
    'regport_flag_weekly_trend': REGPORT_FLAG_WEEKLY_TREND,

    # RegPort Case Management
    'regport_case_status_distribution': REGPORT_CASE_STATUS_DISTRIBUTION,
    'regport_case_resolution_time': REGPORT_CASE_RESOLUTION_TIME,
    'regport_case_action_depth': REGPORT_CASE_ACTION_DEPTH,
    'regport_flag_to_case_ratio': REGPORT_FLAG_TO_CASE_RATIO,
    'regport_case_age_buckets': REGPORT_CASE_AGE_BUCKETS,

    # RegPort CDD & Verification
    'regport_verify_pass_fail_by_service': REGPORT_VERIFY_PASS_FAIL_BY_SERVICE,
    'regport_screening_hit_rate': REGPORT_SCREENING_HIT_RATE,
    'regport_screening_depth_score': REGPORT_SCREENING_DEPTH_SCORE,
    'regport_kyc_kyb_split': REGPORT_KYC_KYB_SPLIT,
    'regport_adverse_media_lag': REGPORT_ADVERSE_MEDIA_LAG,
    'regport_report_pipeline': REGPORT_REPORT_PIPELINE,
    'regport_upload_quality_by_org': REGPORT_UPLOAD_QUALITY_BY_ORG,
    'regport_template_type_coverage': REGPORT_TEMPLATE_TYPE_COVERAGE,
    'regport_upload_error_trend': REGPORT_UPLOAD_ERROR_TREND,
    'regport_upload_to_action_latency': REGPORT_UPLOAD_TO_ACTION_LATENCY,
    'regport_file_type_distribution': REGPORT_FILE_TYPE_DISTRIBUTION,
    'regport_compliance_chain_map': REGPORT_COMPLIANCE_CHAIN_MAP,
    'regport_module_breadth_distribution': REGPORT_MODULE_BREADTH_DISTRIBUTION,
    'regport_support_signal_by_module': REGPORT_SUPPORT_SIGNAL_BY_MODULE,
    'regport_module_activity_volume': REGPORT_MODULE_ACTIVITY_VOLUME,
    'regport_org_health_matrix': REGPORT_ORG_HEALTH_MATRIX,
    'regport_dormancy_risk_list': REGPORT_DORMANCY_RISK_LIST,
    'regport_org_tier_segmentation': REGPORT_ORG_TIER_SEGMENTATION,

    # RegWatch
    'regwatch_assessment_summary': REGWATCH_ASSESSMENT_SUMMARY,
    'regwatch_assessment_trend_monthly': REGWATCH_ASSESSMENT_TREND_MONTHLY,
    'regwatch_assessment_status_breakdown': REGWATCH_ASSESSMENT_STATUS_BREAKDOWN,
    'regwatch_deadline_adherence': REGWATCH_DEADLINE_ADHERENCE,
    'regwatch_compliance_score_distribution': REGWATCH_COMPLIANCE_SCORE_DISTRIBUTION,
    'regwatch_regulatory_area_coverage': REGWATCH_REGULATORY_AREA_COVERAGE,
    'regwatch_repeat_assessment_rate': REGWATCH_REPEAT_ASSESSMENT_RATE,
    'regwatch_regulator_usage': REGWATCH_REGULATOR_USAGE,
    'regwatch_low_compliance_regulations': REGWATCH_LOW_COMPLIANCE_REGULATIONS,
    'regwatch_deep_org_profile': REGWATCH_DEEP_ORG_PROFILE,
    'regwatch_deep_ga4_summary': REGWATCH_DEEP_GA4_SUMMARY,
    'regwatch_deep_northstar_events': REGWATCH_DEEP_NORTHSTAR_EVENTS,
    'regwatch_org_engagement_summary': REGPORT_ORG_ENGAGEMENT_SUMMARY,
    'regwatch_org_engagement_daily_trend': REGPORT_ORG_ENGAGEMENT_DAILY_TREND,
    'regwatch_org_session_device_split': REGPORT_ORG_SESSION_DEVICE_SPLIT,
    'regwatch_org_traffic_source': REGPORT_ORG_TRAFFIC_SOURCE,
    'regwatch_deep_assessment_summary': REGWATCH_DEEP_ASSESSMENT_SUMMARY,
    
    # Organization Deep-Dive Assessment Behaviour and Compliance queries
    'regwatch_deep_assessment_monthly': REGWATCH_DEEP_ASSESSMENT_MONTHLY,
    'regwatch_deep_time_to_complete': REGWATCH_DEEP_TIME_TO_COMPLETE,
    'regwatch_deep_deadline_adherence': REGWATCH_DEEP_DEADLINE_ADHERENCE,
    'regwatch_deep_compliance_score_dist': REGWATCH_DEEP_COMPLIANCE_SCORE_DIST,
    'regwatch_deep_compliance_trend': REGWATCH_DEEP_COMPLIANCE_TREND,
    'regwatch_deep_compliance_summary': REGWATCH_DEEP_COMPLIANCE_SUMMARY,
    'regwatch_deep_low_compliance_regs': REGWATCH_DEEP_LOW_COMPLIANCE_REGS,
    'regwatch_deep_compliance_improvement': REGWATCH_DEEP_COMPLIANCE_IMPROVEMENT,
    'regwatch_deep_regulatory_area': REGWATCH_DEEP_REGULATORY_AREA,
    'regwatch_deep_risk_level_profile': REGWATCH_DEEP_RISK_LEVEL_PROFILE,
    'regwatch_deep_regulator_breakdown': REGWATCH_DEEP_REGULATOR_BREAKDOWN,
    'regwatch_deep_top_regulations': REGWATCH_DEEP_TOP_REGULATIONS,
    'regwatch_deep_assessor_leaderboard': REGWATCH_DEEP_ASSESSOR_LEADERBOARD,
    'regwatch_deep_assessor_monthly_activity': REGWATCH_DEEP_ASSESSOR_MONTHLY_ACTIVITY
}
