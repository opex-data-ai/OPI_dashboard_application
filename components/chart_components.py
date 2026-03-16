"""
Reusable chart components for displaying KPI metrics
"""
from nicegui import ui
import pandas as pd
import plotly.express as px
import pycountry
from typing import List, Dict, Any, Optional
from components.theme_manager import ThemeManager

def create_kpi_metrics(metrics: List[Dict[str, Any]]):
    """
    Create KPI metric cards displaying key statistics in a consistent grid layout.
    
    Args:
        metrics: List of dicts with keys:
            - label: Metric name/label
            - value: Metric value
            - icon: Material icon name (optional)
            - color: Color scheme (default: blue)
            - subtitle: Additional context text (optional)
    """
    # Use a responsive grid that adapts columns based on screen size
    # items-stretch ensures all cards in a row have the same height
    grid_cols = len(metrics)
    with ui.grid(columns=grid_cols).classes(f'w-full gap-4 mb-6 items-stretch grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-{grid_cols}'):
        for metric in metrics:
            # Handle theme colors
            color_name = metric.get('color', 'blue')
            theme = ThemeManager.get_current_theme()
            
            # If monochrome, overriding colors to grayscale/slate
            if theme == 'monochrome':
                icon_color = 'text-slate-700'
                card_style = ThemeManager.get_card_style() # Border slate-200
            else:
                icon_color = f'text-{color_name}-500'
                card_style = ThemeManager.get_card_style()

            # h-full ensures the card fills the grid cell height
            with ui.card().classes(f'h-full p-6 {card_style} hover:shadow-lg transition-all flex flex-col'):
                # Header: Label
                with ui.row().classes('w-full items-start mb-2 shrink-0'):   
                    ui.label(metric['label']).classes(ThemeManager.TYPOGRAPHY['small'] + ' leading-tight')
                
                # Content Area: Value and Subtitle (pushed to bottom if needed)
                with ui.column().classes('mt-auto w-full'):
                    # Value
                    value = metric['value']
                    if isinstance(value, (int, float)):
                        formatted_value = f"{value:,.0f}" if isinstance(value, int) or (isinstance(value, float) and value.is_integer()) else f"{value:,.2f}"
                    else:
                        formatted_value = str(value)
                    
                    ui.label(formatted_value).classes('text-2xl font-bold text-slate-900 leading-none break-words')
                    
                    # Subtitle (if provided)
                    if 'subtitle' in metric:
                        ui.label(metric['subtitle']).classes('text-xs text-slate-500 mt-2 leading-relaxed')



_iso_cache = {}

def get_iso_code(country_name):
    """Helper to get ISO alpha-3 code for country names with caching"""
    if not country_name or pd.isna(country_name):
        return None
    if country_name in _iso_cache:
        return _iso_cache[country_name]
    try:
        # Normalize common names
        norm_map = {
            'USA': 'United States',
            'UK': 'United Kingdom',
            'South Korea': 'Korea, Republic of',
            'Russia': 'Russian Federation',
            'Vietnam': 'Viet Nam'
        }
        name = norm_map.get(country_name, country_name)
        code = pycountry.countries.search_fuzzy(name)[0].alpha_3
        _iso_cache[country_name] = code
        return code
    except:
        _iso_cache[country_name] = None
        return None

