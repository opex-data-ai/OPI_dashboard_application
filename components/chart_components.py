from nicegui import ui, run
import pandas as pd
import plotly.express as px
import pycountry
from typing import List, Dict, Any, Optional
from components.theme_manager import ThemeManager

def _download_csv_helper(data, title):
    """Helper to download a DataFrame or list of dicts as CSV"""
    import pandas as pd
    if isinstance(data, list):
        df = pd.DataFrame(data)
    elif isinstance(data, dict):
        df = pd.DataFrame([data])
    elif isinstance(data, pd.DataFrame):
        df = data
    else:
        df = None
    
    if df is not None and not df.empty:
        cols_to_exclude = ['iso_code', 'date_str', 'landing_page_label', 'next_action_label']
        df_export = df.drop(columns=[c for c in cols_to_exclude if c in df.columns])
        csv_content = df_export.to_csv(index=False).encode('utf-8')
        ui.download(csv_content, f"{title.replace(' ', '_').lower()}.csv")
    else:
        ui.notify("No data available to download.", type='warning')

async def show_ai_insight_dialog(metric_id: str):
    """Open a dialog showing AI-generated insights for a specific metric/chart."""
    from data_engine.chart_descriptions import METRIC_INFO
    from ai_engine import ai_insight_in_chart
    desc_data = METRIC_INFO.get(metric_id)
    if not desc_data:
        ui.notify("No metadata found for this metric.", type='warning')
        return

    with ui.dialog() as dialog, ui.card().classes('w-[600px] p-0 overflow-hidden rounded-2xl shadow-2xl'):
        dialog.open()
        with ui.row().classes('w-full items-center justify-between py-3 px-5 bg-slate-50 border-b border-slate-100'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('auto_awesome').classes('text-purple-600 text-xl')
                ui.label(desc_data['title']).classes('text-base font-bold text-slate-900')
            ui.button(icon='close', on_click=dialog.close).props('flat round size=sm').classes('text-slate-400 hover:bg-slate-200 transition-colors')
        
        content_container = ui.column().classes('w-full p-5 justify-center')
        with content_container:
            spinner = ui.spinner(size='md', color='purple-600').classes('self-center my-2')
            try:
                from utils.anonymizer import anonymize_data, restore_pii
                import logging
                logger = logging.getLogger(__name__)
                chart_data = desc_data.get('chart_data')
                pii_mapping = {}
                if desc_data.get('has_pii') and desc_data.get('pii_columns') and chart_data:
                    chart_data, pii_mapping = anonymize_data(chart_data, desc_data['pii_columns'])
                
                insight = await run.io_bound(ai_insight_in_chart, desc_data.get('title', 'Unknown Metric'), desc_data.get('description', ''), chart_data, desc_data.get('schema_explanation', ''))
                if pii_mapping:
                    insight = restore_pii(insight, pii_mapping)
                spinner.delete()
                ui.label(insight).classes('text-slate-700 leading-snug text-sm whitespace-pre-wrap')
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"AI Insight Dialog Error for '{metric_id}': {e}")
                spinner.delete()
                ui.label("Unable to generate insight at this time. Please try again later.").classes('text-slate-500 italic text-center w-full text-sm')
        
        with ui.row().classes('w-full justify-end py-2 px-4 bg-slate-50 border-t border-slate-100'):
            ui.button('Dismiss', on_click=dialog.close).props('flat').classes('text-slate-600 font-bold uppercase tracking-wider text-[10px]')

