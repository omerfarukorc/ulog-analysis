import streamlit as st
import os
from pyulog import ULog
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Config
ULOG_DIR = "uploaded_ulogs"
os.makedirs(ULOG_DIR, exist_ok=True)

st.set_page_config(
    layout="wide",
    page_title="ULog Analytics",
    initial_sidebar_state="collapsed"
)

# Compact Modern Dark Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    #MainMenu, footer, .stDeployButton { display: none !important; }
    [data-testid="stHeader"] { background: transparent; }
    
    .block-container { padding: 0.5rem 0.75rem !important; max-width: 100%; }
    .stApp { background: #0f172a; }
    
    /* Panel başlık */
    .panel-header {
        font-size: 0.6rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.4rem;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid #1e293b;
    }
    
    /* Seçili chip - kompakt */
    .selected-chip {
        display: inline-block;
        background: #3b82f6;
        border-radius: 8px;
        padding: 2px 6px;
        margin: 2px;
        font-size: 0.6rem;
        color: white;
    }
    
    /* Info box - dark */
    .info-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1.5rem;
        text-align: center;
        color: #64748b;
    }
    .info-box h3 { color: #94a3b8; font-size: 1rem; font-weight: 500; margin-bottom: 0.3rem; }
    .info-box p { font-size: 0.8rem; margin: 0; }
    
    /* Scrollbar */
    ::-webkit-scrollbar { width: 3px; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 2px; }
    
    hr { border-color: #1e293b; margin: 0.3rem 0; }
    
    /* Input - kompakt */
    .stTextInput > div > div > input { 
        font-size: 0.7rem !important; 
        padding: 0.3rem 0.5rem !important;
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 4px !important;
        color: #e2e8f0 !important;
    }
    
    /* Button - çok kompakt */
    .stButton > button { 
        font-size: 0.65rem !important; 
        padding: 0.2rem 0.4rem !important;
        min-height: 0 !important;
        line-height: 1.2 !important;
        border-radius: 3px !important;
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        color: #94a3b8 !important;
    }
    .stButton > button:hover {
        background: #334155 !important;
        color: #e2e8f0 !important;
    }
    
    /* Caption - küçük */
    .stCaption { font-size: 0.6rem !important; color: #64748b !important; }
    
    /* Selectbox - kompakt */
    .stSelectbox > div > div { 
        font-size: 0.7rem !important;
        background: #1e293b !important;
    }
    .stSelectbox label { font-size: 0.6rem !important; color: #64748b !important; }
    
    /* File uploader - kompakt */
    .stFileUploader { padding: 0 !important; }
    .stFileUploader > div { padding: 0.3rem !important; }
    .stFileUploader label { font-size: 0.6rem !important; }
    
    /* Tabs - kompakt */
    .stTabs [data-baseweb="tab"] { font-size: 0.7rem !important; padding: 0.3rem 0.6rem !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# LAZY LOADING CACHE FUNCTIONS
# ============================================================================

@st.cache_data(show_spinner=False)
def load_topic_names(file_path: str) -> list:
    """Sadece topic isimlerini yükle - çok hızlı"""
    try:
        ulog = ULog(file_path)
        return sorted([f"{d.name}_{d.multi_id}" for d in ulog.data_list])
    except:
        return []

@st.cache_data(show_spinner=False)
def load_topic_fields(file_path: str, topic: str) -> list:
    """Bir topic'in field'larını yükle - topic tıklanınca"""
    try:
        ulog = ULog(file_path)
        for d in ulog.data_list:
            if f"{d.name}_{d.multi_id}" == topic:
                return sorted([k for k in d.data.keys() if k != 'timestamp'])
        return []
    except:
        return []

@st.cache_data(show_spinner=False)
def load_field_data(file_path: str, topic: str, field: str):
    """Sadece seçilen verinin time-series'ini yükle - grafik çizilirken"""
    try:
        ulog = ULog(file_path)
        for d in ulog.data_list:
            if f"{d.name}_{d.multi_id}" == topic:
                t = d.data['timestamp'] / 1e6
                y = d.data[field]
                return t, y
        return None, None
    except:
        return None, None

# ============================================================================
# SESSION STATE
# ============================================================================

if "expanded_topics" not in st.session_state:
    st.session_state.expanded_topics = []
if "selected_params" not in st.session_state:
    st.session_state.selected_params = []

# ============================================================================
# LAYOUT: Sol Panel | Orta (Grafik) | Sağ Panel
# ============================================================================

col_left, col_main, col_right = st.columns([1.2, 4, 1.5])

# --- SOL PANEL: DOSYA ---
with col_left:
    st.markdown('<div class="panel-header">Dosya</div>', unsafe_allow_html=True)
    
    uploaded = st.file_uploader("", type=["ulg"], label_visibility="collapsed")
    if uploaded:
        with open(os.path.join(ULOG_DIR, uploaded.name), "wb") as f:
            f.write(uploaded.getbuffer())
        st.success(f"{uploaded.name}")
    
    files = sorted([f for f in os.listdir(ULOG_DIR) if f.endswith(".ulg")])
    if not files:
        st.info("ULog yükleyin")
        st.stop()
    
    selected_file = st.selectbox("", files, label_visibility="collapsed")
    ulog_path = os.path.join(ULOG_DIR, selected_file)
    
    size_mb = os.path.getsize(ulog_path) / (1024*1024)
    st.caption(f"{size_mb:.2f} MB")
    
    # Seçili parametreler
    if st.session_state.selected_params:
        st.markdown('<div class="panel-header">Secili</div>', unsafe_allow_html=True)
        for tp, fd in st.session_state.selected_params:
            st.markdown(f'<span class="selected-chip">{fd[:15]}</span>', unsafe_allow_html=True)
        
        if st.button("Temizle", use_container_width=True):
            st.session_state.selected_params = []
            st.rerun()

# --- SAĞ PANEL: VERİ SEÇİMİ (LAZY LOADING) ---
with col_right:
    st.markdown('<div class="panel-header">Veri Secimi</div>', unsafe_allow_html=True)
    
    search = st.text_input("", placeholder="Ara...", label_visibility="collapsed")
    
    # Sadece topic isimlerini yükle (çok hızlı)
    topics = load_topic_names(ulog_path)
    
    # Filtrele
    if search:
        topics = [t for t in topics if search.lower() in t.lower()]
    
    st.caption(f"{len(topics)} topic")
    
    # Topic listesi (scrollable)
    topic_container = st.container(height=550)
    
    with topic_container:
        for topic in topics[:60]:  # Performans için limit
            is_expanded = topic in st.session_state.expanded_topics
            arrow = "▼" if is_expanded else "▶"
            
            # Topic butonu
            if st.button(f"{arrow} {topic[:28]}", key=f"t_{topic}", use_container_width=True):
                if is_expanded:
                    st.session_state.expanded_topics.remove(topic)
                else:
                    st.session_state.expanded_topics.append(topic)
                st.rerun()
            
            # Field'lar - SADECE AÇIKSA YÜKLE (Lazy Loading)
            if is_expanded:
                fields = load_topic_fields(ulog_path, topic)  # Sadece bu topic için yükle
                
                for field in fields[:30]:
                    param = (topic, field)
                    is_selected = param in st.session_state.selected_params
                    
                    fc1, fc2 = st.columns([5, 1])
                    with fc1:
                        st.caption(f"  {field[:20]}")
                    with fc2:
                        btn_label = "✓" if is_selected else "+"
                        if st.button(btn_label, key=f"f_{topic}_{field}"):
                            if is_selected:
                                st.session_state.selected_params.remove(param)
                            else:
                                st.session_state.selected_params.append(param)
                            st.rerun()

# --- ORTA: GRAFİK ---
COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

with col_main:
    if st.session_state.selected_params:
        tab1, tab2 = st.tabs(["Grafik", "Istatistik"])
        
        with tab1:
            fig = go.Figure()
            
            for idx, (topic, field) in enumerate(st.session_state.selected_params):
                # Sadece seçili veriyi yükle (Lazy Loading)
                t, y = load_field_data(ulog_path, topic, field)
                
                if t is not None:
                    fig.add_trace(go.Scatter(
                        x=t, y=y,
                        name=f"{topic.split('_')[0]}.{field}",
                        mode='lines',
                        line=dict(color=COLORS[idx % len(COLORS)], width=1.5)
                    ))
            
            fig.update_layout(
                height=600,
                template="plotly_dark",
                hovermode="x unified",
                margin=dict(l=50, r=20, t=30, b=50),
                paper_bgcolor='#0f172a',
                plot_bgcolor='#1e293b',
                xaxis=dict(title="Zaman (s)", gridcolor='#334155'),
                yaxis=dict(title="Deger", gridcolor='#334155'),
                legend=dict(orientation="h", y=1.02, font=dict(size=9))
            )
            
            st.plotly_chart(fig, use_container_width=True, config={
                'scrollZoom': True,
                'displayModeBar': True,
                'displaylogo': False
            })
        
        with tab2:
            stats = []
            for topic, field in st.session_state.selected_params:
                t, y = load_field_data(ulog_path, topic, field)
                if y is not None:
                    stats.append({
                        "Parametre": f"{topic.split('_')[0]}.{field}",
                        "Min": f"{float(np.nanmin(y)):.4f}",
                        "Max": f"{float(np.nanmax(y)):.4f}",
                        "Ort": f"{float(np.nanmean(y)):.4f}",
                        "Std": f"{float(np.nanstd(y)):.4f}"
                    })
            st.dataframe(pd.DataFrame(stats), use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div class="info-box">
            <h3 style="color: rgba(255,255,255,0.7); font-weight: 500;">Grafik Goruntuleme</h3>
            <p>Sag panelden veri secin</p>
        </div>
        """, unsafe_allow_html=True)
