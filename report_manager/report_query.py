# =============================================================================
# RegTech365 Report Module — DuckDB Query Store
# report_queries.py
#
# All queries use DuckDB SQL syntax.
# Params are injected via Python f-strings after sanitisation in engine.py.
# Variables injected:
#   {platform}       — 'RegComply' | 'RegPort' | 'RegWatch' | 'All'
#   {start_date}     — 'YYYY-MM-DD'
#   {end_date}       — 'YYYY-MM-DD'
#   {org_id}         — specific org ID or None (optional filter)
#
# HOW TO ADD A NEW REPORT:
#   1. Add query constants below in the relevant section
#   2. Register the report in REPORT_CATALOG inside engine.py
#   3. Add a _build_<key> method to ReportEngine in engine.py
# =============================================================================


# =============================================================================
# REPORT 1 — Executive Platform Health Summary
# Audience: CEO, MD, Board
# Sheets: Platform Snapshot, Org Health, User Growth, Audit Performance (RC only)
# =============================================================================

# Sheet 1: Cross-platform snapshot KPIs
EXEC_PLATFORM_SNAPSHOT = """
WITH orgs AS (
    SELECT
        platform,
        COUNT(DISTINCT organization_id)                                     AS total_orgs,
        COUNT(DISTINCT CASE WHEN organization_start_date::DATE
              <= '{end_date}'::DATE THEN organization_id END)               AS registered_orgs
    FROM all_organizations
    WHERE platform != 'Unknown'
      {platform_filter_orgs}
    GROUP BY platform
),
users AS (
    SELECT
        platform,
        COUNT(DISTINCT user_id)                                             AS total_users
    FROM all_users
    WHERE platform != 'Unknown'
      {platform_filter_users}
    GROUP BY platform
),
sessions AS (
    SELECT
        platform,
        SUM(CAST(sessions AS INTEGER))                                      AS total_sessions,
        SUM(CAST(engaged_sessions AS INTEGER))                              AS engaged_sessions,
        ROUND(100.0 * SUM(CAST(engaged_sessions AS INTEGER))
              / NULLIF(SUM(CAST(sessions AS INTEGER)), 0), 2)               AS engagement_rate_pct,
        ROUND(AVG(CAST(avg_engagement_time_msec AS DOUBLE)) / 60000.0, 2)   AS avg_eng_mins,
        SUM(CAST(active_users AS INTEGER))                                  AS total_active_user_days,
        SUM(CAST(key_events AS INTEGER))                                    AS total_key_events
    FROM daily_organization_metrics
    WHERE date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
      AND platform != 'Unknown'
      {platform_filter_dom}
    GROUP BY platform
)
SELECT
    o.platform,
    o.total_orgs,
    u.total_users,
    s.total_sessions,
    s.engaged_sessions,
    s.engagement_rate_pct,
    s.avg_eng_mins             AS avg_engagement_mins,
    s.total_active_user_days,
    s.total_key_events,
    ROUND(100.0 * s.total_active_user_days
          / NULLIF(u.total_users, 0), 1)   AS user_activity_rate_pct
FROM orgs o
LEFT JOIN users u   ON o.platform = u.platform
LEFT JOIN sessions s ON o.platform = s.platform
ORDER BY o.total_orgs DESC;
"""

# Sheet 2: Org health — active / at-risk / churned this period
EXEC_ORG_HEALTH = """
WITH org_activity AS (
    SELECT
        organization_id,
        organizationName,
        platform,
        COUNT(DISTINCT date)                                AS active_days,
        SUM(CAST(sessions AS INTEGER))                      AS sessions,
        SUM(CAST(key_events AS INTEGER))                    AS key_events,
        MAX(date::DATE)                                     AS last_active_date
    FROM daily_organization_metrics
    WHERE date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
      AND platform != 'Unknown'
      {platform_filter_dom}
    GROUP BY organization_id, organizationName, platform
),
all_orgs AS (
    SELECT organization_id, organizationName, platform, organization_start_date
    FROM all_organizations
    WHERE platform != 'Unknown'
      {platform_filter_orgs}
)
SELECT
    a.platform,
    a.organizationName                                                      AS organization,
    a.organization_start_date::DATE                                         AS joined_date,
    COALESCE(o.active_days, 0)                                              AS active_days,
    COALESCE(o.sessions, 0)                                                 AS sessions,
    COALESCE(o.key_events, 0)                                               AS key_events,
    o.last_active_date,
    CASE
        WHEN o.organization_id IS NULL                   THEN 'Never Active'
        WHEN o.last_active_date >= '{end_date}'::DATE - 7 THEN 'Active'
        WHEN o.last_active_date >= '{end_date}'::DATE - 30 THEN 'At Risk'
        ELSE 'Churned'
    END                                                                     AS health_status,
    CASE
        WHEN o.active_days >= 15  THEN 'High'
        WHEN o.active_days >= 5   THEN 'Medium'
        ELSE 'Low'
    END                                                                     AS engagement_tier
FROM all_orgs a
LEFT JOIN org_activity o ON a.organization_id = o.organization_id
ORDER BY COALESCE(o.sessions, 0) DESC;
"""

