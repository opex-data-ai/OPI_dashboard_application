import os
import logging
from nicegui import ui, app, run
from fastapi import Request
from services.google_auth import get_user_info_from_code
from services.auth_service import register_google_user


from pages.login import show_login_page
from pages.overview import show_overview_page
from pages.register import show_register_page
from pages.forgot_password import show_forgot_page
from pages.change_password import show_change_password_page

from pages.product.regwatch import show_regwatch_product_page
from pages.product.regcomply import show_regcomply_product_page
from pages.product.regport import show_regport_product_page
from pages.product.home import show_product_home_page
from pages.project.project import show_projects_page
from pages.project.task import show_tasks_page
from pages.people.utilization import show_utilization_page
from pages.people.performance import show_performance_page
from pages.settings import show_settings_page
from pages.ai_insights import show_ai_insights_page
from pages.reports import show_reports_page
from components.dashboard_layout import dashboard_layout


from dotenv import load_dotenv
load_dotenv()



# Configure structured logging - trigger reload
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("opex_dashboard")

# Enforce mandatory STORAGE_SECRET
STORAGE_SECRET = os.getenv('STORAGE_SECRET')
if not STORAGE_SECRET:
    logger.critical("FATAL: STORAGE_SECRET environment variable is missing!")
    logger.critical("For security reasons, the application cannot start without a secret key.")
    logger.critical("Please set STORAGE_SECRET in your .env file or environment.")
    import sys
    sys.exit(1)

app.add_static_files('/assets', 'assets')

# Add global CSS styles for all pages with shared=True
ui.add_head_html('''
    <style>
        html, body {
            margin: 0 !important;
            padding: 0 !important;
            height: 100% !important;
        }
        #app, .nicegui-content {
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .q-page-container, .q-page {
            padding: 0 !important;
        }
        
        /* Add overflow hidden only to specific pages that need it */
        .no-scroll {
            overflow: hidden !important;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            /* Hide sidebar by default on mobile */
            .q-drawer {
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }
            
            /* Show sidebar when opened */
            .q-drawer--mobile.q-drawer--on-top {
                transform: translateX(0);
            }
            
            /* Adjust header for mobile */
            .q-header {
                padding-left: 60px !important;
            }
            
            /* Add hamburger menu button */
            .mobile-menu-btn {
                display: block !important;
            }
        }
        
        @media (min-width: 769px) {
            .mobile-menu-btn {
                display: none !important;
            }
        }
        
        /* Smooth transitions for sidebar */
        .q-drawer {
            transition: width 0.3s ease, transform 0.3s ease;
        }
        
        /* Scrollbar styling */
        .q-drawer .q-scrollarea__content::-webkit-scrollbar {
            width: 8px;
        }
        
        .q-drawer .q-scrollarea__content::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
        }
        
        .q-drawer .q-scrollarea__content::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
            transition: background 0.2s ease;
        }
        
        .q-drawer .q-scrollarea__content::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.3);
        }
    </style>
''', shared=True)

