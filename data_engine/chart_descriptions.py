"""
Central dictionary for metric descriptions used in dashboard cards.
Now fully mapped to standard query keys in the global query store.
"""

METRIC_INFO = {
    # KPI Metrics
    'active_org_rate': {
        'title': 'Active Organization Rate',
        'description': 'Percentage of active organizations out of total organizations',
        'show_ai_icon': False,
        'chart_data': 'platform_rate_metrics',
        'schema_explanation': "Calculated as (active_orgs / total_orgs) * 100. Measures the proportion of active organizations."
    },
    'active_users_rate': {
        'title': 'Active Users Rate',
        'description': 'Percentage of active users out of total users',
        'show_ai_icon': False,
        'chart_data': 'platform_rate_metrics',
        'schema_explanation': "Calculated as (active_users / total_users) * 100. Measures the proportion of active users."
    },
    'anonymous_users_rate': {
        'title': 'Anonymous User Rate',
        'description': 'The percentage of visitors who did not sign in out of the total number of unique visitors',
        'show_ai_icon': False,
        'chart_data': 'product_anonymous_users_pct',
        'schema_explanation': "Calculated as (total_users - signed_in_users) / total_users. Measures the proportion of unauthenticated traffic."
    },
    'active_org_count': {
        'title': 'Active Organizations',
        'description': 'Number of unique organizations that had at least one session during the selected time period.',
        'show_ai_icon': False,
        'chart_data': 'product_active_org_count',
        'schema_explanation': "Count of unique organization_id from the 'sessions' table, representing distinct enterprise clients active in the period."
    },
    'active_signed_in_users': {
        'title': 'Active Signed-In Users',
        'description': 'Count of unique users who were logged into their accounts during the period.',
        'show_ai_icon': False,
        'chart_data': 'product_active_signed_in_users',
        'schema_explanation': "Count of unique user_id where user_id is not null, representing the registered user base activity."
    },
    'total_sessions': {
        'title': 'Total Sessions',
        'description': 'The total number of sessions initiated by users in the organization during the selected time period.',
        'show_ai_icon': False,
        'schema_explanation': "Count of distinct session_id from the session log database for the current organization."
    },
    'active_users': {
        'title': 'Active Users',
        'description': 'The number of unique users active in the organization during the selected time period.',
        'show_ai_icon': False,
        'schema_explanation': "Distinct count of user_id active in this organization."
    },
    'avg_session_time': {
        'title': 'Avg Session Time',
        'description': 'The average duration of a user session in the platform.',
        'show_ai_icon': False,
        'schema_explanation': "Total session duration divided by the number of sessions, formatted into a readable duration value."
    },
    'key_events': {
        'title': 'Key Events',
        'description': 'The count of critical high-value user conversion actions and core feature uses recorded.',
        'show_ai_icon': False,
        'schema_explanation': "Aggregated count of tagged conversion events (e.g. downloads, creations, submits) for this organization."
    },
    'active_days': {
        'title': 'Active Days',
        'description': 'The total number of calendar days in which at least one user session was recorded for this organization.',
        'show_ai_icon': False,
        'schema_explanation': "Count of distinct calendar dates where session events were registered for the organization."
    },
    'regulation_views': {
        'title': 'Regulation Views',
        'description': 'The total number of regulation view and query events initiated by users in the organization during the selected time period.',
        'show_ai_icon': False,
        'schema_explanation': "Count of GA4 regulation_view events triggered during the active date range."
    },
    'engagement_rate': {
        'title': 'Engagement Rate',
        'description': 'Percentage of total sessions that were engaging (lasting longer than 10 seconds, having a conversion event, or at least 2 page views).',
        'show_ai_icon': False,
        'chart_data': 'product_engagement_rate',
        'schema_explanation': "Ratio of 'engaged_sessions' to 'total_sessions'. Engagement is defined by GA4 standards (time > 10s, 2+ page views, or 1+ conversion)."
    },
    'avg_pages_session': {
        'title': 'Avg Pages / Session',
        'description': 'Indicates how many pages users open within a single session.',
        'show_ai_icon': False,
        'chart_data': 'product_avg_pages_per_session',
        'schema_explanation': "Total pageviews divided by total sessions. Higher values typically indicate better content relevance or deeper site exploration."
    },
    'avg_time_signup': {
        'title': 'Avg Time to Signup',
        'description': 'Average cumulative engagement time of a user before completing their first signup.',
        'show_ai_icon': False,
        'chart_data': 'product_time_to_signup',
        'schema_explanation': "Total engagement time (milliseconds) across all sessions before a 'signup_complete' event, averaged per user."
    },
    'landing_exit_rate': {
        'title': 'Landing Page Exit Rate',
        'description': 'Percentage of sessions that start and end on the same page, with no further navigation.',
        'show_ai_icon': False,
        'chart_data': 'product_exit_rate_landing',
        'schema_explanation': "Percentage of sessions where the landing page was also the exit page. High rates may suggest landing page optimization needs."
    },
    'new_orgs': {
        'title': 'New Organizations',
        'description': 'Number of newly registered enterprise organizations within the selected date range.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Count of newly registered enterprise organization accounts during this time period."
    },
    'new_users': {
        'title': 'New Users',
        'description': 'Number of unique newly registered or first-time active users within the selected date range.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Count of first-time active or newly registered users tracked."
    },
    'new_visitors': {
        'title': 'New Visitors (GA4)',
        'description': 'Number of unique first-time visitors tracked via Google Analytics 4 (GA4) daily traffic metrics.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Google Analytics 4 count of unique first-time visitors based on ga_session_number = 1."
    },
    'signed_in_rate_pct': {
        'title': 'Signed-In Rate',
        'description': 'Percentage of unique sessions that were successfully authenticated compared to total active sessions.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Calculated as authenticated sessions divided by total active sessions, representing user log-in conversion."
    },
    'avg_users_org': {
        'title': 'Avg Users / Org',
        'description': 'The average number of registered team members per enterprise organization.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Calculated as total active users divided by total active organizations in the system."
    },
    'device_browser': {
        'title': 'Device & Browser Breakdown',
        'description': 'Distribution of active users by their device category (desktop, mobile, tablet) and web browsers used to access the application.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Shows user counts grouped by device category and browser type to understand hardware adoption trends."
    },

    # Charts
    'user_acquisition_trend': {
        'title': 'User Acquisition Trend',
        'description': 'Daily tracking of active sessions, broken down by signed-in users and anonymous visitors.',
        'show_ai_icon': True,
        'chart_data': 'product_user_acquisition_trend',
        'schema_explanation': "Time-series data with columns 'date' (YYYY-MM-DD), 'signed_in_sessions', and 'anonymous_sessions'. Shows the mix of user types over time."
    },
    'map_distribution': {
        'title': 'Geographic Distribution',
        'description': 'Global distribution of visitors and their behavioral patterns.',
        'show_ai_icon': True,
        'chart_data': 'product_geographic_metrics',
        'schema_explanation': "DataFrame with 'country' name and 'total_visitors'. Measures international adoption."
    },
    'country_breakdown': {
        'title': 'Country Breakdown',
        'description': 'Top countries ranked by visitor count',
        'show_ai_icon': True,
        'chart_data': 'product_geographic_metrics',
        'schema_explanation': "DataFrame with 'country' name and 'total_visitors'. Measures international adoption."
    },
    'traffic_source': {
        'title': 'Traffic Source Analysis',
        'description': 'Analysis of where traffic originates',
        'show_ai_icon': True,
        'chart_data': 'product_traffic_source_metrics',
        'schema_explanation': "DataFrame with 'source' (e.g. google, direct) and 'session_count'. Identifies high-performing marketing channels."
    },
    'traffic_medium': {
        'title': 'Traffic Medium',
        'description': 'Analysis of how traffic reaches the platform',
        'show_ai_icon': True,
        'chart_data': 'product_traffic_source_metrics',
        'schema_explanation': "DataFrame with 'medium' (e.g. organic, email, cpc), and 'session_count'. Identifies high-performing marketing channels."
    },
    'stickiness_ratios': {
        'title': 'User Stickiness',
        'description': 'Ratios of Daily (DAU) to Weekly (WAU) and Monthly (MAU) active users, indicating platform retention.',
        'show_ai_icon': True,
        'chart_data': 'product_stickiness',
        'schema_explanation': "Comparison of DAU/MAU and DAU/WAU percentages. Values above 20% are generally considered healthy for B2B SaaS."
    },
    'acq_new_vs_returning': {
        'title': 'New vs Returning Users',
        'description': 'Weekly tracking of new visitors versus returning users, showing user loyalty and engagement trends.',
        'show_ai_icon': True,
        'chart_data': 'product_user_acquisition_trend',
        'schema_explanation': "Weekly aggregated counts where 'new_users' represents sessions with ga_session_number = 1, and 'returning_users' represents sessions with ga_session_number > 1."
    },
    'engaged_vs_churned': {
        'title': 'Engaged vs Churned',
        'description': 'Comparative analysis of behavior patterns between users who remain active and those who stop returning.',
        'show_ai_icon': True,
        'chart_data': 'product_engaged_vs_churned_metrics',
        'schema_explanation': "Bucketed user counts: 'highly_engaged' (3+ sessions/week), 'returning', and 'churn_risk' (no activity in 14 days)."
    },
    'funnel_analysis': {
        'title': 'Funnel Analysis',
        'description': 'Visualizing the progression of users from landing pages to key functional modules.',
        'show_ai_icon': True,
        'chart_data': 'product_landing_page_funnel',
        'schema_explanation': "Sequence of events: 'page_view' -> 'module_click' -> 'data_engagement' -> 'conversion'. Shows drop-off at each stage."
    },
    'user_journeys': {
        'title': 'High-Engagement Journeys',
        'description': 'Common navigation paths taken by users who show high levels of platform interaction.',
        'show_ai_icon': True,
        'chart_data': 'product_user_journey',
        'schema_explanation': "Transition paths between pages. 'conversion_path' shows the sequence of URLs, 'user_pct' is the share of users following that path."
    },
    'page_engagement': {
        'title': 'Page Performance',
        'description': 'Detailed engagement metrics, scroll depth, and interaction counts for individual platform pages.',
        'show_ai_icon': True,
        'chart_data': 'product_page_engagement_table',
        'schema_explanation': "Metrics per URL: 'avg_scroll_depth', 'button_clicks', and 'avg_time_on_page'. Identifies content friction points."
    },
    'churn_risk_dormant': {
        'title': 'Churn Risk — Dormant Orgs',
        'description': 'List of organizations with zero activity for over 30 days, highlighted by high risk levels.',
        'show_ai_icon': True,
        'chart_data': 'product_dormant_organizations',
        'schema_explanation': "DataFrame containing 'org_name' and 'days_dormant' to identify accounts at risk of churning."
    },
    'signup_login_trend': {
        'title': 'Weekly Sign-Up & Login Trend',
        'description': 'Weekly comparison of user registrations and login activities over time.',
        'show_ai_icon': True,
        'chart_data': 'product_weekly_signup_login_trend',
        'schema_explanation': "DataFrame with 'week_start', 'signups', and 'logins' tracking user activation and retention."
    },
    'org_engagement': {
        'title': 'Organization Engagement',
        'description': 'Aggregated engagement behavior for specific enterprise accounts and organizations.',
        'show_ai_icon': True,
        'chart_data': 'product_org_engagement_table',
        'schema_explanation': "Totals grouped by organizationDomain. Measures account-level activity and health.",
        'has_pii': True,
        'pii_columns': ['organizationName']
    },
    
    # Ecosystem / Home Page Metrics
    'ecosystem_orgs': {
        'title': 'Total Ecosystem Organizations',
        'description': 'The total number of unique organizations registered across all platforms in the ecosystem.',
        'show_ai_icon': False,
        'chart_data': 'organization_by_platform',
        'schema_explanation': "Sum of distinct organization counts across all product databases (RegWatch, RegPort, etc.)."
    },
    'ecosystem_users': {
        'title': 'Total Ecosystem Users',
        'description': 'The total count of unique users registered across all platforms in the ecosystem.',
        'show_ai_icon': False,
        'chart_data': 'user_by_platform',
        'schema_explanation': "Sum of distinct user counts across all product databases."
    },
    'ecosystem_platforms': {
        'title': 'Total Platforms',
        'description': 'The number of active product platforms currently integrated into the monitoring dashboard.',
        'show_ai_icon': False,
        'chart_data': 'platform_organization_user_count',
        'schema_explanation': "Metric showing the footprint of the enterprise suite."
    },
    'multi_platform_rate': {
        'title': 'Multi-platform Adoption Rate',
        'description': 'The percentage of organizations that are active on more than one platform.',
        'show_ai_icon': False,
        'chart_data': 'ecosystem_adoption_rate',
        'schema_explanation': "Count of orgs present in 2+ platform tables / total unique orgs."
    },
    'full_ecosystem_rate': {
        'title': 'Full Ecosystem Adoption Rate',
        'description': 'The percentage of organizations that have adopted and are active on all available platforms.',
        'show_ai_icon': False,
        'chart_data': 'ecosystem_adoption_rate',
        'schema_explanation': "Count of orgs present in ALL platform tables / total unique orgs."
    },
    'org_breakdown': {
        'title': 'Platform Organization Breakdown',
        'description': 'Comparison of direct organization counts across different platforms.',
        'show_ai_icon': True,
        'chart_data': 'organization_by_platform',
        'schema_explanation': "DataFrame with 'platform' and 'total_orgs'. Vertically compares product reach."
    },
    'user_breakdown': {
        'title': 'Platform User Breakdown',
        'description': 'Comparison of unique user counts across different platforms.',
        'show_ai_icon': True,
        'chart_data': 'user_by_platform',
        'schema_explanation': "DataFrame with 'platform' and 'total_users'. Vertically compares product usage."
    },
    
    # Dashboard Overview Metrics
    'overview_revenue': {
        'title': 'Total Revenue',
        'description': 'Aggregated revenue across all product lines and services for the current period.',
        'show_ai_icon': False,
        'chart_data': 'platform_rate_metrics',
        'schema_explanation': "Unified billing data summed across all active subscriptions."
    },
    'overview_projects': {
        'title': 'Active Projects',
        'description': 'Total number of client projects and internal initiatives currently in progress.',
        'show_ai_icon': False,
        'chart_data': 'platform_rate_metrics',
        'schema_explanation': "Count of projects with status != 'Completed' or 'Cancelled'."
    },
    'overview_utilization': {
        'title': 'Team Utilization',
        'description': 'Average percentage of team capacity currently allocated to active projects.',
        'show_ai_icon': False,
        'chart_data': 'platform_rate_metrics',
        'schema_explanation': "Average of individual utilization rates (billable_hours / total_capacity)."
    },
    'overview_score': {
        'title': 'Performance Score',
        'description': 'Composite metric evaluating efficiency, quality, and delivery speed across the organization.',
        'show_ai_icon': False,
        'chart_data': 'platform_rate_metrics',
        'schema_explanation': "Weighted average of revenue, utilization, and project health scores."
    },

    # RegComply Feature Adoption Metrics
    'regcomply_total_audits': {
        'title': 'Total Audits',
        'description': 'The total number of audits conducted during the selected period.',
        'show_ai_icon': False,
        'chart_data': 'regcomply_audit_count',
        'schema_explanation': "Total count of records in the audit metrics table for the given date range."
    },
    'regcomply_completion_rate': {
        'title': 'Audit Completion Rate',
        'description': 'Percentage of audits that have reached a completed, approved, or audited status.',
        'show_ai_icon': False,
        'chart_data': 'regcomply_audit_completion_rate',
        'schema_explanation': "Calculated as (Completed Audits / Total Audits) * 100."
    },
    'regcomply_active_audits': {
        'title': 'Active Audits',
        'description': 'Number of audits currently in ongoing, pending, or request status.',
        'show_ai_icon': False,
        'chart_data': 'regcomply_active_audits',
        'schema_explanation': "Count of audits where status is 'ongoing', 'pending', or 'request'."
    },
    'regcomply_avg_duration': {
        'title': 'Avg Audit Duration',
        'description': 'Average number of days taken to complete an audit.',
        'show_ai_icon': False,
        'chart_data': 'regcomply_average_audit_duration',
        'schema_explanation': "Average difference in days between the start date and completion date (or current date if ongoing)."
    },
    'regcomply_external_pct': {
        'title': 'External Audit %',
        'description': 'Percentage of total audits that were performed by external parties.',
        'show_ai_icon': False,
        'chart_data': 'regcomply_external_audit_pct',
        'schema_explanation': "Calculated as (External Audits / Total Audits) * 100."
    },
    'regcomply_audit_funnel': {
        'title': 'Audit Lifecycle Funnel',
        'description': 'Tracking the progression of audits from creation to completion.',
        'show_ai_icon': True,
        'chart_data': 'regcomply_audit_funnel',
        'schema_explanation': "Stages of an audit: Created -> Questions Set -> Responded -> Audited -> Completed."
    },
    'regcomply_status_distribution': {
        'title': 'Audit Status Distribution',
        'description': 'Breakdown of audits by their current lifecycle status group.',
        'show_ai_icon': True,
        'chart_data': 'regcomply_status_distribution',
        'schema_explanation': "Groups statuses into Active, Completed, or Failed categories."
    },
    'regcomply_audit_type_split': {
        'title': 'Audit Type Breakdown',
        'description': 'Comparison of different audit types (e.g., Internal vs External).',
        'show_ai_icon': True,
        'chart_data': 'regcomply_audit_type_split',
        'schema_explanation': "Counts audits based on the 'auditType' field."
    },
    'regcomply_audits_by_standard': {
        'title': 'Audits by Compliance Standard',
        'description': 'Total audits conducted per regulatory or compliance standard.',
        'show_ai_icon': True,
        'chart_data': 'regcomply_audits_by_standard',
        'schema_explanation': "Counts audits grouped by 'standardName'."
    },
    'regcomply_audit_duration_trend': {
        'title': 'Average Audit Duration Trend',
        'description': 'Daily trend of the average time taken to complete audits.',
        'show_ai_icon': True,
        'chart_data': 'regcomply_audit_duration_trend',
        'schema_explanation': "Calculated as daily average of (Completed Date - Start Date)."
    },
    'regcomply_time_to_questions': {
        'title': 'Time to Questions Set',
        'description': 'Average hours taken from audit creation to setting the questions.',
        'show_ai_icon': False,
        'chart_data': 'regcomply_time_to_questions',
        'schema_explanation': "Hours between 'createdAt' and 'questionsSetAt'."
    },
    'regcomply_time_to_respond': {
        'title': 'Time to Respond',
        'description': 'Average hours taken from setting questions to receiving a response.',
        'show_ai_icon': False,
        'chart_data': 'regcomply_time_to_respond',
        'schema_explanation': "Hours between 'questionsSetAt' and 'respondedAt'."
    },
    'regcomply_time_to_complete': {
        'title': 'Time to Complete',
        'description': 'Average days taken from creation to full audit completion.',
        'show_ai_icon': False,
        'chart_data': 'regcomply_time_to_complete',
        'schema_explanation': "Days between 'createdAt' and 'completedAt'."
    },
    'regcomply_extension_rate': {
        'title': 'Extension Request Rate',
        'description': 'Percentage of audits that requested an end-date extension.',
        'show_ai_icon': False,
        'chart_data': 'regcomply_extension_rate',
        'schema_explanation': "Calculated as (Audits with Extension / Total Audits) * 100."
    },
    'regcomply_delayed_audits': {
        'title': 'Delayed Audits',
        'description': 'Number of audits that exceeded their planned end date.',
        'show_ai_icon': False,
        'chart_data': 'regcomply_delayed_audits',
        'schema_explanation': "Audits where completion date or current date is past 'endDate'."
    },
    'regcomply_org_performance_table': {
        'title': 'Organizational Audit Performance',
        'description': 'Detailed breakdown of audit metrics per organization.',
        'show_ai_icon': True,
        'chart_data': 'regcomply_org_performance_table',
        'schema_explanation': "Table showing total audits, completion rate, avg duration, and active counts per org."
    },
    'regcomply_lifecycle_duration_table': {
        'title': 'Audit Lifecycle Duration Analysis',
        'description': 'Average time (in days, hours, mins) spent at each stage of the audit lifecycle, grouped by audit title.',
        'show_ai_icon': True,
        'chart_data': 'regcomply_lifecycle_duration_table',
        'schema_explanation': "For each audit title: creation-to-next, approval, question, response, feedback, planned, and actual duration stages. All durations converted from raw seconds to a human-readable d/h/m format."
    },

    # RegPort Feature Adoption (PULSE KPIs)
    'pulse_active_orgs': {
        'title': 'Active Organizations (Pulse)',
        'description': 'Unique organizations active on the platform during the period.',
        'show_ai_icon': True,
        'chart_data': 'regport_pulse_active_orgs',
        'schema_explanation': "Count of unique organizationId from audit trails. MoM delta compares with previous 30-day window."
    },
    'pulse_workflow_completion': {
        'title': 'Workflow Completion Rate',
        'description': 'Percentage of active organizations that completed the full E2E workflow.',
        'show_ai_icon': True,
        'chart_data': 'regport_pulse_workflow_completion',
        'schema_explanation': "Ratio of orgs with ingestion AND screening AND reporting to total active orgs."
    },
    'pulse_avg_modules': {
        'title': 'Avg Modules / Org',
        'description': 'The average number of unique functional modules used per active organization.',
        'show_ai_icon': True,
        'chart_data': 'regport_pulse_avg_modules',
        'schema_explanation': "Average of distinct module counts per organizationId in the audit trails."
    },
    'pulse_flag_resolution': {
        'title': 'Flag Resolution Rate',
        'description': 'Percentage of flagged transactions that have been confirmed, dismissed, or escalated.',
        'show_ai_icon': True,
        'chart_data': 'regport_pulse_flag_resolution',
        'schema_explanation': "Ratio of resolution audit events to total flagged transactions created in the period."
    },
    'pulse_report_approval': {
        'title': 'Report Approval Rate',
        'description': 'Percentage of generated reports that received an approval status.',
        'show_ai_icon': True,
        'chart_data': 'regport_pulse_report_approval',
        'schema_explanation': "Ratio of 'Report Approval' actions to total 'Report Approval' + 'Report Rejection' actions."
    },
    'pulse_support_touch': {
        'title': 'Support Touch Rate',
        'description': 'Percentage of active organizations that interacted with support channels.',
        'show_ai_icon': True,
        'chart_data': 'regport_pulse_support_touch',
        'schema_explanation': "Ratio of unique orgs with support-related audit actions to total active orgs."
    },

    # Product Organization Deep-Dive Charts
    'daily_active_users_sessions': {
        'title': 'Daily Active Users & Sessions',
        'description': 'A daily timeline tracking the number of unique active users (bars) and total sessions (line) registered for this organization.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Active users counted as daily unique visitor/user IDs. Sessions counted as total daily distinct session logs."
    },
    'session_device_split': {
        'title': 'Session Device Split',
        'description': 'Breakdown of user sessions by device type (desktop, mobile, tablet) used to access the application.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Derived from user-agent device category mapping in session metrics."
    },
    'day_of_week_engagement': {
        'title': 'Day-of-Week Engagement Pattern',
        'description': 'Average engagement activity (active users) grouped by day of the week to analyze peak usage periods.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Calculated as the average active user count grouped by day of week (Sunday-Saturday)."
    },
    'top_traffic_sources': {
        'title': 'Top Traffic Sources',
        'description': 'Referral traffic analysis showing which channels (direct, organic search, referral, etc.) bring users to the platform.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Breakdown of session traffic source and medium campaigns."
    },
    'audit_funnel_bottlenecks': {
        'title': 'Audit Funnel & Bottlenecks',
        'description': 'Detailed stage-by-stage progression of audits with average duration in days, identifying processing bottlenecks.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Computed using date differences between consecutive stage transitions in compliance audits."
    },
    'standard_performance': {
        'title': 'Standard Performance',
        'description': 'Compliance scores and audit drop-off rates broken down per regulation or standard framework.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Completion percentage and dropout rates analyzed across regulatory standard frameworks."
    },
    'top_viewed_regulations': {
        'title': 'Top Viewed Regulations',
        'description': 'The most frequently accessed and queried regulation topics by users of the organization.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Aggregated count of regulation view events grouped by document or regulation title."
    },
    'pre_assessment_standard_performance': {
        'title': 'Pre-Assessment Standard Performance',
        'description': 'Detailed compliance drop-off and completeness scores across various standards during pre-assessment.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Aggregated completion percentage per pre-assessment checklist item and standard."
    },
    'rules_trigger_funnel': {
        'title': 'Rules Trigger Funnel',
        'description': 'Progression funnel of transaction monitoring rules from initial trigger to screening and eventual compliance verification.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Funnel analysis tracking transition count of accounts across screening and rules validation stages."
    },
    'rule_performance_drop_off': {
        'title': 'Rule Performance Drop-Off',
        'description': 'Detailed performance breakdown of regulatory compliance rules, displaying drop-off ratios per rule standard.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Breakdown of rule screening drops, showing validation and completion percentages."
    },
    'conversion_milestones': {
        'title': 'Conversion Milestones',
        'description': 'Key operational conversion metrics, subscription statuses, and checklist usage statistics for this organization.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Aggregated milestones, subscription tier information, and checklist events counts."
    },
    'avg_days_per_stage': {
        'title': 'Average Days Per Stage',
        'description': 'Average processing time (in days) spent at each stage of the compliance or operational workflow to uncover bottleneck areas.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Days difference between sequential state transition timestamps per organization."
    },
    'flag_resolution_funnel': {
        'title': 'Flag Resolution Funnel',
        'description': 'Conversion funnel from dashboard access to final transaction resolution (confirmation, dismissal, or escalation).',
        'show_ai_icon': True,
        'chart_data': 'regport_flag_resolution_funnel',
        'schema_explanation': "Funnel of action types registered in audit logs starting from initial dashboard entry to resolution actions."
    },
    'manual_vs_rule_triggered': {
        'title': 'Manual vs Rule-Triggered',
        'description': 'Proportion of compliance cases and alerts flagged manually by investigators versus automatically via compliance rules.',
        'show_ai_icon': True,
        'chart_data': 'regport_flag_manual_vs_rule',
        'schema_explanation': "Compares manual flags to rule template-triggered alerts in the compliance tables."
    },
    'rule_effectiveness': {
        'title': 'Rule Effectiveness',
        'description': 'Outcomes of rule-triggered flags, showing the ratio of confirmed, dismissed, and escalated actions per template.',
        'show_ai_icon': True,
        'chart_data': 'regport_rule_effectiveness',
        'schema_explanation': "Outcome split per rule code, showing the precision and effectiveness of various transaction rules."
    },
    'weekly_flag_volume_resolution_rate': {
        'title': 'Weekly Flag Volume & Resolution Rate',
        'description': 'Weekly volume of flagged transactions plotted alongside the resolution percentage to track queue clearance efficiency.',
        'show_ai_icon': True,
        'chart_data': 'regport_flag_weekly_trend',
        'schema_explanation': "Weekly flag counts versus resolved flags to measure operations processing speeds."
    },
    'debit_credit_flag_split': {
        'title': 'Debit vs Credit Flag Split',
        'description': 'Outcomes and distribution of flagged events categorized by debit and credit transaction types.',
        'show_ai_icon': True,
        'chart_data': 'regport_flag_debit_credit',
        'schema_explanation': "Outcome ratios segmented by transactional directions (debit vs credit)."
    },
    'flag_rate_by_org': {
        'title': 'Flag Rate by Organisation',
        'description': 'Percentage of transactions flagged per organization. Standard compliance thresholds tag flag rates above 5% in red.',
        'show_ai_icon': True,
        'chart_data': 'regport_flag_rate_by_org',
        'schema_explanation': "Calculated as flagged transactions divided by total transaction counts per organization."
    },
    'case_status_pipeline': {
        'title': 'Case Status Pipeline',
        'description': 'Distribution of active monitoring cases across New, Under Review, and Closed workflow pipelines.',
        'show_ai_icon': True,
        'chart_data': 'regport_case_status_distribution',
        'schema_explanation': "Current status counts of monitored client cases in the pipeline database."
    },
    'avg_resolution_time': {
        'title': 'Avg Resolution Time',
        'description': 'Average number of days taken to resolve and close cases per organization.',
        'show_ai_icon': True,
        'chart_data': 'regport_case_resolution_time',
        'schema_explanation': "Calculated as average days between case creation date and case closure timestamp."
    },
    'case_action_depth': {
        'title': 'Case Action Depth',
        'description': 'Average number of audit events and compliance touches recorded per closed case across organizations.',
        'show_ai_icon': True,
        'chart_data': 'regport_case_action_depth',
        'schema_explanation': "Aggregated audit events divided by case count to represent thoroughness of investigation."
    },
    'flags_to_case_ratio': {
        'title': 'Flags-to-Case Ratio',
        'description': 'Ratio of total flagged transactions to actual escalations. High ratios (>50:1) signal possible under-escalation.',
        'show_ai_icon': True,
        'chart_data': 'regport_flag_to_case_ratio',
        'schema_explanation': "Flagged transactions divided by escalated cases. Highlights differences in risk tolerance."
    },
    'open_case_age_buckets': {
        'title': 'Open Case Age Buckets',
        'description': 'Age distribution of outstanding compliance cases, highlighting cases open for more than 30 or 90 days.',
        'show_ai_icon': True,
        'chart_data': 'regport_case_age_buckets',
        'schema_explanation': "Groups active cases (New + Under Review) into <7d, 7-30d, 30-90d, and >90d buckets since creation."
    },
    'verification_pass_fail': {
        'title': 'Verification Pass / Fail',
        'description': 'Total count of customer verifications that passed versus failed, broken down by integrated verification service.',
        'show_ai_icon': True,
        'chart_data': 'regport_verify_pass_fail_by_service',
        'schema_explanation': "Aggregated pass/fail results from the customer verification logs grouped by identity service."
    },
    'screening_hit_rate': {
        'title': 'Screening Hit Rate',
        'description': 'Proportion of customer screenings that flagged sanction list matches, PEP matches, or returned completely clean.',
        'show_ai_icon': True,
        'chart_data': 'regport_screening_hit_rate',
        'schema_explanation': "Ratio of PEP/Sanction matches to total user and corporate screenings performed."
    },
    'kyc_kyb_split': {
        'title': 'KYC vs KYB Split',
        'description': 'Distribution of verification types (individual KYC vs corporate KYB) conducted per enterprise client.',
        'show_ai_icon': True,
        'chart_data': 'regport_kyc_kyb_split',
        'schema_explanation': "Grouped verification counts comparing retail/individual verifications to corporate reviews."
    },
    'adverse_media_response_lag': {
        'title': 'Adverse Media Response Lag',
        'description': 'Average turnaround time (in hours) between initial screening match and launching an adverse media investigation.',
        'show_ai_icon': True,
        'chart_data': 'regport_adverse_media_lag',
        'schema_explanation': "Time delta between screening trigger and subsequent investigative audit actions."
    },
    'screening_depth_score': {
        'title': 'Screening Depth Score',
        'description': 'Maturity index showing which screening modules (individual, batch, custom list, sanction, pep) are active per org.',
        'show_ai_icon': True,
        'chart_data': 'regport_screening_depth_score',
        'schema_explanation': "Weighted score out of 5 based on boolean activation of core compliance checking modules."
    },
    'report_pipeline_per_org': {
        'title': 'Report Pipeline Per Org',
        'description': 'Pipeline tracking compliance reports that were generated, subsequently approved, or rejected per organization.',
        'show_ai_icon': True,
        'chart_data': 'regport_report_pipeline',
        'schema_explanation': "Flow tracking from report generation to final QA approval or rejection status in audit trail."
    },
    'approval_rate': {
        'title': 'Approval Rate',
        'description': 'Overall percentage of generated regulatory reports that passed internal compliance QA reviews.',
        'show_ai_icon': True,
        'chart_data': 'regport_report_pipeline',
        'schema_explanation': "Calculated as Approved reports divided by (Approved + Rejected) reports."
    },
    'upload_quality_score': {
        'title': 'Upload Quality Score',
        'description': 'Percentage of batch records processed successfully without parsing failures or schema errors.',
        'show_ai_icon': True,
        'chart_data': 'regport_upload_quality_by_org',
        'schema_explanation': "Successful record counts divided by total uploaded records inside batch tracking logs."
    },
    'template_type_coverage': {
        'title': 'Template Type Coverage',
        'description': 'Count of distinct ingestion templates and rule configurations active per enterprise account.',
        'show_ai_icon': True,
        'chart_data': 'regport_template_type_coverage',
        'schema_explanation': "Measures diversification of active automated schema configurations."
    },
    'file_type_distribution': {
        'title': 'File Type Distribution',
        'description': 'Breakdown of uploaded compliance documents by file type. High CSV usage indicates automated pipelines.',
        'show_ai_icon': True,
        'chart_data': 'regport_file_type_distribution',
        'schema_explanation': "Compares CSV (typically system-to-system) to XLSX (typically manual spreadsheet) upload events."
    },
    'compliance_chain_completion_map': {
        'title': 'Compliance Chain Completion Map',
        'description': 'Integration checklist tracking which stages of the core compliance chain (ingest, screen, monitor, cases, reports) are active.',
        'show_ai_icon': True,
        'chart_data': 'regport_compliance_chain_map',
        'schema_explanation': "Audit audit events mapping presence of ingestion, screening, monitoring, case, and reporting events per client."
    },
    'module_breadth_distribution': {
        'title': 'Module Breadth Distribution',
        'description': 'Maturity clustering showing how many enterprise accounts are utilizing 1, 2, or 5+ core functional modules.',
        'show_ai_icon': True,
        'chart_data': 'regport_module_breadth_distribution',
        'schema_explanation': "Aggregates organizations based on their core module footprint counts."
    },
    'module_activity_volume': {
        'title': 'Module Activity Volume',
        'description': 'Total daily transaction and system event volumes recorded across each core compliance module.',
        'show_ai_icon': True,
        'chart_data': 'regport_module_activity_volume',
        'schema_explanation': "Sum of audit trail events grouped by compliance module category."
    },
    'support_signal_by_module': {
        'title': 'Support Signal by Module',
        'description': 'Ux friction analysis tracking support tickets opened within 30 minutes of visiting a specific module.',
        'show_ai_icon': True,
        'chart_data': 'regport_support_signal_by_module',
        'schema_explanation': "Session sequence analysis tracking support events within a 30-minute window of module actions."
    },
    'org_health_matrix': {
        'title': 'Organisation Health Matrix',
        'description': 'Composite risk matrix tracking activity recency, module breadth, pipeline completion, and alert ratios per client.',
        'show_ai_icon': True,
        'chart_data': 'regport_org_health_matrix',
        'schema_explanation': "Matrix compiling key adoption indices (days since active, breadth, completion, approvals) to generate a composite risk tier."
    },
    'dormancy_risk_list': {
        'title': 'Dormancy Risk List',
        'description': 'List of enterprise clients that were highly active but have had zero activity for more than 21 days.',
        'show_ai_icon': True,
        'chart_data': 'regport_dormancy_risk_list',
        'schema_explanation': "Filters active clients with high historical activity that show no audit trail records in the last 21 days."
    },
    'tier_segmentation': {
        'title': 'Tier Segmentation',
        'description': 'Segmentation of customer base into high engagement categories (Power, Steady, At-Risk, Dormant) based on usage signals.',
        'show_ai_icon': True,
        'chart_data': 'regport_org_tier_segmentation',
        'schema_explanation': "Categorizes organizations based on activity thresholds and inactivity indicators."
    },
    'total_assessments': {
        'title': 'Total Assessments',
        'description': 'Total number of regulatory compliance assessments created or active in the platform.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_assessment_summary',
        'schema_explanation': 'Count of unique assessment records in RegWatch within the selected date range.'
    },
    'completion_rate': {
        'title': 'Completion Rate',
        'description': 'Percentage of compliance assessments that have been fully finalized and completed.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_assessment_summary',
        'schema_explanation': 'Completed assessments divided by total assessments, multiplied by 100.'
    },
    'avg_compliance': {
        'title': 'Average Compliance Score',
        'description': 'Average compliance level across all completed assessments, based on compliant vs non-compliant checklist items.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_assessment_summary',
        'schema_explanation': 'Average compliance percentage calculated from compliant items relative to total answered items.'
    },
    'expired': {
        'title': 'Expired Assessments',
        'description': 'Assessments that have passed their target completion deadline without being completed.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_assessment_summary',
        'schema_explanation': 'Count of incomplete assessments where the deadline date is prior to the current date.'
    },
    'not_started': {
        'title': 'Not Started Assessments',
        'description': 'Compliance assessments that have been generated but have zero progress or answered checklist items.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_assessment_summary',
        'schema_explanation': "Count of assessments in 'Not Started' status."
    },
    'distinct_assessors': {
        'title': 'Distinct Assessors',
        'description': 'Number of unique compliance officers or platform users who performed or signed off on assessments.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_assessment_summary',
        'schema_explanation': 'Distinct count of assessor user IDs recorded across the assessments in the period.'
    },
    'regulations_covered': {
        'title': 'Regulations Covered',
        'description': 'Number of distinct statutory compliance standards or regulatory requirements assessed.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_assessment_summary',
        'schema_explanation': 'Distinct count of regulation IDs or names mapped to assessments active in the period.'
    },
    'avg_time_to_complete': {
        'title': 'Avg Time to Complete',
        'description': 'The average time elapsed (in minutes) from assessment initiation to final compliance sign-off.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_assessment_summary',
        'schema_explanation': 'Average duration in minutes between the creation timestamp and completion timestamp of assessments.'
    },
    'monthly_assessment_volume_watch': {
        'title': 'Monthly Assessment Volume & Avg Compliance',
        'description': 'Monthly trend of started, completed, and expired assessments along with the monthly average compliance percentage.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_assessment_trend_monthly',
        'schema_explanation': 'Started, completed, and expired counts per month along with the average compliance score across completed runs.'
    },
    'assessment_status_split_watch': {
        'title': 'Assessment Status Split',
        'description': 'Breakdown of assessments by their current lifecycle status: Completed, Expired, or Not Started.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_assessment_status_breakdown',
        'schema_explanation': 'Proportionate split of all assessment records categorized by status within the selected date range.'
    },
    'deadline_adherence_watch': {
        'title': 'Deadline Adherence',
        'description': 'Measures compliance with set deadlines, displaying assessments completed on-time, completed late, or expired.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deadline_adherence',
        'schema_explanation': 'Calculates time differences between completed_at or target deadline dates.'
    },
    'compliance_score_distribution_watch': {
        'title': 'Compliance Score Distribution',
        'description': 'Distribution of completed assessments across predefined compliance score bands (e.g., 100%, 80-99%).',
        'show_ai_icon': True,
        'chart_data': 'regwatch_compliance_score_distribution',
        'schema_explanation': 'Buckets compliance percentages into intervals to show score concentrations.'
    },
    'assessment_response_quality_watch': {
        'title': 'Assessment Response Quality',
        'description': 'Breakdown of answer status (Compliant, Non-Compliant, Unanswered) per completed assessment over time.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_assessment_trend_monthly',
        'schema_explanation': 'Tracks the average number of compliant, non-compliant, and unanswered checklist items.'
    },
    'assessments_by_regulatory_area_watch': {
        'title': 'Assessments by Regulatory Area',
        'description': 'Overview of assessments administered across different regulation segments (such as AML, Data Protection).',
        'show_ai_icon': True,
        'chart_data': 'regwatch_regulatory_area_coverage',
        'schema_explanation': 'Assessments grouped by regulatory area showing assessment volume and compliance rates.'
    },
    'repeat_assessments_watch': {
        'title': 'Repeat Assessments',
        'description': 'Identification of regulations that have undergone multiple assessment cycles, indicating periodic renewals.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_repeat_assessment_rate',
        'schema_explanation': 'Counts and lists regulations with 2 or more assessment records.'
    },
    'regulator_engagement_watch': {
        'title': 'Regulator Engagement',
        'description': 'Detailed view of assessments run under different regulatory authorities and their average compliance score.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_regulator_usage',
        'schema_explanation': 'Tracks regulator coverage, number of unique regulations, and average compliance levels.'
    },
    'low_compliance_alerts_watch': {
        'title': 'Low Compliance Alerts',
        'description': 'Real-time alert highlighting High Risk regulations where compliance levels have fallen below 80%.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_low_compliance_regulations',
        'schema_explanation': 'Filters assessments with compliance scores <80% in High Risk categories.'
    },
    'monthly_assessment_volume_deep_watch': {
        'title': 'Monthly Assessment Volume & Compliance',
        'description': 'Monthly volume and compliance score trends specifically for the selected organization.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_assessment_monthly',
        'schema_explanation': 'Filtered monthly assessment counts and average compliance score for a single organization.'
    },
    'assessment_pipeline_deep_watch': {
        'title': 'Assessment Pipeline',
        'description': 'Deadline adherence and completion speed buckets for outstanding/completed assessments in this organization.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_deadline_adherence',
        'schema_explanation': 'Pipeline tracking showing active, completed, late, and durational buckets per org.'
    },
    'compliance_score_trend_deep_watch': {
        'title': 'Compliance Score Trend',
        'description': 'Timeline of the organization\'s average compliance score compared to the target threshold (80%).',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_compliance_trend',
        'schema_explanation': 'Calculates the monthly average compliance percentage over time for the target org.'
    },
    'compliance_score_distribution_deep_watch': {
        'title': 'Compliance Score Distribution',
        'description': 'Detailed score band breakdown and item-level response quality (Compliant vs Non-Compliant) for the organization.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_compliance_score_dist',
        'schema_explanation': 'Bucketed completed assessment scores and average answer quality values.'
    },
    'low_compliance_alerts_deep_watch': {
        'title': 'Low-Compliance Alerts',
        'description': 'Targeted alerts highlighting specific high-risk regulations where the organization scored under 80%.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_low_compliance_regs',
        'schema_explanation': 'Lists regulation titles under 80% compliance for high-risk audits for the selected org.'
    },
    'compliance_improvement_deep_watch': {
        'title': 'Compliance Improvement',
        'description': 'Measures performance gains by comparing the organization\'s first score vs latest score on multi-attempt regulations.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_compliance_improvement',
        'schema_explanation': 'Calculates compliance score difference (delta) between the first and latest assessment run.'
    },
    'risk_level_profile_deep_watch': {
        'title': 'Risk Level Profile',
        'description': 'Categorizes the organization\'s assessments by regulation risk level (High, Medium, Low).',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_risk_level_profile',
        'schema_explanation': 'Grouped counts of active or completed assessments categorized by regulation risk severity.'
    },
    'regulatory_area_coverage_deep_watch': {
        'title': 'Regulatory Area Coverage',
        'description': 'Organization\'s footprint and compliance score across different regulatory areas.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_regulatory_area',
        'schema_explanation': 'Distinct counts of assessment runs and average score grouped by regulatory area.'
    },
    'regulator_engagement_deep_watch': {
        'title': 'Regulator Engagement',
        'description': 'Engagement levels and average score specifically with different regulatory authorities.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_regulator_breakdown',
        'schema_explanation': 'Aggregates assessments under this organization by their governing authority.'
    },
    'most_assessed_regulations_deep_watch': {
        'title': 'Most Assessed Regulations',
        'description': 'The specific statutory standards or regulations that this organization assesses most frequently.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_top_regulations',
        'schema_explanation': 'Ranking of regulation titles by count of runs completed under this organization.'
    },
    'assessor_performance_leaderboard_deep_watch': {
        'title': 'Assessor Performance Leaderboard',
        'description': 'Performance metrics and assessment activity counts for the organization\'s top compliance officers.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_assessor_leaderboard',
        'schema_explanation': 'Assessor performance rankings based on total started, completed, and average score.'
    },
    'monthly_activity_trend_deep_watch': {
        'title': 'Monthly Activity Trend',
        'description': 'Monthly timeline tracking assessment submissions of the top active assessors in this organization.',
        'show_ai_icon': True,
        'chart_data': 'regwatch_deep_assessor_monthly_activity',
        'schema_explanation': 'Assessor-specific monthly trend counts showing audit and review velocity.'
    }
}