# Sheet 3: Weekly user growth trend
EXEC_USER_GROWTH_TREND = """
SELECT
    DATE_TRUNC('week', organization_start_date::DATE)   AS cohort_week,
    platform,
    COUNT(DISTINCT organization_id)                     AS new_orgs,
    SUM(COUNT(DISTINCT organization_id)) OVER (
        PARTITION BY platform
        ORDER BY DATE_TRUNC('week', organization_start_date::DATE)
    )                                                   AS cumulative_orgs
FROM all_organizations
WHERE organization_start_date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  AND platform != 'Unknown'
  {platform_filter_orgs}
GROUP BY cohort_week, platform
ORDER BY cohort_week, platform;
"""

# Sheet 4: RegComply audit performance (executive level)
EXEC_AUDIT_PERFORMANCE = """
SELECT
    standardName                                                            AS compliance_standard,
    auditType                                                               AS audit_type,
    COUNT(*)                                                                AS total_audits,
    COUNT(*) FILTER (WHERE status IN ('completed','audited','approved'))    AS completed_audits,
    COUNT(*) FILTER (WHERE status IN ('ongoing','pending','request'))       AS active_audits,
    COUNT(*) FILTER (WHERE status = 'declined')                             AS declined_audits,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status IN ('completed','audited','approved'))
          / NULLIF(COUNT(*), 0), 1)                                         AS completion_rate_pct,
    ROUND(AVG(CASE WHEN completedAt IS NOT NULL THEN
        date_diff('day', TRY_CAST(createdAt AS TIMESTAMP),
                          TRY_CAST(completedAt AS TIMESTAMP)) END), 1)      AS avg_days_to_complete,
    COUNT(*) FILTER (WHERE useCheckList = true)                             AS checklist_used,
    COUNT(*) FILTER (WHERE requestExtension = true)                         AS extensions_requested
FROM regcomply_audit
WHERE TRY_CAST(startDate AS TIMESTAMP)::DATE
      BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  AND isDeleted = false
  {org_filter_audit}
GROUP BY standardName, auditType
ORDER BY total_audits DESC;
"""


# =============================================================================
# REPORT 2 — Sales Opportunity & Churn Risk
# Audience: Sales reps, Account managers
# Sheets: Churn Risk Table, Expansion Signals, Org Leaderboard
# =============================================================================

