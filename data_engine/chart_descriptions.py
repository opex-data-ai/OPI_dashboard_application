"""
Central dictionary for metric descriptions used in dashboard cards.
"""

METRIC_INFO = {
    # KPI Metrics
    'active_org_rate':{
        'title': 'Active Organization Rate',
        'description': 'Percentage of active organizations out of total organizations',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Calculated as (active_orgs / total_orgs) * 100. Measures the proportion of active organizations."
    },
    'active_users_rate':{
        'title': 'Active Users Rate',
        'description': 'Percentage of active users out of total users',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Calculated as (active_users / total_users) * 100. Measures the proportion of active users."
    },
        'anonymous_users_rate': {
        'title': 'Anonymous User Rate',
        'description': 'The percentage of visitors who did not sign in out of the total number of unique visitors',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Calculated as (total_users - signed_in_users) / total_users. Measures the proportion of unauthenticated traffic."
    },

    'active_org_count': {
        'title': 'Active Organizations',
        'description': 'Number of unique organizations that had at least one session during the selected time period.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Count of unique organization_id from the 'sessions' table, representing distinct enterprise clients active in the period."
    },
    'active_signed_in_users': {
        'title': 'Active Signed-In Users',
        'description': 'Count of unique users who were logged into their accounts during the period.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Count of unique user_id where user_id is not null, representing the registered user base activity."
    },
    'engagement_rate': {
        'title': 'Engagement Rate',
        'description': 'Percentage of total sessions that were engaging (lasting longer than 10 seconds, having a conversion event, or at least 2 page views).',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Ratio of 'engaged_sessions' to 'total_sessions'. Engagement is defined by GA4 standards (time > 10s, 2+ page views, or 1+ conversion)."
    },
    'avg_pages_session': {
        'title': 'Avg Pages / Session',
        'description': 'Indicates how many pages users open within a single session.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Total pageviews divided by total sessions. Higher values typically indicate better content relevance or deeper site exploration."
    },
    'avg_time_signup': {
        'title': 'Avg Time to Signup',
        'description': 'Average cumulative engagement time of a user before completing their first signup.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Total engagement time (milliseconds) across all sessions before a 'signup_complete' event, averaged per user."
    },
    'landing_exit_rate': {
        'title': 'Landing Page Exit Rate',
        'description': 'Percentage of sessions that start and end on the same page, with no further navigation.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Percentage of sessions where the landing page was also the exit page. High rates may suggest landing page optimization needs."
    },

    # Charts
    'user_acquisition_trend': {
        'title': 'User Acquisition Trend',
        'description': 'Daily tracking of active sessions, broken down by signed-in users and anonymous visitors.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Time-series data with columns 'date' (YYYY-MM-DD), 'signed_in_sessions', and 'anonymous_sessions'. Shows the mix of user types over time."
    },
    'map_distribution': {
        'title': 'Geographic Distribution',
        'description': 'Global map of where visitors are coming from',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "DataFrame with 'country' name and 'total_visitors'. Measures international adoption."
    },
    'country_breakdown': {
        'title': 'Country Breakdown',
        'description': 'Top countries ranked by visitor count',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "DataFrame with 'country' name and 'total_visitors'. Measures international adoption."
    },
    'traffic_source': {
        'title': 'Traffic Source Analysis',
        'description': 'Analysis of where traffic originates',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "DataFrame with 'source' (e.g. google, direct) and 'session_count'. Identifies high-performing marketing channels."
    },
    'traffic_medium': {
        'title': 'Traffic Medium',
        'description': 'Analysis of how traffic reaches the platform',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "DataFrame with 'medium' (e.g. organic, email, cpc), and 'session_count'. Identifies high-performing marketing channels."
    },
    'stickiness_ratios': {
        'title': 'User Stickiness',
        'description': 'Ratios of Daily (DAU) to Weekly (WAU) and Monthly (MAU) active users, indicating platform retention.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Comparison of DAU/MAU and DAU/WAU percentages. Values above 20% are generally considered healthy for B2B SaaS."
    },
    'engaged_vs_churned': {
        'title': 'Engaged vs Churned',
        'description': 'Comparative analysis of behavior patterns between users who remain active and those who stop returning.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Bucketed user counts: 'highly_engaged' (3+ sessions/week), 'returning', and 'churn_risk' (no activity in 14 days)."
    },
    'funnel_analysis': {
        'title': 'Funnel Analysis',
        'description': 'Visualizing the progression of users from landing pages to key functional modules.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Sequence of events: 'page_view' -> 'module_click' -> 'data_engagement' -> 'conversion'. Shows drop-off at each stage."
    },
    'user_journeys': {
        'title': 'High-Engagement Journeys',
        'description': 'Common navigation paths taken by users who show high levels of platform interaction.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Transition paths between pages. 'conversion_path' shows the sequence of URLs, 'user_pct' is the share of users following that path."
    },
    'page_engagement': {
        'title': 'Page Performance',
        'description': 'Detailed engagement metrics, scroll depth, and interaction counts for individual platform pages.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Metrics per URL: 'avg_scroll_depth', 'button_clicks', and 'avg_time_on_page'. Identifies content friction points."
    },
    'org_engagement': {
        'title': 'Organization Engagement',
        'description': 'Aggregated engagement behavior for specific enterprise accounts and organizations.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "Totals grouped by organizationDomain. Measures account-level activity and health.",
        'has_pii': True,
        'pii_columns': ['organizationName']
    },
    
    # Ecosystem / Home Page Metrics
    'ecosystem_orgs': {
        'title': 'Total Ecosystem Organizations',
        'description': 'The total number of unique organizations registered across all platforms in the ecosystem.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Sum of distinct organization counts across all product databases (RegWatch, RegPort, etc.)."
    },
    'ecosystem_users': {
        'title': 'Total Ecosystem Users',
        'description': 'The total count of unique users registered across all platforms in the ecosystem.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Sum of distinct user counts across all product databases."
    },
    'ecosystem_platforms': {
        'title': 'Total Platforms',
        'description': 'The number of active product platforms currently integrated into the monitoring dashboard.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Metric showing the footprint of the enterprise suite."
    },
    'multi_platform_rate': {
        'title': 'Multi-platform Adoption Rate',
        'description': 'The percentage of organizations that are active on more than one platform.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Count of orgs present in 2+ platform tables / total unique orgs."
    },
    'full_ecosystem_rate': {
        'title': 'Full Ecosystem Adoption Rate',
        'description': 'The percentage of organizations that have adopted and are active on all available platforms.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Count of orgs present in ALL platform tables / total unique orgs."
    },
    'org_breakdown': {
        'title': 'Platform Organization Breakdown',
        'description': 'Comparison of direct organization counts across different platforms.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "DataFrame with 'platform' and 'total_orgs'. Vertically compares product reach."
    },
    'user_breakdown': {
        'title': 'Platform User Breakdown',
        'description': 'Comparison of unique user counts across different platforms.',
        'show_ai_icon': True,
        'chart_data': None,
        'schema_explanation': "DataFrame with 'platform' and 'total_users'. Vertically compares product usage."
    },
    
    # Dashboard Overview Metrics
    'overview_revenue': {
        'title': 'Total Revenue',
        'description': 'Aggregated revenue across all product lines and services for the current period.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Unified billing data summed across all active subscriptions."
    },
    'overview_projects': {
        'title': 'Active Projects',
        'description': 'Total number of client projects and internal initiatives currently in progress.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Count of projects with status != 'Completed' or 'Cancelled'."
    },
    'overview_utilization': {
        'title': 'Team Utilization',
        'description': 'Average percentage of team capacity currently allocated to active projects.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Average of individual utilization rates (billable_hours / total_capacity)."
    },
    'overview_score': {
        'title': 'Performance Score',
        'description': 'Composite metric evaluating efficiency, quality, and delivery speed across the organization.',
        'show_ai_icon': False,
        'chart_data': None,
        'schema_explanation': "Weighted average of revenue, utilization, and project health scores."
    }
}
