# pages/ai_insights.py (No template - custom layout)
from nicegui import ui
from components.dashboard_layout import dashboard_layout

async def show_ai_insights_page():
    async def content():
        ui.label('AI Insights').classes('text-3xl font-bold text-slate-900 mb-2')
        ui.label('This page is still in development').classes('text-slate-600')
    await dashboard_layout(content, page_title="AI Insights", active_page="ai-insights")