# ── Global Font & Design System ───────────────────────────────────────────
# Three-font hierarchy:
#   DM Sans         → Navigation chrome: sidebar, header bar, tab titles
#   Sora            → Page content: headings, card labels, body text
#   IBM Plex Mono   → Data values: KPI numbers, IDs, dates, table values
ui.add_head_html('''
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&family=IBM+Plex+Mono:wght@400;500;600&family=Sora:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* ════════════════════════════════════════════════════════════════
           OPEX PI HUB — GLOBAL DESIGN SYSTEM
           Font roles:
             --nav-font  DM Sans    → Sidebar, header bar, tab labels
             --ds-font   Sora       → Page content, cards, headings
             --ds-mono   IBM Plex Mono → KPI numbers, data, IDs, dates
           ════════════════════════════════════════════════════════════════ */

        :root {
            --nav-font: "DM Sans",  system-ui, sans-serif;
            --ds-font:  "Sora",     system-ui, -apple-system, sans-serif;
            --ds-mono:  "IBM Plex Mono", "DM Mono", monospace;
            --ds-text1: #0f172a;
            --ds-text2: #475569;
            --ds-text3: #64748b;
        }

        /* ── 1. Content base — Sora for all page content (no !important) ── */
        html, body {
            font-family: var(--ds-font);
            -webkit-font-smoothing: antialiased;
            color: var(--ds-text1);
        }

        /* ── 2. NAVIGATION CHROME — DM Sans ── */
        /* Sidebar drawer & popup dropdown menus */
        .q-drawer,
        .q-drawer .q-item,
        .q-drawer .q-item__label,
        .q-drawer .q-expansion-item,
        .q-drawer .q-expansion-item__content,
        .q-drawer .q-item__section,
        .q-drawer .q-btn,
        .q-drawer .q-btn__content,
        .q-menu,
        .q-menu .q-item,
        .q-menu .q-item__label {
            font-family: var(--nav-font) !important;
        }
        /* Sidebar parent nav items: medium weight, slightly spaced */
        .q-drawer .q-item__label--header,
        .q-drawer .q-expansion-item > .q-item .q-item__label {
            font-size: 13px !important;
            font-weight: 500 !important;
            letter-spacing: 0.01em !important;
        }
        /* Sidebar child items: lighter, smaller */
        .q-drawer .q-expansion-item__content .q-item__label {
            font-size: 12px !important;
            font-weight: 400 !important;
            letter-spacing: 0.005em !important;
        }
        /* Simple (non-dropdown) sidebar items */
        .q-drawer .q-item > .q-item__section--main .q-item__label {
            font-size: 13px !important;
            font-weight: 400 !important;
        }
        /* Sidebar brand label */
        .q-drawer .sidebar-brand-label {
            font-family: var(--nav-font) !important;
            font-size: 8px !important;
            font-weight: 500 !important;
            letter-spacing: 0.12em !important;
            text-transform: uppercase !important;
        }

        /* Header bar */
        .q-header,
        .q-header .q-btn,
        .q-header .q-btn__content,
        .q-header label,
        .q-header span {
            font-family: var(--nav-font) !important;
        }
        /* Header page title — DM Sans bold */
        .q-header .ds-h2 {
            font-family: var(--nav-font) !important;
            font-size: 20px !important;
            font-weight: 500 !important;
            letter-spacing: -0.01em !important;
            color: var(--ds-text1) !important;
        }
        /* Header user name */
        .q-header .nav-username {
            font-family: var(--nav-font) !important;
            font-size: 13px !important;
            font-weight: 500 !important;
        }
        /* Header user role */
        .q-header .nav-role {
            font-family: var(--nav-font) !important;
            font-size: 11px !important;
            font-weight: 300 !important;
            color: var(--ds-text3) !important;
        }

        /* Tab bars (Quasar q-tabs) */
        .q-tabs,
        .q-tab,
        .q-tab__label {
            font-family: var(--nav-font) !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            letter-spacing: 0.02em !important;
        }
        .q-tab--active .q-tab__label {
            font-weight: 600 !important;
        }

        /* ── 3. DATA VALUES — IBM Plex Mono ── */
        .ds-value, .rp-kpi-value, .ds-kpi-value {
            font-family: var(--ds-mono) !important;
            font-variant-numeric: tabular-nums;
            letter-spacing: -0.03em;
        }
        .ds-mono, .rp-mono-cell {
            font-family: var(--ds-mono) !important;
            font-size: 11px;
            letter-spacing: -0.01em;
        }

        /* ── 4. CONTENT TYPOGRAPHY — Sora ── */

        /* Page headings */
        .ds-h1 { font-size: 26px; font-weight: 700; color: var(--ds-text1); letter-spacing: -0.02em; line-height: 1.2; }
        .ds-h2 { font-size: 20px; font-weight: 600; color: var(--ds-text1); letter-spacing: -0.01em; }
        .ds-h3 { font-size: 15px; font-weight: 600; color: var(--ds-text1); }

        /* Section dividers */
        .ds-section-label, .rp-section-label {
            font-size: 10px; font-weight: 500;
            letter-spacing: 0.09em; text-transform: uppercase;
            color: var(--ds-text3);
        }

        /* Card titles & subtitles */
        .ds-card-title, .rp-card-title {
            font-size: 13px; font-weight: 600;
            color: var(--ds-text1); letter-spacing: -0.01em;
        }
        .ds-card-sub, .rp-card-sub {
            font-size: 10px; font-weight: 400; color: var(--ds-text3);
        }

        /* KPI labels */
        .ds-kpi-label, .rp-kpi-label {
            font-size: 9px; font-weight: 500;
            letter-spacing: 0.07em; text-transform: uppercase;
            color: var(--ds-text3);
        }
        /* KPI large numbers — Mono */
        .ds-kpi-value, .rp-kpi-value {
            font-family: var(--ds-mono) !important;
            font-size: 22px; font-weight: 600;
            color: var(--ds-text1); letter-spacing: -0.03em; line-height: 1;
        }
        /* KPI sub-label */
        .ds-kpi-sub, .rp-kpi-sub {
            font-size: 10px; color: var(--ds-text3);
        }

        /* Body text */
        .ds-body  { font-size: 13px; color: var(--ds-text2); line-height: 1.6; }
        .ds-small { font-size: 11px; color: var(--ds-text3); }
        .ds-tiny  { font-size: 10px; color: var(--ds-text3); letter-spacing: 0.01em; }

        /* Org header labels */
        .rp-org-name      { font-size: 18px; font-weight: 600; color: var(--ds-text1); letter-spacing: -0.01em; }
        .rp-org-meta      { font-size: 12px; font-weight: 400; color: var(--ds-text2); }
        .rp-org-meta-bold { font-size: 12px; font-weight: 600; color: var(--ds-text1); }

        /* ── 5. Table typography ── */
        .q-table th {
            font-family: var(--nav-font) !important;
            font-size: 10px !important;
            font-weight: 500 !important;
            letter-spacing: 0.07em !important;
            text-transform: uppercase !important;
            color: var(--ds-text3) !important;
        }
        .q-table td {
            font-family: var(--ds-font) !important;
            font-size: 12px !important;
            color: var(--ds-text2) !important;
        }

        /* ── 6. Global thin scrollbar ── */
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 2px; }

        /* ── 7. Global Component Tokens (Cards & Buttons) ── */
        .card-default {
            background-color: #ffffff !important;
            border: 1px solid rgba(226, 232, 240, 0.8) !important;
            border-radius: 16px !important;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
        }
        .card-elevated {
            background-color: #ffffff !important;
            border-radius: 16px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
            border: 0 !important;
        }
        .card-glass {
            background-color: rgba(255, 255, 255, 0.8) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(241, 245, 249, 0.8) !important;
            border-radius: 16px !important;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
        }

        .btn-primary {
            background-color: #6366f1 !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            text-transform: none !important;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
            transition: all 0.2s ease !important;
        }
        .btn-primary:hover {
            background-color: #4f46e5 !important;
        }
        .btn-secondary {
            background-color: #f1f5f9 !important;
            color: #334155 !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            text-transform: none !important;
            transition: all 0.2s ease !important;
        }
        .btn-secondary:hover {
            background-color: #e2e8f0 !important;
        }
        .btn-ghost {
            background-color: transparent !important;
            border: 1px solid #e2e8f0 !important;
            color: #334155 !important;
            border-radius: 12px !important;
            text-transform: none !important;
            transition: all 0.2s ease !important;
        }
        .btn-ghost:hover {
            background-color: #f8fafc !important;
        }
        .btn-danger {
            background-color: #ef4444 !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            text-transform: none !important;
            transition: all 0.2s ease !important;
        }
        .btn-danger:hover {
            background-color: #dc2626 !important;
        }
    </style>
''', shared=True)