# Sheet 1: Per-org churn risk with actionable context
SALES_CHURN_RISK = """
WITH org_sessions AS (
    SELECT
        organization_id,
        organizationName,
        platform,
        SUM(CAST(sessions AS INTEGER))                                      AS total_sessions,
        SUM(CAST(key_events AS INTEGER))                                    AS total_key_events,
        SUM(CAST(active_users AS INTEGER))                                  AS total_active_user_days,
        COUNT(DISTINCT date)                                                AS active_days,
        MAX(date::DATE)                                                     AS last_session_date,
        MIN(date::DATE)                                                     AS first_session_date
    FROM daily_organization_metrics
    WHERE date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
      AND platform != 'Unknown'
      {platform_filter_dom}
    GROUP BY organization_id, organizationName, platform
),
rc_orgs AS (
    SELECT
        organization_id,
        subscriptionPlan,
        subscriptionStatus,
        upgrade,
        upgradePlan,
        employeeSize,
        industry,
        country_name
    FROM regcomply_organizations
),
audit_summary AS (
    SELECT
        organization_id,
        COUNT(*)                                                            AS total_audits,
        COUNT(*) FILTER (WHERE status IN ('completed','audited','approved')) AS completed_audits,
        MAX(TRY_CAST(createdAt AS TIMESTAMP))::DATE                         AS last_audit_created
    FROM regcomply_audit
    WHERE isDeleted = false
      AND TRY_CAST(startDate AS TIMESTAMP)::DATE
          BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
    GROUP BY organization_id
)
SELECT
    s.platform,
    s.organizationName                                                      AS organization,
    r.industry,
    r.country_name                                                          AS country,
    r.subscriptionPlan                                                      AS plan,
    r.subscriptionStatus                                                    AS sub_status,
    r.employeeSize                                                          AS company_size,
    s.total_sessions,
    s.total_key_events,
    s.active_days,
    s.last_session_date,
    CASE
        WHEN s.last_session_date IS NULL                           THEN 'Never Active'
        WHEN s.last_session_date >= '{end_date}'::DATE - 7        THEN 'Active'
        WHEN s.last_session_date >= '{end_date}'::DATE - 21       THEN 'At Risk'
        WHEN s.last_session_date >= '{end_date}'::DATE - 45       THEN 'Churning'
        ELSE 'Churned'
    END                                                                     AS churn_signal,
    -- Churn score 0-100 (higher = more at risk)
    LEAST(100, GREATEST(0,
        CASE WHEN s.last_session_date < '{end_date}'::DATE - 30 THEN 40 ELSE 0 END
        + CASE WHEN s.active_days < 3 THEN 30 ELSE 0 END
        + CASE WHEN s.total_key_events = 0 THEN 20 ELSE 0 END
        + CASE WHEN a.completed_audits = 0 THEN 10 ELSE 0 END
    ))                                                                      AS churn_score,
    COALESCE(a.total_audits, 0)                                             AS audits_created,
    COALESCE(a.completed_audits, 0)                                         AS audits_completed,
    a.last_audit_created,
    CASE WHEN r.upgrade = true THEN 'Yes' ELSE 'No' END                     AS upgrade_intent,
    r.upgradePlan                                                           AS target_upgrade_plan,
    CASE
        WHEN r.upgrade = true AND s.total_key_events >= 5 THEN 'Hot — ready to upgrade'
        WHEN s.active_days >= 10 AND COALESCE(a.completed_audits,0) >= 2    THEN 'Warm — expand usage'
        WHEN s.last_session_date < '{end_date}'::DATE - 21                  THEN 'Cold — re-engagement needed'
        ELSE 'Monitor'
    END                                                                     AS sales_action
FROM org_sessions s
LEFT JOIN rc_orgs r       ON s.organization_id = r.organization_id
LEFT JOIN audit_summary a ON s.organization_id = a.organization_id
ORDER BY churn_score DESC, s.total_sessions DESC;
"""

# Sheet 2: Expansion signals — orgs showing strong usage ready for upsell
SALES_EXPANSION_SIGNALS = """
WITH org_metrics AS (
    SELECT
        organization_id,
        organizationName,
        platform,
        SUM(CAST(sessions AS INTEGER))                  AS sessions,
        SUM(CAST(key_events AS INTEGER))                AS key_events,
        COUNT(DISTINCT date)                            AS active_days,
        ROUND(AVG(CAST(avg_engagement_time_msec AS DOUBLE)) / 60000.0, 2) AS avg_eng_mins
    FROM daily_organization_metrics
    WHERE date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
      AND platform != 'Unknown'
      {platform_filter_dom}
    GROUP BY organization_id, organizationName, platform
),
rc_info AS (
    SELECT organization_id, subscriptionPlan, upgrade, upgradePlan, industry
    FROM regcomply_organizations
)
SELECT
    m.platform,
    m.organizationName                                  AS organization,
    r.industry,
    r.subscriptionPlan                                  AS current_plan,
    m.sessions,
    m.key_events,
    m.active_days,
    m.avg_eng_mins,
    CASE WHEN r.upgrade = true THEN 'Yes' ELSE 'No' END AS upgrade_flagged,
    r.upgradePlan                                       AS suggested_plan,
    CASE
        WHEN m.key_events >= 10 AND m.active_days >= 12 THEN 'Tier 1 — Priority'
        WHEN m.key_events >= 5  AND m.active_days >= 7  THEN 'Tier 2 — Strong'
        ELSE 'Tier 3 — Monitor'
    END                                                 AS expansion_tier
FROM org_metrics m
LEFT JOIN rc_info r ON m.organization_id = r.organization_id
WHERE m.sessions >= 5 AND m.key_events >= 2
ORDER BY m.key_events DESC, m.sessions DESC
LIMIT 50;
"""