def create_kpi_metrics(metrics: List[Dict[str, Any]]):
    grid_cols = len(metrics)
    with ui.grid(columns=grid_cols).classes(f'w-full gap-4 mb-6 items-stretch grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-{grid_cols}'):
        for metric in metrics:
            card_style = ThemeManager.get_card_style()
            with ui.card().classes(f'h-full p-6 {card_style} hover:shadow-lg transition-all flex flex-col pt-4'):
                with ui.row().classes('w-full items-start justify-between mb-1 shrink-0'):   
                    ui.label(metric['label']).classes(ThemeManager.TYPOGRAPHY['small'] + ' leading-tight font-bold')
                    with ui.row().classes('items-center gap-2'):
                        if 'id' in metric and metric.get('show_info', True):
                            from data_engine.chart_descriptions import METRIC_INFO
                            desc_data = METRIC_INFO.get(metric['id'])
                            if desc_data and desc_data.get('show_ai_icon', False):
                                ui.button(icon='auto_awesome', on_click=lambda m_id=metric['id']: show_ai_insight_dialog(m_id)).props('flat round size=sm').classes('text-amber-500 p-0 transform hover:scale-110 transition-transform cursor-pointer')
                            if desc_data:
                                with ui.button(icon='info_outline', color='slate-100').props('flat round size=sm').classes('opacity-60 hover:opacity-100 p-0'):
                                    with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                        ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                        ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                
                with ui.column().classes('mt-auto w-full'):
                    val = metric['value']
                    f_val = f"{val:,.0f}" if isinstance(val, int) else (f"{val:,.0f}" if isinstance(val, float) else str(val))
                    ui.label(f_val).classes('text-2xl font-bold text-slate-900 leading-none break-words')
                    if 'subtitle' in metric:
                        ui.label(metric['subtitle']).classes('text-xs text-slate-500 mt-2 leading-relaxed')

_iso_cache = {}
def get_iso_code(country_name):
    if not country_name or pd.isna(country_name): return None
    if country_name in _iso_cache: return _iso_cache[country_name]
    try:
        norm_map = {'USA': 'United States', 'UK': 'United Kingdom', 'Korea': 'Korea, Republic of', 'Russia': 'Russian Federation'}
        name = norm_map.get(country_name, country_name)
        code = pycountry.countries.search_fuzzy(name)[0].alpha_3
        _iso_cache[country_name] = code
        return code
    except: return None

def create_country_metrics_row(data: pd.DataFrame, title: str, value_col: Any, id_1: str = None, id_2: str = None, show_info: bool = True):
    df_copy = data.copy()
    
    if isinstance(value_col, list):
        valid = [c for c in value_col if c in df_copy.columns]
        df_copy['display_value'] = df_copy[valid].sum(axis=1) if valid else 0
        active_col = 'display_value'
    else:
        active_col = value_col
        if active_col not in df_copy.columns:
            df_copy[active_col] = 0

    with ui.grid(columns=5).classes('w-full gap-4 mb-6 items-stretch'):
        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
            with ui.row().classes('w-full items-start justify-between mb-1'):
                ui.label(title).classes('text-xl font-bold text-slate-900')
                with ui.row().classes('items-center gap-2'):
                    if id_1 and show_info:
                        from data_engine.chart_descriptions import METRIC_INFO
                        desc_data = METRIC_INFO.get(id_1)
                        if desc_data:
                            if desc_data.get('show_ai_icon', True):
                                ui.button(icon='auto_awesome', on_click=lambda m_id=id_1: show_ai_insight_dialog(m_id)).props('flat round size=sm').classes('text-amber-500 p-0 transform hover:scale-110 transition-transform cursor-pointer')
                            with ui.button(icon='info_outline').props('flat round size=sm').classes('opacity-60 hover:opacity-100 p-0'):
                                with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                    ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                    ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                    ui.button(icon='download', on_click=lambda: _download_csv_helper(data, title)).props('flat round size=sm').classes('opacity-60')

            if df_copy.empty:
                ui.label('No data').classes('text-slate-500 italic py-20 w-full text-center')
            else:
                df_copy['iso_code'] = df_copy['country'].apply(get_iso_code)
                data_clean = df_copy.dropna(subset=['iso_code'])
                fig = px.choropleth(
                    data_clean, locations='iso_code', color=active_col, hover_name='country',
                    color_continuous_scale=['#e0f2fe', '#7dd3fc', '#0ea5e9', '#0284c7', '#0369a1'],
                    labels={active_col: 'Users'}
                )
                fig.update_layout(
                    geo=dict(showframe=False, showcoastlines=True, coastlinecolor="#cbd5e1", projection_type='natural earth', bgcolor='rgba(0,0,0,0)', showland=True, landcolor='#f8fafc', showocean=False),
                    height=500, margin=dict(l=0, r=0, t=0, b=0), coloraxis_showscale=False
                )
                ui.plotly(fig).classes('w-full')

        with ui.card().classes('col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl'):
            with ui.row().classes('w-full items-start justify-between mb-4'):
                ui.label('Top Countries').classes('text-xl font-bold text-slate-900')
                with ui.row().classes('items-center gap-2'):
                    if id_2 and show_info:
                        from data_engine.chart_descriptions import METRIC_INFO
                        desc_data = METRIC_INFO.get(id_2)
                        if desc_data:
                            if desc_data.get('show_ai_icon', True):
                                ui.button(icon='auto_awesome', on_click=lambda m_id=id_2: show_ai_insight_dialog(m_id)).props('flat round size=sm').classes('text-amber-500 p-0 transform hover:scale-110 transition-transform cursor-pointer')
                            with ui.button(icon='info_outline').props('flat round size=sm').classes('opacity-60 hover:opacity-100 p-0'):
                                with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                    ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                    ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                    ui.button(icon='download', on_click=lambda: _download_csv_helper(data, 'Top Countries')).props('flat round size=sm').classes('opacity-60')

            if not df_copy.empty:
                top = df_copy.nlargest(7, active_col).copy()
                ui.table(
                    columns=[
                        {'name': 'c', 'label': 'COUNTRY', 'field': 'country', 'align': 'left'},
                        {'name': 'v', 'label': 'USERS', 'field': active_col, 'align': 'right'}
                    ],
                    rows=top.to_dict('records')
                ).classes('w-full').props('flat hide-bottom')

