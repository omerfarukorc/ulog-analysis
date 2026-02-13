"""
ULog Explorer - Dash Version
PX4 Flight Review style dashboard with collapsible sidebar,
vehicle info panel, multi-graph support, and standard PX4 graphs.
"""

import os
import json
from dash import Dash, html, dcc, callback, Output, Input, State, ALL, MATCH, no_update, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from pyulog import ULog
import numpy as np
import base64

from px4_graphs import (
    get_vehicle_info, generate_all_graphs, STANDARD_GRAPHS,
    COLORS, TRACE_COLORS, _base_layout, _downsample
)

# Config
ULOG_DIR = "uploaded_ulogs"
os.makedirs(ULOG_DIR, exist_ok=True)

# Cache
_cache = {}

def get_ulog(file_path):
    if file_path not in _cache:
        _cache[file_path] = ULog(file_path)
    return _cache[file_path]

def get_topics(file_path):
    try:
        ulog = get_ulog(file_path)
        return sorted([f"{d.name}_{d.multi_id}" for d in ulog.data_list])
    except:
        return []

def get_fields(file_path, topic):
    try:
        ulog = get_ulog(file_path)
        for d in ulog.data_list:
            if f"{d.name}_{d.multi_id}" == topic:
                return sorted([k for k in d.data.keys() if k != 'timestamp'])
        return []
    except:
        return []

def get_data(file_path, topic, field):
    try:
        ulog = get_ulog(file_path)
        for d in ulog.data_list:
            if f"{d.name}_{d.multi_id}" == topic:
                t = d.data['timestamp'] / 1e6
                y = d.data[field]
                return t, y
        return None, None
    except:
        return None, None

def get_files():
    return sorted([f for f in os.listdir(ULOG_DIR) if f.endswith(".ulg")])


# ============================================================
# App Init
# ============================================================
app = Dash(__name__, external_stylesheets=[dbc.themes.SLATE], suppress_callback_exceptions=True)
app.title = "ULog Explorer"