# Sheet 3: Org leaderboard — most active orgs this period
SALES_ORG_LEADERBOARD = """
SELECT
    dom.platform,
    dom.organizationName                                                    AS organization,
    SUM(CAST(dom.sessions AS INTEGER))                                      AS sessions,
    SUM(CAST(dom.key_events AS INTEGER))                                    AS key_events,
    SUM(CAST(dom.signed_in_users AS INTEGER))                               AS signed_in_users,
    COUNT(DISTINCT dom.date)                                                AS active_days,
    ROUND(AVG(CAST(dom.avg_engagement_time_msec AS DOUBLE)) / 60000.0, 2)  AS avg_eng_mins,
    MAX(dom.date::DATE)                                                     AS last_active,
    RANK() OVER (PARTITION BY dom.platform ORDER BY SUM(CAST(dom.sessions AS INTEGER)) DESC)
                                                                            AS platform_rank
FROM daily_organization_metrics dom
WHERE dom.date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  AND dom.platform != 'Unknown'
  {platform_filter_dom}
GROUP BY dom.platform, dom.organizationName, dom.organization_id
ORDER BY sessions DESC
LIMIT 100;
"""


# =============================================================================
# REPORT 3 — Product Feature Adoption & Module Usage
# Audience: Product managers, CPO
# Sheets: Module Usage, Audit Funnel Depth, Feature Signals, User Role Breakdown
# =============================================================================

# Sheet 1: Page/module usage across platforms
PRODUCT_MODULE_USAGE = """
SELECT
    platform,
    page_path_level_1                                                       AS module,
    SUM(CAST(page_views AS INTEGER))                                        AS total_page_views,
    SUM(CAST(sessions AS INTEGER))                                          AS sessions,
    SUM(CAST(signed_in_users AS INTEGER))                                   AS signed_in_visitors,
    SUM(CAST(anonymous_visitors AS INTEGER))                                AS anonymous_visitors,
    SUM(CAST(key_events AS INTEGER))                                        AS key_events,
    ROUND(AVG(CAST(avg_engagement_time_msec AS DOUBLE)) / 60000.0, 2)      AS avg_eng_mins,
    ROUND(100.0 * SUM(CAST(key_events AS INTEGER))
          / NULLIF(SUM(CAST(sessions AS INTEGER)), 0), 2)                   AS key_event_rate,
    ROUND(100.0 * SUM(CAST(signed_in_users AS INTEGER))
          / NULLIF(SUM(CAST(signed_in_users AS INTEGER))
                   + SUM(CAST(anonymous_visitors AS INTEGER)), 0), 1)       AS signin_rate_pct
FROM daily_page_metrics
WHERE date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  AND platform != 'Unknown'
  AND page_path_level_1 IS NOT NULL
  AND page_path_level_1 NOT IN ('/', '')
  {platform_filter_dpm}
GROUP BY platform, page_path_level_1
ORDER BY total_page_views DESC
LIMIT 50;
"""