def create_comparison_cards(comparisons: List[Dict[str, Any]]):
    with ui.row().classes('w-full gap-4 mb-6 items-stretch'):
        for comp in comparisons:
            with ui.card().classes('flex-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl hover:shadow-lg transition-shadow flex flex-col'):
                with ui.row().classes('w-full justify-between items-start mb-2'):
                    ui.label(comp['title']).classes('text-sm text-slate-600 font-semibold')
                    with ui.row().classes('items-center gap-2'):
                        if 'id' in comp and comp.get('show_info', True):
                            from data_engine.chart_descriptions import METRIC_INFO
                            desc_data = METRIC_INFO.get(comp['id'])
                            if desc_data:
                                if desc_data.get('show_ai_icon', True):
                                    ui.button(icon='auto_awesome', on_click=lambda m_id=comp['id']: show_ai_insight_dialog(m_id)).props('flat round size=sm').classes('text-amber-500 p-0 transform hover:scale-110 cursor-pointer')
                                with ui.button(icon='info_outline').props('flat round size=sm').classes('opacity-60 hover:opacity-100 p-0'):
                                    with ui.menu().classes('p-4 max-w-xs'):
                                        ui.label(desc_data['title']).classes('font-bold mb-1')
                                        ui.label(desc_data['description']).classes('text-sm text-slate-600')

                with ui.row().classes('w-full gap-2 items-center mt-auto'):
                    with ui.column().classes('flex-1 items-start gap-1'):
                        ui.label(comp['metric_a_name']).classes('text-xs text-slate-500 whitespace-nowrap')
                        ui.label(f"{comp['metric_a_value']}").classes('text-lg font-bold leading-tight')
                    ui.label('vs').classes('text-base font-bold text-slate-400 shrink-0')
                    with ui.column().classes('flex-1 items-end gap-1'):
                        ui.label(comp['metric_b_name']).classes('text-xs text-slate-500 whitespace-nowrap')
                        ui.label(f"{comp['metric_b_value']}").classes('text-lg font-bold leading-tight text-right')

                # Percentage bar
                show_pct_bar = comp.get('pct_bar', False)
                if show_pct_bar and isinstance(comp['metric_a_value'], (int, float)) and comp['metric_a_value'] > 0:
                    method = comp.get('pct_method', 'divide')
                    if method == 'divide':
                        percentage = (comp['metric_b_value'] / comp['metric_a_value']) * 100
                    elif method == 'total':
                        total = comp['metric_a_value'] + comp['metric_b_value']
                        percentage = (comp['metric_a_value'] / total) * 100
                    else:
                        percentage = (comp['metric_b_value'] / comp['metric_a_value']) * 100
                    
                    p = min(percentage, 100)
                    if p >= 75:
                        bar_color = '#22c55e'   # green-500
                    elif p >= 50:
                        bar_color = '#84cc16'   # lime-500
                    elif p >= 35:
                        bar_color = '#f59e0b'   # amber-500
                    elif p >= 20:
                        bar_color = '#f97316'   # orange-500
                    else:
                        bar_color = '#ef4444'   # red-500

                    with ui.row().classes('w-full items-center gap-2 mt-3'):
                        with ui.element('div').classes('flex-1 h-2 bg-slate-200 rounded-full overflow-hidden'):
                            ui.element('div').style(f'width: {p:.1f}%; height: 100%; background-color: {bar_color}; border-radius: 9999px;')
                        ui.label(f'{percentage:.1f}%').classes('text-xs font-semibold').style(f'color: {bar_color}')
                        
