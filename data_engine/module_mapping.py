PLATFORM_MODULE_MAPPING = {
    'RegComply': {
        'Landing':       {'pattern': '%/', 'is_module': False, 'is_landing': True},
        'Login':      {'pattern': '%/login',           'is_module': False, 'is_landing': True},
        'Book Demo':  {'pattern': '%/book-a-demo',     'is_module': False, 'is_landing': True},
        'Organization - Dashboard':  {'pattern': '%/dashboard%',       'is_module': False, 'is_landing': True},
        'Organization - Risk Management': {'pattern': '%/risk-management%', 'is_module': True, 'is_landing': False},
        'Organization - Task Management': {'pattern': '%/task-management%', 'is_module': True, 'is_landing': False},
        'Organization - Document Management':    {'pattern': '%/document-management%', 'is_module': True, 'is_landing': False},
        'Organization - Compliance Framework':   {'pattern': '%/compliance/frameworks%', 'is_module': True, 'is_landing': False},
        'Organization - Compliance Audit':   {'pattern': '%/compliance/audit%', 'is_module': True, 'is_landing': False},
        'Organization - Compliance CSAT':   {'pattern': '%/compliance/csat%', 'is_module': True, 'is_landing': False},
        'Organization - My Organization':   {'pattern': '%/my-organization%', 'is_module': True, 'is_landing': False},
        'Organization - Settings':   {'pattern': '%/settings%', 'is_module': False, 'is_landing': False},
        'Audit Firm - Dashboard': {'pattern': '%/firm', 'is_module': False, 'is_landing': True},
        'Audit Firm - Incoming Audit Requests': {'pattern': '%/firm/incoming-requests%', 'is_module': True, 'is_landing': False},
        'Audit Firm - Ongoing Audits': {'pattern': '%/firm/ongoing-audits%', 'is_module': True, 'is_landing': False},
        'Audit Firm - Team Management': {'pattern': '%/firm/teams%', 'is_module': True, 'is_landing': False},
        'Audit Firm - CBN Audit': {'pattern': '%/firm/cbn-audits%', 'is_module': True, 'is_landing': False},
        'Audit Firm - Task Management': {'pattern': '%/firm/tasks%', 'is_module': True, 'is_landing': False},
        'Audit Firm - CSAT': {'pattern': '%/firm/csat%', 'is_module': True, 'is_landing': False},
    },
    'RegWatch': {
        'Landing': {'pattern': '%/', 'is_module': False, 'is_landing': True},
        'Login': {'pattern': '%/sign-in', 'is_module': False, 'is_landing': True},
        'Register': {'pattern': '%/sign-up', 'is_module': False, 'is_landing': True},
        'Dashboard': {'pattern': '%/dashboard', 'is_module': False, 'is_landing': True},
        'Pre-Assessement': {'pattern': '%/assessment%', 'is_module': True, 'is_landing': False},
        'RegWatch AI': {'pattern': '%/chatbot-ai%', 'is_module': True, 'is_landing': False},
        'Notification': {'pattern': '%/notifications%', 'is_module': True, 'is_landing': False},
        'Regulation': {'pattern': '%/regulations-page%', 'is_module': True, 'is_landing': False},
    },
    'RegPort': {
        'Landing': {'pattern': '%/', 'is_module': False, 'is_landing': True},
        'Login': {'pattern': '%/sign-in%', 'is_module': False, 'is_landing': True},
        'Register': {'pattern': '%sign-up%', 'is_module': False, 'is_landing': True},
        'Transaction Monitoring Dashboard':{'pattern': '%/dashboard%', 'is_module': False, 'is_landing': True},
        'Flagged Transactions': {'pattern': '%/transactions%', 'is_module': True, 'is_landing': False},
        'Case Management': {'pattern': '%/cases%', 'is_module': True, 'is_landing': False},
        'Reports': {'pattern': '%/reports%', 'is_module': True, 'is_landing': False},
        'Customer Verification': {'pattern': '%/kyc-kyb%', 'is_module': True, 'is_landing': False},
        'CDD Screening': {'pattern': '%/cdd%', 'is_module': True, 'is_landing': False},
        'Risk Aggregator': {'pattern': '%/risk-simulator%', 'is_module': True, 'is_landing': False},
        'Audit Trail': {'pattern': '%/audit-trail%', 'is_module': True, 'is_landing': False},
        'Notification': {'pattern': '%/notifications%', 'is_module': False, 'is_landing': True},
        'Developer Documentation': {'pattern': '%/documentations%', 'is_module': False, 'is_landing': True},
        'Pricing': {'pattern': '%/price%', 'is_module': False, 'is_landing': False},
        'Support': {'pattern': '%/support%', 'is_module': False, 'is_landing': False},
        'Profile - Company Profile': {'pattern': '%/profile/company-profile%', 'is_module': False, 'is_landing': False},
        'Profile - Team Invitation': {'pattern': '%/profile/team-access%', 'is_module': False, 'is_landing': False},
        'Settings - Data Integration (API/Batch Upload)': {'pattern': '%/settings/data-integration%', 'is_module': True, 'is_landing': False},
        'Settings - Monitoring Rules': {'pattern': '%/settings/monitoring-rules%', 'is_module': True, 'is_landing': False},
        'Settings - Data Retention & Privacy': {'pattern': '%/settings/data-retention%', 'is_module': False, 'is_landing': False},
        'Settings - Regulatory Reporting Setup': {'pattern': '%/settings/regulatory-setup%', 'is_module': False, 'is_landing': False},
        'Settings - Alerts & Notifications': {'pattern': '%/settings/alerts%', 'is_module': False, 'is_landing': False},
        'Settings - Screening Data Config': {'pattern': '%/settings/screening-config%', 'is_module': False, 'is_landing': False},
        'Settings - Data Retention & Privacy': {'pattern': '%/settings/data-retention%', 'is_module': False, 'is_landing': False}
        },
}

import re

def map_path_to_module(path, platform):
    """
    Map a page path to a module name based on the PLATFORM_MODULE_MAPPING.
    If is_module is True for a matching pattern, returns the module name.
    Otherwise, returns None.
    """
    if not path or not isinstance(path, str):
        return None
        
    platform_mapping = PLATFORM_MODULE_MAPPING.get(platform, {})
    
    for label, info in platform_mapping.items():
        if not info.get('is_module'):
            continue
            
        pattern = info.get('pattern', '')
        # Strip hostname from pattern if it exists to match path-only strings
        clean_pattern = re.sub(r'^%?[^/]+/', '/', pattern) if '/' in pattern else pattern
        regex_pattern = clean_pattern.replace('%', '.*')
        
        try:
            if re.match(f"^{regex_pattern}$", path, re.IGNORECASE):
                return label
        except re.error:
            continue
            
    return None

def map_path_to_landing(path, platform):
    """
    Map a page path to its raw structure if it is a valid landing page.
    If is_landing is True for a matching pattern, returns the original path.
    Otherwise, returns None.
    """
    if not path or not isinstance(path, str):
        return None
        
    platform_mapping = PLATFORM_MODULE_MAPPING.get(platform, {})
    
    for label, info in platform_mapping.items():
        if not info.get('is_landing'):
            continue
            
        pattern = info.get('pattern', '')
        # Clean pattern and convert to regex
        clean_pattern = re.sub(r'^%?[^/]+/', '/', pattern) if '/' in pattern else pattern
        regex_pattern = clean_pattern.replace('%', '.*')
        
        try:
            if re.match(f"^{regex_pattern}$", path, re.IGNORECASE):
                return path  # Return the raw path
        except re.error:
            continue
            
    return None