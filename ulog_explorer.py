import streamlit as st
import os
import shutil
from pyulog import ULog
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Logların kalıcı olarak saklanacağı klasör
ULOG_STORAGE_DIR = "uploaded_ulogs"
if not os.path.exists(ULOG_STORAGE_DIR):
    os.makedirs(ULOG_STORAGE_DIR)

st.set_page_config(
    layout="wide", 
    page_title="ULog Analiz",
    initial_sidebar_state="collapsed",
    menu_items={}
)

# Minimal ve Şık CSS Tasarımı
st.markdown("""
<style>
    /* Header, footer ve deploy gizle */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stHeader"] {display: none;}
    
    /* Sayfa boşlukları */
    .block-container {
        padding: 1rem 1.5rem !important;
        max-width: 100% !important;
    }
    
    /* Font */
    * {
        font-family: 'Segoe UI', -apple-system, sans-serif;
    }
    
    /* Sol panel - kompakt dosya yönetimi */
    .file-panel {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        height: fit-content;
    }
    
    .file-panel-dark {
        background: #1e293b;
        border: 1px solid #334155;
    }
    
    /* Sağ panel - veri seçimi */
    .data-panel {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        max-height: 75vh;
        overflow-y: auto;
    }
    
    /* Panel başlıkları */
    .panel-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #e2e8f0;
    }
    
    /* Expander stil */
    .streamlit-expanderHeader {
        font-size: 0.85rem !important;
        font-weight: 500;
        background: #f1f5f9;
        border-radius: 6px;
        padding: 0.5rem !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: #e2e8f0;
    }
    
    /* Checkbox */
    .stCheckbox label span {
        font-size: 0.8rem !important;
        color: #475569;
    }
    
    /* İnput alanları */
    .stTextInput input {
        font-size: 0.85rem;
        border-radius: 6px;
        border: 1px solid #cbd5e1;
    }
    
    .stTextInput input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    
    /* Selectbox */
    .stSelectbox > div > div {
        font-size: 0.85rem;
        border-radius: 6px;
    }
    
    /* Tab stil */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #f1f5f9;
        border-radius: 8px;
        padding: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        color: #64748b;
        font-weight: 500;
        font-size: 0.85rem;
        border: none;
    }
    
    .stTabs [aria-selected="true"] {
        background: white;
        color: #1e293b;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Butonlar */
    .stDownloadButton button {
        background: #3b82f6;
        border: none;
        border-radius: 6px;
        color: white;
        font-weight: 500;
        font-size: 0.8rem;
        padding: 0.4rem 1rem;
    }
    
    .stDownloadButton button:hover {
        background: #2563eb;
    }
    
    /* File uploader - kompakt */
    .stFileUploader {
        padding: 0;
    }
    
    .stFileUploader > div {
        padding: 0.5rem;
    }
    
    .stFileUploader label {
        font-size: 0.8rem !important;
    }
    
    /* Seçim sayacı */
    .selection-badge {
        background: #3b82f6;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 5px;
        height: 5px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }
    
    /* Alert stilleri */
    .stAlert {
        padding: 0.75rem;
        font-size: 0.85rem;
    }
    
    /* Caption */
    .stCaption {
        font-size: 0.75rem !important;
        color: #94a3b8 !important;
    }
    
    /* Bilgi mesajı */
    .info-message {
        text-align: center;
        padding: 3rem;
        color: #64748b;
    }
    
    .info-message h3 {
        font-weight: 400;
        color: #475569;
        margin-bottom: 0.5rem;
    }
    
    .info-message p {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# === LAYOUT: SOL PANEL | ORTA (GRAFİK) | SAĞ PANEL ===
col_left, col_main, col_right = st.columns([1.2, 4, 1.5])

# --- SOL PANEL: DOSYA YÖNETİMİ ---
with col_left:
    st.markdown('<div class="panel-title">Dosya Yonetimi</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Log Yukle", type=["ulg"], label_visibility="collapsed")
    if uploaded_file:
        file_path = os.path.join(ULOG_STORAGE_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"{uploaded_file.name} yuklendi")
    
    existing_files = [f for f in os.listdir(ULOG_STORAGE_DIR) if f.endswith(".ulg")]
    
    selected_file_name = None
    if existing_files:
        selected_file_name = st.selectbox(
            "Dosya", 
            existing_files, 
            index=len(existing_files)-1,
            label_visibility="collapsed"
        )
        if selected_file_name:
            file_path = os.path.join(ULOG_STORAGE_DIR, selected_file_name)
            size_mb = os.path.getsize(file_path) / (1024*1024)
            st.caption(f"{size_mb:.2f} MB")
    else:
        st.info("Dosya yukleyin")

# Ana ekran kontrolü
if not selected_file_name:
    with col_main:
        st.markdown("""
        <div class="info-message">
            <h3>ULog Analiz</h3>
            <p>Sol panelden bir log dosyasi yukleyin veya secin</p>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# Dosyayı Oku
ulog = None
try:
    ulog = ULog(os.path.join(ULOG_STORAGE_DIR, selected_file_name))
except Exception as e:
    with col_main:
        st.error(f"Dosya okuma hatasi: {e}")
    st.stop()

# Veri Hazırlama
topics = {}
msg_data_map = {}
for data in ulog.data_list:
    t_name = f"{data.name} ({data.multi_id})"
    keys = sorted([k for k in data.data.keys() if k != 'timestamp'])
    topics[t_name] = keys
    msg_data_map[t_name] = data

# --- SAĞ PANEL: VERİ SEÇİMİ ---
selected_series = []

with col_right:
    st.markdown('<div class="panel-title">Veri Secimi</div>', unsafe_allow_html=True)
    
    search_query = st.text_input("Ara", placeholder="ornek: battery", label_visibility="collapsed")
    
    search_topic = ""
    search_field = ""
    if "." in search_query:
        parts = search_query.split(".", 1)
        search_topic, search_field = parts[0].lower(), parts[1].lower()
    else:
        search_topic = search_query.lower()

    count_found = 0
    
    # Topic listesi
    for topic_name in sorted(topics.keys()):
        fields = topics[topic_name]
        
        t_name_lower = topic_name.lower()
        topic_matches = search_topic in t_name_lower
        
        if "." in search_query:
            display_fields = [f for f in fields if search_field in f.lower()] if topic_matches else []
        else:
            display_fields = fields if topic_matches else [f for f in fields if search_query.lower() in f.lower()]
            
        if not display_fields:
            continue
            
        count_found += 1
        
        with st.expander(topic_name, expanded=bool(search_query)):
            for field in display_fields:
                unique_key = f"{topic_name}_{field}"
                if st.checkbox(field, key=unique_key):
                    selected_series.append((topic_name, field))

    if search_query and count_found == 0:
        st.caption("Sonuc bulunamadi")
    
    # Seçim sayısı
    if selected_series:
        st.markdown(f'<span class="selection-badge">{len(selected_series)} secili</span>', unsafe_allow_html=True)

# --- ORTA ALAN: GRAFİK ---
with col_main:
    if selected_series:
        tab1, tab2 = st.tabs(["Grafik", "Istatistikler"])
        
        with tab1:
            fig = go.Figure()
            
            colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']
            
            for idx, (topic, field) in enumerate(selected_series):
                data_obj = msg_data_map[topic]
                t = data_obj.data['timestamp'] / 1e6
                y = data_obj.data[field]
                color = colors[idx % len(colors)]
                fig.add_trace(go.Scatter(
                    x=t, y=y, 
                    name=f"{topic.split(' ')[0]}.{field}", 
                    mode='lines',
                    line=dict(color=color, width=1.5)
                ))
            
            fig.update_layout(
                xaxis_title="Zaman (s)",
                yaxis_title="Deger",
                height=600,
                template="plotly_white",
                hovermode="x unified",
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="right", 
                    x=1,
                    font=dict(size=10)
                ),
                margin=dict(l=50, r=20, t=30, b=50),
                xaxis=dict(
                    gridcolor='#f1f5f9',
                    zerolinecolor='#e2e8f0',
                    tickfont=dict(size=10)
                ),
                yaxis=dict(
                    gridcolor='#f1f5f9',
                    zerolinecolor='#e2e8f0',
                    tickfont=dict(size=10)
                )
            )
            
            st.plotly_chart(fig, use_container_width=True, config={
                'scrollZoom': True,
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'v1hovermode', 'hoverclosest'],
                'toImageButtonOptions': {'format': 'png', 'filename': f'analiz_{selected_file_name}', 'scale': 2}
            })
            
            # HTML İndir
            import io
            buffer = io.StringIO()
            fig.write_html(buffer)
            st.download_button(
                "HTML Indir", 
                buffer.getvalue().encode('utf-8'), 
                f"analiz_{selected_file_name}.html", 
                "text/html"
            )

        with tab2:
            stats_data = []
            for topic, field in selected_series:
                data_obj = msg_data_map[topic]
                y = data_obj.data[field]
                stats_data.append({
                    "Parametre": f"{topic.split(' ')[0]}.{field}",
                    "Min": f"{float(np.nanmin(y)):.4f}",
                    "Maks": f"{float(np.nanmax(y)):.4f}",
                    "Ort": f"{float(np.nanmean(y)):.4f}",
                    "Std": f"{float(np.nanstd(y)):.4f}"
                })
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)
            
    else:
        st.markdown("""
        <div class="info-message">
            <h3>Grafik Goruntulemesi</h3>
            <p>Sag panelden analiz edilecek verileri secin</p>
        </div>
        """, unsafe_allow_html=True)