def create_pie_chart(data: Dict[str, Any], title: str, colors: List[Any] = None, height: str = 'h-80', id: str = None, show_info: bool = True):
    if colors is None: colors = ThemeManager.get_chart_colors()
    pie_data = [{'value': v, 'name': k} for k, v in data.items()]
    with ui.card().classes(f'w-full p-6 pt-4 {ThemeManager.get_card_style()}'):
        chart_container = ui.column().classes('w-full')
        with ui.row().classes('w-full items-start justify-between mb-1'):
            ui.label(title).classes(ThemeManager.TYPOGRAPHY['h3'])
            with ui.row().classes('items-center gap-2'):
                if id and show_info:
                    from data_engine.chart_descriptions import METRIC_INFO
                    desc_data = METRIC_INFO.get(id)
                    if desc_data:
                        if desc_data.get('show_ai_icon', True):
                            ui.button(icon='auto_awesome', on_click=lambda m_id=id: show_ai_insight_dialog(m_id)).props('flat round size=sm').classes('text-amber-500 p-0 hover:scale-110')
                        with ui.button(icon='info_outline').props('flat round size=sm').classes('opacity-60'):
                            with ui.menu().classes('p-4 max-w-xs'):
                                ui.label(desc_data['title']).classes('font-bold')
                                ui.label(desc_data['description']).classes('text-sm')
                ui.button(icon='download', on_click=lambda: ui.run_javascript(f"downloadChart('{{chart_el.id}}', '{{title}}')")).props('flat round size=sm').classes('opacity-60 hover:opacity-100')
        with chart_container:
            chart_el = ui.echart({'series': [{'type': 'pie', 'radius': '70%', 'data': pie_data, 'label': {'show': True}}]}).classes(f'w-full {height}')