# Sheet 2: RegComply audit funnel stage analysis
PRODUCT_AUDIT_FUNNEL = """
WITH base AS (
    SELECT *
    FROM regcomply_audit
    WHERE isDeleted = false
      AND TRY_CAST(startDate AS TIMESTAMP)::DATE
          BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
      {org_filter_audit}
)
SELECT
    'Created'       AS stage, 1 AS stage_order,
    COUNT(*)        AS count,
    100.0           AS pct_of_created,
    0               AS avg_days_in_stage
FROM base
UNION ALL
SELECT
    'Approved', 2,
    COUNT(*) FILTER (WHERE approvedAt IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE approvedAt IS NOT NULL) / NULLIF(COUNT(*),0), 1),
    ROUND(AVG(CASE WHEN approvedAt IS NOT NULL THEN
        date_diff('hour', TRY_CAST(createdAt AS TIMESTAMP),
                           TRY_CAST(approvedAt AS TIMESTAMP)) / 24.0 END), 2)
FROM base
UNION ALL
SELECT
    'Questions Set', 3,
    COUNT(*) FILTER (WHERE questionsSetAt IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE questionsSetAt IS NOT NULL) / NULLIF(COUNT(*),0), 1),
    ROUND(AVG(CASE WHEN questionsSetAt IS NOT NULL AND approvedAt IS NOT NULL THEN
        date_diff('hour', TRY_CAST(approvedAt AS TIMESTAMP),
                           TRY_CAST(questionsSetAt AS TIMESTAMP)) / 24.0 END), 2)
FROM base
UNION ALL
SELECT
    'Responded', 4,
    COUNT(*) FILTER (WHERE respondedAt IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE respondedAt IS NOT NULL) / NULLIF(COUNT(*),0), 1),
    ROUND(AVG(CASE WHEN respondedAt IS NOT NULL AND questionsSetAt IS NOT NULL THEN
        date_diff('hour', TRY_CAST(questionsSetAt AS TIMESTAMP),
                           TRY_CAST(respondedAt AS TIMESTAMP)) / 24.0 END), 2)
FROM base
UNION ALL
SELECT
    'Audited', 5,
    COUNT(*) FILTER (WHERE auditedAt IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE auditedAt IS NOT NULL) / NULLIF(COUNT(*),0), 1),
    ROUND(AVG(CASE WHEN auditedAt IS NOT NULL AND respondedAt IS NOT NULL THEN
        date_diff('hour', TRY_CAST(respondedAt AS TIMESTAMP),
                           TRY_CAST(auditedAt AS TIMESTAMP)) / 24.0 END), 2)
FROM base
UNION ALL
SELECT
    'Completed', 6,
    COUNT(*) FILTER (WHERE completedAt IS NOT NULL),
    ROUND(100.0 * COUNT(*) FILTER (WHERE completedAt IS NOT NULL) / NULLIF(COUNT(*),0), 1),
    ROUND(AVG(CASE WHEN completedAt IS NOT NULL AND createdAt IS NOT NULL THEN
        date_diff('day', TRY_CAST(createdAt AS TIMESTAMP),
                          TRY_CAST(completedAt AS TIMESTAMP)) END), 2)
FROM base
ORDER BY stage_order;
"""

# Sheet 3: Feature signals — checklist, scoring, extension usage per org
PRODUCT_FEATURE_SIGNALS = """
SELECT
    org_name                                                                AS organization,
    COUNT(*)                                                                AS total_audits,
    COUNT(*) FILTER (WHERE useCheckList = true)                             AS checklist_used,
    ROUND(100.0 * COUNT(*) FILTER (WHERE useCheckList = true)
          / NULLIF(COUNT(*), 0), 1)                                         AS checklist_adoption_pct,
    COUNT(*) FILTER (WHERE requestExtension = true)                         AS extensions_requested,
    COUNT(DISTINCT scoringPattern)                                           AS scoring_patterns_used,
    COUNT(DISTINCT standardName)                                            AS standards_covered,
    COUNT(*) FILTER (WHERE auditType = 'external')                          AS external_audits,
    COUNT(*) FILTER (WHERE auditType = 'internal')                          AS internal_audits,
    COUNT(*) FILTER (WHERE status IN ('completed','audited','approved'))     AS completed_audits,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status IN ('completed','audited','approved'))
          / NULLIF(COUNT(*), 0), 1)                                         AS completion_rate_pct,
    ROUND(AVG(CASE WHEN completedAt IS NOT NULL THEN
        date_diff('day', TRY_CAST(createdAt AS TIMESTAMP),
                          TRY_CAST(completedAt AS TIMESTAMP)) END), 1)      AS avg_days_to_complete
FROM regcomply_audit
WHERE isDeleted = false
  AND TRY_CAST(startDate AS TIMESTAMP)::DATE
      BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  {org_filter_audit}
GROUP BY org_name
ORDER BY total_audits DESC
LIMIT 50;
"""

# Sheet 4: User role breakdown per platform
PRODUCT_USER_ROLES = """
SELECT
    platform,
    role_name,
    COUNT(DISTINCT user_id)                         AS user_count,
    COUNT(DISTINCT organization_id)                 AS orgs_with_this_role,
    ROUND(100.0 * COUNT(DISTINCT user_id)
          / SUM(COUNT(DISTINCT user_id)) OVER (PARTITION BY platform), 1)
                                                    AS pct_of_platform_users
FROM all_users
WHERE platform != 'Unknown'
  {platform_filter_users}
GROUP BY platform, role_name
ORDER BY platform, user_count DESC;
"""


