"""
Reports Page V2 - Stunning, Premium UI with robust downloads.
"""
from nicegui import ui, app
from components.dashboard_layout import dashboard_layout
from components.theme_manager import ThemeManager
from report_manager.engine import get_report_engine, REPORT_CATALOG
from report_manager.requests import save_report_request, get_all_report_requests, log_report_download
import logging
import os
import time

logger = logging.getLogger(__name__)

# Custom CSS for Stunning UI
REPORT_STYLE = '''
<style>
    .glass-card {
        background: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07) !important;
    }
    .hover-glimmer:hover {
        transform: translateY(-4px) scale(1.01) !important;
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.12) !important;
        border: 1px solid rgba(255, 255, 255, 0.5) !important;
    }
    .gradient-text {
        background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .action-btn {
        background: linear-gradient(135deg, #f59e0b, #ef4444) !important;
        color: white !important;
        border-radius: 12px !important;
        text-transform: none !important;
        font-weight: 600 !important;
    }
    .report-tab-panel {
        padding: 24px 0 !important;
    }
    .priority-high { color: #ef4444; font-weight: bold; }
    .priority-medium { color: #f59e0b; font-weight: bold; }
    .priority-low { color: #10b981; font-weight: bold; }
</style>
'''

async def show_reports_page():
    ui.add_head_html(REPORT_STYLE)
    user_email = app.storage.user.get('email', 'unknown@example.com')
    engine = get_report_engine()

    # Ensure temp dir exists
    TEMP_DIR = os.path.join('assets', 'temp_reports')
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR, exist_ok=True)

    async def content():
        # Clean up old files in temp dir (> 1 hour old)
        now = time.time()
        for f in os.listdir(TEMP_DIR):
            fpath = os.path.join(TEMP_DIR, f)
            if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > 3600:
                try: os.remove(fpath)
                except: pass

        # Hero Header
        with ui.column().classes('w-full mb-10'):
            ui.label('Analytics Center').classes('text-5xl font-extrabold gradient-text mb-3 tracking-tight')
            ui.label('Intelligence, delivered. Generate premium reports or collaborate on custom insights.').classes('text-lg text-slate-500 max-w-2xl leading-relaxed')

        # Custom Tabs Styling
        with ui.tabs().classes('w-full border-b border-slate-100 mb-8 bg-transparent') as tabs:
            available_tab = ui.tab('AVAILABLE', icon='insights').classes('px-8 py-4 font-bold tracking-widest text-xs')
            request_tab = ui.tab('REQUESTS', icon='auto_awesome_motion').classes('px-8 py-4 font-bold tracking-widest text-xs')

        with ui.tab_panels(tabs, value=available_tab).classes('w-full bg-transparent'):
            # --- TAB 1: AVAILABLE REPORTS ---
            with ui.tab_panel(available_tab).classes('report-tab-panel'):
                with ui.row().classes('w-full gap-8'):
                    for key, info in REPORT_CATALOG.items():
                        with ui.card().classes(f'glass-card hover-glimmer p-8 w-full md:w-[48%] lg:w-[31%] flex flex-col items-center text-center transition-all duration-300'):
                            # Icon Area
                            with ui.avatar(icon=info['icon'], color='orange-50').classes('text-orange-500 mb-6 scale-150 p-4'):
                                pass
                            
                            ui.label(info['title']).classes('text-2xl font-bold text-slate-900 mb-3')
                            ui.label(info['description']).classes('text-sm text-slate-500 mb-8 leading-relaxed h-12 overflow-hidden')

                            # Platform Selection within card
                            with ui.row().classes('w-full items-center justify-center gap-4 mb-8 bg-slate-50/50 p-3 rounded-2xl'):
                                ui.label('SCOPE:').classes('text-[10px] font-black text-slate-400 tracking-tighter')
                                p_select = ui.select(
                                    options=['All', 'RegComply', 'RegWatch', 'RegPort'],
                                    value='All'
                                ).props('dense flat borderless color=orange').classes('text-sm font-bold text-orange-600')

                            async def run_v2_report(k=key, ps=p_select):
                                platform = ps.value
                                try:
                                    notify = ui.notification('Preparing high-fidelity report...', spinner=True, timeout=None)
                                    
                                    # Unique temp file
                                    ts = int(time.time())
                                    safe_filename = f"report_{k}_{platform.lower()}_{ts}.xlsx"
                                    file_path = os.path.join(TEMP_DIR, safe_filename)
                                    
                                    # Generate to file
                                    engine.generate_excel_report(k, platform, file_path=file_path)
                                    
                                    # Log
                                    log_report_download(REPORT_CATALOG[k]['title'], platform, user_email)
                                    
                                    # Serve from assets URL
                                    public_url = f"/assets/temp_reports/{safe_filename}"
                                    ui.download(public_url)
                                    
                                    notify.dismiss()
                                    ui.notify('Report ready for download!', color='positive', icon='cloud_done')
                                except Exception as e:
                                    if 'notify' in locals(): notify.dismiss()
                                    ui.notify(f"Generation error: {str(e)}", color='negative', icon='warning')
                                    logger.error(f"Reports V2 Error: {e}")

                            ui.button('GENERATE REPORT', icon='auto_fix_high', on_click=run_v2_report).classes('action-btn w-full py-4')

            # --- TAB 2: REQUESTS ---
            with ui.tab_panel(request_tab).classes('report-tab-panel'):
                with ui.row().classes('w-full gap-10 items-start'):
                    # Elegant Request Form
                    with ui.card().classes('glass-card p-10 flex-1'):
                        ui.label('Strategic Request').classes('text-3xl font-black text-slate-900 mb-2')
                        ui.label('Describe the cross-platform intelligence you need.').classes('text-sm text-slate-400 mb-8')
                        
                        title_i = ui.input('REPORT TITLE').props('stack-label').classes('w-full mb-6 text-lg font-bold')
                        desc_i = ui.textarea('DATA REQUIREMENTS & BUSINESS GOAL').props('stack-label rows=5').classes('w-full mb-6')
                        
                        with ui.row().classes('w-full gap-6 mb-8'):
                            priority_i = ui.select(['Low', 'Medium', 'High'], value='Medium', label='PRIORITY').classes('flex-1')
                            
                        ui.label('COMPONENTS NEEDED').classes('text-[10px] font-black text-slate-400 tracking-widest mb-4')
                        c_checks = []
                        with ui.row().classes('w-full gap-x-8 gap-y-3 mb-10'):
                            for s in ['KPIs', 'Trends', 'User Lists', 'Financials', 'Security', 'Geo']:
                                c_checks.append(ui.checkbox(s).props('color=orange'))

                        async def submit_v2_request():
                            title = title_i.value
                            desc = desc_i.value
                            if not title or not desc:
                                ui.notify('Complete all fields', color='warning')
                                return
                            
                            success = save_report_request(title, desc, priority_i.value, [c.text for c in c_checks if c.value], user_email)
                            if success:
                                ui.notify('Intelligence request logged', color='positive')
                                title_i.value = desc_i.value = ''
                                for c in c_checks: c.value = False
                                r_grid.update_rows(get_all_report_requests())
                            else:
                                ui.notify('Network error', color='negative')

                        ui.button('SUBMIT REQUEST', on_click=submit_v2_request).classes('action-btn px-12 py-4 h-14')

                    # Request Stream (Table)
                    with ui.column().classes('flex-[1.5]'):
                        ui.label('Request Stream').classes('text-xl font-black text-slate-900 mb-6')
                        
                        cols = [
                            {'name': 'created_at', 'label': 'TIMESTAMP', 'field': 'created_at', 'align': 'left'},
                            {'name': 'title', 'label': 'REPORT TITLE', 'field': 'title', 'align': 'left'},
                            {'name': 'priority', 'label': 'PRIORITY', 'field': 'priority'},
                            {'name': 'status', 'label': 'STATUS', 'field': 'status'},
                        ]

                        def get_rows_v2():
                            rs = get_all_report_requests()
                            for r in rs:
                                if r.get('created_at') and not isinstance(r['created_at'], str):
                                    r['created_at'] = r['created_at'].strftime("%b %d, %H:%M")
                            return rs

                        r_grid = ui.table(columns=cols, rows=get_rows_v2(), row_key='_id').classes('w-full glass-card border-none')
                        
                        # Custom styling for cells
                        r_grid.add_slot('body-cell-priority', '''
                            <q-td :props="props" :class="'priority-' + props.value.toLowerCase()">
                                {{ props.value }}
                            </q-td>
                        ''')
                        r_grid.add_slot('body-cell-status', '''
                            <q-td :props="props">
                                <q-badge :color="props.value === 'Pending' ? 'orange-2' : (props.value === 'Completed' ? 'green-2' : 'blue-2')" 
                                         :text-color="props.value === 'Pending' ? 'orange-9' : (props.value === 'Completed' ? 'green-9' : 'blue-9')"
                                         class="px-3 py-1 font-bold">
                                    {{ props.value }}
                                </q-badge>
                            </q-td>
                        ''')

    await dashboard_layout(content, page_title="Intelligence Reports", active_page="reports")
