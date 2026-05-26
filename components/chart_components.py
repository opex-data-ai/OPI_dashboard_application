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


def render_chart_header(title: str, id: Optional[str] = None, show_info: bool = True, download_callback: Optional[Any] = None, data: Optional[Any] = None):
    """Renders a unified chart header with Title, Info icon, AI Insight, and Download button."""
    ui.label(title).classes(ThemeManager.TYPOGRAPHY['h3'] + ' font-bold text-slate-800 tracking-tight')
    
    desc_data = None
    if id and show_info:
        from data_engine.chart_descriptions import METRIC_INFO
        
        # Clean product specific suffixes to find standard base descriptions
        base_id = id
        for suffix in ['_comply', '_watch', '_port']:
            if id.endswith(suffix):
                base_id = id[:-len(suffix)]
                break
                
        # If the base key exists in METRIC_INFO, reuse its registered metadata!
        if base_id in METRIC_INFO:
            desc_data = METRIC_INFO[base_id].copy()
        else:
            desc_data = {
                'title': title,
                'description': f"Breakdown and analytics for {title}.",
                'show_ai_icon': True,
                'chart_data': None,
                'schema_explanation': f"Data metrics for {title}."
            }
            METRIC_INFO[id] = desc_data
        
        # Auto-serialize data if provided and not already populated
        if data is not None and not desc_data.get('chart_data'):
            if isinstance(data, pd.DataFrame):
                desc_data['chart_data'] = data.to_dict('records')
            elif isinstance(data, dict):
                desc_data['chart_data'] = data
            
            # Synchronize into global cache
            if base_id in METRIC_INFO:
                METRIC_INFO[base_id]['chart_data'] = desc_data['chart_data']
            METRIC_INFO[id] = desc_data

    with ui.row().classes('items-center gap-2'):
        if id and show_info and desc_data:
            # 1. AI Insight button (auto_awesome)
            ui.button(icon='auto_awesome', on_click=lambda m_id=id: show_ai_insight_dialog(m_id)).props('flat round size=sm').classes('text-violet-500 p-0 transform hover:scale-110 transition-transform cursor-pointer')
            
            # 2. Info icon (info_outline)
            with ui.button(icon='info_outline').props('flat round size=sm').classes('text-slate-400 opacity-60 hover:opacity-100 p-0'):
                with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                    ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                    ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                    
        # 3. Download button
        if download_callback:
            if isinstance(download_callback, str):
                ui.button(icon='download', on_click=lambda: ui.run_javascript(download_callback)).props('flat round size=sm').classes('opacity-60 hover:opacity-100')
            else:
                ui.button(icon='download', on_click=download_callback).props('flat round size=sm').classes('opacity-60 hover:opacity-100')


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
                ui.icon('auto_awesome').classes('text-violet-500 text-xl')
                ui.label(desc_data['title']).classes('text-base font-bold text-slate-900')
            ui.button(icon='close', on_click=dialog.close).props('flat round size=sm').classes('text-slate-400 hover:bg-slate-200 transition-colors')
        
        content_container = ui.column().classes('w-full p-5 justify-center')
        with content_container:
            spinner = ui.spinner(size='md').classes('self-center my-2 text-violet-500')
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

def render_kpi_info_icon(label: str):
    """Render a premium info icon with descriptions from METRIC_INFO fallback"""
    from data_engine.chart_descriptions import METRIC_INFO
    m_id = label.lower().replace(' ', '_').replace('-', '_')
    desc_data = METRIC_INFO.get(m_id)
    if not desc_data:
        desc_data = {
            'title': label.title(),
            'description': f"Analytics and breakdown metrics for {label}."
        }
    with ui.button(icon='info_outline').props('flat round size=sm').classes('text-slate-400 opacity-60 hover:opacity-100 p-0'):
        with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
            ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
            ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')

def create_kpi_metrics(metrics: List[Dict[str, Any]]):
    grid_cols = len(metrics)
    with ui.grid(columns=grid_cols).classes(f'w-full gap-4 mb-6 items-stretch grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-{grid_cols}'):
        for metric in metrics:
            card_style = ThemeManager.get_card_style()
            border_class = ""
            if 'color' in metric:
                color_map = {
                    'blue': 'border-l-blue-500',
                    'green': 'border-l-emerald-500',
                    'emerald': 'border-l-emerald-500',
                    'orange': 'border-l-amber-500',
                    'amber': 'border-l-amber-500',
                    'indigo': 'border-l-indigo-500',
                    'purple': 'border-l-purple-500',
                    'pink': 'border-l-pink-500',
                    'rose': 'border-l-rose-500',
                    'teal': 'border-l-teal-500',
                    'red': 'border-l-red-500',
                }
                c_name = metric['color']
                border_color_class = color_map.get(c_name, f'border-l-{c_name}-500')
                border_class = f' border-l-4 {border_color_class} relative overflow-hidden'
            with ui.card().classes(f'h-full p-6 {card_style}{border_class} hover:shadow-lg transition-all flex flex-col pt-4'):
                with ui.row().classes('w-full items-start justify-between mb-1 no-wrap shrink-0'):   
                    ui.label(metric['label']).classes(ThemeManager.TYPOGRAPHY['small'] + ' leading-tight font-bold')
                    with ui.row().classes('items-center gap-2'):
                        if metric.get('show_info', True):
                            from data_engine.chart_descriptions import METRIC_INFO
                            m_id = metric.get('id') or metric.get('label', '').lower().replace(' ', '_')
                            desc_data = METRIC_INFO.get(m_id)
                            if not desc_data:
                                desc_data = {
                                    'title': metric['label'],
                                    'description': f"Analytics and breakdown metrics for {metric['label']}."
                                }
                            with ui.button(icon='info_outline').props('flat round size=sm').classes('text-slate-400 opacity-60 hover:opacity-100 p-0'):
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
        match = pycountry.countries.search_fuzzy(country_name)
        if match:
            code = match[0].alpha_3
            _iso_cache[country_name] = code
            return code
    except Exception:
        pass
    _iso_cache[country_name] = None
    return None

def create_country_metrics_row(data: pd.DataFrame, title: str, id_1: str, id_2: str, value_col: Optional[str] = None, show_info: bool = True):
    if data is None or data.empty:
        df_copy = pd.DataFrame(columns=['country', 'users'])
    else:
        df_copy = data.copy()
        
    if not value_col:
        # Determine value col automatically
        active_col = 'users' if 'users' in df_copy.columns else ('unique_users' if 'unique_users' in df_copy.columns else None)
        if not active_col and not df_copy.empty:
            num_cols = df_copy.select_dtypes(include=['number']).columns
            if len(num_cols) > 0:
                active_col = num_cols[0]
            else:
                active_col = df_copy.columns[-1]
    else:
        active_col = value_col
        if active_col not in df_copy.columns:
            df_copy[active_col] = 0

    with ui.grid(columns=5).classes('w-full gap-4 mb-6 items-stretch'):
        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
            with ui.row().classes('w-full items-start justify-between mb-1'):
                render_chart_header(title, id_1, show_info, lambda: _download_csv_helper(data, title), data)

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
                render_chart_header('Top Countries', id_2, show_info, lambda: _download_csv_helper(data, 'Top Countries'), data)

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
                with ui.row().classes('w-full justify-between items-start mb-2 no-wrap'):
                    ui.label(comp['title']).classes('text-sm text-slate-600 font-semibold')
                    with ui.row().classes('items-center gap-2'):
                        if 'id' in comp and comp.get('show_info', True):
                            from data_engine.chart_descriptions import METRIC_INFO
                            desc_data = METRIC_INFO.get(comp['id'])
                            if desc_data:
                                with ui.button(icon='info_outline').props('flat round size=sm').classes('text-slate-400 opacity-60 hover:opacity-100 p-0'):
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
                        