ui.add_head_html('''
    <script src="https://cdn.jsdelivr.net/npm/echarts/dist/echarts.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/echarts/map/js/world.js"></script>
    <script>
        function downloadChart(chartId, fileName) {
            const chartElement = document.getElementById(chartId);
            if (!chartElement) {
                console.error('Chart element not found:', chartId);
                return;
            }
            const chart = echarts.getInstanceByDom(chartElement);
            if (chart) {
                const url = chart.getDataURL({
                    type: 'png',
                    pixelRatio: 2,
                    backgroundColor: '#fff',
                    excludeComponents: ['toolbox']
                });
                const link = document.createElement('a');
                link.href = url;
                link.download = fileName + '.png';
                link.click();
            } else {
                console.error('ECharts instance not found for:', chartId);
            }
        }

        function downloadPlotly(chartId, fileName) {
            const chartElement = document.getElementById(chartId);
            if (chartElement) {
                Plotly.downloadImage(chartElement, {
                    format: 'png',
                    width: 1200,
                    height: 800,
                    filename: fileName
                });
            }
        }
    </script>
''', shared=True)


@ui.page('/auth/google/callback')
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    
    # Get authorization code from query parameters
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    
    if not code:
        ui.notify('Authentication failed', color='red')
        ui.navigate.to('/login')
        return
    
    # Verify state for CSRF protection
    stored_state = app.storage.user.get('oauth_state')
    if state != stored_state:
        ui.notify('Invalid authentication state', color='red')
        ui.navigate.to('/login')
        return
    
    # Exchange code for user info
    user_info = get_user_info_from_code(code, state)
    
    if not user_info or not user_info.get('email'):
        ui.notify('Failed to get user information', color='red')
        ui.navigate.to('/login')
        return
    
    # Register or update user
    user_data = register_google_user(
        email=user_info['email'],
        first_name=user_info['first_name'],
        last_name=user_info['last_name'],
        profile_picture=user_info.get('picture')
    )
    
    if user_data.get('isActive') == 'Deactivated':
        ui.notify('Account is deactivated. Please contact support.', type='negative')
        ui.navigate.to('/login')
        return

    # Store user data in session
    app.storage.user['email'] = user_data['email']
    app.storage.user['first_name'] = user_data['first_name']
    app.storage.user['last_name'] = user_data['last_name']
    app.storage.user['role'] = user_data['role']
    app.storage.user['logged_in'] = True
    app.storage.user['auth_method'] = 'google'
    app.storage.user['isActive'] = user_data.get('isActive', 'Active')
    
    # Sync preferences from DB
    from services.auth_service import get_user_settings, get_user_notifications
    settings = await run.io_bound(get_user_settings, user_data['email'])
    notifications = await run.io_bound(get_user_notifications, user_data['email'])
    
    app.storage.user['notifications'] = notifications

    # Clear oauth state
    app.storage.user.pop('oauth_state', None)
    
    ui.notify(f'Welcome, {user_data["first_name"]}!', color='green')
    ui.navigate.to('/overview')

