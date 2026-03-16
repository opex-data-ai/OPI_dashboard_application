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
  SUM(CAST(dgm.unique_visitors AS INTEGER)) AS total_visitors,
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
),
session_pages AS (
  SELECT
    dsm.ga_session_id,
    dsm.user_pseudo_id,
    COUNT(DISTINCT dsm.page_location) AS pages_in_session
  FROM daily_session_metrics dsm, vars v
  WHERE dsm.date::DATE BETWEEN v.start_date AND v.end_date
    AND LOWER(dsm.platform) = LOWER(v.platform)
  GROUP BY 1, 2
)
SELECT
  ROUND(AVG(pages_in_session), 2) AS avg_pages_per_session,
  MAX(pages_in_session)           AS max_pages_in_session,
  MIN(pages_in_session)           AS min_pages_in_session
FROM session_pages;
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
    COUNT(DISTINCT dsm.page_location) AS pages_visited
  FROM daily_session_metrics dsm, vars v
  WHERE dsm.date::DATE BETWEEN v.start_date AND v.end_date
    AND LOWER(dsm.platform) = LOWER(v.platform)
  GROUP BY dsm.ga_session_id
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
  SELECT ?::DATE AS start_date, ?::DATE AS end_date, ? AS platform
),
all_users AS (
  SELECT
    COUNT(DISTINCT user_pseudo_id) AS total_users
  FROM daily_user_metrics dum, vars v
  WHERE date::DATE BETWEEN v.start_date AND v.end_date
    AND LOWER(dum.platform) = LOWER(v.platform)
)
SELECT
  dcpm.conversion_path,
  dcpm.path_percentage,
  dcpm.path_occurrence_count,
  dcpm.num_pages,
  dcpm.unique_pages,
  dcpm.unique_users_count,
  ROUND(
    100.0 * dcpm.unique_users_count / NULLIF(au.total_users, 0),
    2
  ) AS user_pct
FROM daily_conversion_path_metrics dcpm, vars v
CROSS JOIN all_users au
WHERE dcpm.date::DATE BETWEEN v.start_date AND v.end_date
  AND LOWER(dcpm.platform) = LOWER(v.platform)
  AND dcpm.unique_pages >= 2
ORDER BY dcpm.unique_pages DESC, dcpm.path_occurrence_count DESC
LIMIT 3;
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
    COUNT(DISTINCT dsm.page_location)                                              AS pages_in_session,
    MAX(CAST(dsm.key_events AS INTEGER))                                           AS had_key_event,
    SUM(COALESCE(CAST(dsm.total_engagement_time_msec AS BIGINT), 0))               AS engagement_time
  FROM daily_session_metrics dsm, params p
  WHERE dsm.date::DATE BETWEEN p.start_date AND p.end_date
    AND LOWER(dsm.platform) = LOWER(p.platform)
  GROUP BY dsm.ga_session_id, dsm.user_pseudo_id, dsm.is_engaged_session
),
engaged_users AS (
  SELECT
    ROUND(AVG(engagement_time), 2)  AS avg_engagement_time,
    ROUND(AVG(pages_in_session), 2) AS avg_pages,
    ROUND(AVG(had_key_event), 2)    AS avg_key_events
  FROM session_pages
  WHERE LOWER(CAST(is_engaged_session AS VARCHAR)) = 'true'
),
churned_users AS (
  SELECT
    ROUND(AVG(engagement_time), 2)  AS avg_engagement_time,
    ROUND(AVG(pages_in_session), 2) AS avg_pages,
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


#-- ============================================================================
#-- QUERY 2.13: Acquisition Tab - Session Traffic by Primary Medium & Source
#-- Output: session_source, session_medium, session_count
#-- ============================================================================
# Dictionary to map query names to their SQL content
# This allows 'transfering them where needed' in a batch
QUERIES = {
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
    'product_landing_page_funnel': PRODUCT_LANDING_PAGE_FUNNEL,
    'product_engaged_vs_churned_metrics': PRODUCT_ENGAGED_VS_CHURNED_METRICS,
    'product_engagement_kpis': PRODUCT_ENGAGEMENT_KPIS,
    'product_page_engagement_table': PRODUCT_PAGE_ENGAGEMENT_TABLE,
    'product_org_engagement_table': PRODUCT_ORG_ENGAGEMENT_TABLE,
    
    # Top organizations
    'top_org_per_platform': TOP_ORG_PER_PLATFORM
}