app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: #0a0f1a;
            margin: 0; padding: 0;
            overflow-x: hidden;
        }
        /* Sidebar */
        .sidebar {
            background: #111827;
            border-radius: 10px;
            padding: 14px;
            height: calc(100vh - 16px);
            overflow-y: auto;
            transition: all 0.3s ease;
            margin: 8px 0 8px 8px;
        }
        .sidebar.collapsed {
            width: 50px !important;
            min-width: 50px;
            padding: 14px 6px;
        }
        .sidebar.collapsed .sidebar-content { display: none; }
        .sidebar-toggle {
            background: #1f2937;
            border: 1px solid #374151;
            color: #9ca3af;
            width: 32px; height: 32px;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            transition: all 0.2s;
            margin-bottom: 10px;
        }
        .sidebar-toggle:hover { background: #374151; color: #e5e7eb; }

        /* Panels */
        .panel-title {
            font-size: 10px;
            font-weight: 700;
            color: #6366f1;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            padding-bottom: 6px;
            border-bottom: 1px solid #1f2937;
        }

        /* Data browser */
        .data-panel {
            background: #111827;
            border-radius: 10px;
            padding: 14px;
            height: calc(100vh - 16px);
            overflow-y: auto;
            margin: 8px 8px 8px 0;
        }
        .topic-btn {
            background: #1f2937;
            border: 1px solid transparent;
            color: #d1d5db;
            padding: 6px 10px;
            border-radius: 6px;
            cursor: pointer;
            width: 100%;
            text-align: left;
            font-size: 11px;
            font-weight: 500;
            margin-bottom: 3px;
            transition: all 0.15s;
        }
        .topic-btn:hover { background: #374151; border-color: #4b5563; color: #f3f4f6; }
        .field-item {
            padding: 4px 8px 4px 20px;
            font-size: 11px;
            color: #9ca3af;
            cursor: pointer;
            border-radius: 4px;
            margin-bottom: 1px;
            transition: all 0.15s;
        }
        .field-item:hover { background: #1f2937; color: #e5e7eb; }

        /* Selected chips */
        .selected-chip {
            display: inline-flex;
            align-items: center;
            background: linear-gradient(135deg, #4f46e5, #6366f1);
            color: #e0e7ff;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 10px;
            font-weight: 500;
            margin: 2px;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
            box-shadow: 0 2px 4px rgba(99,102,241,0.2);
        }
        .selected-chip:hover { background: linear-gradient(135deg, #6366f1, #818cf8); transform: scale(1.03); }
        .chip-x { margin-left: 6px; font-weight: bold; opacity: 0.7; }
        .chip-x:hover { opacity: 1; }

        /* Main content */
        .main-area {
            margin: 8px 6px;
            height: calc(100vh - 16px);
            overflow-y: auto;
            scroll-behavior: smooth;
        }

        /* Info card */
        .info-card {
            background: linear-gradient(135deg, #111827 0%, #1a1f35 100%);
            border: 1px solid #1f2937;
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 10px;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 8px;
        }
        .info-item {
            background: rgba(31,41,55,0.5);
            border-radius: 6px;
            padding: 8px 12px;
        }
        .info-label {
            font-size: 9px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }
        .info-value {
            font-size: 12px;
            color: #e5e7eb;
            font-weight: 500;
            margin-top: 2px;
        }

        /* Graph Containers */
        .graph-card {
            background: #111827;
            border-radius: 10px;
            margin-bottom: 10px;
            overflow: hidden;
            border: 1px solid #1f2937;
        }

        /* Tab styling */
        .custom-tabs .tab {
            background: #1f2937 !important;
            border: none !important;
            color: #9ca3af !important;
            padding: 8px 16px !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            border-radius: 6px 6px 0 0 !important;
            margin-right: 2px !important;
        }
        .custom-tabs .tab--selected {
            background: #111827 !important;
            color: #6366f1 !important;
            border-bottom: 2px solid #6366f1 !important;
        }

        /* Inputs */
        select, input[type="text"] {
            background: #1f2937 !important;
            border: 1px solid #374151 !important;
            color: #e5e7eb !important;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 11px;
            width: 100%;
        }
        select:focus, input:focus { outline: none; border-color: #6366f1 !important; }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #374151; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #4b5563; }

        /* Action buttons */
        .action-btn {
            background: linear-gradient(135deg, #4f46e5, #6366f1);
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .action-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99,102,241,0.3); }
        .action-btn.secondary {
            background: #1f2937;
            border: 1px solid #374151;
            color: #d1d5db;
        }
        .action-btn.secondary:hover { background: #374151; }
        .action-btn.danger { background: linear-gradient(135deg, #dc2626, #ef4444); }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
'''

# ============================================================
# Layout
# ============================================================

def make_info_item(label, value):
    return html.Div([
        html.Div(label, className='info-label'),
        html.Div(str(value), className='info-value'),
    ], className='info-item')


app.layout = html.Div([
    # Stores
    dcc.Store(id='selected-params', data=[]),
    dcc.Store(id='expanded-topics', data=[]),
    dcc.Store(id='topic-click-store', data=None),
    dcc.Store(id='field-click-store', data=None),
    dcc.Store(id='sidebar-collapsed', data=False),
    dcc.Store(id='active-tab', data='standard'),

    html.Div([
        # LEFT SIDEBAR
        html.Div([
            html.Button('☰', id='sidebar-toggle-btn', className='sidebar-toggle', n_clicks=0),
            html.Div([
                html.Div("Dosya", className="panel-title"),
                dcc.Upload(
                    id='upload',
                    children=html.Div(['📁 Dosya Yükle'], style={
                        'padding': '10px', 'textAlign': 'center',
                        'border': '1px dashed #4f46e5', 'borderRadius': '8px',
                        'cursor': 'pointer', 'color': '#818cf8', 'fontSize': '11px',
                        'background': 'rgba(79,70,229,0.05)',
                        'transition': 'all 0.2s',
                    }),
                    multiple=False,
                    style={'marginBottom': '8px'}
                ),
                html.Div(id='upload-status', style={'fontSize': '10px', 'color': '#10b981', 'marginTop': '2px'}),
                html.Hr(style={'borderColor': '#1f2937', 'margin': '10px 0'}),
                dcc.Dropdown(
                    id='file-select',
                    options=[{'label': f, 'value': f} for f in get_files()],
                    value=get_files()[0] if get_files() else None,
                    style={'fontSize': '11px'},
                    className='dash-dropdown'
                ),
                html.Hr(style={'borderColor': '#1f2937', 'margin': '10px 0'}),
                html.Div("Seçili Veriler", className="panel-title"),
                html.Div(id='selected-display'),
            ], className='sidebar-content')
        ], id='sidebar', className='sidebar', style={
            'width': '220px', 'minWidth': '220px', 'flexShrink': 0
        }),

        # MAIN CONTENT
        html.Div([
            # Vehicle Info
            html.Div(id='vehicle-info-panel'),

            # Tabs
            html.Div([
                html.Button('Standart Grafikler', id='tab-standard', className='action-btn',
                            n_clicks=0, style={'marginRight': '6px'}),
                html.Button('Özel Grafikler', id='tab-custom', className='action-btn secondary',
                            n_clicks=0, style={'marginRight': '6px'}),
            ], style={'marginBottom': '10px', 'display': 'flex', 'flexWrap': 'wrap', 'gap': '4px'}),

            # Graph area
            html.Div(id='graph-area'),
        ], className='main-area', style={'flex': 1}),

        # RIGHT PANEL - Data Selection
        html.Div([
            html.Div("Veri Seçimi", className="panel-title"),
            dcc.Input(id='search', type='text', placeholder='Topic ara...', style={'marginBottom': '10px'}),
            html.Div(id='topic-list', style={'overflowY': 'auto', 'maxHeight': 'calc(100vh - 130px)'})
        ], id='right-panel', className='data-panel', style={
            'width': '280px', 'minWidth': '280px', 'flexShrink': 0, 'display': 'none'
        }),
    ], style={
        'display': 'flex', 'height': '100vh', 'gap': '0',
    })
])


# ============================================================
# Callbacks
# ============================================================

# Upload
@callback(
    Output('upload-status', 'children'),
    Output('file-select', 'options'),
    Input('upload', 'contents'),
    State('upload', 'filename')
)
def upload_file(contents, filename):
    if contents and filename:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        file_path = os.path.join(ULOG_DIR, filename)
        with open(file_path, 'wb') as f:
            f.write(decoded)
        files = get_files()
        return f"✓ {filename}", [{'label': f, 'value': f} for f in files]
    files = get_files()
    return "", [{'label': f, 'value': f} for f in files]


# Sidebar toggle
app.clientside_callback(
    """
    function(n) {
        var sb = document.getElementById('sidebar');
        if (!sb) return dash_clientside.no_update;
        var collapsed = sb.classList.toggle('collapsed');
        if (collapsed) {
            sb.style.width = '50px';
            sb.style.minWidth = '50px';
        } else {
            sb.style.width = '220px';
            sb.style.minWidth = '220px';
        }
        return collapsed;
    }
    """,
    Output('sidebar-collapsed', 'data'),
    Input('sidebar-toggle-btn', 'n_clicks'),
    prevent_initial_call=True
)


# Tab switching
@callback(
    Output('active-tab', 'data'),
    Output('tab-standard', 'className'),
    Output('tab-custom', 'className'),
    Input('tab-standard', 'n_clicks'),
    Input('tab-custom', 'n_clicks'),
    prevent_initial_call=True
)
def switch_tab(n_std, n_cust):
    trigger = ctx.triggered_id
    if trigger == 'tab-standard':
        return 'standard', 'action-btn', 'action-btn secondary'
    else:
        return 'custom', 'action-btn secondary', 'action-btn'


# Right panel visibility based on tab
app.clientside_callback(
    """
    function(tab) {
        var rp = document.getElementById('right-panel');
        if (!rp) return dash_clientside.no_update;
        if (tab === 'custom') {
            rp.style.display = 'block';
        } else {
            rp.style.display = 'none';
        }
        return dash_clientside.no_update;
    }
    """,
    Output('right-panel', 'style'),
    Input('active-tab', 'data'),
    prevent_initial_call=True
)


# Vehicle Info
@callback(
    Output('vehicle-info-panel', 'children'),
    Input('file-select', 'value')
)
def update_vehicle_info(filename):
    if not filename:
        return html.Div()

    file_path = os.path.join(ULOG_DIR, filename)
    try:
        ulog = get_ulog(file_path)
        info = get_vehicle_info(ulog)
    except Exception as e:
        return html.Div(f"Bilgi alınamadı: {e}", style={'color': '#ef4444', 'fontSize': '11px'})

    items = [
        make_info_item('Sistem', info.get('sys_name', 'N/A')),
        make_info_item('Hardware', info.get('ver_hw', 'N/A')),
        make_info_item('Software', info.get('ver_sw_release', 'N/A')),
        make_info_item('OS', f"{info.get('ver_os', '')} {info.get('ver_os_version', '')}"),
        make_info_item('Estimator', info.get('estimator', 'N/A')),
        make_info_item('Süre', info.get('duration', 'N/A')),
        make_info_item('Başlangıç', info.get('start_time', 'N/A')),
    ]

    # Add flight stats if available
    for key, label in [('distance', 'Mesafe'), ('max_alt', 'Maks. Yükseklik'),
                       ('max_speed', 'Maks. Hız'), ('avg_speed', 'Ort. Hız'),
                       ('max_speed_up', 'Maks. Yükselme'), ('max_speed_down', 'Maks. Alçalma'),
                       ('max_tilt', 'Maks. Eğim')]:
        if key in info:
            items.append(make_info_item(label, info[key]))

    return html.Div([
        html.Div([
            html.Div("✈️ " + filename, style={
                'fontSize': '13px', 'fontWeight': '700', 'color': '#e5e7eb',
                'marginBottom': '10px'
            }),
            html.Div(items, className='info-grid')
        ], className='info-card')
    ])


# Graph area rendering
@callback(
    Output('graph-area', 'children'),
    Input('active-tab', 'data'),
    Input('file-select', 'value'),
    Input('selected-params', 'data')
)
def render_graph_area(tab, filename, selected):
    if not filename:
        return html.Div("Bir ULog dosyası seçin", style={
            'color': '#4b5563', 'textAlign': 'center', 'padding': '60px',
            'fontSize': '14px'
        })

    file_path = os.path.join(ULOG_DIR, filename)

    if tab == 'standard':
        return render_standard_graphs(file_path)
    else:
        return render_custom_graph(file_path, selected)


def render_standard_graphs(file_path):
    """Render all PX4 standard graphs for the loaded ULog."""
    try:
        ulog = get_ulog(file_path)
        graphs = generate_all_graphs(ulog)
    except Exception as e:
        return html.Div(f"Hata: {e}", style={'color': '#ef4444'})

    if not graphs:
        return html.Div("Bu dosyada standart grafikler için veri bulunamadı.", style={
            'color': '#6b7280', 'textAlign': 'center', 'padding': '40px'
        })

    children = []
    children.append(html.Div(
        f"{len(graphs)} standart grafik oluşturuldu",
        style={'color': '#6366f1', 'fontSize': '12px', 'fontWeight': '600', 'marginBottom': '8px'}
    ))

    for key, title, fig in graphs:
        children.append(
            html.Div([
                dcc.Graph(
                    figure=fig,
                    config={'scrollZoom': True, 'displaylogo': False,
                            'modeBarButtonsToRemove': ['lasso2d', 'select2d']},
                    style={'height': '500px'}
                )
            ], className='graph-card')
        )

    return html.Div(children)


def render_custom_graph(file_path, selected):
    """Render custom user-selected graph."""
    if not selected:
        return html.Div([
            html.Div("Özel Grafikler", style={
                'color': '#e5e7eb', 'fontSize': '14px', 'fontWeight': '600', 'marginBottom': '8px'
            }),
            html.Div("Sağ panelden topic ve field seçerek özel grafikler oluşturun.", style={
                'color': '#6b7280', 'fontSize': '12px', 'padding': '30px', 'textAlign': 'center',
                'background': '#111827', 'borderRadius': '10px', 'border': '1px dashed #374151',
            })
        ])

    colors = TRACE_COLORS
    fig = go.Figure()

    for idx, param in enumerate(selected):
        topic, field = param
        t, y = get_data(file_path, topic, field)
        if t is not None:
            # Downsample for performance
            td, yd = _downsample(np.asarray(t, dtype=np.float64), np.asarray(y, dtype=np.float64))
            fig.add_trace(go.Scatter(
                x=td, y=yd,
                name=f"{topic.split('_')[0]}.{field}",
                mode='lines',
                line=dict(color=colors[idx % len(colors)], width=1.5)
            ))

    fig.update_layout(**_base_layout('Özel Grafik', 'Değer', height=500))
    fig.update_layout(margin=dict(l=55, r=15, t=35, b=50))

    return html.Div([
        html.Div([
            html.Div("Özel Grafikler", style={
                'color': '#e5e7eb', 'fontSize': '14px', 'fontWeight': '600', 'marginBottom': '8px'
            }),
            html.Div([
                dcc.Graph(
                    figure=fig,
                    config={'scrollZoom': True, 'displaylogo': False},
                    style={'height': '500px'}
                )
            ], className='graph-card'),
        ])
    ])


# Topic click clientside callback
app.clientside_callback(
    """
    function() {
        const triggered = dash_clientside.callback_context.triggered;
        if (!triggered || triggered.length === 0) return dash_clientside.no_update;
        for (let i = 0; i < triggered.length; i++) {
            if (triggered[i].value && triggered[i].value > 0) {
                const id = JSON.parse(triggered[i].prop_id.split('.')[0]);
                return {topic: id.topic, ts: Date.now()};
            }
        }
        return dash_clientside.no_update;
    }
    """,
    Output('topic-click-store', 'data'),
    Input({'type': 'topic-btn', 'topic': ALL}, 'n_clicks'),
    prevent_initial_call=True
)

# Field click clientside callback
app.clientside_callback(
    """
    function() {
        const triggered = dash_clientside.callback_context.triggered;
        if (!triggered || triggered.length === 0) return dash_clientside.no_update;
        for (let i = 0; i < triggered.length; i++) {
            if (triggered[i].value && triggered[i].value > 0) {
                const id = JSON.parse(triggered[i].prop_id.split('.')[0]);
                return {topic: id.topic, field: id.field, ts: Date.now()};
            }
        }
        return dash_clientside.no_update;
    }
    """,
    Output('field-click-store', 'data'),
    Input({'type': 'field-item', 'topic': ALL, 'field': ALL}, 'n_clicks'),
    prevent_initial_call=True
)


# Toggle topic expansion
@callback(
    Output('expanded-topics', 'data'),
    Input('topic-click-store', 'data'),
    State('expanded-topics', 'data'),
    prevent_initial_call=True
)
def toggle_topic(click_data, expanded):
    if not click_data or 'topic' not in click_data:
        raise PreventUpdate
    topic = click_data['topic']
    expanded = list(expanded or [])
    if topic in expanded:
        expanded.remove(topic)
    else:
        expanded.append(topic)
    return expanded


# Toggle field selection
@callback(
    Output('selected-params', 'data'),
    Input('field-click-store', 'data'),
    State('selected-params', 'data'),
    prevent_initial_call=True
)
def toggle_field(click_data, selected):
    if not click_data or 'topic' not in click_data or 'field' not in click_data:
        raise PreventUpdate
    topic = click_data['topic']
    field = click_data['field']
    param = [topic, field]
    selected = [list(s) for s in (selected or [])]
    if param in selected:
        selected.remove(param)
    else:
        selected.append(param)
    return selected


# Render topic list
@callback(
    Output('topic-list', 'children'),
    Input('file-select', 'value'),
    Input('search', 'value'),
    Input('expanded-topics', 'data'),
    Input('selected-params', 'data')
)
def update_topic_list(filename, search, expanded, selected):
    if not filename:
        return html.Div("Dosya seçin", style={'color': '#64748b', 'fontSize': '12px'})

    file_path = os.path.join(ULOG_DIR, filename)
    topics = get_topics(file_path)

    if search:
        topics = [t for t in topics if search.lower() in t.lower()]

    items = []
    for topic in topics[:80]:
        is_expanded = topic in (expanded or [])
        arrow = "▼" if is_expanded else "▶"

        # Count selected fields in this topic
        sel_count = sum(1 for s in (selected or []) if s[0] == topic)
        badge = f" ({sel_count})" if sel_count > 0 else ""

        items.append(
            html.Button(
                f"{arrow} {topic[:35]}{badge}",
                id={'type': 'topic-btn', 'topic': topic},
                className='topic-btn',
                style={'borderLeft': '3px solid #6366f1'} if sel_count > 0 else {},
            )
        )

        if is_expanded:
            fields = get_fields(file_path, topic)
            for field in fields[:30]:
                is_sel = [topic, field] in (selected or [])
                style = {
                    'background': 'rgba(99,102,241,0.2)',
                    'color': '#a5b4fc',
                    'borderLeft': '2px solid #6366f1'
                } if is_sel else {}
                items.append(
                    html.Div(
                        f"{'✓ ' if is_sel else '  '}{field[:28]}",
                        id={'type': 'field-item', 'topic': topic, 'field': field},
                        className='field-item',
                        style=style,
                    )
                )

    return items


# Render selected chips
@callback(
    Output('selected-display', 'children'),
    Input('selected-params', 'data')
)
def update_selected_display(selected):
    if not selected:
        return html.Div("Henüz seçim yok", style={'color': '#4b5563', 'fontSize': '10px'})

    chips = []
    for idx, p in enumerate(selected):
        chips.append(
            html.Button(
                [f"{p[0].split('_')[0]}.{p[1][:14]}", html.Span(" ✕", className='chip-x')],
                id={'type': 'chip-remove', 'index': idx},
                className='selected-chip',
            )
        )
    return chips


# Remove chip
@callback(
    Output('selected-params', 'data', allow_duplicate=True),
    Input({'type': 'chip-remove', 'index': ALL}, 'n_clicks'),
    State('selected-params', 'data'),
    prevent_initial_call=True
)
def remove_chip(clicks, selected):
    if not ctx.triggered_id or not selected:
        raise PreventUpdate
    if not any(c for c in clicks if c and c > 0):
        raise PreventUpdate

    idx = ctx.triggered_id['index']
    selected = [list(s) for s in (selected or [])]
    if 0 <= idx < len(selected):
        selected.pop(idx)
    return selected


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  ULog Explorer - PX4 Flight Review Dashboard")
    print("  http://localhost:8050")
    print("=" * 50 + "\n")
    app.run(debug=False, port=8050)
