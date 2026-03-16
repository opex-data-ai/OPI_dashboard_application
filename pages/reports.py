# pages/reports.py (No template - custom layout)
from nicegui import ui
from components.dashboard_layout import dashboard_layout
from components.theme_manager import ThemeManager

async def show_reports_page():
    async def content():
        ui.label('Reports').classes(ThemeManager.TYPOGRAPHY['h1'].replace('text-4xl', 'text-3xl') + ' mb-2')
        ui.label('This page is still in development').classes(ThemeManager.TYPOGRAPHY['body'])
    await dashboard_layout(content, page_title="Reports", active_page="reports")