# =============================================================================
# REPORT 4 — User Engagement & Retention
# Audience: Product, Growth, Customer Success
# Sheets: Engagement KPIs, Daily Trend, Stickiness, Traffic Quality, Geo
# =============================================================================

# Sheet 1: Aggregated engagement KPIs per platform
ENGAGEMENT_KPIS = """
SELECT
    platform,
    COUNT(DISTINCT date)                                                    AS days_with_data,
    SUM(CAST(sessions AS INTEGER))                                          AS total_sessions,
    SUM(CAST(engaged_sessions AS INTEGER))                                  AS engaged_sessions,
    ROUND(100.0 * SUM(CAST(engaged_sessions AS INTEGER))
          / NULLIF(SUM(CAST(sessions AS INTEGER)), 0), 2)                   AS engagement_rate_pct,
    ROUND(AVG(CAST(avg_engagement_time_msec AS DOUBLE)) / 60000.0, 2)      AS avg_eng_mins_per_day,
    SUM(CAST(key_events AS INTEGER))                                        AS total_key_events,
    SUM(CAST(page_views AS INTEGER))                                        AS total_page_views,
    SUM(CAST(total_events AS INTEGER))                                      AS total_events,
    ROUND(SUM(CAST(key_events AS INTEGER)) * 1.0
          / NULLIF(SUM(CAST(sessions AS INTEGER)), 0), 3)                   AS key_events_per_session,
    SUM(CAST(signed_in_users AS INTEGER))                                   AS total_signed_in_days,
    SUM(CAST(anonymous_visitors AS INTEGER))                                AS total_anonymous_days
FROM daily_organization_metrics
WHERE date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  AND platform != 'Unknown'
  {platform_filter_dom}
GROUP BY platform
ORDER BY total_sessions DESC;
"""

# Sheet 2: Daily engagement trend
ENGAGEMENT_DAILY_TREND = """
SELECT
    date::DATE                                                              AS day,
    platform,
    SUM(CAST(sessions AS INTEGER))                                          AS sessions,
    SUM(CAST(engaged_sessions AS INTEGER))                                  AS engaged_sessions,
    SUM(CAST(active_users AS INTEGER))                                      AS active_users,
    ROUND(AVG(CAST(avg_engagement_time_msec AS DOUBLE)) / 60000.0, 2)      AS avg_eng_mins,
    SUM(CAST(key_events AS INTEGER))                                        AS key_events,
    ROUND(100.0 * SUM(CAST(engaged_sessions AS INTEGER))
          / NULLIF(SUM(CAST(sessions AS INTEGER)), 0), 1)                   AS engagement_rate_pct
FROM daily_organization_metrics
WHERE date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  AND platform != 'Unknown'
  {platform_filter_dom}
GROUP BY day, platform
ORDER BY day, platform;
"""

# Sheet 3: User-level engagement segments (power / regular / passive)
ENGAGEMENT_USER_SEGMENTS = """
WITH user_agg AS (
    SELECT
        user_id,
        platform,
        SUM(CAST(session_count AS INTEGER))             AS sessions,
        SUM(CAST(key_event_count AS INTEGER))           AS key_events,
        COUNT(DISTINCT date)                            AS active_days,
        ROUND(SUM(CAST(total_engagement_time_msec AS DOUBLE)) / 60000.0, 2) AS total_eng_mins,
        MAX(date::DATE)                                 AS last_active
    FROM daily_user_metrics
    WHERE date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
      AND platform != 'Unknown'
      {platform_filter_dum}
    GROUP BY user_id, platform
),
pcts AS (
    SELECT
        platform,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY key_events) AS p75
    FROM user_agg
    GROUP BY platform
)
SELECT
    u.platform,
    CASE
        WHEN u.key_events >= p.p75 THEN 'Power User'
        WHEN u.key_events > 0       THEN 'Regular User'
        ELSE 'Passive User'
    END                                                 AS segment,
    COUNT(*)                                            AS user_count,
    ROUND(AVG(u.sessions), 2)                           AS avg_sessions,
    ROUND(AVG(u.key_events), 2)                         AS avg_key_events,
    ROUND(AVG(u.active_days), 1)                        AS avg_active_days,
    ROUND(AVG(u.total_eng_mins), 2)                     AS avg_total_eng_mins
FROM user_agg u
JOIN pcts p ON u.platform = p.platform
GROUP BY u.platform, segment
ORDER BY u.platform, avg_key_events DESC;
"""

