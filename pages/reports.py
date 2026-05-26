"""
Reports Page V3 - Modern, Premium Report Hub with Dynamic Date Range & Organisation Scopes.
"""
from nicegui import ui, app
from components.dashboard_layout import dashboard_layout
from report_manager.engine import get_report_engine, REPORT_CATALOG
from report_manager.requests import save_report_request, get_all_report_requests, log_report_download
from data_engine.data_loader import get_data_loader
import logging
import os
import time

logger = logging.getLogger(__name__)

from components.theme_manager import ThemeManager

REPORT_STYLE = '''
<style>
    .sheet-badge {
        background: #f5f3ff;
        color: #6d28d9;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 6px;
        border: 1px solid #ddd6fe;
    }
</style>
'''

async def show_reports_page():
    ui.add_head_html(REPORT_STYLE)
    user_email = app.storage.user.get('email', 'unknown@example.com')
    engine = get_report_engine()
    loader = get_data_loader()

    # Ensure temp dir exists
    TEMP_DIR = os.path.join('assets', 'temp_reports')
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR, exist_ok=True)

    # 1. Fetch dynamic organizations list from DuckDB
    org_options = {'': 'All Organisations'}
    try:
        query_orgs = """
            SELECT DISTINCT organization_id, organizationName 
            FROM all_organizations 
            WHERE organizationName IS NOT NULL AND organizationName != '' 
            ORDER BY organizationName ASC
        """
        df_orgs = loader.execute_query(query_orgs)
        for _, row in df_orgs.iterrows():
            org_options[row['organization_id']] = row['organizationName']
    except Exception as e:
        logger.error(f"Error loading organizations for dropdown: {e}")

    async def content():
        # Clean up old files in temp dir (> 1 hour old)
        now = time.time()
        for f in os.listdir(TEMP_DIR):
            fpath = os.path.join(TEMP_DIR, f)
            if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > 3600:
                try: os.remove(fpath)
                except: pass

        # Hero Header Banner
        with ui.row().classes('w-full items-center justify-between mb-6'):
            with ui.column().classes('gap-1'):
                ui.label('Analytics Center').classes('ds-h1 mb-1')
                ui.label('Compile high-fidelity audit workbooks, filter operational datasets, and collaborate on strategic insights.').classes('ds-body text-slate-500 mb-6')
            
            # Interactive Page Documentation Pill
            with ui.element('div').classes('px-4 py-2 bg-slate-50 border border-slate-100 rounded-xl flex items-center gap-2'):
                ui.icon('verified_user').classes('text-emerald-500 text-sm')
                ui.label('Secure Workbook Compiler').classes('text-[11px] font-bold text-slate-600 uppercase tracking-wider')

        # Custom Tabs Styling (Sliding rounded pill design)
        with ui.element('div').classes('bg-slate-300/60 p-1 rounded-xl inline-flex mb-8'):
            with ui.tabs().props('dense no-caps align="left" breakpoint=0 indicator-color="transparent" active-bg-color="white" active-text-color="dark"') \
                .classes('bg-transparent') as tabs:
                available_tab = ui.tab('Available Report Workbooks', icon='analytics').classes('rounded-lg px-6 min-h-[32px] transition-all text-xs font-bold')
                request_tab = ui.tab('Request', icon='history_edu').classes('rounded-lg px-6 min-h-[32px] transition-all text-xs font-bold')

        with ui.tab_panels(tabs, value=available_tab).classes('w-full bg-transparent'):
            
            # ─────────────────────────────────────────────────────────
            #  TAB 1: AVAILABLE HIGH-FIDELITY REPORTS
            # ─────────────────────────────────────────────────────────
            with ui.tab_panel(available_tab).classes('px-0 py-4'):
                # Available reports grid
                with ui.row().classes('w-full gap-8'):
                    for key, info in REPORT_CATALOG.items():
                        # Define the right modal (dialog drawer) for this specific report card
                        with ui.dialog().props('position=right') as dialog:
                            with ui.card().classes('h-full w-[450px] max-w-full p-8 flex flex-col justify-between bg-white rounded-l-2xl shadow-xl').style('height: 100vh; max-height: 100vh; margin: 0 !important;'):
                                # Modal Header
                                with ui.row().classes('w-full items-center justify-between border-b border-slate-100 pb-4 mb-4'):
                                    with ui.row().classes('items-center gap-3'):
                                        with ui.avatar(icon=info['icon'], color='indigo-50').classes('text-indigo-600 scale-110'):
                                            pass
                                        with ui.column().classes('gap-0.5'):
                                            ui.label(info['title']).classes('ds-h2 text-slate-800')
                                    ui.button(icon='close', on_click=dialog.close).props('flat round size=sm').classes('text-slate-400 hover:bg-slate-100 transition-colors')
                                
                                # Modal Scrollable Content
                                with ui.scroll_area().classes('flex-1 pr-2 mb-6'):
                                    with ui.column().classes('w-full gap-6'):
                                        # Description
                                        with ui.column().classes('gap-1'):
                                            ui.label('DESCRIPTION').classes('text-[10px] font-black text-slate-400 tracking-wider')
                                            ui.label(info['description']).classes('text-sm text-slate-600 leading-relaxed')

                                        # Included sheets
                                        with ui.column().classes('gap-2'):
                                            ui.label('INCLUDED WORKBOOK SHEETS').classes('text-[10px] font-black text-slate-400 tracking-wider')
                                            with ui.row().classes('gap-1.5 flex-wrap'):
                                                for sh in info['sheets']:
                                                    ui.label(sh).classes('sheet-badge')

                                        ui.separator().classes('my-2')

                                        # Parameter Controls
                                        ui.label('REPORT PARAMETERS').classes('text-xs font-bold text-slate-700 uppercase tracking-wider mb-2')
                                        
                                        start_date_input = ui.input('Start Date', value='2026-01-01').props('type=date stack-label outline').classes('w-full text-sm font-semibold')
                                        end_date_input = ui.input('End Date', value='2026-05-31').props('type=date stack-label outline').classes('w-full text-sm font-semibold')
                                        
                                        platform_select = ui.select(
                                            options=['All', 'RegComply', 'RegWatch', 'RegPort'],
                                            value='All',
                                            label='Platform Scope'
                                        ).classes('w-full text-sm font-semibold')
                                        
                                        org_select = ui.select(
                                            options=org_options,
                                            value='',
                                            label='Organization Filter'
                                        ).classes('w-full text-sm font-semibold')

                                # Modal Footer Compile Button
                                with ui.column().classes('w-full pt-4 border-t border-slate-100 gap-3'):
                                    async def run_report(k=key, start_in=start_date_input, end_in=end_date_input, plat_sel=platform_select, org_sel=org_select, dlg=dialog):
                                        start_d = start_in.value
                                        end_d = end_in.value
                                        platform_s = plat_sel.value
                                        selected_org = org_sel.value

                                        if not start_d or not end_d:
                                            ui.notify('Please specify a valid start and end date range.', color='warning', icon='warning')
                                            return

                                        try:
                                            notify = ui.notification('Compiling workbook and running high-fidelity queries...', spinner=True, timeout=None)
                                            
                                            # Formulate high-fidelity filename
                                            safe_plat = platform_s.lower()
                                            safe_org_slug = f"_org_{selected_org[:8]}" if selected_org else ""
                                            ts = int(time.time())
                                            safe_filename = f"report_{k}_{safe_plat}{safe_org_slug}_{ts}.xlsx"
                                            file_path = os.path.join(TEMP_DIR, safe_filename)
                                            
                                            # Generate Excel to assets/temp_reports
                                            engine.generate_excel_report(
                                                report_key=k, 
                                                platform=platform_s, 
                                                start_date=start_d, 
                                                end_date=end_d, 
                                                org_id=selected_org if selected_org else None,
                                                file_path=file_path
                                            )
                                            
                                            # Log download in database
                                            log_report_download(info['title'], platform_s, user_email)
                                            
                                            # Stream download to client browser
                                            public_url = f"/assets/temp_reports/{safe_filename}"
                                            ui.download(public_url)
                                            
                                            notify.dismiss()
                                            ui.notify(f"{info['title']} compiled and ready!", color='positive', icon='cloud_done')
                                            dlg.close()
                                        except Exception as e:
                                            if 'notify' in locals(): notify.dismiss()
                                            ui.notify(f"Query Execution Error: {str(e)}", color='negative', icon='warning')
                                            logger.error(f"Excel Generation Error for {k}: {e}")

                                    ui.button(
                                        'COMPILE WORKBOOK', 
                                        icon='cloud_download', 
                                        on_click=run_report
                                    ).classes('btn-primary w-full py-3 text-sm')

                        # Elegant, compact card trigger
                        with ui.card().classes(f'p-5 w-full md:w-[48%] lg:w-[31%] cursor-pointer flex flex-col justify-between transition-all duration-300 {ThemeManager.get_card_style()} hover:shadow-md hover:border-indigo-200 hover:-translate-y-0.5').on('click', dialog.open):
                            with ui.column().classes('w-full gap-3'):
                                # Icon header
                                with ui.row().classes('w-full items-center justify-between'):
                                    with ui.avatar(icon=info['icon'], color='indigo-50').classes('text-indigo-600 scale-100'):
                                        pass
                                
                                ui.label(info['title']).classes('ds-h3 text-slate-800')
                            
                            with ui.row().classes('w-full items-center justify-between mt-4 pt-3 border-t border-slate-100'):
                                ui.label(f"{len(info['sheets'])} workbook sheets").classes('text-[10px] text-slate-400 font-semibold')
                                with ui.row().classes('items-center gap-1 text-indigo-600 hover:text-indigo-700'):
                                    ui.label('Configure').classes('text-[10px] font-bold uppercase tracking-wider')
                                    ui.icon('arrow_forward', size='xs').classes('scale-90')

            # ─────────────────────────────────────────────────────────
            #  TAB 2: REPORT REQUEST STREAM
            # ─────────────────────────────────────────────────────────
            with ui.tab_panel(request_tab).classes('px-0 py-4'):
                with ui.card().classes(f'w-full p-8 flex flex-col gap-6 {ThemeManager.get_card_style()}'):
                    with ui.row().classes('w-full items-center justify-between'):
                        with ui.column().classes('gap-1'):
                            ui.label('Report Requests').classes('ds-h2 text-slate-800')
                            ui.label('Track, review, and collaborate on strategic dataset compiles and custom report requests.').classes('ds-body text-slate-500 mb-2')
                        
                        # Add "+ New Request" button
                        new_request_btn = ui.button(
                            'NEW REPORT REQUEST', 
                            icon='add', 
                            on_click=lambda: request_dialog.open()
                        ).classes('btn-primary px-6 py-2.5 h-11 text-xs')

                    # Define the Dialog for making a new Request
                    with ui.dialog() as request_dialog:
                        with ui.card().classes('w-[550px] max-w-full p-8 flex flex-col gap-6 rounded-2xl bg-white shadow-2xl'):
                            # Dialog Header
                            with ui.row().classes('w-full items-center justify-between border-b border-slate-100 pb-4'):
                                with ui.column().classes('gap-1'):
                                    ui.label('Report Request').classes('ds-h2 text-slate-800')
                                    ui.label('Specify the filters, scopes, and details of your dataset request.').classes('ds-body text-slate-500 mb-2')
                                ui.button(icon='close', on_click=request_dialog.close).props('flat round size=sm').classes('text-slate-400 hover:bg-slate-100')

                            # Dialog Scrollable Form Content
                            with ui.scroll_area().classes('w-full pr-2').style('height: 380px;'):
                                with ui.column().classes('w-full gap-4 pb-4'):
                                    req_title = ui.input('Report Title').props('stack-label outline').classes('w-full font-semibold text-sm')
                                    req_desc = ui.textarea('Data Requirements & Calculations').props('stack-label outline rows=3').classes('w-full text-xs')
                                    
                                    with ui.row().classes('w-full gap-4'):
                                        req_start = ui.input('Required Start Date', value='2026-01-01').props('type=date stack-label outline').classes('flex-1 text-xs')
                                        req_end = ui.input('Required End Date', value='2026-05-31').props('type=date stack-label outline').classes('flex-1 text-xs')
                                    
                                    with ui.row().classes('w-full gap-4'):
                                        req_plat = ui.select(['All', 'RegComply', 'RegWatch', 'RegPort'], value='All', label='Platform Scope').classes('flex-1 text-xs')
                                        req_priority = ui.select(['Low', 'Medium', 'High'], value='Medium', label='Priority Tier').classes('flex-1 text-xs')
                                        
                                    ui.label('COMPONENTS TO INCLUDE').classes('text-[9px] font-black text-slate-400 tracking-wider mt-2')
                                    c_checkboxes = []
                                    with ui.row().classes('w-full gap-x-4 gap-y-1'):
                                        for s in ['AML Logs', 'Compliance Audits', 'Active Users', 'Churn Analysis', 'Traffic Quality']:
                                            c_checkboxes.append(ui.checkbox(s).props('color=indigo').classes('text-xs font-semibold text-slate-600'))

                            # Dialog Footer Submit
                            with ui.row().classes('w-full justify-end border-t border-slate-100 pt-4 gap-3'):
                                ui.button('Cancel', on_click=request_dialog.close).props('flat').classes('text-slate-500 font-bold text-xs')
                                
                                async def submit_request(dlg=request_dialog):
                                    title = req_title.value
                                    desc = req_desc.value
                                    start_d = req_start.value
                                    end_d = req_end.value
                                    platform = req_plat.value
                                    priority = req_priority.value
                                    
                                    if not title or not desc or not start_d or not end_d:
                                        ui.notify('Please fill out all request parameters, including dates.', color='warning', icon='warning')
                                        return
                                    
                                    # Gather checklist values
                                    included_sections = [cb.text for cb in c_checkboxes if cb.value]
                                    
                                    success = save_report_request(
                                        title=title,
                                        description=desc,
                                        priority=priority,
                                        sections=included_sections,
                                        requested_by=user_email,
                                        start_date=start_d,
                                        end_date=end_d,
                                        platform=platform
                                    )
                                    
                                    if success:
                                        ui.notify('Strategic report request saved to queue!', color='positive', icon='done_all')
                                        # Reset fields
                                        req_title.value = req_desc.value = ''
                                        for cb in c_checkboxes:
                                            cb.value = False
                                        dlg.close()
                                        # Refresh table
                                        request_table.update_rows(get_rows_list())
                                    else:
                                        ui.notify('Connection error. Please try again.', color='negative', icon='error')

                                ui.button('SUBMIT REQUEST', icon='send', on_click=submit_request).classes('btn-primary px-6 py-2.5 h-11 text-xs')

                    # Request Stream Table (Full width)
                    cols = [
                        {'name': 'created_at', 'label': 'TIMESTAMP', 'field': 'created_at', 'align': 'left'},
                        {'name': 'title', 'label': 'REPORT TITLE', 'field': 'title', 'align': 'left'},
                        {'name': 'platform', 'label': 'PLATFORM', 'field': 'platform', 'align': 'left'},
                        {'name': 'priority', 'label': 'PRIORITY', 'field': 'priority'},
                        {'name': 'status', 'label': 'STATUS', 'field': 'status'},
                    ]

                    def get_rows_list():
                        requests = get_all_report_requests()
                        for r in requests:
                            if r.get('created_at') and not isinstance(r['created_at'], str):
                                r['created_at'] = r['created_at'].strftime("%b %d, %H:%M")
                        return requests

                    request_table = ui.table(columns=cols, rows=get_rows_list(), row_key='_id').classes('w-full border-none shadow-none')
                    
                    # Style tags slot for Priority
                    request_table.add_slot('body-cell-priority', '''
                        <q-td :props="props">
                            <q-badge :color="props.value === 'High' ? 'red-1' : (props.value === 'Medium' ? 'amber-1' : 'teal-1')"
                                     :text-color="props.value === 'High' ? 'red-9' : (props.value === 'Medium' ? 'amber-9' : 'teal-9')"
                                     class="px-2.5 py-0.5 font-bold rounded">
                                {{ props.value }}
                            </q-badge>
                        </q-td>
                    ''')
                    
                    # Style tags slot for Status
                    request_table.add_slot('body-cell-status', '''
                        <q-td :props="props">
                            <q-badge :color="props.value === 'Pending' ? 'orange-2' : (props.value === 'Completed' ? 'green-2' : 'blue-2')" 
                                     :text-color="props.value === 'Pending' ? 'orange-9' : (props.value === 'Completed' ? 'green-9' : 'blue-9')"
                                     class="px-2.5 py-1 font-bold">
                                {{ props.value }}
                            </q-badge>
                        </q-td>
                    ''')

    await dashboard_layout(content, page_title="Intelligence Reports", active_page="reports")