@ui.page('/', title='Opex Product Intelligence Hub', favicon='assets/favicon.ico')
def root_page():
    ui.navigate.to('/login')


@ui.page('/login', title='Opex Product Intelligence Hub')
def login_page():
    show_login_page()


@ui.page('/register', title='Opex Product Intelligence Hub')
def register_page():
    show_register_page()


@ui.page('/forgot', title='Opex Product Intelligence Hub')
def forgot_page():
    show_forgot_page()


@ui.page('/change_password', title='Opex Product Intelligence Hub')
def change_password_page(request: Request):
    email = request.query_params.get('email')
    show_change_password_page(email)


@ui.page('/overview', title='Opex Product Intelligence Hub')
async def overview_page():
    await show_overview_page()

@ui.page('/product/regcomply', title='Opex Product Intelligence Hub')
async def regcomply_page():
    await show_regcomply_product_page()

@ui.page('/product/regport', title='Opex Product Intelligence Hub')
async def regport_page():
    await show_regport_product_page()

@ui.page('/product/regwatch', title='Opex Product Intelligence Hub')
async def regwatch_page():
    await show_regwatch_product_page()

@ui.page('/product/home', title='Opex Product Intelligence Hub')
async def product_home_page():
    await show_product_home_page()

@ui.page('/project/project', title='Opex Product Intelligence Hub')
async def project_page():
    await show_projects_page()