def create_country_metrics_row(data: pd.DataFrame, title: str, value_col: Any):
    """
    Create a dual-card layout: 2/3 width Plotly Map and 1/3 width Top 7 Table
    Supports value_col as a string or a list of strings (which will be summed).
    """
    # Create a copy so we don't modify the original DF passed in
    df_copy = data.copy()
    
    # Determine the active data column
    if isinstance(value_col, list):
        # Filter to only existing columns in the dataframe
        valid_cols = [c for c in value_col if c in df_copy.columns]
        if valid_cols:
            df_copy['display_value'] = df_copy[valid_cols].sum(axis=1)
        else:
            df_copy['display_value'] = 0
        active_col = 'display_value'
    else:
        active_col = value_col
        # If the column doesn't exist, create it with 0s to avoid errors
        if active_col not in df_copy.columns:
            df_copy[active_col] = 0
    
    with ui.row().classes('w-full gap-4 mb-6 items-stretch'):
        # 1. Map Card (2/3 width)   
        with ui.card().classes('flex-[2] p-6 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
            ui.label(title).classes('text-xl font-bold text-slate-900 mb-2')
            
            if df_copy.empty:
                ui.label('No country data available').classes('text-slate-500 italic py-20 w-full text-center')
            else:
                df_copy['iso_code'] = df_copy['country'].apply(get_iso_code)
                data_clean = df_copy.dropna(subset=['iso_code'])
                
                # Create choropleth map
                fig = px.choropleth(
                    data_clean,
                    locations='iso_code',
                    color=active_col,
                    hover_name='country',
                    hover_data={active_col: True, 'iso_code': False, 'country': False},
                    color_continuous_scale=['#e0f2fe', '#7dd3fc', '#0ea5e9', '#0284c7', '#0369a1'],
                    labels={active_col: 'Users'}
                )
                
                fig.update_layout(
                    geo=dict(
                        showframe=False,
                        showcoastlines=True,
                        coastlinecolor="#cbd5e1",
                        projection_type='natural earth',
                        bgcolor='rgba(0,0,0,0)',
                        showland=True,
                        landcolor='#f8fafc',
                        showocean=False,
                    ),
                    height=500,
                    margin=dict(l=0, r=0, t=0, b=0),
                    coloraxis_showscale=False # Keep it clean like the image
                )
                
                ui.plotly(fig).classes('w-full')

        # 2. Top Countries Table Card (1/3 width)
        with ui.card().classes('flex-[1] p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
            ui.label('Top Countries').classes('text-sm font-semibold text-slate-500 mb-4 uppercase tracking-wider')
            
            if df_copy.empty:
                ui.label('No data available').classes('text-slate-500 italic py-10 w-full text-center')
            else:
                top_countries = df_copy.nlargest(7, active_col).copy()
                
                columns = [
                    {'name': 'country', 'label': 'COUNTRY', 'field': 'country', 'align': 'left'},
                    {'name': 'users', 'label': 'ACTIVE USERS', 'field': active_col, 'align': 'right'},
                ]
                
                rows = top_countries.to_dict('records')
                # Format numbers
                for row in rows:
                    val = row[active_col]
                    if val >= 1000:
                        row[active_col] = f"{val/1000:.1f}K"
                    else:
                        row[active_col] = str(int(val))
                
                ui.table(
                    columns=columns,
                    rows=rows,
                    row_key='country'
                ).classes('w-full border-none shadow-none text-slate-800').props('flat bordered=false hide-bottom pagination="{rowsPerPage: 0}"')

def create_comparison_cards(comparisons: List[Dict[str, Any]]):
    """
    Create comparison cards showing metric A vs metric B
    
    Args:
        comparisons: List of dicts with keys:
            - title: Card title
            - metric_a_name: Name of first metric
            - metric_a_value: Value of first metric
            - metric_b_name: Name of second metric
            - metric_b_value: Value of second metric
            - icon: Material icon name
            - color: Color scheme (blue, green, orange, purple)
            - pct_method: Method to calculate percentage (divide: [Metrics B/ Metrics A] * 100 or Total: Metrics A/ [Metrics A + Metrics B] * 100)
    """
    with ui.row().classes('w-full gap-4 mb-6'):
        for comp in comparisons:
            with ui.card().classes('flex-1 p-6 border border-slate-200 shadow-sm bg-white rounded-xl hover:shadow-lg transition-shadow'):
                # Header with icon
                with ui.row().classes('w-full justify-between items-start mb-4'):
                    ui.label(comp['title']).classes('text-sm text-slate-600 font-semibold')
                    ui.icon(comp['icon']).classes(f'text-3xl text-{comp["color"]}-500')
                
                # Metrics comparison
                with ui.row().classes('w-full gap-2 items-center'):
                    # Metric A
                    with ui.column().classes('flex-1 w-full items-start'):
                        ui.label(comp['metric_a_name']).classes('text-xs text-slate-500 mb-1')
                        ui.label(f"{comp['metric_a_value']:,}").classes('text-2xl font-bold text-slate-900')
                    
                    # VS divider
                    ui.label('vs').classes('text-lg font-bold text-slate-400')
                    
                    # Metric B
                    with ui.column().classes('flex-1 w-full items-end'):
                        ui.label(comp['metric_b_name']).classes('text-xs text-slate-500 mb-1')
                        ui.label(f"{comp['metric_b_value']:,}").classes('text-2xl font-bold text-slate-900')
                
                # Percentage bar
                if comp['metric_a_value'] > 0:
                    method = comp.get('pct_method', 'divide')
                    if method == 'divide':
                        percentage = (comp['metric_b_value'] / comp['metric_a_value']) * 100
                    elif method == 'total':
                        total = comp['metric_a_value'] + comp['metric_b_value']
                        percentage = (comp['metric_a_value'] / total) * 100
                    else:
                        percentage = (comp['metric_b_value'] / comp['metric_a_value']) * 100
                    with ui.row().classes('w-full items-center gap-2 mt-3'):
                        with ui.element('div').classes('flex-1 h-2 bg-slate-200 rounded-full overflow-hidden'):
                            ui.element('div').classes(f'h-full bg-{comp["color"]}-500').style(f'width: {min(percentage, 100):.1f}%')
                        ui.label(f'{percentage:.1f}%').classes('text-xs text-slate-600 font-semibold')




def create_bar_chart(data: pd.DataFrame, title: str, x_col: str, y_cols: List[str], colors: List[Any] = None, height: str = 'h-96', labels: Optional[List[str]] = None, show_legend: bool = True):
    """
    Create a horizontal bar chart comparing multiple metrics
    
    Args:
        data: DataFrame with metrics
        title: Chart title
        x_col: Column name for x-axis (categories)
        y_cols: List of column names for y-axis (values)
        colors: List of colors or ECharts color objects
        height: Tailwind height class
        labels: Optional list of custom labels for the legend
        show_legend: Whether to show the legend (default: True)
    """
    if colors is None:
        # Use theme manager colors if none provided
        colors = ThemeManager.get_chart_colors()
    
    # Determine display labels: use provided labels if available and matching length, otherwise fallback to column names
    display_labels = labels if labels and len(labels) == len(y_cols) else [col.replace('_', ' ').title() for col in y_cols]
    
    with ui.card().classes(f'w-full p-6 {ThemeManager.get_card_style()}'):
        if title:
            ui.label(title).classes(ThemeManager.TYPOGRAPHY['h3'] + ' mb-4')
        
        categories = data[x_col].tolist()
        
        ui.echart({
            'xAxis': {
                'type': 'value',
                'splitLine': {'show': False},
                'axisLine': {'show': True},
                'axisTick': {'show': True}
            },
            'yAxis': {
                'type': 'category',
                'data': categories,
                'axisLine': {'show': True},
                'axisTick': {'show': True},
                'axisLabel': {'fontSize': 12}
            },
            'series': [
                {
                    'name': display_labels[idx],
                    'type': 'bar',
                    'data': data[col].tolist(),
                    'itemStyle': {'color': colors[idx % len(colors)]},
                    'label': {'show': True, 'position': 'right', 'fontSize': 12, 'fontWeight': 'bold'}
                }
                for idx, col in enumerate(y_cols)
            ],
            'tooltip': {
                'trigger': 'axis',
                'axisPointer': {'type': 'shadow'}
            },
            'legend': {
                'show': show_legend,
                'data': display_labels,
                'top': 10,
                'right': 10
            },
            'grid': {
                'left': '3%',
                'right': '4%',
                'top': '15%',
                'bottom': '3%',
                'containLabel': True
            }
        }).classes(f'w-full {height}')



def create_column_chart(data: pd.DataFrame, title: str, x_col: str, y_cols: List[str], colors: List[Any] = None, height: str = 'h-96'):
    """
    Create a vertical column chart comparing multiple metrics
    
    Args:
        data: DataFrame with metrics
        title: Chart title
        x_col: Column name for x-axis (categories)
        y_cols: List of column names for y-axis (values)
        colors: List of colors or ECharts color objects
        height: Tailwind height class
    """
    if colors is None:
        colors = ThemeManager.get_chart_colors()
    
    with ui.card().classes(f'w-full p-6 {ThemeManager.get_card_style()}'):
        if title:
            ui.label(title).classes(ThemeManager.TYPOGRAPHY['h3'] + ' mb-4')
        
        categories = data[x_col].tolist()
        
        ui.echart({
            'xAxis': {
                'type': 'category',
                'data': categories,
                'axisLine': {'show': True},
                'axisTick': {'show': True},
                'axisLabel': {'rotate': 0, 'fontSize': 12}
            },
            'yAxis': {
                'type': 'value',
                'splitLine': {'show': False},
                'axisLine': {'show': True},
                'axisTick': {'show': True}
            },
            'series': [
                {
                    'name': col.replace('_', ' ').title(),
                    'type': 'bar',
                    'data': data[col].tolist(),
                    'itemStyle': {'color': colors[idx % len(colors)]},
                    'label': {'show': True, 'position': 'top', 'fontSize': 12, 'fontWeight': 'bold'}
                }
                for idx, col in enumerate(y_cols)
            ],
            'tooltip': {
                'trigger': 'axis',
                'axisPointer': {'type': 'shadow'}
            },
            'legend': {
                'data': [col.replace('_', ' ').title() for col in y_cols],
                'top': 10,
                'right': 10
            },
            'grid': {
                'left': '3%',
                'right': '4%',
                'top': '20%',
                'bottom': '8%',
                'containLabel': True
            }
        }).classes(f'w-full {height}')


def create_line_chart(data: pd.DataFrame, title: str, x_col: str, y_cols: Any, colors: List[str] = None, height: str = 'h-96', y_axis_name: str = None, rotate_labels: int = 45, show_area: bool = True):
    """
    Create a line chart for trend visualization
    """
    if colors is None:
        # Standard dashboard palette: Indigo, Emerald, Amber, Violet, Rose
        colors = ['#6366f1', '#10b981', '#f59e0b', '#8b5cf6', '#f43f5e']
    
    # Normalize y_cols and labels
    if isinstance(y_cols, dict):
        cols = list(y_cols.keys())
        labels = list(y_cols.values())
    else:
        cols = y_cols
        labels = [col.replace('_', ' ').title() for col in y_cols]
    
    with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
        ui.label(title).classes('text-xl font-bold text-slate-900 mb-4')
        
        categories = data[x_col].tolist()
        
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

        ui.echart({
            'xAxis': {
                'type': 'category',
                'data': categories,
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


def create_donut_chart(data: Dict[str, float], title: str, colors: List[str] = None):
    """
    Create a donut chart for proportional data
    
    Args:
        data: Dictionary of label: value pairs
        title: Chart title
        colors: List of colors for segments
    """
    if colors is None:
        colors = ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']
    
    with ui.card().classes('flex-1 p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
        ui.label(title).classes('text-xl font-bold text-slate-900 mb-4')
        
        chart_data = [
            {'value': value, 'name': name}
            for name, value in data.items()
        ]
        
        ui.echart({
            'tooltip': {
                'trigger': 'item',
                'formatter': '{b}: {c} ({d}%)'
            },
            'legend': {
                'orient': 'vertical',
                'left': 'left'
            },
            'series': [{
                'type': 'pie',
                'radius': ['40%', '70%'],
                'avoidLabelOverlap': False,
                'itemStyle': {
                    'borderRadius': 10,
                    'borderColor': '#fff',
                    'borderWidth': 2
                },
                'label': {
                    'show': False,
                    'position': 'center'
                },
                'emphasis': {
                    'label': {
                        'show': True,
                        'fontSize': 20,
                        'fontWeight': 'bold'
                    }
                },
                'data': chart_data,
                'color': colors
            }]
        }).classes('w-full h-80')


def create_metric_table(data: pd.DataFrame, title: str = "Detailed Metrics", height: str = None):
    """
    Create a formatted table for displaying metrics, with optional fixed height and sticky header.
    
    Args:
        data: DataFrame to display
        title: Table title
        height: Optional Tailwind height class (e.g., 'h-[400px]') for scrollable container.
    """
    with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
        ui.label(title).classes('text-xl font-bold text-slate-900 mb-4')
        
        # Define Columns
        columns = [
            {
                'name': col,
                'label': col.replace('_', ' ').title(),
                'field': col,
                'align': 'left' if col == data.columns[0] else 'right',
                'sortable': True
            }
            for col in data.columns
        ]
        
        # Format rows
        rows = data.copy()
        for col in rows.select_dtypes(include=['number']).columns:
            if 'pct' in col.lower() or 'rate' in col.lower():
                rows[col] = rows[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")
            else:
                rows[col] = rows[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
        
        # Use sticky-header if height is provided
        table = ui.table(
            columns=columns,
            rows=rows.to_dict('records'),
            row_key=data.columns[0]
        ).classes('w-full').props(
            'flat bordered=false binary-state-sort '
            'pagination="{rowsPerPage: 0}" '
            ':rows-per-page-options="[0]"'
        )
        
        if height:
            # Quasar's sticky-header prop requires a height/max-height on the element
            table.props('sticky-header')
            # Apply height class (e.g., h-[180px])
            table.classes(height)
            # Extra CSS to ensure the header stays at top with a solid background
            # This is sometimes needed in tailored dashboard themes
            table.add_slot('header', r'''
                <q-tr :props="props">
                    <q-th v-for="col in props.cols" :key="col.name" :props="props" 
                          class="bg-white sticky top-0 z-10 font-bold border-b-2 border-slate-100">
                        {{ col.label }}
                    </q-th>
                </q-tr>
            ''')


def create_gauge_chart(value: float, max_value: float, title: str, color: str = '#2563eb'):
    """
    Create a gauge chart for single metric visualization
    
    Args:
        value: Current value
        max_value: Maximum value for scale
        title: Chart title
        color: Gauge color
    """
    percentage = (value / max_value * 100) if max_value > 0 else 0
    
    with ui.card().classes('flex-1 p-6 border border-slate-200 shadow-sm bg-white rounded-xl text-center'):
        ui.label(title).classes('text-sm text-slate-600 font-semibold mb-4')
        
        ui.echart({
            'series': [{
                'type': 'gauge',
                'startAngle': 180,
                'endAngle': 0,
                'min': 0,
                'max': max_value,
                'splitNumber': 5,
                'itemStyle': {
                    'color': color
                },
                'progress': {
                    'show': True,
                    'width': 18
                },
                'pointer': {
                    'show': False
                },
                'axisLine': {
                    'lineStyle': {
                        'width': 18
                    }
                },
                'axisTick': {
                    'show': False
                },
                'splitLine': {
                    'show': False
                },
                'axisLabel': {
                    'show': False
                },
                'detail': {
                    'valueAnimation': True,
                    'formatter': '{value}',
                    'color': '#1e293b',
                    'fontSize': 24,
                    'fontWeight': 'bold',
                    'offsetCenter': [0, '0%']
                },
                'data': [{
                    'value': value,
                    'name': ''
                }]
            }]
        }).classes('w-full h-48')
        
        ui.label(f'{percentage:.1f}% of maximum').classes('text-xs text-slate-500 mt-2')


def create_placeholder_card(title: str, height: str = 'h-96'):
    """
    Create a styled placeholder card for charts/metrics
    """
    with ui.card().classes(f'w-full {height} p-6 border border-dashed border-slate-300 bg-slate-50 rounded-xl flex items-center justify-center shadow-none hover:border-slate-400 transition-colors'):
        with ui.column().classes('items-center gap-2'):
            ui.icon('insert_chart', size='3rem').classes('text-slate-300')
            ui.label(title).classes('text-sm font-semibold text-slate-400 uppercase tracking-wider')
            ui.label('Data connection pending').classes('text-xs text-slate-400')


def create_traffic_source_row(source_data: pd.DataFrame, source_title: str, medium_data: pd.DataFrame, medium_title: str, value_col: str, value_label: str):
    """
    Create a side-by-side row with a bar chart and a table for traffic source metrics
    """
    with ui.grid(columns=3).classes('w-full gap-4 mb-6 items-stretch'):
        # 1. Bar Chart (2/3) - Primary Source
        with ui.card().classes('col-span-2 p-6 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
            ui.label(source_title).classes('text-xl font-bold text-slate-900 mb-4')
            
            if source_data.empty:
                ui.label('No traffic source data available').classes('text-slate-500 italic py-20 w-full text-center')
            else:
                # Top 10 sources for the bar chart
                chart_data = source_data.nlargest(10, value_col).sort_values(value_col, ascending=True)
                # Find the category column (the one that is not value_col)
                cat_col = [c for c in chart_data.columns if c != value_col][0]
                
                ui.echart({
                    'xAxis': {'type': 'value', 'splitLine': {'show': False}},
                    'yAxis': {
                        'type': 'category',
                        'data': chart_data[cat_col].tolist(),
                        'axisLabel': {'fontSize': 11}
                    },
                    'series': [{
                        'name': value_label,
                        'type': 'bar',
                        'data': chart_data[value_col].tolist(),
                        'itemStyle': {
                            'color': {
                                'type': 'linear', 'x': 0, 'y': 0, 'x2': 1, 'y2': 0,
                                'colorStops': [
                                    {'offset': 0, 'color': 'rgba(99, 102, 241, 0.6)'},
                                    {'offset': 1, 'color': 'rgba(99, 102, 241, 0.9)'}
                                ]
                            }
                        },
                        'label': {'show': True, 'position': 'right', 'fontWeight': 'bold'}
                    }],
                    'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
                    'grid': {'left': '3%', 'right': '10%', 'top': '5%', 'bottom': '5%', 'containLabel': True}
                }).classes('w-full h-80')

        # 2. Table (1/3) - Medium Breakdown
        with ui.card().classes('col-span-1 p-6 border border-slate-200 shadow-sm bg-white rounded-xl overflow-hidden'):
            ui.label(medium_title).classes('text-sm font-semibold text-slate-500 mb-4 uppercase tracking-wider')
            
            if medium_data.empty:
                ui.label('No data available').classes('text-slate-500 italic py-10 w-full text-center')
            else:
                top_data = medium_data.nlargest(10, value_col).copy()
                # Find the category column
                cat_col = [c for c in top_data.columns if c != value_col][0]
                
                columns = [
                    {'name': 'category', 'label': cat_col.replace('_', ' ').upper(), 'field': cat_col, 'align': 'left'},
                    {'name': 'values', 'label': value_label.upper(), 'field': value_col, 'align': 'right', 'sortable': True},
                ]
                
                rows = top_data.to_dict('records')
                for row in rows:
                    val = row[value_col]
                    row[value_col] = f"{int(val):,}" if pd.notna(val) else "0"
                
                ui.table(
                    columns=columns,
                    rows=rows,
                    row_key=cat_col
                ).classes('w-full border-none shadow-none').props('flat bordered=false hide-bottom pagination="{rowsPerPage: 0}"')


def create_user_journey_section(data: pd.DataFrame):
    """
    Display the Top 3 user journeys in a stylized textual format
    """
    with ui.column().classes('w-full gap-4 mt-8'):
        ui.label('High-Engagement User Journeys').classes('text-2xl font-bold text-slate-900 mb-2')
        ui.label('Analysis of the deepest navigation sequences taken by users').classes('text-sm text-slate-500 mb-4')
        
        if data.empty:
            with ui.card().classes('w-full p-12 items-center border border-slate-200 shadow-sm rounded-xl'):
                ui.icon('explore', size='3rem').classes('text-slate-200 mb-4')
                ui.label('No complex journey data found for this period').classes('text-slate-500 italic')
            return

        for idx, row in data.iterrows():
            path = str(row['conversion_path'])
            # Robust splitting: handle common separators ' > ', ' → ', and the corrupted ' â†’ '
            import re
            steps = [s.strip() for s in re.split(r' > | → | â†’ ', path) if s.strip()]
            
            with ui.card().classes('w-full p-8 border border-slate-200 shadow-sm rounded-2xl hover:shadow-lg transition-all relative overflow-hidden'):
                # Background Highlight for the Card
                ui.element('div').classes('absolute -right-20 -top-20 w-64 h-64 bg-slate-50 rounded-full opacity-50')
                
                with ui.row().classes('w-full items-center justify-between mb-8 relative z-10'):
                    with ui.row().classes('items-center gap-3'):
                        with ui.element('div').classes('p-2 bg-indigo-50 rounded-lg'):
                            ui.icon('insights', size='1.5rem').classes('text-indigo-600')
                        with ui.column().classes('gap-0'):
                            ui.label(f'Journey Pattern #{idx + 1}').classes('text-xl font-black text-slate-800')
                            ui.label(f"{row['unique_pages']} Unique high-value steps").classes('text-[10px] text-slate-400 font-bold uppercase tracking-wider')
                    
                    with ui.row().classes('gap-8'):
                        # Reach Metric
                        with ui.column().classes('items-end gap-1'):
                            user_pct = row.get('user_pct', 0)
                            ui.label(f"{user_pct:.1f}%").classes('text-2xl font-black text-indigo-700 leading-none')
                            ui.label('User Base Reach').classes('text-[10px] text-slate-400 font-bold uppercase tracking-tighter')
                        
                        # Count Metric
                        with ui.column().classes('items-end gap-1'):
                            occ = row.get('path_occurrence_count', 0)
                            ui.label(f"{int(occ):,}").classes('text-2xl font-black text-slate-800 leading-none')
                            ui.label('Total Occurrences').classes('text-[10px] text-slate-400 font-bold uppercase tracking-tighter')

                # The Flow visualization
                with ui.row().classes('w-full gap-3 items-center overflow-x-auto pb-4 no-wrap relative z-10 custom-scrollbar'):
                    for step_idx, step in enumerate(steps):
                        # Step Tag
                        with ui.element('div').classes('px-5 py-3 bg-white border-2 border-slate-100 rounded-xl shadow-sm shrink-0 flex items-center gap-3'):
                            ui.element('div').classes('w-2 h-2 rounded-full bg-indigo-500')
                            ui.label(step).classes('text-sm font-bold text-slate-700')
                        
                        # Connecting Arrow
                        if step_idx < len(steps) - 1:
                            ui.icon('arrow_forward', size='1.2rem').classes('text-slate-300 shrink-0 mx-1 animate-pulse')