def create_pie_chart(data: Dict[str, Any], title: str, colors: Optional[List[Any]] = None, height: str = 'h-80', id: Optional[str] = None, show_info: bool = True):
    if colors is None: colors = ThemeManager.get_chart_colors()
    pie_data = [{'value': v, 'name': k} for k, v in data.items()]
    with ui.card().classes(f'w-full p-6 pt-4 {ThemeManager.get_card_style()}'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header(title, id, show_info, lambda: ui.run_javascript(f"downloadChart('{chart_el.id}', '{title}')"), data)
        chart_container = ui.column().classes('w-full')
        with chart_container:
            chart_el = ui.echart({'series': [{'type': 'pie', 'radius': '70%', 'data': pie_data, 'label': {'show': True}}]}).classes(f'w-full {height}')

def create_bar_chart(data: pd.DataFrame, title: str, x_col: str, y_cols: List[str], colors: Optional[List[Any]] = None, height: str = 'h-96', labels: Optional[List[str]] = None, show_legend: bool = True, id: Optional[str] = None, show_info: bool = True):
    if colors is None: colors = ThemeManager.get_chart_colors()
    display_labels = labels if labels and len(labels) == len(y_cols) else [col.replace('_', ' ').title() for col in y_cols]
    with ui.card().classes(f'w-full p-6 pt-4 {ThemeManager.get_card_style()}'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header(title, id, show_info, lambda: ui.run_javascript(f"downloadChart('{chart_el.id}', '{title}')"), data)
        chart_container = ui.column().classes('w-full')
        with chart_container:
            chart_el = ui.echart({
                'xAxis': {'type': 'value'}, 
                'yAxis': {
                    'type': 'category', 
                    'data': data[x_col].tolist(),
                    'axisLabel': {'interval': 0, 'fontSize': 10}
                },
                'series': [{'name': display_labels[idx], 'type': 'bar', 'data': data[col].tolist()} for idx, col in enumerate(y_cols)]
            }).classes(f'w-full {height}')

def create_column_chart(data: pd.DataFrame, title: str, x_col: str, y_cols: List[str], colors: Optional[List[Any]] = None, height: str = 'h-96', id: Optional[str] = None, show_info: bool = True):
    if colors is None: colors = ThemeManager.get_chart_colors()
    with ui.card().classes(f'w-full p-6 pt-4 {ThemeManager.get_card_style()}'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header(title, id, show_info, lambda: ui.run_javascript(f"downloadChart('{chart_el.id}', '{title}')"), data)
        chart_container = ui.column().classes('w-full')
        with chart_container:
            chart_el = ui.echart({
                'xAxis': {
                    'type': 'category', 
                    'data': data[x_col].tolist(),
                    'axisLabel': {'interval': 0, 'rotate': 30, 'fontSize': 10}
                }, 
                'yAxis': {'type': 'value'},
                'series': [{'name': col, 'type': 'bar', 'data': data[col].tolist()} for col in y_cols]
            }).classes(f'w-full {height}')

def create_funnel_chart(data: pd.DataFrame, title: str, x_col: str, y_col: str, colors: Optional[List[Any]] = None, height: str = 'h-96', id: Optional[str] = None, show_info: bool = True):
    if colors is None: colors = ThemeManager.get_chart_colors()
    # Format data for ECharts funnel: [{'value': 100, 'name': 'Stage 1'}, ...]
    funnel_data = data[[y_col, x_col]].rename(columns={y_col: 'value', x_col: 'name'}).to_dict('records')
    
    with ui.card().classes(f'w-full p-6 pt-4 {ThemeManager.get_card_style()}'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header(title, id, show_info, lambda: ui.run_javascript(f"downloadChart('{chart_el.id}', '{title}')"), data)
        
        chart_container = ui.column().classes('w-full')
        with chart_container:
            chart_el = ui.echart({
                'tooltip': {
                    'trigger': 'item',
                    'formatter': '{b} : {c}'
                },
                'series': [
                    {
                        'name': title,
                        'type': 'funnel',
                        'left': '5%',
                        'top': 20,
                        'bottom': 20,
                        'width': '55%',
                        'min': 0,
                        'max': data[y_col].max() if not data.empty else 100,
                        'minSize': '0%',
                        'maxSize': '100%',
                        'sort': 'descending',
                        'gap': 2,
                        'label': {
                            'show': True,
                            'position': 'inside',
                            'formatter': '{c}'
                        },
                        'emphasis': {
                            'label': {
                                'fontSize': 20
                            }
                        },
                        'data': funnel_data,
                        'color': colors
                    },
                    {
                        'name': title,
                        'type': 'funnel',
                        'left': '5%',
                        'top': 20,
                        'bottom': 20,
                        'width': '55%',
                        'min': 0,
                        'max': data[y_col].max() if not data.empty else 100,
                        'minSize': '0%',
                        'maxSize': '100%',
                        'sort': 'descending',
                        'gap': 2,
                        'label': {
                            'show': True,
                            'position': 'right',
                            'formatter': '{b}',
                            'color': '#334155',
                            'fontSize': 11,
                            'fontWeight': 'bold'
                        },
                        'labelLine': {
                            'show': True,
                            'length': 20,
                            'lineStyle': {
                                'color': '#cbd5e1',
                                'width': 1
                            }
                        },
                        'data': funnel_data,
                        'itemStyle': {
                            'color': 'transparent'
                        }
                    }
                ]
            }).classes(f'w-full {height}')

def create_line_chart(data: pd.DataFrame, title: str, x_col: str, y_cols: Any, colors: Optional[List[str]] = None, height: str = 'h-96', y_axis_name: Optional[str] = None, rotate_labels: int = 45, show_area: bool = True, id: Optional[str] = None, show_info: bool = True):
    if colors is None: colors = ['#6366f1', '#10b981', '#f59e0b', '#8b5cf6', '#f43f5e']
    if isinstance(y_cols, dict): cols, labels = list(y_cols.keys()), list(y_cols.values())  # ← was 'lables'
    else: cols, labels = y_cols, [col.replace('_', ' ').title() for col in y_cols]

    with ui.card().classes('w-full p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header(title, id, show_info, lambda: ui.run_javascript(f"downloadChart('{chart_el.id}', '{title}')"), data)
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

            # Format labels: truncate 'YYYY-MM-DDTHH:MM:SS' or keep first 10 chars if it looks like a date string
            x_data = data[x_col].tolist()
            if x_data and isinstance(x_data[0], str) and len(x_data[0]) > 10:
                x_data = [str(val)[:10] for val in x_data]

            chart_el = ui.echart({
                'xAxis': {
                    'type': 'category',
                    'data': x_data,
                    'boundaryGap': False,
                    'axisLabel': {'rotate': rotate_labels, 'fontSize': 10, 'color': '#64748b', 'hideOverlap': True},
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

def create_donut_chart(data: Dict[str, float], title: str, colors: Optional[List[str]] = None, id: Optional[str] = None, show_info: bool = True):
    if colors is None: colors = ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']
    chart_data = [{'value': v, 'name': k} for k, v in data.items()]
    with ui.card().classes('flex-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header(title, id, show_info, lambda: ui.run_javascript(f"downloadChart('{chart_el.id}', '{title}')"), data)
        chart_container = ui.column().classes('w-full')
        with chart_container:
            chart_el = ui.echart({
                'tooltip': {'trigger': 'item'},
                'series': [{'type': 'pie', 'radius': ['40%', '70%'], 'data': chart_data, 'color': colors}]
            }).classes('w-full h-80')

def create_metric_table(data: pd.DataFrame, title: str = "Detailed Metrics", height: Optional[str] = None, id: Optional[str] = None, show_info: bool = True):
    with ui.card().classes('w-full p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header(title, id, show_info, lambda: _download_csv_helper(data, title), data)
        from utils.formatters import format_msec_to_compact_time
        rows = data.copy()
        for col in rows.select_dtypes(include=['number']).columns:
            if 'msec' in col.lower():
                rows[col] = rows[col].apply(lambda x: format_msec_to_compact_time(float(x)) if pd.notna(x) else "N/A")
            else:
                rows[col] = rows[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) and ('pct' in col.lower() or 'rate' in col.lower()) else (f"{int(x):,}" if pd.notna(x) else "0"))
        cols_def = [{'name': c, 'label': c.replace('_',' ').title(), 'field': c, 'sortable': True} for c in data.columns]
        pagination = {'rowsPerPage': 15}
        # Options: 15, 20, 25, 30, 35, 40, 45, 50
        page_options = '[15, 20, 25, 30, 35, 40, 45, 50]'
        
        if height:
            ui.table(columns=cols_def, rows=rows.to_dict('records'), pagination=pagination) \
                .classes(f'w-full {height} overflow-auto') \
                .props(f'flat binary-state-sort sticky-header :rows-per-page-options="{page_options}"')
        else:
            ui.table(columns=cols_def, rows=rows.to_dict('records'), pagination=pagination) \
                .classes('w-full') \
                .props(f'flat binary-state-sort :rows-per-page-options="{page_options}"')

def create_gauge_chart(value: float, max_value: float, title: str, color: str = '#2563eb', id: Optional[str] = None, show_info: bool = True):
    percentage = (value / max_value * 100) if max_value > 0 else 0
    with ui.card().classes('flex-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl text-center'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header(title, id, show_info, None, {'value': value, 'max_value': max_value})
        ui.echart({
            'series': [{'type': 'gauge', 'startAngle': 180, 'endAngle': 0, 'min': 0, 'max': max_value, 'progress': {'show': True}, 'detail': {'valueAnimation': True}, 'data': [{'value': value}]}]
        }).classes('w-full h-48')
        ui.label(f'{percentage:.1f}% of maximum').classes('text-xs text-slate-500 mt-2')

def create_placeholder_card(title: str, height: str = 'h-96'):
    with ui.card().classes(f'w-full {height} p-6 border border-dashed border-slate-300 bg-slate-50 rounded-xl flex items-center justify-center'):
        with ui.column().classes('items-center gap-2'):
            ui.icon('insert_chart', size='3rem').classes('text-slate-300')
            ui.label(title).classes('text-sm font-semibold text-slate-400 uppercase tracking-wider')

def create_traffic_source_row(source_data: pd.DataFrame, source_title: str, id_1: str, medium_data: pd.DataFrame, medium_title: str, id_2: str, value_col: str, value_label: str, id: Optional[str] = None, show_info: bool = True):
    with ui.grid(columns=5).classes('w-full gap-4 mb-6 items-stretch'):
        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
            with ui.row().classes('w-full items-start justify-between mb-1'):
                render_chart_header(source_title, id_1, show_info, lambda: _download_csv_helper(source_data, source_title), source_data)

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
                render_chart_header(medium_title, id_2, show_info, lambda: _download_csv_helper(medium_data, medium_title), medium_data)
            if not medium_data.empty:
                top = medium_data.nlargest(10, value_col).copy()
                cat_col = [c for c in top.columns if c != value_col][0]
                ui.table(columns=[{'name': 'c', 'label': cat_col.upper(), 'field': cat_col, 'align': 'left'}, {'name': 'v', 'label': value_label.upper(), 'field': value_col, 'align': 'right'}], rows=top.to_dict('records')).classes('w-full border-none shadow-none').props('flat hide-bottom')

def create_user_journey_section(data: pd.DataFrame, platform_name: str = 'RegComply', id: Optional[str] = None, show_info: bool = True, title: Optional[str] = None):
    import json
    rows = []
    if not data.empty:
        for _, r in data.iterrows():
            
            rows.append({
                'path': str(r.get('conversion_path', '')),
                'pct': float(r.get('path_percentage', 0.0)),
                'occ': int(r.get('path_occurrence_count', 0)),
                'num': int(r.get('num_pages', 0)),
                'uniq': int(r.get('unique_pages', 0)),
                'users': int(r.get('unique_users_count', 0)),
                'upct': float(r.get('user_pct', 0.0))
            })
    json_data = json.dumps(rows)

    section_title = title if title else 'User Journey Paths'

    with ui.column().classes('w-full gap-4 mt-8'):
        with ui.row().classes('w-full items-start justify-between mb-2'):
            with ui.column().classes('gap-1'):
                ui.label(section_title).classes('text-2xl font-bold text-slate-900')
            render_chart_header('', id, show_info, lambda: _download_csv_helper(data, 'User Journeys'), data)

        if data.empty:
            with ui.card().classes('w-full p-12 items-center border border-slate-200 shadow-sm rounded-xl'):
                ui.icon('explore', size='3rem').classes('text-slate-200 mb-4')
                ui.label('No complex journey data found for this period').classes('text-slate-500 italic')
            return
        # Render interactive user journey paths UI
        html_markup = '''
<div class="uj-container">
  <style>
  .uj-container {
    font-family: 'DM Sans', sans-serif;
    color: #101828;
    font-size: 13px;
    line-height: 1.5;
    --bg: #fff; --bg2: #f8f9fb; --bg3: #f2f4f7;
    --bd: #e4e7ec; --bd2: #d0d5dd;
    --t1: #101828; --t2: #344054; --t3: #667085; --t4: #98a2b3;
    --blue: #1570ef; --blue-50: #eff8ff; --blue-100: #b2ddff; --blue-800: #0c447c;
    --green-50: #ecfdf3; --green-100: #abefc6; --green-800: #054f31; --green-600: #067647;
    --amber-50: #fffaeb; --amber-100: #fedf89; --amber-800: #633806; --amber-600: #b54708;
    --red-50: #fef3f2; --red-100: #fecdca; --red-800: #7a1c1c;
    --purple-50: #f9f5ff; --purple-100: #d9d6fe; --purple-800: #3c3489;
    --r: 6px; --rl: 10px;
    width: 100%;
  }
  .uj-container .filter-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 18px; flex-wrap: wrap; padding-bottom: 14px; border-bottom: 1px solid var(--bd); }
  .uj-container .filter-group { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .uj-container .filter-sep { width: 1px; height: 18px; background: var(--bd); margin: 0 4px; }
  .uj-container .fl { font-size: 12px; color: var(--t3); white-space: nowrap; }
  .uj-container .sort-btn { font-family: 'DM Sans', sans-serif; font-size: 12px; padding: 4px 11px; border-radius: 20px; border: 0.5px solid var(--bd2); background: transparent; color: var(--t2); cursor: pointer; transition: all .15s; }
  .uj-container .sort-btn:hover { border-color: var(--blue); color: var(--blue); }
  .uj-container .sort-btn.active { background: var(--blue-50); color: var(--blue-800); border-color: var(--blue-100); font-weight: 500; }
  .uj-container .type-btn { font-family: 'DM Sans', sans-serif; font-size: 12px; padding: 4px 11px; border-radius: 20px; border: 0.5px solid var(--bd2); background: transparent; color: var(--t2); cursor: pointer; transition: all .15s; }
  .uj-container .type-btn:hover { background: var(--bg3); }
  .uj-container .type-btn.t-all { background: var(--blue-50); color: var(--blue-800); border-color: var(--blue-100); font-weight: 500; }
  .uj-container .type-btn.t-direct { background: var(--green-50); color: var(--green-800); border-color: var(--green-100); font-weight: 500; }
  .uj-container .type-btn.t-explorer { background: var(--blue-50); color: var(--blue-800); border-color: var(--blue-100); font-weight: 500; }
  .uj-container .type-btn.t-looper { background: var(--amber-50); color: var(--amber-800); border-color: var(--amber-100); font-weight: 500; }
  .uj-container .type-btn.t-trial { background: var(--purple-50); color: var(--purple-800); border-color: var(--purple-100); font-weight: 500; }
  .uj-container .legend { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 14px; }
  .uj-container .leg { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--t3); }
  .uj-container .leg-dot { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
  .uj-container .card { border: 0.5px solid var(--bd); border-radius: var(--rl); background: var(--bg); margin-bottom: 10px; overflow: hidden; }
  .uj-container .card-head { display: flex; align-items: flex-start; gap: 12px; padding: 14px 16px 12px; border-bottom: 0.5px solid var(--bd); }
  .uj-container .card-rank { font-size: 11px; font-weight: 500; color: var(--t3); min-width: 24px; margin-top: 2px; font-family: 'DM Mono', monospace; }
  .uj-container .card-meta { flex: 1; min-width: 0; }
  .uj-container .card-title { font-size: 14px; font-weight: 500; color: var(--t1); margin-bottom: 5px; }
  .uj-container .card-stats { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
  .uj-container .stat { font-size: 11px; color: var(--t3); display: flex; align-items: center; gap: 3px; }
  .uj-container .stat strong { color: var(--t2); font-weight: 500; }
  .uj-container .type-badge { font-size: 10px; font-weight: 500; padding: 2px 8px; border-radius: 20px; white-space: nowrap; }
  .uj-container .tb-direct { background: var(--green-50); color: var(--green-800); }
  .uj-container .tb-explorer { background: var(--blue-50); color: var(--blue-800); }
  .uj-container .tb-looper { background: var(--amber-50); color: var(--amber-800); }
  .uj-container .tb-trial { background: var(--purple-50); color: var(--purple-800); }
  .uj-container .card-right { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; flex-shrink: 0; }
  .uj-container .reach-val { font-size: 20px; font-weight: 500; color: var(--blue); line-height: 1; }
  .uj-container .reach-lbl { font-size: 10px; color: var(--t4); text-align: right; }
  .uj-container .sessions-pct { font-size: 11px; color: var(--t3); }
  .uj-container .steps-wrap { padding: 12px 16px; }
  .uj-container .steps-inner { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .uj-container .step { display: inline-flex; align-items: center; gap: 4px; padding: 4px 9px; border-radius: var(--r); font-size: 11px; font-weight: 400; border: 0.5px solid transparent; white-space: nowrap; }
  .uj-container .step-n { font-size: 9px; opacity: .55; font-family: 'DM Mono', monospace; }
  .uj-container .step-auth { background: var(--blue-50); color: var(--blue-800); border-color: var(--blue-100); }
  .uj-container .step-module { background: var(--green-50); color: var(--green-800); border-color: var(--green-100); }
  .uj-container .step-settings { background: var(--amber-50); color: var(--amber-800); border-color: var(--amber-100); }
  .uj-container .step-loop { background: var(--red-50); color: var(--red-800); border-color: var(--red-100); }
  .uj-container .step-trial { background: var(--purple-50); color: var(--purple-800); border-color: var(--purple-100); }
  .uj-container .step-other { background: var(--bg3); color: var(--t3); border-color: var(--bd); }
  .uj-container .arrow { color: var(--t4); font-size: 14px; display: flex; align-items: center; flex-shrink: 0; }
  .uj-container .more-btn { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: var(--blue); cursor: pointer; padding: 4px 8px; border-radius: var(--r); border: 0.5px solid var(--blue-100); background: var(--blue-50); white-space: nowrap; font-family: 'DM Sans', sans-serif; }
  .uj-container .more-btn:hover { background: var(--blue-100); }
  .uj-container .collapse-btn { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: var(--t3); cursor: pointer; padding: 4px 8px; border-radius: var(--r); border: 0.5px solid var(--bd2); background: var(--bg3); white-space: nowrap; font-family: 'DM Sans', sans-serif; }
  .uj-container .collapse-btn:hover { background: var(--bd); }
  .uj-container .eff-bar-row { display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-top: 0.5px solid var(--bd); }
  .uj-container .eff-lbl { font-size: 11px; color: var(--t3); width: 110px; flex-shrink: 0; }
  .uj-container .eff-track { flex: 1; height: 6px; border-radius: 3px; background: var(--bg3); overflow: hidden; }
  .uj-container .eff-fill { height: 100%; border-radius: 3px; }
  .uj-container .eff-val { font-size: 11px; font-weight: 500; width: 72px; text-align: right; flex-shrink: 0; }
  .uj-container .insight-row { display: flex; align-items: flex-start; gap: 6px; padding: 8px 16px 12px; border-top: 0.5px solid var(--bd); }
  .uj-container .insight-row i { font-size: 13px; color: var(--blue); flex-shrink: 0; margin-top: 1px; }
  .uj-container .insight-row span { font-size: 11px; color: var(--t3); line-height: 1.5; }
  .uj-container .load-wrap { display: flex; justify-content: center; margin-top: 14px; }
  .uj-container .load-btn { font-family: 'DM Sans', sans-serif; font-size: 12px; color: var(--t3); background: transparent; border: 0.5px solid var(--bd2); border-radius: var(--rl); padding: 8px 22px; cursor: pointer; display: flex; align-items: center; gap: 6px; }
  .uj-container .load-btn:hover { background: var(--bg2); color: var(--t2); }
  .uj-container .empty { padding: 40px; text-align: center; color: var(--t3); font-size: 13px; }
  .uj-container .summary-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
  .uj-container .summary-txt { font-size: 12px; color: var(--t3); }
  .uj-container .summary-txt strong { color: var(--t2); font-weight: 500; }
  </style>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">

  <!-- FILTER BAR -->
  <div class="filter-bar">
    <span class="fl">Sort</span>
    <div class="filter-group">
      <button class="sort-btn active" id="sort_user_pct" onclick="uj_setSort('user_pct')">User reach</button>
      <button class="sort-btn" id="sort_unique_pages" onclick="uj_setSort('unique_pages')">Path depth</button>
      <button class="sort-btn" id="sort_path_occurrence_count" onclick="uj_setSort('path_occurrence_count')">Frequency</button>
    </div>
    <div class="filter-sep"></div>
    <span class="fl">Type</span>
    <div class="filter-group">
      <button class="type-btn t-all" id="type_all" onclick="uj_setType('all')">All</button>
      <button class="type-btn" id="type_direct" onclick="uj_setType('direct')">Direct</button>
      <button class="type-btn" id="type_explorer" onclick="uj_setType('explorer')">Explorer</button>
      <button class="type-btn" id="type_looper" onclick="uj_setType('looper')">Looper</button>
      <button class="type-btn" id="type_trial" onclick="uj_setType('trial')">Trial</button>
    </div>
  </div>

  <!-- LEGEND -->
  <div class="legend">
    <span class="leg"><span class="leg-dot" style="background:#b2ddff"></span>Auth / login</span>
    <span class="leg"><span class="leg-dot" style="background:#abefc6"></span>Compliance module</span>
    <span class="leg"><span class="leg-dot" style="background:#fedf89"></span>Settings / profile</span>
    <span class="leg"><span class="leg-dot" style="background:#fecdca"></span>Repeated (loop)</span>
    <span class="leg"><span class="leg-dot" style="background:#d9d6fe"></span>Trial / onboarding</span>
  </div>

  <!-- SUMMARY -->
  <div class="summary-row">
    <span class="summary-txt" id="ujSummaryTxt">Showing <strong>5</strong> of <strong>20</strong> journeys</span>
  </div>

  <!-- LIST -->
  <div id="ujList"></div>

  <!-- LOAD MORE -->
  <div class="load-wrap">
    <button class="load-btn" id="ujLoadBtn" onclick="uj_loadMore()">
      <i class="ti ti-chevron-down"></i>
      Show 5 more journeys
    </button>
  </div>
</div>
'''

        js_code = '''
(function() {
  const DATA = __JSON_DATA__;
  const platform = "__PLATFORM_NAME__";

  const AUTH_PAGES = new Set();
  const MODULE_PAGES = new Set();
  const SETTING_PAGES = new Set();
  const TRIAL_PAGES = new Set();

  if (platform === 'RegPort') {
    ['/sign-in','/login','/sign-up','/auth','/2fa-otp-verification'].forEach(p => AUTH_PAGES.add(p));
    ['/transactions','/cases','/reports','/kyc-kyb','/cdd','/risk-simulator','/audit-trail','/dashboard','/alerts'].forEach(p => MODULE_PAGES.add(p));
    ['/settings','/profile','/notifications','/price','/support','/documentations'].forEach(p => SETTING_PAGES.add(p));
    ['/trial-sign-up','/trial-onboarding','/onboarding','/payment','/book-a-demo'].forEach(p => TRIAL_PAGES.add(p));
  } else if (platform === 'RegComply') {
    ['/login','/auth','/sign-in'].forEach(p => AUTH_PAGES.add(p));
    ['/dashboard','/risk-management','/task-management','/document-management','/compliance/frameworks','/compliance/audit','/compliance/csat','/my-organization','/firm/incoming-requests','/firm/ongoing-audits','/firm/teams','/firm/cbn-audits','/firm/tasks','/firm/csat'].forEach(p => MODULE_PAGES.add(p));
    ['/settings'].forEach(p => SETTING_PAGES.add(p));
    ['/book-a-demo'].forEach(p => TRIAL_PAGES.add(p));
  } else if (platform === 'RegWatch') {
    ['/sign-in','/sign-up','/login'].forEach(p => AUTH_PAGES.add(p));
    ['/dashboard','/assessment','/chatbot-ai','/notifications','/regulations-page'].forEach(p => MODULE_PAGES.add(p));
    ['/profile','/settings'].forEach(p => SETTING_PAGES.add(p));
    ['/demo'].forEach(p => TRIAL_PAGES.add(p));
  }

  const SHOW_INITIAL = 6;
  let sortKey = 'user_pct';
  let filterType = 'all';
  let shownCount = 5;
  let expanded = new Set();

  function journeyType(steps) {
    const hasTrial = steps.some(s => TRIAL_PAGES.has(s) || s.includes('trial') || s.includes('onboarding') || s.includes('demo'));
    const seen = {};
    steps.forEach(s => seen[s] = (seen[s]||0)+1);
    const hasLoop = Object.values(seen).some(v => v > 1);
    const eff = new Set(steps).size / steps.length;
    if (hasTrial) return 'trial';
    if (hasLoop && eff < 0.7) return 'looper';
    if (steps.length <= 5 && !hasLoop) return 'direct';
    return 'explorer';
  }

  function typeLabel(t) {
    return {direct:'Direct path',explorer:'Explorer path',looper:'Loop pattern',trial:'Trial journey'}[t] || 'Explorer path';
  }

  function insight(j, type) {
    const steps = j.steps;
    const modules = steps.filter(s => (MODULE_PAGES.has(s) || s.includes('assessment') || s.includes('cases') || s.includes('transactions')) && s !== '/dashboard');
    const looped = steps.filter((s,i) => steps.slice(0,i).includes(s));
    if (type === 'direct') return `Clean ${steps.length}-step path — user arrived with clear intent and no backtracking.`;
    if (type === 'looper') return `Revisited ${ [...new Set(looped)].slice(0,3).join(', ') } — indicates repeated action or confusion at these pages.`;
    if (type === 'trial') return `Trial → onboarding conversion path with ${steps.length} steps. ${modules.some(m=>m.includes('reports')||m.includes('assessment'))? 'Reached core functionality.':'Did not reach core module yet.'}`;
    if (modules.length >= 4) return `Deep explorer touching ${modules.length} modules — high-value power user pattern.`;
    return `${steps.length} total steps across ${j.uniq} unique pages (${Math.round(j.uniq/j.num*100)}% efficiency).`;
  }

  function effColor(pct) {
    if (pct >= 80) return '#067647';
    if (pct >= 55) return '#b54708';
    return '#b42318';
  }

  function processed() {
    return DATA.map(d => {
      const steps = d.path.split(/\\s*→\\s*|\\s*>\\s*|\\s*â†’\\s*/);
      return {
        ...d,
        steps: steps,
        type: journeyType(steps)
      };
    });
  }

  function filtered() {
    let d = processed();
    if (filterType !== 'all') d = d.filter(j => j.type === filterType);
    return d.sort((a,b) => {
      if (sortKey === 'user_pct') return b.upct - a.upct || b.uniq - a.uniq;
      if (sortKey === 'unique_pages') return b.uniq - a.uniq;
      if (sortKey === 'path_occurrence_count') return b.occ - a.occ;
      return 0;
    });
  }

  function renderCard(j, rank, dataIdx) {
    const isExpanded = expanded.has(dataIdx);
    const hasMore = j.steps.length > SHOW_INITIAL;
    const toShow = (!hasMore || isExpanded) ? j.steps : j.steps.slice(0, SHOW_INITIAL);
    const hiddenN = j.steps.length - SHOW_INITIAL;
    const eff = Math.round(j.uniq / j.num * 100);
    const tc = `tb-${j.type}`;

    const seenSoFar = [];
    let stepsHtml = '';
    toShow.forEach((s, si) => {
      const isLoop = seenSoFar.includes(s);
      seenSoFar.push(s);
      const cls = isLoop ? 'step-loop'
        : TRIAL_PAGES.has(s) || s.includes('trial') || s.includes('onboarding') || s.includes('demo') ? 'step-trial'
        : AUTH_PAGES.has(s) || s.includes('sign-in') || s.includes('login') ? 'step-auth'
        : MODULE_PAGES.has(s) || s.includes('cases') || s.includes('transactions') || s.includes('assessment') || s.includes('dashboard') ? 'step-module'
        : SETTING_PAGES.has(s) || s.includes('settings') || s.includes('profile') ? 'step-settings'
        : 'step-other';
      stepsHtml += `<span class="step ${cls}"><span class="step-n">${si+1}</span>${s}</span>`;
      if (si < toShow.length - 1 || (hasMore && !isExpanded)) {
        stepsHtml += `<span class="arrow"><i class="ti ti-arrow-right"></i></span>`;
      }
    });
    if (hasMore && !isExpanded) {
      stepsHtml += `<button class="more-btn" onclick="uj_toggle(${dataIdx})"><i class="ti ti-dots"></i>+${hiddenN} more</button>`;
    } else if (hasMore && isExpanded) {
      stepsHtml += `<button class="collapse-btn" onclick="uj_toggle(${dataIdx})"><i class="ti ti-chevron-up" style="font-size:11px"></i>Collapse</button>`;
    }

    return `<div class="card">
      <div class="card-head">
        <span class="card-rank">#${rank}</span>
        <div class="card-meta">
          <div class="card-title">${typeLabel(j.type)}</div>
          <div class="card-stats">
            <span class="stat"><i class="ti ti-route" style="font-size:13px"></i>&nbsp;<strong>${j.uniq}</strong>&nbsp;unique pages</span>
            <span class="stat"><i class="ti ti-list-numbers" style="font-size:13px"></i>&nbsp;<strong>${j.num}</strong>&nbsp;total steps</span>
            <span class="stat"><i class="ti ti-users" style="font-size:13px"></i>&nbsp;<strong>${j.users}</strong>&nbsp;user${j.users!==1?'s':''}</span>
            <span class="stat"><i class="ti ti-repeat" style="font-size:13px"></i>&nbsp;<strong>${j.occ}×</strong>&nbsp;occurred</span>
            <span class="type-badge ${tc}">${typeLabel(j.type)}</span>
          </div>
        </div>
        <div class="card-right">
          <span class="reach-val">${j.upct.toFixed(2)}%</span>
          <span class="reach-lbl">user reach</span>
          <span class="sessions-pct">${j.pct.toFixed(1)}% of sessions</span>
        </div>
      </div>
      <div class="steps-wrap">
        <div class="steps-inner">${stepsHtml}</div>
      </div>
      <div class="eff-bar-row">
        <span class="eff-lbl">Path efficiency</span>
        <div class="eff-track"><div class="eff-fill" style="width:${eff}%;background:${effColor(eff)}"></div></div>
        <span class="eff-val" style="color:${effColor(eff)}">${eff}% unique</span>
      </div>
      <div class="insight-row">
        <i class="ti ti-bulb"></i>
        <span>${insight(j, j.type)}</span>
      </div>
    </div>`;
  }

  function render() {
    const data = filtered();
    const list = document.getElementById('ujList');
    const btn = document.getElementById('ujLoadBtn');
    const summ = document.getElementById('ujSummaryTxt');

    if (!list || !btn || !summ) {
      setTimeout(render, 100);
      return;
    }

    summ.innerHTML = `Showing <strong>${Math.min(shownCount, data.length)}</strong> of <strong>${data.length}</strong> journey${data.length!==1?'s':''}`;

    if (!data.length) {
      list.innerHTML = '<div class="empty">No journeys match the selected filter.</div>';
      btn.style.display = 'none';
      return;
    }
    
    list.innerHTML = data.slice(0, shownCount).map((j,i) => {
      const originalIdx = DATA.findIndex(d => d.path === j.path);
      return renderCard(j, i+1, originalIdx);
    }).join('');

    const rem = Math.min(5, data.length - shownCount);
    if (rem <= 0) {
      btn.style.display = 'none';
    } else {
      btn.style.display = 'flex';
      btn.innerHTML = `<i class="ti ti-chevron-down"></i>&nbsp;Show ${rem} more journey${rem!==1?'s':''}`;
    }
  }

  window.uj_setSort = function(k) {
    sortKey = k;
    shownCount = 5;
    expanded.clear();
    document.querySelectorAll('.uj-container .sort-btn').forEach(b => b.classList.remove('active'));
    const activeBtn = document.getElementById('sort_' + k);
    if (activeBtn) activeBtn.classList.add('active');
    render();
  };

  window.uj_setType = function(t) {
    filterType = t;
    shownCount = 5;
    expanded.clear();
    document.querySelectorAll('.uj-container .type-btn').forEach(b => {
      b.className = 'type-btn';
    });
    const activeBtn = document.getElementById('type_' + t);
    if (activeBtn) activeBtn.classList.add('t-' + t);
    render();
  };

  window.uj_loadMore = function() {
    shownCount += 5;
    render();
  };

  window.uj_toggle = function(idx) {
    expanded.has(idx) ? expanded.delete(idx) : expanded.add(idx);
    render();
  };

  setTimeout(render, 100);
})();
'''.replace('__JSON_DATA__', json_data).replace('__PLATFORM_NAME__', platform_name)

        # Ensure all IDs and javascript handlers are strictly scoped to this specific chart section
        suffix = id if id else 'default'
        html_markup = html_markup.replace('<div class="uj-container">', f'<div class="uj-container uj-container-{suffix}">')
        html_markup = html_markup.replace('id="sort_user_pct"', f'id="sort_user_pct_{suffix}"')
        html_markup = html_markup.replace('onclick="uj_setSort', f'onclick="uj_setSort_{suffix}')
        html_markup = html_markup.replace('id="sort_unique_pages"', f'id="sort_unique_pages_{suffix}"')
        html_markup = html_markup.replace('id="sort_path_occurrence_count"', f'id="sort_path_occurrence_count_{suffix}"')
        html_markup = html_markup.replace('id="type_all"', f'id="type_all_{suffix}"')
        html_markup = html_markup.replace('onclick="uj_setType', f'onclick="uj_setType_{suffix}')
        html_markup = html_markup.replace('id="type_direct"', f'id="type_direct_{suffix}"')
        html_markup = html_markup.replace('id="type_explorer"', f'id="type_explorer_{suffix}"')
        html_markup = html_markup.replace('id="type_looper"', f'id="type_looper_{suffix}"')
        html_markup = html_markup.replace('id="type_trial"', f'id="type_trial_{suffix}"')
        html_markup = html_markup.replace('id="ujSummaryTxt"', f'id="ujSummaryTxt_{suffix}"')
        html_markup = html_markup.replace('id="ujList"', f'id="ujList_{suffix}"')
        html_markup = html_markup.replace('id="ujLoadBtn"', f'id="ujLoadBtn_{suffix}"')
        html_markup = html_markup.replace('onclick="uj_loadMore()"', f'onclick="uj_loadMore_{suffix}()"')

        js_code = js_code.replace('document.getElementById(\'ujList\')', f'document.getElementById(\'ujList_{suffix}\')')
        js_code = js_code.replace('document.getElementById(\'ujLoadBtn\')', f'document.getElementById(\'ujLoadBtn_{suffix}\')')
        js_code = js_code.replace('document.getElementById(\'ujSummaryTxt\')', f'document.getElementById(\'ujSummaryTxt_{suffix}\')')
        js_code = js_code.replace('document.getElementById(\'sort_\' + k)', f'document.getElementById(\'sort_\' + k + \'_{suffix}\')')
        js_code = js_code.replace('document.getElementById(\'type_\' + t)', f'document.getElementById(\'type_\' + t + \'_{suffix}\')')
        js_code = js_code.replace('document.querySelectorAll(\'.uj-container .sort-btn\')', f'document.querySelectorAll(\'.uj-container-{suffix} .sort-btn\')')
        js_code = js_code.replace('document.querySelectorAll(\'.uj-container .type-btn\')', f'document.querySelectorAll(\'.uj-container-{suffix} .type-btn\')')
        js_code = js_code.replace('window.uj_setSort', f'window.uj_setSort_{suffix}')
        js_code = js_code.replace('window.uj_setType', f'window.uj_setType_{suffix}')
        js_code = js_code.replace('window.uj_loadMore', f'window.uj_loadMore_{suffix}')
        js_code = js_code.replace('window.uj_toggle', f'window.uj_toggle_{suffix}')
        js_code = js_code.replace('uj_toggle(${dataIdx})', f'uj_toggle_{suffix}(${{dataIdx}})')

        ui.html(html_markup, sanitize=False).classes('w-full')
        ui.run_javascript(js_code)

def create_funnel_analysis_row(data: pd.DataFrame, title: str, subtitle: str, label_col: str, value_col: str, mapping: Optional[Dict[str, str]] = None, colors: Optional[Dict[str, str]] = None, id: Optional[str] = None, show_info: bool = True):
    """
    Creates a high-density horizontal funnel chart with drop-off analytics.
    """
    with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header(title, id, show_info, lambda: _download_csv_helper(data, title), data)
        ui.label(subtitle).classes('text-[11px] text-slate-500 mb-6')
        
        if data.empty:
            ui.label('No data available').classes('text-slate-400 italic text-sm py-10 w-full text-center')
            return

        df = data.copy().sort_values(value_col, ascending=False).reset_index(drop=True)
        max_val = df[value_col].max() or 1
        df['prev_val'] = df[value_col].shift(1)
        
        for i, row in df.iterrows():
            raw_label = row[label_col]
            label = mapping.get(raw_label, raw_label) if mapping else raw_label
            val = int(row[value_col]) if pd.notna(row[value_col]) else 0
            pct_of_max = (val / max_val) * 100
            
            bar_color = colors.get(raw_label, '#bae6fd') if colors else '#bae6fd'
            
            drop_text = ""
            if i > 0 and not pd.isna(row['prev_val']):
                prev = int(row['prev_val'])
                if prev > 0:
                    drop = ((val - prev) / prev) * 100
                    drop_text = f'{drop:+.0f}%'

            with ui.row().classes('w-full items-center gap-0 mb-0.5 h-5 flex-nowrap'):
                # 1. Label
                ui.label(label).classes('text-[12px] text-slate-600 w-34 shrink-0 font-medium truncate')
                
                # 2. Bar Container with Percentage Inside
                with ui.element('div').classes('flex-1 bg-slate-50 rounded-sm h-full overflow-hidden border border-slate-100 relative'):
                    # The Bar
                    ui.element('div').classes('h-full transition-all duration-700').style(f'width: {pct_of_max}%; background-color: {bar_color};')
                    # The Percentage (Inside Bar)
                    ui.label(f'{pct_of_max:.0f}%').classes('absolute left-2 top-1/2 -translate-y-1/2 text-[10px] font-bold text-slate-800')
                
                # 3. Absolute Value
                ui.label(f'{val:,}').classes('text-[11px] font-bold text-slate-700 w-14 text-right tabular-nums shrink-0')
                
                # 4. Drop-off Percentage
                ui.label(drop_text).classes('text-[11px] font-bold text-red-500 w-10 text-right shrink-0')

def create_stacked_effectiveness_chart(
    data: pd.DataFrame, 
    title: str, 
    label_col: str, 
    segments: List[Dict[str, str]], 
    subtitle: Optional[str] = None,
    total_col: Optional[str] = None,
    id: Optional[str] = None,
    show_info: bool = True
):
    """
    Creates a high-density 100% stacked horizontal bar chart for rule effectiveness.
    'segments' is a list of: [{'col': 'confirmed', 'label': 'Confirmed', 'color': '#10b981'}, ...]
    """
    with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
        with ui.row().classes('w-full items-start justify-between mb-2'):
            render_chart_header(title, id, show_info, lambda: _download_csv_helper(data, title), data)
            
            # Horizontal Legend
            with ui.row().classes('items-center gap-3'):
                for seg in segments:
                    with ui.row().classes('items-center gap-1'):
                        ui.element('div').classes('w-2 h-2 rounded-full').style(f'background: {seg["color"]}')
                        ui.label(seg['label']).classes('text-[10px] font-bold text-slate-500 uppercase tracking-tighter')
                # Unresolved Legend
                with ui.row().classes('items-center gap-1'):
                    ui.element('div').classes('w-2 h-2 rounded-full').style('background: #e2e8f0')
                    ui.label('Unresolved').classes('text-[10px] font-bold text-slate-400 uppercase tracking-tighter')

        if subtitle:
            ui.label(subtitle).classes('text-[11px] text-slate-500 mb-2')

        if data.empty:
            ui.label('No effectiveness data available').classes('text-slate-400 italic text-sm py-10 w-full text-center')
            return

        # Header Row
        with ui.row().classes('w-full items-center gap-3 mb-2 h-4 flex-nowrap border-b border-slate-100 pb-1'):
            ui.label('Category / Name').classes('text-[9px] font-bold text-slate-400 uppercase tracking-wider w-44 shrink-0')
            ui.label('Outcome Distribution').classes('text-[9px] font-bold text-slate-400 uppercase tracking-wider flex-1')
            ui.label('Total Flags').classes('text-[9px] font-bold text-slate-400 uppercase tracking-wider w-16 text-right shrink-0')

        for _, row in data.head(10).iterrows():
            # If total_col is specified, use that; otherwise sum segments
            if total_col and total_col in row:
                display_total = float(row[total_col])
            else:
                display_total = sum(float(row[seg['col']]) for seg in segments)
                
            label = str(row[label_col])
            
            with ui.row().classes('w-full items-center gap-3 mb-1.5 h-4 flex-nowrap'):
                # 1. Label
                ui.label(label).classes('text-[11px] text-slate-600 w-44 shrink-0 font-medium truncate')
                
                # 2. Stacked Bar
                seg_sum = sum(float(row[seg['col']]) for seg in segments)
                with ui.row().classes('flex-1 h-full rounded-sm overflow-hidden border border-slate-100 gap-0 bg-slate-50'):
                    if seg_sum == 0:
                        # All outcomes are 0 — show full bar as 'Unresolved'
                        ui.element('div').classes('h-full w-full').style('flex-grow: 1; background-color: #e2e8f0').props('title="Unresolved: no resolution actions recorded"')
                    else:
                        for seg in segments:
                            val = float(row[seg['col']])
                            if val > 0:
                                pct = (val / seg_sum) * 100
                                ui.element('div').classes('h-full transition-all duration-500').style(f'flex-grow: {val}; background-color: {seg["color"]}').props(f'title="{seg["label"]}: {int(val)} ({pct:.1f}%)"')
                
                # 3. Total Count
                formatted_total = f"{int(display_total):,}"
                ui.label(formatted_total).classes('text-[10px] font-bold text-slate-500 w-16 text-right tabular-nums shrink-0')

def create_analytical_donut_chart(data: Dict[str, float], title: str, subtitle: Optional[str] = None, footer_text: Optional[str] = None, colors: Optional[List[str]] = None, id: Optional[str] = None, show_info: bool = True):
    """
    Creates a high-density donut chart with centered legend and footer insights.
    """
    if colors is None: colors = ['#b42318', '#1570ef', '#f59e0b', '#7839ee', '#10b981']
    
    total = sum(data.values()) or 1
    chart_data = []
    legend_items = []
    
    for i, (name, val) in enumerate(data.items()):
        color = colors[i % len(colors)]
        pct = (val / total) * 100
        chart_data.append({'value': val, 'name': name, 'itemStyle': {'color': color}})
        legend_items.append({'name': name, 'pct': pct, 'color': color})

    with ui.card().classes('w-full h-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header(title, id, show_info, lambda: _download_csv_helper(data, title), data)
        if subtitle:
            ui.label(subtitle).classes('text-[11px] text-slate-500 mb-4')
        
        ui.echart({
            'tooltip': {'trigger': 'item', 'formatter': '{b}: {c} ({d}%)'},
            'series': [{
                'type': 'pie', 
                'radius': ['55%', '80%'],
                'label': {'show': False},
                'emphasis': {'scale': True, 'scaleSize': 8},
                'data': chart_data
            }]
        }).classes('h-40 w-full')
        
        # Centered Legend
        with ui.row().classes('w-full justify-center gap-4 mt-2'):
            for item in legend_items:
                with ui.row().classes('items-center gap-1.5'):
                    ui.element('div').classes('w-2 h-2 rounded-full').style(f'background: {item["color"]}')
                    ui.label(f'{item["name"]} ({item["pct"]:.0f}%)').classes('text-[11px] font-semibold text-slate-700')
        
        if footer_text:
            ui.html(f'<div style="font-size:11px;color:#667085;text-align:center;margin-top:12px;padding-top:8px;border-top:1px solid #f2f4f7;width:100%">'
                    f'{footer_text}</div>')

def create_dual_axis_trend_chart(data: pd.DataFrame, title: str, subtitle: str, x_col: str, bar_col: str, line_col: str, bar_label: str, line_label: str, id: Optional[str] = None, show_info: bool = True):
    """
    Creates a high-density dual-axis trend chart (bars + line).
    """
    with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
        with ui.row().classes('w-full items-start justify-between mb-2'):
            render_chart_header(title, id, show_info, lambda: _download_csv_helper(data, title), data)
            
            # Custom Legend
            with ui.row().classes('items-center gap-4'):
                with ui.row().classes('items-center gap-1.5'):
                    ui.element('div').classes('w-3 h-3 rounded-sm bg-[#b2ddff]')
                    ui.label(bar_label).classes('text-[11px] font-bold text-slate-500')
                with ui.row().classes('items-center gap-1.5'):
                    ui.element('div').classes('w-3 h-0.5 bg-[#067647] border-b border-dashed border-[#067647]')
                    ui.element('div').classes('w-1.5 h-1.5 rounded-full bg-[#067647] -ml-1')
                    ui.label(line_label).classes('text-[11px] font-bold text-slate-500')

        if data.empty:
            ui.label('No trend data available').classes('text-slate-400 italic text-sm py-10 w-full text-center')
            return

        x_data = data[x_col].tolist()
        # Format X-axis labels if they are dates
        if len(x_data) > 0 and (isinstance(x_data[0], str) or hasattr(x_data[0], 'strftime')):
            try:
                x_data = [pd.to_datetime(d).strftime('%b %d') for d in x_data]
            except:
                pass

        ui.echart({
            'tooltip': {'trigger': 'axis', 'backgroundColor': 'rgba(255, 255, 255, 0.98)', 'textStyle': {'color': '#1e293b', 'fontSize': 11}},
            'grid': {'left': '5%', 'right': '5%', 'top': '10%', 'bottom': '12%', 'containLabel': True},
            'xAxis': {
                'type': 'category',
                'data': x_data,
                'axisLabel': {'fontSize': 10, 'color': '#64748b', 'margin': 12},
                'axisTick': {'show': False},
                'axisLine': {'lineStyle': {'color': '#f1f5f9'}}
            },
            'yAxis': [
                {
                    'type': 'value',
                    'name': '',
                    'axisLabel': {'fontSize': 10, 'color': '#64748b'},
                    'splitLine': {'lineStyle': {'color': '#f1f5f9', 'type': 'dashed'}}
                },
                {
                    'type': 'value',
                    'name': '',
                    'min': 0, 'max': 100,
                    'axisLabel': {'fontSize': 10, 'color': '#067647', 'formatter': '{value}%'},
                    'splitLine': {'show': False}
                }
            ],
            'series': [
                {
                    'name': bar_label,
                    'type': 'bar',
                    'data': data[bar_col].tolist(),
                    'itemStyle': {'color': '#b2ddff', 'borderRadius': [2, 2, 0, 0]},
                    'barMaxWidth': 30
                },
                {
                    'name': line_label,
                    'type': 'line',
                    'yAxisIndex': 1,
                    'data': data[line_col].tolist(),
                    'itemStyle': {'color': '#067647'},
                    'lineStyle': {'width': 2, 'type': 'dashed'},
                    'symbol': 'circle',
                    'symbolSize': 6,
                    'smooth': True
                }
            ]
        }).classes('h-52 w-full')


def create_flag_rate_chart(data: pd.DataFrame, title: str, subtitle: str, label_col: str, rate_col: str, count_col: str, total_col: str, id: Optional[str] = None, show_info: bool = True):
    """
    Creates a gorgeous horizontal bar chart for organization flag rates.
    Color codes the bar:
      - Red fill if rate > 5%
      - Amber fill if rate > 2%
      - Green fill otherwise
    Shows the actual percentage inside the bar and (Flagged / Total) on the right.
    """
    with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header(title, id, show_info, lambda: _download_csv_helper(data, title), data)
        ui.label(subtitle).classes('text-[11px] text-slate-500 mb-6')
        
        if data.empty:
            ui.label('No data available').classes('text-slate-400 italic text-sm py-10 w-full text-center')
            return

        # Header Row
        with ui.row().classes('w-full items-center gap-3 mb-2 h-4 flex-nowrap border-b border-slate-100 pb-1'):
            ui.label('Organisation').classes('text-[9px] font-bold text-slate-400 uppercase tracking-wider w-44 shrink-0')
            ui.label('Flag Rate (%)').classes('text-[9px] font-bold text-slate-400 uppercase tracking-wider flex-1')
            ui.label('Flagged / Total').classes('text-[9px] font-bold text-slate-400 uppercase tracking-wider w-24 text-right shrink-0')

        for _, row in data.head(10).iterrows():
            org_name = str(row[label_col])
            rate = float(row[rate_col]) if pd.notna(row[rate_col]) else 0.0
            flagged = int(row[count_col]) if pd.notna(row[count_col]) else 0
            total = int(row[total_col]) if pd.notna(row[total_col]) else 0
            
            # Color coding based on thresholds: red > 5%, amber > 2%, green otherwise
            if rate > 5.0:
                fill_color = '#ef4444'     # Red fill
            elif rate > 2.0:
                fill_color = '#f59e0b'     # Amber fill
            else:
                fill_color = '#10b981'     # Green fill

            # Map 0%-10% flag rate to 0%-100% of the bar width, capped at 100%
            visual_pct = min((rate / 10.0) * 100, 100) if rate > 0 else 0

            with ui.row().classes('w-full items-center gap-3 mb-1.5 h-5 flex-nowrap'):
                # 1. Organisation Label
                ui.label(org_name).classes('text-[11px] text-slate-600 w-44 shrink-0 font-medium truncate')
                
                # 2. Progress Bar
                with ui.element('div').classes('flex-1 rounded-sm h-full overflow-hidden relative border border-slate-100 bg-slate-50'):
                    # The filled part
                    ui.element('div').classes('h-full transition-all duration-700').style(f'width: {visual_pct}%; background-color: {fill_color};')
                    # Rate text overlays perfectly
                    ui.label(f'{rate:.2f}%').classes('absolute left-2 top-1/2 -translate-y-1/2 text-[10px] font-bold text-slate-800')
                
                # 3. Flagged / Total Count
                ui.label(f'{flagged:,} / {total:,}').classes('text-[10px] font-bold text-slate-500 w-24 text-right tabular-nums shrink-0')


def create_engagement_analysis_charts(freq_df: pd.DataFrame, time_df: pd.DataFrame, depth_df: pd.DataFrame, id_1: Optional[str] = 'engagement_frequency_segments', id_2: Optional[str] = 'engagement_time_distribution', id_3: Optional[str] = 'engagement_session_depth', show_info: bool = True):
    colors = ['#f43f5e', '#d97706', '#3b82f6', '#34d399', '#059669']
    
    with ui.grid(columns=3).classes('w-full gap-6 mb-6 items-stretch grid-cols-1 lg:grid-cols-3'):
        # Chart 1: User Frequency Segments
        with ui.card().classes('p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full'):
            with ui.row().classes('w-full items-start justify-between mb-1'):
                render_chart_header('User Frequency Segments', id_1, show_info, lambda: _download_csv_helper(freq_df, 'User Frequency Segments'), freq_df)
            
            if not freq_df.empty:
                # Map names to clean categories
                name_map = {
                    'One-time': 'One-time',
                    'Occasional (2–3)': 'Occasional',
                    'Regular (4–7)': 'Regular',
                    'Frequent (8–14)': 'Frequent',
                    'Power User (15+)': 'Power User'
                }
                x_data = [name_map.get(str(x), str(x)) for x in freq_df['frequency_segment']]
                # Plot 'pct' on y-axis as shown in the screenshot (values go up to 35)
                y_data = []
                for i, pct in enumerate(freq_df['pct']):
                    y_data.append({
                        'value': float(pct),
                        'itemStyle': {'color': colors[i % len(colors)]}
                    })
                
                ui.echart({
                    'tooltip': {
                        'trigger': 'axis',
                        'axisPointer': {'type': 'shadow'},
                        'formatter': '{b}: {c}%'
                    },
                    'grid': {
                        'left': '3%',
                        'right': '4%',
                        'top': '8%',
                        'bottom': '12%',
                        'containLabel': True
                    },
                    'xAxis': {
                        'type': 'category',
                        'data': x_data,
                        'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                        'axisLabel': {'color': '#64748b', 'fontWeight': 'semibold', 'fontSize': 9, 'interval': 0, 'rotate': 15}
                    },
                    'yAxis': {
                        'type': 'value',
                        'axisLine': {'show': False},
                        'axisTick': {'show': False},
                        'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                    },
                    'series': [{
                        'type': 'bar',
                        'barWidth': '55%',
                        'data': y_data,
                        'showBackground': True,
                        'backgroundStyle': {
                            'color': 'rgba(180, 180, 180, 0.05)'
                        }
                    }]
                }).classes('w-full h-64')
            else:
                ui.label('No frequency data available').classes('text-slate-500 italic m-auto')

        # Chart 2: Session Time Distribution
        with ui.card().classes('p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full'):
            with ui.row().classes('w-full items-start justify-between mb-1'):
                render_chart_header('Session Time Distribution', id_2, show_info, lambda: _download_csv_helper(time_df, 'Session Time Distribution'), time_df)
            
            if not time_df.empty:
                x_data = [str(x) for x in time_df['time_bucket']]
                y_data = []
                for i, pct in enumerate(time_df['pct']):
                    y_data.append({
                        'value': float(pct),
                        'itemStyle': {'color': colors[i % len(colors)]}
                    })
                
                ui.echart({
                    'tooltip': {
                        'trigger': 'axis',
                        'axisPointer': {'type': 'shadow'},
                        'formatter': '{b}: {c}%'
                    },
                    'grid': {
                        'left': '3%',
                        'right': '4%',
                        'top': '8%',
                        'bottom': '12%',
                        'containLabel': True
                    },
                    'xAxis': {
                        'type': 'category',
                        'data': x_data,
                        'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                        'axisLabel': {'color': '#64748b', 'fontWeight': 'semibold', 'fontSize': 9, 'interval': 0, 'rotate': 15}
                    },
                    'yAxis': {
                        'type': 'value',
                        'axisLine': {'show': False},
                        'axisTick': {'show': False},
                        'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                    },
                    'series': [{
                        'type': 'bar',
                        'barWidth': '55%',
                        'data': y_data,
                        'showBackground': True,
                        'backgroundStyle': {
                            'color': 'rgba(180, 180, 180, 0.05)'
                        }
                    }]
                }).classes('w-full h-64')
            else:
                ui.label('No time bucket data available').classes('text-slate-500 italic m-auto')

        # Chart 3: Session Depth (Pages per Session)
        with ui.card().classes('p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full'):
            with ui.row().classes('w-full items-start justify-between mb-1'):
                render_chart_header('Session Depth', id_3, show_info, lambda: _download_csv_helper(depth_df, 'Session Depth'), depth_df)
            
            if not depth_df.empty:
                x_data = [str(x) for x in depth_df['depth_bucket']]
                y_data = []
                for i, pct in enumerate(depth_df['pct']):
                    y_data.append({
                        'value': float(pct),
                        'itemStyle': {'color': colors[i % len(colors)]}
                    })
                
                ui.echart({
                    'tooltip': {
                        'trigger': 'axis',
                        'axisPointer': {'type': 'shadow'},
                        'formatter': '{b}: {c}%'
                    },
                    'grid': {
                        'left': '3%',
                        'right': '4%',
                        'top': '8%',
                        'bottom': '12%',
                        'containLabel': True
                    },
                    'xAxis': {
                        'type': 'category',
                        'data': x_data,
                        'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                        'axisLabel': {'color': '#64748b', 'fontWeight': 'semibold', 'fontSize': 9, 'interval': 0, 'rotate': 15}
                    },
                    'yAxis': {
                        'type': 'value',
                        'axisLine': {'show': False},
                        'axisTick': {'show': False},
                        'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                    },
                    'series': [{
                        'type': 'bar',
                        'barWidth': '55%',
                        'data': y_data,
                        'showBackground': True,
                        'backgroundStyle': {
                            'color': 'rgba(180, 180, 180, 0.05)'
                        }
                    }]
                }).classes('w-full h-64')
            else:
                ui.label('No depth bucket data available').classes('text-slate-500 italic m-auto')


def create_geographic_distribution_table(df: pd.DataFrame, platform_name: str, id: str = 'map_distribution', show_info: bool = True):
    with ui.card().classes('w-full p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header('Geographic distribution', id, show_info, lambda: _download_csv_helper(df, 'Geographic distribution'), df)
        
        if df is None or df.empty:
            ui.label('No geographic data available').classes('text-slate-400 italic text-sm py-10 w-full text-center')
            return
            
        # Table Header
        with ui.row().classes('w-full items-center py-2 border-b border-slate-100 flex-nowrap pr-4 gap-0'):
            ui.label('REGION / STATE').classes('text-[10px] font-bold text-slate-400 uppercase tracking-wider w-[24%] shrink-0')
            ui.label('SIGNED-IN USERS').classes('text-[10px] font-bold text-slate-400 uppercase tracking-wider w-[18%] text-right shrink-0 pr-2')
            ui.label('SESSIONS').classes('text-[10px] font-bold text-slate-400 uppercase tracking-wider w-[18%] text-right shrink-0 pr-2')
            ui.label('ENGAGEMENT RATE').classes('text-[10px] font-bold text-slate-400 uppercase tracking-wider w-[20%] text-center shrink-0')
            ui.label('KEY EVENTS').classes('text-[10px] font-bold text-slate-400 uppercase tracking-wider w-[20%] text-right shrink-0 pr-2')
            
        # Scrollable Rows Container
        with ui.column().classes('w-full max-h-[350px] overflow-y-auto pr-1 gap-0'):
            # Table Rows
            for _, row in df.iterrows():
                region = str(row.get('region', '')).strip()
                if not region or region.lower() in ('none', 'nan', 'null', '(not set)'):
                    region = 'Unknown Region'
                
                signed_in = int(row.get('signed_in_users', 0))
                sessions = int(row.get('sessions', 0))
                eng_rate = float(row.get('avg_engagement_rate_pct', 0.0))
                key_events = int(row.get('key_events', 0))
                
                # Cap engagement rate at 100.0% to keep data realistic and professional in case of mock data anomalies
                if eng_rate > 100.0:
                    eng_rate = 100.0
                elif eng_rate < 0.0:
                    eng_rate = 0.0
                
                # Determine color pill for engagement rate
                if eng_rate >= 80:
                    pill_classes = 'bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full font-bold text-xs'
                elif eng_rate >= 65:
                    pill_classes = 'bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full font-bold text-xs'
                else:
                    pill_classes = 'bg-rose-50 text-rose-700 px-2 py-0.5 rounded-full font-bold text-xs'
                    
                with ui.row().classes('w-full items-center py-3 border-b border-slate-100 flex-nowrap hover:bg-slate-50 transition-colors gap-0'):
                    ui.label(region).classes('text-sm font-semibold text-slate-700 w-[24%] shrink-0 truncate pr-2')
                    ui.label(f'{signed_in:,}').classes('text-sm text-slate-600 w-[18%] text-right shrink-0 pr-2 tabular-nums')
                    ui.label(f'{sessions:,}').classes('text-sm text-slate-600 w-[18%] text-right shrink-0 pr-2 tabular-nums')
                    with ui.row().classes('w-[20%] justify-center shrink-0'):
                        ui.label(f'{eng_rate:.0f}%').classes(pill_classes)
                    ui.label(f'{key_events:,}').classes('text-sm text-slate-600 w-[20%] text-right shrink-0 pr-2 tabular-nums')


def create_device_browser_breakdown(df: pd.DataFrame, platform_name: str, id: str = 'device_browser', show_info: bool = True):
    with ui.card().classes('flex-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header('Device & browser breakdown', id, show_info, lambda: _download_csv_helper(df, 'Device Breakdown'), df)
        
        if df is None or df.empty:
            ui.label('No device or browser data available').classes('text-slate-400 italic text-sm py-10 w-full text-center')
            return
            
        # 1. Donut Chart (Device Category Mix)
        device_df = df.groupby('device_category', as_index=False).agg({'unique_users': 'sum'})
        device_data = []
        colors = []
        color_map = {
            'desktop': '#1570ef',
            'mobile': '#b42318',
            'tablet': '#94a3b8',
            'smarttv': '#64748b'
        }
        for _, row in device_df.iterrows():
            cat = str(row['device_category'])
            val = int(row['unique_users'])
            device_data.append({'value': val, 'name': cat.capitalize()})
            colors.append(color_map.get(cat.lower(), '#cbd5e1'))
            
        chart_options = {
            'tooltip': {'trigger': 'item'},
            'legend': {
                'top': '0%',
                'left': 'left',
                'icon': 'circle',
                'textStyle': {'color': '#64748b', 'fontWeight': 'bold'}
            },
            'series': [{
                'type': 'pie',
                'radius': ['40%', '70%'],
                'avoidLabelOverlap': False,
                'label': {'show': False},
                'emphasis': {'label': {'show': False}},
                'labelLine': {'show': False},
                'data': device_data,
                'color': colors
            }]
        }
        
        with ui.column().classes('w-full items-center mb-6'):
            ui.echart(chart_options).classes('w-full h-44')
            
        # 2. Browser Mix
        ui.label('Browser mix').classes('text-sm font-bold text-slate-800 mb-3')
        
        browser_df = df.groupby('browser', as_index=False).agg({'unique_users': 'sum'}).sort_values('unique_users', ascending=False)
        browser_total = browser_df['unique_users'].sum() or 1
        
        for _, row in browser_df.head(5).iterrows():
            browser_name = str(row['browser'])
            browser_users = int(row['unique_users'])
            pct = (browser_users / browser_total) * 100
            
            with ui.row().classes('w-full items-center gap-4 mb-2 flex-nowrap'):
                ui.label(browser_name).classes('text-xs font-semibold text-slate-600 w-20 shrink-0 truncate')
                with ui.element('div').classes('flex-1 bg-slate-100 rounded-full h-2 overflow-hidden'):
                    ui.element('div').classes('h-full bg-sky-200 rounded-full').style(f'width: {pct:.1f}%')
                ui.label(f'{pct:.0f}%').classes('text-xs font-bold text-slate-600 w-8 text-right shrink-0')


def create_weekly_signup_login_trend(df: pd.DataFrame, id: str = 'signup_login_trend', show_info: bool = True):
    with ui.card().classes(f'w-full p-6 pt-4 {ThemeManager.get_card_style()}'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header('Weekly Sign-Up & Login Trend', id, show_info, lambda: ui.run_javascript(f"downloadChart('{chart_el.id}', 'Weekly Sign-Up and Login Trend')"), df)
        
        if df is None or df.empty:
            ui.label('No trend data available').classes('text-slate-400 italic text-sm py-20 w-full text-center')
            return
            
        # Format the x-axis labels as month abbreviations
        df = df.copy()
        df['month_label'] = pd.to_datetime(df['week_start']).dt.strftime('%b')
        
        weeks = df['month_label'].tolist()
        signups = df['signups'].tolist()
        logins = df['logins'].tolist()
        
        chart_options = {
            'tooltip': {
                'trigger': 'axis',
                'axisPointer': {'type': 'cross'}
            },
            'legend': {
                'data': ['Signups', 'Logins'],
                'top': 0
            },
            'xAxis': [{
                'type': 'category',
                'data': weeks,
                'axisLabel': {'fontSize': 10, 'color': '#64748b', 'fontWeight': 'bold'}
            }],
            'yAxis': [
                {
                    'type': 'value',
                    'name': 'Signups',
                    'position': 'left',
                    'axisLabel': {'color': '#16a34a', 'fontWeight': 'bold'},
                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                },
                {
                    'type': 'value',
                    'name': 'Logins',
                    'position': 'right',
                    'axisLabel': {'color': '#2563eb', 'fontWeight': 'bold'},
                    'splitLine': {'show': False}
                }
            ],
            'series': [
                {
                    'name': 'Signups',
                    'type': 'line',
                    'data': signups,
                    'smooth': True,
                    'yAxisIndex': 0,
                    'symbol': 'circle',
                    'symbolSize': 8,
                    'lineStyle': {'color': '#16a34a', 'width': 3},
                    'itemStyle': {'color': '#16a34a', 'borderColor': '#ffffff', 'borderWidth': 2}
                },
                {
                    'name': 'Logins',
                    'type': 'line',
                    'data': logins,
                    'smooth': True,
                    'yAxisIndex': 1,
                    'symbol': 'circle',
                    'symbolSize': 8,
                    'lineStyle': {'color': '#2563eb', 'width': 3, 'type': 'dashed'},
                    'itemStyle': {'color': '#2563eb', 'borderColor': '#ffffff', 'borderWidth': 2}
                }
            ],
            'grid': {
                'left': '8%',
                'right': '8%',
                'top': '15%',
                'bottom': '10%',
                'containLabel': True
            }
        }
        
        chart_el = ui.echart(chart_options).classes('w-full h-80')


def create_dormant_organizations_card(df: pd.DataFrame, platform_name: str, id: str = 'churn_risk_dormant', show_info: bool = True):
    with ui.card().classes(f'w-full p-6 pt-4 {ThemeManager.get_card_style()}'):
        with ui.row().classes('w-full items-start justify-between mb-1'):
            render_chart_header('Churn Risk — Dormant Orgs', id, show_info, lambda: _download_csv_helper(df, 'Dormant Organizations'), df)
        
        if df is None or df.empty:
            ui.label('No dormant organizations found').classes('text-slate-400 italic text-sm py-10 w-full text-center')
            return
            
        with ui.column().classes('w-full gap-3 mt-2 max-h-[320px] overflow-y-auto pr-1'):
            for _, row in df.iterrows():
                org_name = str(row.get('org_name', 'Unknown'))
                days_dormant = int(row.get('days_dormant', 0))
                
                # Determine risk level and colors
                if days_dormant >= 30:
                    dot_color = 'bg-rose-500'
                    pill_bg = 'bg-[#fffbeb]'
                    pill_text = 'text-[#d97706]'
                    pill_border = 'border border-[#fef3c7]'
                    risk_label = 'High Risk'
                else:
                    dot_color = 'bg-amber-600'
                    pill_bg = 'bg-[#fef3c7]'
                    pill_text = 'text-[#b45309]'
                    pill_border = 'border border-[#fde68a]'
                    risk_label = 'Med Risk'
                
                # Render Row
                with ui.row().classes('w-full items-center justify-between px-4 py-3 bg-[#f8f6f0] rounded-xl hover:bg-slate-50 transition-colors flex-nowrap'):
                    with ui.row().classes('items-center gap-3 flex-nowrap'):
                        ui.element('span').classes(f'w-2 h-2 rounded-full {dot_color} shrink-0')
                        ui.label(org_name).classes('text-sm font-semibold text-slate-700 truncate max-w-[180px]')
                    
                    with ui.row().classes('items-center gap-3 flex-nowrap shrink-0'):
                        ui.label(risk_label).classes(f'{pill_bg} {pill_text} {pill_border} rounded-full px-3 py-0.5 font-bold text-[10px] uppercase tracking-wider')
                        ui.label(f'{days_dormant}d dormant').classes('text-sm font-semibold text-rose-600')