@ui.page('/project/task', title='Opex Product Intelligence Hub')
async def task_page():
    await show_tasks_page()

@ui.page('/people/utilization', title='Opex Product Intelligence Hub')
async def utilization_page():
    await show_utilization_page()

@ui.page('/people/performance', title='Opex Product Intelligence Hub')
async def performance_page(): 
    await show_performance_page()

# Section Redirects
@ui.page('/product')
async def product_redirect():
    ui.navigate.to('/product/home')

@ui.page('/people')
async def people_redirect():
    ui.navigate.to('/people/utilization')

@ui.page('/project')
async def project_redirect():
    ui.navigate.to('/project/project')

@ui.page('/settings', title='Opex Product Intelligence Hub')
async def settings_page():
    await show_settings_page()

@ui.page('/ai_insights', title='Opex Product Intelligence Hub')
async def ai_insights_page():
    await show_ai_insights_page()

@ui.page('/reports', title='Opex Product Intelligence Hub')
async def reports_page(): 
    await show_reports_page()



# Handle data loading on startup
@app.on_startup
async def load_data():
    import os
    from data_engine.data_loader import get_data_loader
    
    # --- Startup Diagnostics ---
    logger.info("=" * 60)
    logger.info("STARTUP DIAGNOSTICS")
    critical_vars = ['MONGO_URI', 'STORAGE_SECRET', 'BQ_SERVICE_ACCOUNT_JSON', 'GOOGLE_CLIENT_ID', 'GOOGLE_REDIRECT_URI', 'GMAIL_TOKEN_BASE64']
    for var in critical_vars:
        val = os.getenv(var)
        if val:
            logger.info(f"  ✅ {var} = SET ({len(val)} chars)")
        else:
            logger.warning(f"  ❌ {var} = NOT SET")
    logger.info("=" * 60)
    
    # Test MongoDB connection
    from services.auth_service import get_db
    try:
        get_db().command('ping')
        logger.info("MongoDB connected successfully")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")

    # Load Drive data into DuckDB
    try:
        loader = get_data_loader()
        


        result = loader.load_all_data()
        
        # Report what tables were loaded
        try:
            tables = loader.con.execute("SHOW TABLES").fetchdf()
            table_list = tables['name'].tolist() if not tables.empty else []
            data_tables = [t for t in table_list if not t.startswith('_')]
            if data_tables:
                logger.info(f"DuckDB loaded {len(data_tables)} table(s): {data_tables}")
            else:
                logger.error(
                    "DuckDB has NO data tables after startup! "
                    "Dashboard queries will all fail. "
                    "Check that BQ_SERVICE_ACCOUNT_JSON is set correctly on Render."
                )
        except Exception as e:
            logger.error(f"Could not inspect DuckDB tables: {e}")
            
        logger.info("Startup data load completed")
    except Exception as e:
        logger.error(f"Error during startup data load: {e}")

@app.on_shutdown
def shutdown():
    from data_engine.data_loader import get_data_loader
    print("Application shutting down... closing connections")
    try:
        loader = get_data_loader()
        loader.close()
        print("Connections closed successfully")
    except Exception as e:
        print(f"Error during shutdown: {e}")

ui.run(
    host='0.0.0.0',
    port=8080,
    storage_secret=STORAGE_SECRET,
    favicon='assets/favicon.ico',
    reload=True
)