# pages/ai_insights.py — AI Chat Assistant (V1)
from nicegui import ui, app, run
from components.dashboard_layout import dashboard_layout
from components.theme_manager import ThemeManager
import logging
import pandas as pd

logger = logging.getLogger(__name__)


async def show_ai_insights_page():
    async def content():
        from ai_engine.chat_assistant import ask as chat_ask

        # ── State ─────────────────────────────────────────────
        chat_history = []  # list of {"role": "user"|"assistant", "content": str, "sql": str|None, "data": list|None}

        # ── Header ────────────────────────────────────────────
        with ui.row().classes('w-full items-center justify-between mb-6'):
            with ui.column().classes('gap-0'):
                ui.label('AI Data Assistant').classes('text-2xl font-bold text-slate-900')
                ui.label('Ask questions about your data in plain English').classes('text-sm text-slate-500')
            with ui.row().classes('items-center gap-2'):
                ui.icon('smart_toy').classes('text-purple-600 text-2xl')

        # ── Chat Container ────────────────────────────────────
        chat_container = ui.column().classes(
            'w-full rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden'
        ).style('max-width: 960px; min-height: 520px;')

        with chat_container:
            # Messages area
            messages_area = ui.scroll_area().classes('w-full px-6 py-4').style('height: 460px;')
            with messages_area:
                messages_column = ui.column().classes('w-full gap-4')

                # Welcome message
                with messages_column:
                    _render_assistant_message(
                        "👋 Hi! I'm your data assistant. Ask me anything about the dashboard data — "
                        "for example:\n\n"
                        "• *How many organizations are on each platform?*\n"
                        "• *What is the total number of users?*\n"
                        "• *Which platform has the highest engagement?*",
                        sql=None, data=None
                    )

            # ── Divider ───────────────────────────────────────
            ui.separator().classes('m-0')

            # ── Input Bar ─────────────────────────────────────
            with ui.row().classes('w-full items-center gap-3 px-4 py-3 bg-slate-50'):
                text_input = ui.input(
                    placeholder='Ask a question about your data...',
                ).props('outlined dense borderless').classes(
                    'flex-grow text-sm'
                ).style('font-size: 14px;')

                send_button = ui.button(icon='send', on_click=lambda: handle_send()).props(
                    'round flat size=md'
                ).classes('text-purple-600 hover:bg-purple-50 transition-colors')

        # ── Handlers ──────────────────────────────────────────
        async def handle_send():
            question = text_input.value
            if not question or not question.strip():
                return

            text_input.value = ''
            question = question.strip()

            # Add user message
            with messages_column:
                _render_user_message(question)

            messages_area.scroll_to(percent=1.0)
            await ui.run_javascript('void(0)')  # Force UI update

            # Show loading
            with messages_column:
                thinking_row = ui.row().classes('w-full justify-start')
                with thinking_row:
                    with ui.card().classes('px-4 py-2 rounded-2xl bg-slate-100 shadow-none border-0'):
                        with ui.row().classes('items-center gap-2'):
                            ui.spinner(size='sm', color='purple-600')
                            ui.label('Thinking...').classes('text-sm text-slate-500 italic')

            messages_area.scroll_to(percent=1.0)

            # Call AI backend
            try:
                result = await run.io_bound(chat_ask, question)
                logger.info(f"Chat response received. Has SQL: {result.get('sql') is not None}, Has data: {result.get('data') is not None}")
            except Exception as e:
                logger.error(f"Chat assistant call failed: {e}")
                result = {
                    "answer": "Sorry, I encountered an error. Please try again.",
                    "sql": None,
                    "data": None,
                    "error": str(e)
                }

            # Remove thinking indicator
            thinking_row.delete()

            # Render assistant response
            with messages_column:
                _render_assistant_message(
                    result.get("answer", "No answer available."),
                    sql=result.get("sql"),
                    data=result.get("data")
                )

            messages_area.scroll_to(percent=1.0)

        # Allow Enter key to send
        text_input.on('keydown.enter', handler=lambda: handle_send())

    await dashboard_layout(content, page_title="AI Insights", active_page="ai-insights")


# ── Render Helpers (module-level) ────────────────────────────────

def _render_user_message(text: str):
    """Render a user chat bubble (right-aligned)."""
    with ui.row().classes('w-full justify-end'):
        ui.label(text).classes(
            'px-4 py-2.5 rounded-2xl text-sm text-white bg-purple-600 shadow-sm'
        ).style('max-width: 75%; word-wrap: break-word;')


def _render_assistant_message(text: str, sql: str = None, data: list = None):
    """Render an assistant chat bubble (left-aligned) with optional SQL and data table."""
    with ui.row().classes('w-full justify-start'):
        with ui.column().classes('gap-2').style('max-width: 80%;'):
            # Main answer
            with ui.card().classes('px-4 py-3 rounded-2xl shadow-none border border-slate-200 bg-slate-50'):
                ui.markdown(text).classes('text-sm text-slate-800 leading-relaxed')

            # SQL expandable (if available)
            if sql:
                with ui.expansion('View generated SQL', icon='code').classes(
                    'w-full text-xs text-slate-500'
                ).props('dense'):
                    ui.code(sql, language='sql').classes('text-xs w-full')

            # Data table (if available and small enough)
            if data and len(data) > 0:
                with ui.expansion(f'View data ({len(data)} rows)', icon='table_chart').classes(
                    'w-full text-xs text-slate-500'
                ).props('dense'):
                    columns = [{'name': k, 'label': k, 'field': k, 'align': 'left', 'sortable': True} for k in data[0].keys()]
                    # Convert any non-serializable values to strings
                    clean_data = []
                    for row in data:
                        clean_row = {}
                        for k, v in row.items():
                            clean_row[k] = str(v) if v is not None else ''
                        clean_data.append(clean_row)
                    ui.table(columns=columns, rows=clean_data, row_key=columns[0]['name']).classes(
                        'w-full text-xs'
                    ).props('dense flat bordered')
