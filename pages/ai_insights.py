# pages/ai_insights.py — AI Analyst (Ask the Data) — V2
# Full redesign: dual-sidebar, persistent chat history, conversation-aware, sleek dark UI
from nicegui import ui, app, run
from components.dashboard_layout import dashboard_layout
from components.theme_manager import ThemeManager
import logging

logger = logging.getLogger(__name__)

# ─── Suggested question hints ────────────────────────────────────
QUESTION_HINTS = [
    "Which platform has the highest user base?",
    "Show me monthly growth trend for RegComply",
    "Top 10 most active organisations",
    "What is the average session duration?",
    "Which organisations have not logged in for 30 days?",
    "Compare active users across all platforms",
    "What is the feature adoption rate by platform?",
    "Show churned organisations this quarter",
]


async def show_ai_insights_page():
    async def content():
        from ai_engine.chat_assistant import ask as chat_ask
        from ai_engine.chat_history import (
            get_all_sessions, get_or_create_today_session,
            create_new_session, get_messages, append_message,
            delete_session, rename_session, build_conversation_context
        )

        # ── Inject custom styles ──────────────────────────────────
        ui.add_head_html("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

        /* ── Chat History Sidebar ── */
        .ai-history-sidebar {
            position: fixed;
            top: 60px;
            left: 260px;
            height: calc(100vh - 60px);
            width: 260px;
            background: #ffffff;
            border-right: 1px solid #e2e8f0;
            z-index: 100;
            display: flex;
            flex-direction: column;
            transition: transform 0.3s cubic-bezier(0.4,0,0.2,1), width 0.3s ease;
            box-shadow: 2px 0 8px rgba(0,0,0,0.06);
            overflow: hidden;
        }
        .ai-history-sidebar.collapsed {
            transform: translateX(-224px);
        }
        .ai-history-sidebar.sidebar-main-collapsed {
            left: 80px;
        }

        /* ── Main content shift ── */
        .ai-main-content {
            transition: margin-left 0.3s cubic-bezier(0.4,0,0.2,1);
        }

        /* ── Chat bubble styles ── */
        .chat-user-bubble {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            border-radius: 18px 18px 4px 18px;
            padding: 12px 16px;
            max-width: 72%;
            word-break: break-word;
            font-size: 14px;
            line-height: 1.6;
            box-shadow: 0 2px 8px rgba(99,102,241,0.25);
        }
        .chat-ai-bubble {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 4px 18px 18px 18px;
            padding: 14px 18px;
            max-width: 78%;
            word-break: break-word;
            font-size: 14px;
            line-height: 1.7;
            color: #1e293b;
        }
        .chat-ts {
            font-size: 10px;
            color: #94a3b8;
            margin-top: 4px;
            font-family: 'DM Mono', monospace;
        }

        /* ── Input area ── */
        .ai-input-wrapper {
            background: white;
            border: 1.5px solid #e2e8f0;
            border-radius: 14px;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }
        .ai-input-wrapper:focus-within {
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99,102,241,0.12);
        }

        /* ── Hint chips ── */
        .hint-chip {
            background: #f1f5f9;
            border: 1px solid #e2e8f0;
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 12px;
            color: #475569;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
            font-family: 'DM Sans', sans-serif;
            font-weight: 500;
        }
        .hint-chip:hover {
            background: #ede9fe;
            border-color: #c4b5fd;
            color: #5b21b6;
            transform: translateY(-1px);
        }

        /* ── Session items ── */
        .session-item {
            padding: 10px 14px;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.15s ease;
            font-size: 13px;
            color: #334155;
        }
        .session-item:hover { background: #f1f5f9; }
        .session-item.active {
            background: #ede9fe;
            color: #5b21b6;
            font-weight: 600;
        }

        /* ── Thinking animation ── */
        @keyframes pulse-dot {
            0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
            40% { transform: scale(1); opacity: 1; }
        }
        .thinking-dot {
            width: 7px; height: 7px; border-radius: 50%;
            background: #6366f1; display: inline-block; margin: 0 2px;
            animation: pulse-dot 1.4s infinite ease-in-out;
        }
        .thinking-dot:nth-child(2) { animation-delay: 0.2s; }
        .thinking-dot:nth-child(3) { animation-delay: 0.4s; }

        /* ── Disclaimer badge ── */
        .disclaimer-badge {
            background: #fef9c3;
            border: 1px solid #fde047;
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 11px;
            color: #713f12;
            font-family: 'DM Sans', sans-serif;
        }
        </style>
        """)

        # ── State ─────────────────────────────────────────────────
        state = {
            'session_id': get_or_create_today_session(),
            'history_collapsed': False,
            'main_sidebar_collapsed': app.storage.user.get('sidebar_collapsed', False),
        }

        # ─── Forward declarations of layout variables ─────────────
        messages_column = None
        messages_scroll = None
        text_input = None
        send_btn = None

        # ─── Load existing messages from session ──────────────────
        def reload_messages():
            if messages_column is None:
                return
            try:
                messages_column.clear()
                with messages_column:
                    _render_welcome(set_hint)
                    sid = state['session_id']
                    msgs = get_messages(sid)
                    for msg in msgs:
                        role = msg.get('role')
                        content = msg.get('content')
                        if role == 'user':
                            _render_user_message(content, msg.get('ts', ''))
                        else:
                            _render_ai_message(
                                content,
                                sql=msg.get('sql'),
                                data=msg.get('data'),
                                ts=msg.get('ts', '')
                            )
            except Exception as e:
                import traceback
                logger.error(f"Exception in reload_messages: {e}\n{traceback.format_exc()}")

        def set_hint(hint_text: str):
            if text_input:
                text_input.value = hint_text
                text_input.run_method('focus')

        def start_new_session():
            try:
                sid = create_new_session()
                state['session_id'] = sid
                reload_messages()
                refresh_sessions_list()
            except Exception as e:
                import traceback
                logger.error(f"start_new_session failed: {e}\n{traceback.format_exc()}")

        # ─── Send handler ─────────────────────────────────────────
        async def handle_send():
            try:
                question = (text_input.value or '').strip() if text_input else ''
                if not question:
                    return
                if text_input:
                    text_input.value = ''

                # Save & render user message
                append_message(state['session_id'], 'user', question)
                
                with messages_column:
                    from datetime import datetime
                    ts = datetime.now().strftime('%H:%M')
                    _render_user_message(question, ts)

                if messages_scroll:
                    messages_scroll.run_method('scrollTo', {'top': 1000000, 'behavior': 'smooth'})

                # Thinking indicator
                thinking_row = None
                with messages_column:
                    thinking_row = ui.row().classes('w-full justify-start items-end gap-2')
                    with thinking_row:
                        with ui.element('div').classes(
                            'px-4 py-3 rounded-2xl bg-slate-100 border border-slate-200'
                        ).style('border-radius: 4px 18px 18px 18px;'):
                            with ui.row().classes('items-center gap-1'):
                                ui.html('<span class="thinking-dot"></span><span class="thinking-dot"></span><span class="thinking-dot"></span>')
                                ui.label('Analysing...').classes('text-xs text-slate-400 ml-2 italic')

                if messages_scroll:
                    messages_scroll.run_method('scrollTo', {'top': 1000000, 'behavior': 'smooth'})

                # Build conversation context from history
                history_msgs = get_messages(state['session_id'])
                context = build_conversation_context(history_msgs[:-1])

                # Call AI backend
                result = await run.io_bound(chat_ask, question, context)

                # Remove thinking indicator
                if thinking_row:
                    thinking_row.delete()

                # Print AI response and received output in the terminal
                print("\n" + "="*50)
                print("🤖 RECEIVED AI ENGINE OUTPUT:")
                print(f"Result Status: {'success' if result else 'failed'}")
                print(f"Formulated SQL: {result.get('sql')}")
                if result.get('data') is not None:
                    print(f"Data Retrieved: {len(result.get('data'))} rows")
                else:
                    print("Data Retrieved: None")
                print(f"Error (if any): {result.get('error')}")
                print("-"*50)
                print("💬 AI RESPONSE TEXT:")
                print(result.get("answer", "No answer available."))
                print("="*50 + "\n", flush=True)

                answer = result.get("answer", "No answer available.")
                sql = result.get("sql")
                data = result.get("data")

                # Save AI response
                append_message(state['session_id'], 'assistant', answer, sql=sql, data=data)
                refresh_sessions_list()

                with messages_column:
                    from datetime import datetime
                    ts = datetime.now().strftime('%H:%M')
                    _render_ai_message(answer, sql=sql, data=data, ts=ts)

                if messages_scroll:
                    messages_scroll.run_method('scrollTo', {'top': 1000000, 'behavior': 'smooth'})
            except Exception as e:
                import traceback
                logger.error(f"Exception in handle_send: {e}\n{traceback.format_exc()}")
                
                # Cleanup thinking row
                try:
                    if thinking_row:
                        thinking_row.delete()
                except Exception:
                    pass
                    
                with messages_column:
                    ui.label(f"Error formulating response: {e}").classes('text-red-500 text-xs italic')

        # ── Compute layout margins ─────────────────────────────────
        def get_left_margin():
            main_w = 80 if state['main_sidebar_collapsed'] else 260
            hist_w = 36 if state['history_collapsed'] else 260
            return main_w + hist_w

        # ── Root container (full page) ────────────────────────────
        page_wrapper = ui.element('div').style(
            f'margin-left: {get_left_margin()}px; '
            'transition: margin-left 0.3s cubic-bezier(0.4,0,0.2,1); '
            'min-height: calc(100vh - 60px); display: flex; flex-direction: column;'
        )

        # ═══════════════════════════════════════════════════════════
        #  CHAT HISTORY SIDEBAR
        # ═══════════════════════════════════════════════════════════
        main_collapsed_cls = 'sidebar-main-collapsed' if state['main_sidebar_collapsed'] else ''
        history_sidebar = ui.element('div').classes(
            f'ai-history-sidebar {main_collapsed_cls}'
        )

        sessions_container = None   # will be populated below

        def refresh_sessions_list():
            nonlocal sessions_container
            if sessions_container is None:
                return
            sessions_container.clear()
            all_sessions = get_all_sessions()
            with sessions_container:
                if not all_sessions:
                    ui.label('No previous chats').classes('text-xs text-slate-400 px-4 py-3 italic')
                for s in all_sessions:
                    is_active = s['id'] == state['session_id']
                    with ui.row().classes(
                        f'session-item {"active" if is_active else ""} w-full items-center justify-between gap-1'
                    ).on('click', lambda sid=s['id']: switch_session(sid)):
                        with ui.column().classes('gap-0 flex-1 min-w-0'):
                            ui.label(s['label']).classes(
                                'text-xs font-semibold truncate'
                                + (' text-violet-700' if is_active else ' text-slate-700')
                            )
                            msg_count = len(s['messages'])
                            ui.label(f"{msg_count // 2} exchange{'s' if msg_count // 2 != 1 else ''}").classes(
                                'text-[10px] text-slate-400'
                            )
                        if not is_active:
                            ui.button(icon='delete_outline', on_click=lambda sid=s['id']: do_delete_session(sid)) \
                                .props('flat round size=xs').classes('text-slate-300 hover:text-red-400')

        def do_delete_session(sid: str):
            delete_session(sid)
            if state['session_id'] == sid:
                state['session_id'] = get_or_create_today_session()
                reload_messages()
            refresh_sessions_list()

        def switch_session(sid: str):
            state['session_id'] = sid
            reload_messages()
            refresh_sessions_list()

        with history_sidebar:
            # Header bar
            with ui.row().classes('w-full items-center justify-between px-3 py-3 border-b border-slate-100'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('history').classes('text-violet-500 text-lg')
                    ui.label('Chat History').classes('text-xs font-bold text-slate-700 uppercase tracking-wider')
                # Collapse toggle
                history_toggle_btn = ui.button(icon='chevron_left', on_click=lambda: toggle_history_sidebar()) \
                    .props('flat round size=xs').classes('text-slate-400 hover:text-slate-600')

            # New chat button
            with ui.row().classes('px-3 py-2'):
                ui.button('+ New Chat', icon='add', on_click=lambda: start_new_session()) \
                    .props('flat no-caps').classes(
                        'w-full text-xs font-semibold text-violet-600 hover:bg-violet-50 rounded-lg '
                        'border border-violet-200 px-3 py-2'
                    )

            # Sessions list (scrollable)
            with ui.scroll_area().classes('flex-1 px-2'):
                sessions_container = ui.column().classes('w-full gap-1 pb-4')
                refresh_sessions_list()



        # ─── History sidebar toggle button (always visible) ────────
        sidebar_toggle_fixed = ui.element('div').style(
            f'position: fixed; top: 50%; '
            f'left: {(80 if state["main_sidebar_collapsed"] else 260) + (36 if state["history_collapsed"] else 260)}px; '
            'transform: translateY(-50%) translateX(-50%); z-index: 110; '
            'transition: left 0.3s ease;'
        )
        with sidebar_toggle_fixed:
            hist_toggle_pill = ui.button(
                icon='chevron_left',
                on_click=lambda: toggle_history_sidebar()
            ).props('flat round').classes(
                'bg-white border border-slate-200 shadow-md text-slate-500 '
                'hover:text-violet-600 hover:border-violet-300 w-6 h-10 rounded-full'
            )

        def toggle_history_sidebar():
            state['history_collapsed'] = not state['history_collapsed']
            if state['history_collapsed']:
                history_sidebar.classes(add='collapsed')
                hist_toggle_pill.props('icon=chevron_right')
                history_toggle_btn.props('icon=chevron_right')
            else:
                history_sidebar.classes(remove='collapsed')
                hist_toggle_pill.props('icon=chevron_left')
                history_toggle_btn.props('icon=chevron_left')
            # Update page margin
            new_margin = get_left_margin()
            page_wrapper.style(
                f'margin-left: {new_margin}px; '
                'transition: margin-left 0.3s cubic-bezier(0.4,0,0.2,1); '
                'min-height: calc(100vh - 60px); display: flex; flex-direction: column;'
            )
            # Update toggle pill position
            sidebar_toggle_fixed.style(
                f'position: fixed; top: 50%; '
                f'left: {(80 if state["main_sidebar_collapsed"] else 260) + (36 if state["history_collapsed"] else 260)}px; '
                'transform: translateY(-50%) translateX(-50%); z-index: 110; '
                'transition: left 0.3s ease;'
            )

        # ═══════════════════════════════════════════════════════════
        #  MAIN CONTENT
        # ═══════════════════════════════════════════════════════════

        with page_wrapper:
            with ui.column().classes('w-full h-full flex-1').style('max-width: 1400px; margin: 0 auto; padding: 24px 24px 0 24px;'):

                # ── Top header ────────────────────────────────────
                with ui.row().classes('w-full items-start justify-between mb-4'):
                    with ui.column().classes('gap-1'):
                        with ui.row().classes('items-center gap-3'):
                            with ui.element('div').classes(
                                'w-10 h-10 rounded-xl flex items-center justify-center'
                            ).style('background: linear-gradient(135deg, #6366f1, #8b5cf6);'):
                                ui.icon('auto_awesome').classes('text-white text-xl')
                            with ui.column().classes('gap-0'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.label('AI Analyst').classes(
                                        'text-xl font-bold text-slate-900'
                                    ).style("font-family: 'DM Sans', sans-serif;")
                                    with ui.element('div').classes(
                                        'px-2 py-0.5 rounded-full text-[9px] font-bold tracking-widest uppercase '
                                        'bg-amber-100 text-amber-700 border border-amber-200'
                                    ):
                                        ui.label('Beta')
                                ui.label('Ask the Data').classes(
                                    'text-sm text-slate-500 font-medium'
                                ).style("font-family: 'DM Sans', sans-serif;")

                    # Disclaimer
                    with ui.element('div').classes('disclaimer-badge items-center flex gap-1.5'):
                        ui.icon('info_outline').classes('text-amber-600 text-sm')
                        ui.label('AI responses should be reviewed before decisions').classes('text-[11px]')

                # ── Chat window ───────────────────────────────────
                chat_card = ui.card().classes(
                    'w-full flex-1 border border-slate-200 shadow-sm rounded-2xl overflow-hidden '
                    'flex flex-col bg-white'
                ).style('min-height: 420px;')

                with chat_card:
                    # Native scrollable messages column (avoids Quasar scroll area collapse bugs)
                    messages_column = ui.column().classes(
                        'w-full px-6 py-4 overflow-y-auto gap-5'
                    ).style('height: 480px; max-height: 480px; flex-grow: 1;')
                    messages_scroll = messages_column

                    with messages_column:
                        _render_welcome(set_hint)
                        try:
                            for msg in get_messages(state['session_id']):
                                role = msg.get('role')
                                content = msg.get('content')
                                if role == 'user':
                                    _render_user_message(content, msg.get('ts', ''))
                                else:
                                    _render_ai_message(
                                        content,
                                        sql=msg.get('sql'),
                                        data=msg.get('data'),
                                        ts=msg.get('ts', '')
                                    )
                        except Exception as e:
                            logger.error(f"Error rendering initial chat messages: {e}")

                    ui.separator().classes('m-0 border-slate-100')

                    # ── Input bar ─────────────────────────────────
                    with ui.column().classes('w-full px-4 py-3 gap-3 bg-slate-50/60'):
                        # Text input row
                        with ui.element('div').classes('ai-input-wrapper w-full flex items-center gap-2 px-4 py-2'):
                            text_input = ui.input(
                                placeholder='Ask anything about your data...',
                            ).props('borderless dense').classes(
                                'flex-grow text-sm text-slate-800'
                            ).style("font-family: 'DM Sans', sans-serif; font-size: 14px;")
                            send_btn = ui.button(icon='send', on_click=handle_send) \
                                .props('round flat').classes(
                                    'text-violet-600 hover:bg-violet-100 transition-all duration-200'
                                )

                        # ── Hint chips ────────────────────────────
                        with ui.row().classes('w-full gap-2 flex-wrap pb-1'):
                            for hint in QUESTION_HINTS[:5]:
                                with ui.element('div').classes('hint-chip').on('click', lambda h=hint: set_hint(h)):
                                    ui.label(hint)

        # ─── Load existing messages from session ──────────────────
        # Enter key sends
        text_input.on('keydown.enter', handle_send)

        # Initial messages pre-rendered synchronously in layout tree

    await dashboard_layout(content, page_title="AI Analyst", active_page="ai_insights")


# ═══════════════════════════════════════════════════════════════════
#  Render helpers
# ═══════════════════════════════════════════════════════════════════

def _render_welcome(on_select_hint=None):
    """Welcome card shown at the top of every fresh session."""
    with ui.element('div').classes(
        'w-full rounded-2xl border border-violet-100 p-5 mb-2'
    ).style('background: linear-gradient(135deg, #faf5ff 0%, #ede9fe 100%);'):
        with ui.row().classes('items-center gap-3 mb-3'):
            with ui.element('div').classes(
                'w-8 h-8 rounded-lg flex items-center justify-center'
            ).style('background: linear-gradient(135deg, #6366f1, #8b5cf6);'):
                ui.icon('auto_awesome').classes('text-white text-base')
            ui.label('AI Analyst · Ask the Data').classes(
                'text-sm font-bold text-violet-800'
            ).style("font-family: 'DM Sans', sans-serif;")

        ui.label(
            "Hi! I'm your AI Analyst. Ask me anything about your platform data — "
            "users, organisations, engagement, compliance trends, or growth patterns."
        ).classes('text-sm text-slate-600 leading-relaxed mb-2')

        with ui.row().classes('gap-2 flex-wrap'):
            for example in [
                "How many platforms are we tracking?",
                "Which platform has the highest user base?",
                "Show me RegComply's monthly growth",
            ]:
                with ui.element('div').classes(
                    'px-3 py-1.5 rounded-full text-xs font-medium '
                    'bg-white border border-violet-200 text-violet-700 cursor-pointer '
                    'hover:bg-violet-50 transition-colors'
                ).on('click', lambda ex=example: on_select_hint(ex) if on_select_hint else None):
                    ui.label(f'"{example}"')


def _render_user_message(text: str, ts: str = ''):
    with ui.row().classes('w-full justify-end items-end gap-2'):
        with ui.column().classes('items-end gap-1'):
            with ui.element('div').classes('chat-user-bubble'):
                ui.label(text)
            if ts:
                ui.label(ts).classes('chat-ts text-right')


def _render_ai_message(text: str, sql: str = None, data: list = None, ts: str = ''):
    # Enforce safe string representation of response text to prevent markdown TypeError
    safe_text = str(text) if text is not None else "No response text generated."
    
    with ui.row().classes('w-full justify-start items-end gap-2'):
        # AI avatar
        with ui.element('div').classes(
            'w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mb-5'
        ).style('background: linear-gradient(135deg, #6366f1, #8b5cf6);'):
            ui.icon('auto_awesome').classes('text-white text-xs')

        with ui.column().classes('gap-1').style('max-width: 78%;'):
            with ui.element('div').classes('chat-ai-bubble'):
                ui.markdown(safe_text).classes('text-sm text-slate-800 leading-relaxed')



            # Data table expandable
            if data and isinstance(data, list) and len(data) > 0:
                with ui.expansion(f'View data · {len(data)} rows', icon='table_chart').classes(
                    'text-xs text-slate-400 rounded-lg border border-slate-100 bg-white mt-1'
                ).props('dense'):
                    try:
                        first_row = data[0] if len(data) > 0 else {}
                        keys = first_row.keys() if isinstance(first_row, dict) else ['value']
                        columns = [
                            {'name': k, 'label': k, 'field': k, 'align': 'left', 'sortable': True}
                            for k in keys
                        ]
                        clean_data = []
                        # Inject unique sequential row_id to prevent QTable from silent-crashing on duplicate row values
                        for idx, row in enumerate(data):
                            if isinstance(row, dict):
                                clean_row = {k: str(v) if v is not None else '' for k, v in row.items()}
                                clean_row['row_id'] = idx
                                clean_data.append(clean_row)
                            else:
                                clean_data.append({'row_id': idx, 'value': str(row)})
                        
                        ui.table(columns=columns, rows=clean_data, row_key='row_id') \
                            .classes('w-full text-xs').props('dense flat bordered')
                    except Exception as e:
                        logger.error(f"Error rendering data table in AI message: {e}")
                        ui.label("Data format is not supported for automatic table rendering.").classes('text-xs text-slate-400 italic')

            if ts:
                ui.label(ts).classes('chat-ts')