# Sheet 4: Traffic source quality
ENGAGEMENT_TRAFFIC_QUALITY = """
SELECT
    platform,
    COALESCE(NULLIF(acquisition_source,'(not set)'), 'direct')             AS source,
    COALESCE(NULLIF(acquisition_medium,'(not set)'), 'none')               AS medium,
    SUM(unique_visitors)                                                    AS total_visitors,
    SUM(signed_in_users)                                                    AS signed_in_users,
    SUM(new_signed_in_users)                                                AS new_users,
    SUM(sessions)                                                           AS sessions,
    SUM(engaged_sessions)                                                   AS engaged_sessions,
    SUM(key_events)                                                         AS key_events,
    ROUND(100.0 * SUM(signed_in_users)
          / NULLIF(SUM(unique_visitors), 0), 1)                             AS signin_rate_pct,
    ROUND(AVG(avg_engagement_time_msec) / 60000.0, 2)                      AS avg_eng_mins
FROM daily_traffic_source_metrics
WHERE date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  AND platform != 'Unknown'
  {platform_filter_tsm}
GROUP BY platform, source, medium
HAVING SUM(unique_visitors) >= 2
ORDER BY total_visitors DESC
LIMIT 30;
"""

# Sheet 5: Geographic distribution
ENGAGEMENT_GEO = """
SELECT
    platform,
    country,
    region,
    city,
    SUM(CAST(total_visitors AS INTEGER))                                    AS total_visitors,
    SUM(CAST(signed_in_users AS INTEGER))                                   AS signed_in_users,
    SUM(CAST(sessions AS INTEGER))                                          AS sessions,
    ROUND(100.0 * SUM(CAST(signed_in_users AS INTEGER))
          / NULLIF(SUM(CAST(total_visitors AS INTEGER)), 0), 1)             AS signin_rate_pct,
    ROUND(AVG(CAST(avg_engagement_time_msec AS DOUBLE)) / 60000.0, 2)      AS avg_eng_mins
FROM daily_geographic_metrics
WHERE date::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  AND platform != 'Unknown'
  {platform_filter_geo}
GROUP BY platform, country, region, city
ORDER BY total_visitors DESC
LIMIT 50;
"""


# =============================================================================
# REPORT 5 — RegPort AML & Compliance Operations
# Audience: Compliance officers, RegPort CSMs, senior management
# Sheets: Transaction Summary, Rule Performance, Verification Activity,
#         Report Approval Pipeline, Monitored Accounts
# =============================================================================

# Sheet 1: Transaction monitoring summary by org
AML_TRANSACTION_SUMMARY = """
SELECT
    t.organizationName                                                      AS organization,
    COUNT(*)                                                                AS total_transactions,
    COUNT(*) FILTER (WHERE t.transactionFlagged = true)                     AS flagged_transactions,
    COUNT(*) FILTER (WHERE t.transactionType = 'Credit')                    AS credit_transactions,
    COUNT(*) FILTER (WHERE t.transactionType = 'Debit')                     AS debit_transactions,
    ROUND(100.0 * COUNT(*) FILTER (WHERE t.transactionFlagged = true)
          / NULLIF(COUNT(*), 0), 2)                                         AS flag_rate_pct,
    ROUND(SUM(t.transactionAmount) / 1e6, 2)                                AS total_volume_millions,
    ROUND(AVG(t.transactionAmount) / 1e6, 4)                                AS avg_transaction_millions,
    COUNT(DISTINCT t.transactionCurrency)                                    AS currencies_used,
    t.ruleTemplateName                                                      AS primary_rule,
    COUNT(*) FILTER (WHERE t.transactionReportStatus = true)                AS reported_transactions
FROM regport_transactions t
WHERE t.transactionCreatedAt::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  AND t.transactionIsDeleted = false
  {org_filter_rp}
GROUP BY t.organizationName, t.ruleTemplateName
ORDER BY flagged_transactions DESC, total_transactions DESC
LIMIT 50;
"""

