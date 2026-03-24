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
from pages.landing import show_landing_page
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

# Configure structured logging
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

@ui.page('/', title='Opex Consulting Dashboard', favicon='💼')
def landing_page():
    show_landing_page()


@ui.page('/login')
def login_page():
    show_login_page()


@ui.page('/register')
def register_page():
    show_register_page()


@ui.page('/forgot')
def forgot_page():
    show_forgot_page()


@ui.page('/change_password')
def change_password_page(request: Request):
    email = request.query_params.get('email')
    show_change_password_page(email)


@ui.page('/overview')
async def overview_page():
    await show_overview_page()

@ui.page('/product/regcomply')
async def regcomply_page():
    await show_regcomply_product_page()

@ui.page('/product/regport')
async def regport_page():
    await show_regport_product_page()

@ui.page('/product/regwatch')
async def regwatch_page():
    await show_regwatch_product_page()

@ui.page('/product/home')
async def product_home_page():
    await show_product_home_page()

@ui.page('/project/project')
async def project_page():
    await show_projects_page()

@ui.page('/project/task')
async def task_page():
    await show_tasks_page()

@ui.page('/people/utilization')
async def utilization_page():
    await show_utilization_page()

@ui.page('/people/performance')
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

@ui.page('/settings')
async def settings_page():
    await show_settings_page()

@ui.page('/ai_insights')
async def ai_insights_page():
    await show_ai_insights_page()

@ui.page('/reports')
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
    reload=True
)