def create_bar_chart(data: pd.DataFrame, title: str, x_col: str, y_cols: List[str], colors: List[Any] = None, height: str = 'h-96', labels: Optional[List[str]] = None, show_legend: bool = True, id: str = None, show_info: bool = True):
    if colors is None: colors = ThemeManager.get_chart_colors()
    display_labels = labels if labels and len(labels) == len(y_cols) else [col.replace('_', ' ').title() for col in y_cols]
    with ui.card().classes(f'w-full p-6 pt-4 {ThemeManager.get_card_style()}'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            ui.label(title).classes(ThemeManager.TYPOGRAPHY['h3'])
            with ui.row().classes('items-center gap-2'):
                if id and show_info:
                    from data_engine.chart_descriptions import METRIC_INFO
                    desc_data = METRIC_INFO.get(id)
                    if desc_data:
                        if desc_data.get('show_ai_icon', True):
                            ui.button(icon='auto_awesome', on_click=lambda m_id=id: show_ai_insight_dialog(m_id)).props('flat round size=sm').classes('text-amber-500 p-0')
                        with ui.button(icon='info_outline').props('flat round size=sm'):
                            with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                ui.button(icon='download', on_click=lambda: ui.run_javascript(f"downloadChart('{{chart_el.id}}', '{{title}}')")).props('flat round size=sm').classes('opacity-60')
        chart_container = ui.column().classes('w-full')
        with chart_container:
            chart_el = ui.echart({
                'xAxis': {'type': 'value'}, 'yAxis': {'type': 'category', 'data': data[x_col].tolist()},
                'series': [{'name': display_labels[idx], 'type': 'bar', 'data': data[col].tolist()} for idx, col in enumerate(y_cols)]
            }).classes(f'w-full {height}')

def create_column_chart(data: pd.DataFrame, title: str, x_col: str, y_cols: List[str], colors: List[Any] = None, height: str = 'h-96', id: str = None, show_info: bool = True):
    if colors is None: colors = ThemeManager.get_chart_colors()
    with ui.card().classes(f'w-full p-6 pt-4 {ThemeManager.get_card_style()}'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            ui.label(title).classes(ThemeManager.TYPOGRAPHY['h3'])
            with ui.row().classes('items-center gap-2'):
                if id and show_info:
                    from data_engine.chart_descriptions import METRIC_INFO
                    desc_data = METRIC_INFO.get(id)
                    if desc_data:
                        if desc_data.get('show_ai_icon', True):
                            ui.button(icon='auto_awesome', on_click=lambda m_id=id: show_ai_insight_dialog(m_id)).props('flat round size=sm').classes('text-amber-500 p-0')
                        with ui.button(icon='info_outline').props('flat round size=sm'):
                            with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                ui.button(icon='download', on_click=lambda: ui.run_javascript(f"downloadChart('{{chart_el.id}}', '{{title}}')")).props('flat round size=sm').classes('opacity-60')
        chart_container = ui.column().classes('w-full')
        with chart_container:
            chart_el = ui.echart({
                'xAxis': {'type': 'category', 'data': data[x_col].tolist()}, 'yAxis': {'type': 'value'},
                'series': [{'name': col, 'type': 'bar', 'data': data[col].tolist()} for col in y_cols]
            }).classes(f'w-full {height}')

def create_line_chart(data: pd.DataFrame, title: str, x_col: str, y_cols: Any, colors: List[str] = None, height: str = 'h-96', y_axis_name: str = None, rotate_labels: int = 45, show_area: bool = True, id: str = None, show_info: bool = True):
    if colors is None: colors = ['#6366f1', '#10b981', '#f59e0b', '#8b5cf6', '#f43f5e']
    if isinstance(y_cols, dict): cols, labels = list(y_cols.keys()), list(y_cols.values())  # ← was 'lables'
    else: cols, labels = y_cols, [col.replace('_', ' ').title() for col in y_cols]

    with ui.card().classes('w-full p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            ui.label(title).classes('text-xl font-bold text-slate-900')
            with ui.row().classes('items-center gap-2'):
                if id and show_info:
                    from data_engine.chart_descriptions import METRIC_INFO
                    desc_data = METRIC_INFO.get(id)
                    if desc_data:
                        if desc_data.get('show_ai_icon', True):
                            ui.button(icon='auto_awesome', on_click=lambda m_id=id: show_ai_insight_dialog(m_id)).props('flat round size=sm')
                        with ui.button(icon='info_outline').props('flat round size=sm'):
                            with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                ui.button(icon='download', on_click=lambda: ui.run_javascript(f"downloadChart('{chart_el.id}', '{title}')")).props('flat round size=sm').classes('opacity-60')
        with ui.column().classes('w-full'):
            series = []
            for idx, col in enumerate(cols):
                s = {
                    'name': labels[idx],
                    'type': 'line',
                    'data': data[col].tolist(),
                    'smooth': True,
                    'itemStyle': {'color': colors[idx % len(colors)]},
                    'lineStyle': {'width': 3},
                    'symbol': 'circle',
                    'symbolSize': 8,
                }
                if show_area:
                    s['areaStyle'] = {'opacity': 0.1}
                series.append(s)

            chart_el = ui.echart({
                'xAxis': {
                    'type': 'category',
                    'data': data[x_col].tolist(),
                    'boundaryGap': False,
                    'axisLabel': {'rotate': rotate_labels, 'fontSize': 10, 'color': '#64748b'},
                    'axisLine': {'lineStyle': {'color': '#e2e8f0'}}
                },
                'yAxis': {
                    'type': 'value',
                    'name': y_axis_name or '',
                    'axisLabel': {'color': '#64748b'},
                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                },
                'series': series,
                'tooltip': {
                    'trigger': 'axis',
                    'axisPointer': {'type': 'cross', 'label': {'backgroundColor': '#6a7985'}}
                },
                'legend': {
                    'data': labels,
                    'bottom': 0,
                    'icon': 'circle',
                    'textStyle': {'color': '#64748b'}
                },
                'grid': {
                    'left': '3%',
                    'right': '4%',
                    'top': '10%',
                    'bottom': '15%',
                    'containLabel': True
                }
            }).classes(f'w-full {height}')

def create_donut_chart(data: Dict[str, float], title: str, colors: List[str] = None, id: str = None, show_info: bool = True):
    if colors is None: colors = ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']
    chart_data = [{'value': v, 'name': k} for k, v in data.items()]
    with ui.card().classes('flex-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl'):
        chart_container = ui.column().classes('w-full')
        with ui.row().classes('w-full items-start justify-between mb-1'):
            ui.label(title).classes('text-xl font-bold text-slate-900')
            with ui.row().classes('items-center gap-2'):
                if id and show_info:
                    from data_engine.chart_descriptions import METRIC_INFO
                    desc_data = METRIC_INFO.get(id)
                    if desc_data:
                        if desc_data.get('show_ai_icon', True):
                            ui.button(icon='auto_awesome', on_click=lambda m_id=id: show_ai_insight_dialog(m_id)).props('flat round size=sm')
                        with ui.button(icon='info_outline').props('flat round size=sm'):
                            with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                ui.button(icon='download', on_click=lambda: ui.run_javascript(f"downloadChart('{{chart_el.id}}', '{{title}}')")).props('flat round size=sm').classes('opacity-60')
        with chart_container:
            chart_el = ui.echart({
                'tooltip': {'trigger': 'item'},
                'series': [{'type': 'pie', 'radius': ['40%', '70%'], 'data': chart_data, 'color': colors}]
            }).classes('w-full h-80')

def create_metric_table(data: pd.DataFrame, title: str = "Detailed Metrics", height: str = None, id: str = None, show_info: bool = True):
    with ui.card().classes('w-full p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            ui.label(title).classes('text-xl font-bold text-slate-900')
            with ui.row().classes('items-center gap-2'):
                if id and show_info:
                    from data_engine.chart_descriptions import METRIC_INFO
                    desc_data = METRIC_INFO.get(id)
                    if desc_data:
                        if desc_data.get('show_ai_icon', True):
                            ui.button(icon='auto_awesome', on_click=lambda m_id=id: show_ai_insight_dialog(m_id)).props('flat round size=sm')
                        with ui.button(icon='info_outline').props('flat round size=sm'):
                            with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                ui.button(icon='download', on_click=lambda: _download_csv_helper(data, title)).props('flat round size=sm').classes('opacity-60')
        rows = data.copy()
        for col in rows.select_dtypes(include=['number']).columns:
            rows[col] = rows[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) and ('pct' in col.lower() or 'rate' in col.lower()) else (f"{int(x):,}" if pd.notna(x) else "0"))
        table = ui.table(columns=[{'name': c, 'label': c.replace('_',' ').title(), 'field': c, 'sortable': True} for c in data.columns], rows=rows.to_dict('records')).classes('w-full').props('flat binary-state-sort')
        if height: table.props('sticky-header').classes(height)

def create_gauge_chart(value: float, max_value: float, title: str, color: str = '#2563eb', id: str = None, show_info: bool = True):
    percentage = (value / max_value * 100) if max_value > 0 else 0
    with ui.card().classes('flex-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl text-center'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            ui.label(title).classes('text-sm text-slate-600 font-semibold')
            with ui.row().classes('items-center gap-2'):
                if id and show_info:
                    from data_engine.chart_descriptions import METRIC_INFO
                    desc_data = METRIC_INFO.get(id)
                    if desc_data:
                        if desc_data.get('show_ai_icon', True):
                            ui.button(icon='auto_awesome', on_click=lambda m_id=id: show_ai_insight_dialog(m_id)).props('flat round size=sm')
                        with ui.button(icon='info_outline').props('flat round size=sm'):
                            with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
        ui.echart({
            'series': [{'type': 'gauge', 'startAngle': 180, 'endAngle': 0, 'min': 0, 'max': max_value, 'progress': {'show': True}, 'detail': {'valueAnimation': True}, 'data': [{'value': value}]}]
        }).classes('w-full h-48')
        ui.label(f'{percentage:.1f}% of maximum').classes('text-xs text-slate-500 mt-2')

def create_placeholder_card(title: str, height: str = 'h-96'):
    with ui.card().classes(f'w-full {height} p-6 border border-dashed border-slate-300 bg-slate-50 rounded-xl flex items-center justify-center'):
        with ui.column().classes('items-center gap-2'):
            ui.icon('insert_chart', size='3rem').classes('text-slate-300')
            ui.label(title).classes('text-sm font-semibold text-slate-400 uppercase tracking-wider')

def create_traffic_source_row(source_data: pd.DataFrame, source_title: str, id_1: str, medium_data: pd.DataFrame, medium_title: str, id_2: str, value_col: str, value_label: str, id: str = None, show_info: bool = True):
    with ui.grid(columns=5).classes('w-full gap-4 mb-6 items-stretch'):
        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
            
            with ui.row().classes('w-full items-start justify-between mb-1'):
                ui.label(source_title).classes('text-xl font-bold text-slate-900')
                with ui.row().classes('items-center gap-2'):
                    if id_1 and show_info:
                        from data_engine.chart_descriptions import METRIC_INFO
                        desc_data = METRIC_INFO.get(id_1)
                        if desc_data:
                            if desc_data.get('show_ai_icon', True):
                                ui.button(icon='auto_awesome', on_click=lambda m_id=id_1: show_ai_insight_dialog(m_id)).props('flat round size=sm')
                            with ui.button(icon='info_outline').props('flat round size=sm'):
                                with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                    ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                    ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                    ui.button(icon='download', on_click=lambda m_id=id, t=source_title: _download_csv_helper(METRIC_INFO.get(m_id, {}).get('chart_data'), t)).props('flat round size=sm').classes('opacity-60 hover:opacity-100 p-0 hover:text-blue-600 transition-colors')

            chart_container = ui.column().classes('w-full')
            if not source_data.empty:
                chart_data = source_data.nlargest(10, value_col).sort_values(value_col, ascending=True)
                cat_col = [c for c in chart_data.columns if c != value_col][0]

                with chart_container:
                    chart_el = ui.echart({'grid': {'left': 180, 'right': 20, 'top': 10, 'bottom': 30, 'containLabel': False},
                                                    'xAxis': {'type': 'value'},
                                                    'yAxis': {'type': 'category','data': chart_data[cat_col].tolist(),'axisLabel': {'width': 200, 'overflow': 'truncate', 'fontSize': 11,}},
                                                    'series': [{'name': value_label, 'type': 'bar', 'data': chart_data[value_col].tolist()}]}).classes('w-full h-80')

        with ui.card().classes('col-span-2 p-6 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
            with ui.row().classes('w-full items-start justify-between mb-1'):
                ui.label(medium_title).classes('text-xl font-bold text-slate-900')
                with ui.row().classes('items-center gap-2'):
                    if id_2 and show_info:
                        from data_engine.chart_descriptions import METRIC_INFO
                        desc_data = METRIC_INFO.get(id_2)
                        if desc_data:
                            if desc_data.get('show_ai_icon', True):
                                ui.button(icon='auto_awesome', on_click=lambda m_id=id_2: show_ai_insight_dialog(m_id)).props('flat round size=sm')
                            with ui.button(icon='info_outline').props('flat round size=sm'):
                                with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                    ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                    ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                    ui.button(icon='download', on_click=lambda m_id=id_2, t=medium_title: _download_csv_helper(METRIC_INFO.get(m_id, {}).get('chart_data'), t)).props('flat round size=sm').classes('opacity-60 hover:opacity-100 p-0 hover:text-blue-600 transition-colors')
            if not medium_data.empty:
                top = medium_data.nlargest(10, value_col).copy()
                cat_col = [c for c in top.columns if c != value_col][0]
                ui.table(columns=[{'name': 'c', 'label': cat_col.upper(), 'field': cat_col, 'align': 'left'}, {'name': 'v', 'label': value_label.upper(), 'field': value_col, 'align': 'right'}], rows=top.to_dict('records')).classes('w-full border-none shadow-none').props('flat hide-bottom')

def create_user_journey_section(data: pd.DataFrame, id: str = None, show_info: bool = True):
    with ui.column().classes('w-full gap-4 mt-8'):
        with ui.row().classes('w-full items-start justify-between mb-2'):
            with ui.column().classes('gap-1'):
                ui.label('High-Engagement User Journeys').classes('text-2xl font-bold text-slate-900')
                ui.label('Analysis of the deepest navigation sequences taken by users').classes('text-sm text-slate-500')
            with ui.row().classes('items-center gap-2'):
                if id and show_info:
                    from data_engine.chart_descriptions import METRIC_INFO
                    desc_data = METRIC_INFO.get(id)
                    if desc_data:
                        if desc_data.get('show_ai_icon', True):
                            ui.button(icon='auto_awesome', on_click=lambda m_id=id: show_ai_insight_dialog(m_id)).props('flat round size=sm')
                        with ui.button(icon='info_outline').props('flat round size=sm'):
                            with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                ui.button(icon='download', on_click=lambda: _download_csv_helper(data, 'User Journeys')).props('flat round size=sm').classes('opacity-60')

        if data.empty:
            with ui.card().classes('w-full p-12 items-center border border-slate-200 shadow-sm rounded-xl'):
                ui.icon('explore', size='3rem').classes('text-slate-200 mb-4')
                ui.label('No complex journey data found for this period').classes('text-slate-500 italic')
            return

        for idx, row in data.iterrows():
            import re
            path = str(row['conversion_path'])
            steps = [s.strip() for s in re.split(r' > | → | â†’ ', path) if s.strip()]

            with ui.card().classes('w-full p-8 border border-slate-200 shadow-sm rounded-2xl hover:shadow-lg transition-all relative overflow-hidden'):
                # Background decorative circle
                ui.element('div').classes('absolute -right-20 -top-20 w-64 h-64 bg-slate-50 rounded-full opacity-50')

                with ui.row().classes('w-full items-center justify-between mb-8 relative z-10'):
                    with ui.row().classes('items-center gap-3'):
                        with ui.element('div').classes('p-2 bg-indigo-50 rounded-lg'):
                            ui.icon('insights', size='1.5rem').classes('text-indigo-600')
                        with ui.column().classes('gap-0'):
                            ui.label(f'Journey Pattern #{idx + 1}').classes('text-xl font-black text-slate-800')
                            ui.label(f"{row.get('unique_pages', '')} Unique high-value steps").classes('text-[10px] text-slate-400 font-bold uppercase tracking-wider')

                    with ui.row().classes('gap-8'):
                        with ui.column().classes('items-end gap-1'):
                            ui.label(f"{row.get('user_pct', 0):.1f}%").classes('text-2xl font-black text-indigo-700 leading-none')
                            ui.label('User Base Reach').classes('text-[10px] text-slate-400 font-bold uppercase tracking-tighter')
                        with ui.column().classes('items-end gap-1'):
                            ui.label(f"{int(row.get('path_occurrence_count', 0)):,}").classes('text-2xl font-black text-slate-800 leading-none')
                            ui.label('Total Occurrences').classes('text-[10px] text-slate-400 font-bold uppercase tracking-tighter')

                with ui.row().classes('w-full gap-3 items-center overflow-x-auto pb-4 relative z-10 flex-nowrap'):
                    for step_idx, step in enumerate(steps):
                        with ui.element('div').classes('px-5 py-3 bg-white border-2 border-slate-100 rounded-xl shadow-sm shrink-0 flex items-center gap-3'):
                            ui.element('div').classes('w-2 h-2 rounded-full bg-indigo-500')
                            ui.label(step).classes('text-sm font-bold text-slate-700')
                        if step_idx < len(steps) - 1:
                            ui.icon('arrow_forward', size='1.2rem').classes('text-slate-300 shrink-0 mx-1 animate-pulse')