# Sheet 2: Rule performance — which rules are firing most
AML_RULE_PERFORMANCE = """
SELECT
    ruleTemplateName                                                        AS rule_name,
    ruleCode                                                                AS rule_code,
    COUNT(*)                                                                AS total_triggers,
    COUNT(DISTINCT organizationName)                                        AS orgs_triggered,
    COUNT(*) FILTER (WHERE transactionFlagged = true)                       AS flagged_count,
    COUNT(*) FILTER (WHERE transactionReportStatus = true)                  AS reported_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE transactionFlagged = true)
          / NULLIF(COUNT(*), 0), 1)                                         AS flag_rate_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE transactionReportStatus = true)
          / NULLIF(COUNT(*) FILTER (WHERE transactionFlagged = true), 0), 1) AS report_conversion_pct,
    ROUND(SUM(transactionAmount) / 1e6, 2)                                  AS total_volume_millions,
    ROUND(AVG(transactionAmount) / 1e6, 4)                                  AS avg_transaction_millions
FROM regport_transactions
WHERE transactionCreatedAt::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  AND transactionIsDeleted = false
GROUP BY ruleTemplateName, ruleCode
ORDER BY total_triggers DESC;
"""

# Sheet 3: KYC/KYB verification activity by org
AML_VERIFICATION_ACTIVITY = """
SELECT
    v.organizationName                                                      AS organization,
    v.verificationType                                                      AS verification_type,
    v.verificationService                                                   AS service_used,
    COUNT(*)                                                                AS verifications_run,
    COUNT(*) FILTER (WHERE v.createdAt::DATE = v.updatedAt::DATE)           AS same_day_completions,
    MIN(v.createdAt::DATE)                                                  AS first_verification,
    MAX(v.createdAt::DATE)                                                  AS last_verification
FROM regport_verify_customers v
WHERE v.createdAt::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  {org_filter_rp}
GROUP BY v.organizationName, v.verificationType, v.verificationService
ORDER BY verifications_run DESC
LIMIT 50;
"""

# Sheet 4: Generated report approval pipeline
AML_REPORT_PIPELINE = """
SELECT
    organizationName                                                        AS organization,
    ruleCode                                                                AS rule_type,
    ruleTemplateName                                                        AS rule_name,
    reportStatus,
    approvalStatus,
    COUNT(*)                                                                AS report_count,
    COUNT(*) FILTER (WHERE transactionFlagged = true)                       AS flagged_in_reports,
    SUM(transactionCount)                                                   AS total_transactions_in_reports,
    MIN(createdAt::DATE)                                                    AS earliest_report,
    MAX(createdAt::DATE)                                                    AS latest_report
FROM regport_generated_report
WHERE createdAt::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  AND isDeleted = false
  {org_filter_rp}
GROUP BY organizationName, ruleCode, ruleTemplateName, reportStatus, approvalStatus
ORDER BY report_count DESC;
"""

# Sheet 5: Monitored accounts status
AML_MONITORED_ACCOUNTS = """
SELECT
    organizationName                                                        AS organization,
    assignedToRole                                                          AS assigned_to_role,
    monitoredAccountStatus                                                  AS status,
    customerType,
    COUNT(*)                                                                AS account_count,
    SUM(flaggedTransactionCount)                                            AS total_flagged_transactions,
    MIN(createdAt::DATE)                                                    AS earliest_monitoring,
    MAX(monitoringEndDate::DATE)                                            AS latest_end_date,
    COUNT(*) FILTER (WHERE monitoredAccountStatus = 'CLOSED')              AS closed_accounts,
    COUNT(*) FILTER (WHERE monitoredAccountStatus != 'CLOSED')             AS active_accounts
FROM regport_monitored_accounts
WHERE isDeleted = false
  AND createdAt::DATE BETWEEN '{start_date}'::DATE AND '{end_date}'::DATE
  {org_filter_rp}
GROUP BY organizationName, assignedToRole, monitoredAccountStatus, customerType
ORDER BY total_flagged_transactions DESC;
"""


# =============================================================================
# FILTER SNIPPETS — injected into queries based on user params
# =============================================================================

def platform_filter(table_alias=''):
    """Returns platform WHERE clause snippet."""
    return {
        'orgs':  "AND platform = '{platform}'",
        'users': "AND platform = '{platform}'",
        'dom':   "AND platform = '{platform}'",   # daily_organization_metrics
        'dpm':   "AND platform = '{platform}'",   # daily_page_metrics
        'dum':   "AND platform = '{platform}'",   # daily_user_metrics
        'geo':   "AND platform = '{platform}'",   # daily_geographic_metrics
        'tsm':   "AND platform = '{platform}'",   # daily_traffic_source_metrics
    }

def org_filter_snippet(org_id):
    if org_id:
        return f"AND organization_id = '{org_id}'"
    return ""
