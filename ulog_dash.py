"""
ULog Explorer - Dash Version
Modern, clean, header-free UI
"""

import os
from dash import Dash, html, dcc, callback, Output, Input, State, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from pyulog import ULog
import numpy as np
import base64

# Config
ULOG_DIR = "uploaded_ulogs"
os.makedirs(ULOG_DIR, exist_ok=True)

# Cache for loaded data
_cache = {}

def get_ulog(file_path):
    """Get cached ULog or load new one"""
    if file_path not in _cache:
        _cache[file_path] = ULog(file_path)
    return _cache[file_path]

def get_topics(file_path):
    """Get topic names from ULog"""
    try:
        ulog = get_ulog(file_path)
        return sorted([f"{d.name}_{d.multi_id}" for d in ulog.data_list])
    except:
        return []

def get_fields(file_path, topic):
    """Get fields for a topic"""
    try:
        ulog = get_ulog(file_path)
        for d in ulog.data_list:
            if f"{d.name}_{d.multi_id}" == topic:
                return sorted([k for k in d.data.keys() if k != 'timestamp'])
        return []
    except:
        return []

def get_data(file_path, topic, field):
    """Get time-series data"""
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
    """Get available ULog files"""
    return sorted([f for f in os.listdir(ULOG_DIR) if f.endswith(".ulg")])

# App
app = Dash(__name__, external_stylesheets=[dbc.themes.SLATE])
app.title = "ULog Explorer"

# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <style>
        body { 
            font-family: 'Inter', -apple-system, sans-serif; 
            background: #0a0f1a;
            margin: 0;
            padding: 0;
        }
        .panel { 
            background: #111827; 
            border-radius: 8px; 
            padding: 12px;
            height: calc(100vh - 24px);
            overflow-y: auto;
        }
        .panel-title {
            font-size: 11px;
            font-weight: 600;
            color: #4b5563;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #1f2937;
        }
        .topic-btn {
            background: #1f2937;
            border: none;
            color: #9ca3af;
            padding: 6px 10px;
            border-radius: 4px;
            cursor: pointer;
            width: 100%;
            text-align: left;
            font-size: 12px;
            margin-bottom: 4px;
        }
        .topic-btn:hover { background: #374151; color: #e5e7eb; }
        .field-item {
            padding: 4px 8px 4px 20px;
            font-size: 11px;
            color: #9ca3af;
            cursor: pointer;
            border-radius: 3px;
        }
        .field-item:hover { background: #1f2937; }
        .selected-chip {
            display: inline-flex;
            align-items: center;
            background: #1e40af;
            color: #dbeafe;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 10px;
            margin: 3px;
            cursor: pointer;
            border: none;
        }
        .selected-chip:hover { background: #1d4ed8; }
        .chip-x {
            margin-left: 6px;
            font-weight: bold;
            opacity: 0.7;
        }
        .chip-x:hover { opacity: 1; }
        .info-box {
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 40px;
            text-align: center;
            color: #4b5563;
        }
        .main-graph { 
            background: #111827; 
            border-radius: 8px; 
            padding: 16px;
            height: calc(100vh - 24px);
        }
        select, input {
            background: #1f2937 !important;
            border: 1px solid #374151 !important;
            color: #e5e7eb !important;
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 12px;
            width: 100%;
        }
        select:focus, input:focus { outline: none; border-color: #3b82f6 !important; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: #374151; border-radius: 2px; }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
'''

# Layout
app.layout = dbc.Container([
    dbc.Row([
        # Left Panel - File
        dbc.Col([
            html.Div([
                html.Div("Dosya", className="panel-title"),
                dcc.Upload(
                    id='upload',
                    children=html.Div(['Yükle'], style={'padding': '8px', 'textAlign': 'center', 'border': '1px dashed #475569', 'borderRadius': '4px', 'cursor': 'pointer', 'color': '#94a3b8', 'fontSize': '12px'}),
                    multiple=False
                ),
                html.Div(id='upload-status', style={'fontSize': '10px', 'color': '#10b981', 'marginTop': '4px'}),
                html.Hr(style={'borderColor': '#334155', 'margin': '12px 0'}),
                dcc.Dropdown(
                    id='file-select',
                    options=[{'label': f, 'value': f} for f in get_files()],
                    value=get_files()[0] if get_files() else None,
                    style={'fontSize': '12px'},
                    className='dash-dropdown'
                ),
                html.Hr(style={'borderColor': '#334155', 'margin': '12px 0'}),
                html.Div("Secili", className="panel-title"),
                html.Div(id='selected-display')
            ], className='panel')
        ], width=2, style={'padding': '12px 6px 12px 12px'}),
        
        # Main - Graph
        dbc.Col([
            html.Div([
                dcc.Graph(id='main-graph', style={'height': 'calc(100vh - 80px)'}, config={'scrollZoom': True, 'displaylogo': False})
            ], className='main-graph')
        ], width=7, style={'padding': '12px 6px'}),
        
        # Right Panel - Data Selection
        dbc.Col([
            html.Div([
                html.Div("Veri Secimi", className="panel-title"),
                dcc.Input(id='search', type='text', placeholder='Ara...', style={'marginBottom': '12px'}),
                html.Div(id='topic-list', style={'overflowY': 'auto', 'maxHeight': 'calc(100vh - 140px)'})
            ], className='panel')
        ], width=3, style={'padding': '12px 12px 12px 6px'})
    ])
], fluid=True, style={'padding': 0, 'maxWidth': '100%'})

# Store for selected params
app.layout.children.insert(0, dcc.Store(id='selected-params', data=[]))
app.layout.children.insert(0, dcc.Store(id='expanded-topics', data=[]))

# Callbacks
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
    for topic in topics[:50]:
        is_expanded = topic in (expanded or [])
        arrow = "▼" if is_expanded else "▶"
        
        items.append(
            html.Button(
                f"{arrow} {topic[:30]}",
                id={'type': 'topic-btn', 'topic': topic},
                className='topic-btn',
                n_clicks=0
            )
        )
        
        if is_expanded:
            fields = get_fields(file_path, topic)
            for field in fields[:25]:
                is_sel = [topic, field] in (selected or [])
                style = {'background': '#3b82f6', 'color': 'white'} if is_sel else {}
                items.append(
                    html.Div(
                        f"{'✓ ' if is_sel else '+ '}{field[:22]}",
                        id={'type': 'field-item', 'topic': topic, 'field': field},
                        className='field-item',
                        style=style,
                        n_clicks=0
                    )
                )
    
    return items

@callback(
    Output('expanded-topics', 'data'),
    Input({'type': 'topic-btn', 'topic': ALL}, 'n_clicks'),
    State('expanded-topics', 'data'),
    prevent_initial_call=True
)
def toggle_topic(clicks, expanded):
    from dash import ctx
    if not ctx.triggered_id:
        return expanded or []
    
    topic = ctx.triggered_id['topic']
    expanded = expanded or []
    
    if topic in expanded:
        expanded.remove(topic)
    else:
        expanded.append(topic)
    
    return expanded

@callback(
    Output('selected-params', 'data'),
    Input({'type': 'field-item', 'topic': ALL, 'field': ALL}, 'n_clicks'),
    State('selected-params', 'data'),
    prevent_initial_call=True
)
def toggle_field(clicks, selected):
    from dash import ctx
    if not ctx.triggered_id:
        return selected or []
    
    topic = ctx.triggered_id['topic']
    field = ctx.triggered_id['field']
    param = [topic, field]
    selected = selected or []
    
    if param in selected:
        selected.remove(param)
    else:
        selected.append(param)
    
    return selected

@callback(
    Output('selected-display', 'children'),
    Input('selected-params', 'data')
)
def update_selected_display(selected):
    if not selected:
        return html.Div("Henüz seçim yok", style={'color': '#4b5563', 'fontSize': '11px'})
    
    chips = []
    for idx, p in enumerate(selected):
        chips.append(
            html.Button(
                [p[1][:12], html.Span(" ✕", className='chip-x')],
                id={'type': 'chip-remove', 'index': idx},
                className='selected-chip',
                n_clicks=0
            )
        )
    return chips

@callback(
    Output('selected-params', 'data', allow_duplicate=True),
    Input({'type': 'chip-remove', 'index': ALL}, 'n_clicks'),
    State('selected-params', 'data'),
    prevent_initial_call=True
)
def remove_chip(clicks, selected):
    from dash import ctx
    if not ctx.triggered_id or not selected:
        return selected or []
    
    idx = ctx.triggered_id['index']
    if 0 <= idx < len(selected):
        selected.pop(idx)
    
    return selected

@callback(
    Output('main-graph', 'figure'),
    Input('selected-params', 'data'),
    Input('file-select', 'value')
)
def update_graph(selected, filename):
    if not selected or not filename:
        return go.Figure().update_layout(
            template='plotly_dark',
            paper_bgcolor='#111827',
            plot_bgcolor='#111827',
            annotations=[{
                'text': 'Sağ panelden veri seçin',
                'xref': 'paper', 'yref': 'paper',
                'x': 0.5, 'y': 0.5,
                'showarrow': False,
                'font': {'size': 16, 'color': '#4b5563'}
            }]
        )
    
    file_path = os.path.join(ULOG_DIR, filename)
    colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']
    
    fig = go.Figure()
    
    for idx, param in enumerate(selected):
        topic, field = param
        t, y = get_data(file_path, topic, field)
        
        if t is not None:
            fig.add_trace(go.Scatter(
                x=t, y=y,
                name=f"{topic.split('_')[0]}.{field}",
                mode='lines',
                line=dict(color=colors[idx % len(colors)], width=1.5)
            ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#111827',
        plot_bgcolor='#0a0f1a',
        hovermode='x unified',
        margin=dict(l=50, r=20, t=30, b=50),
        xaxis=dict(title='Zaman (s)', gridcolor='#1f2937'),
        yaxis=dict(title='Değer', gridcolor='#1f2937'),
        legend=dict(orientation='h', y=1.02, font=dict(size=10))
    )
    
    return fig

if __name__ == '__main__':
    print("\n" + "="*50)
    print("ULog Explorer - Dash")
    print("http://localhost:8050")
    print("="*50 + "\n")
    app.run(debug=False, port=8050)
