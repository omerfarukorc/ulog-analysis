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
    page_title="ULog Analiz Sistemi",
    initial_sidebar_state="expanded"
)

# CSS Düzenlemesi (Standart Görünüm)
st.markdown("""
<style>
    /* Sadece üst boşluğu biraz azaltalim, gerisine karismiyoruz */
    .block-container {
        padding-top: 2rem;
    }
    
    /* Font iyilestirmesi kalsin */
    * {
        font-family: 'Segoe UI', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# --- SOL SIDEBAR (DOSYA YÖNETİMİ) ---
with st.sidebar:
    st.header("Dosya Yonetimi")
    
    uploaded_file = st.file_uploader("Yeni Log Yukle", type=["ulg"])
    if uploaded_file:
        file_path = os.path.join(ULOG_STORAGE_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"{uploaded_file.name} yuklendi.")
    
    st.markdown("---")
    
    existing_files = [f for f in os.listdir(ULOG_STORAGE_DIR) if f.endswith(".ulg")]
    
    selected_file_name = None
    if existing_files:
        selected_file_name = st.selectbox(
            "Incelenecek Dosyayi Secin:", 
            existing_files, 
            index=len(existing_files)-1
        )
        if selected_file_name:
            file_path = os.path.join(ULOG_STORAGE_DIR, selected_file_name)
            size_mb = os.path.getsize(file_path) / (1024*1024)
            st.caption(f"Boyut: {size_mb:.2f} MB")
    else:
        st.info("Kayitli dosya yok.")

# --- ANA EKRAN YAPISI ---
if not selected_file_name:
    st.info("Lutfen sol menuden bir dosya yukleyin veya secin.")
    st.stop()

# Dosyayı Oku
ulog = None
try:
    ulog = ULog(os.path.join(ULOG_STORAGE_DIR, selected_file_name))
except Exception as e:
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


# --- LAYOUT: [ GRAFİK (SOL %75) ]  [ VERİ SEÇİMİ (SAĞ %25) ] ---
col_graph, col_data = st.columns([3, 1])

# --- SAĞ SÜTUN (VERİ SEÇİMİ) ---
selected_series = []

with col_data:
    st.subheader("Veri Secimi")
    st.caption("Gormek istediginiz verileri isaretleyin.")
    
    search_query = st.text_input("Ara", placeholder="ornek: battery.voltage")
    
    search_topic = ""
    search_field = ""
    if "." in search_query:
        parts = search_query.split(".", 1)
        search_topic, search_field = parts[0].lower(), parts[1].lower()
    else:
        search_topic = search_query.lower()

    count_found = 0
    
    # Tüm topicleri listeleme
    for topic_name in sorted(topics.keys()):
        fields = topics[topic_name]
        
        t_name_lower = topic_name.lower()
        topic_matches = search_topic in t_name_lower
        
        # Filtreleme mantığı
        if "." in search_query:
            display_fields = [f for f in fields if search_field in f.lower()] if topic_matches else []
        else:
            display_fields = fields if topic_matches else [f for f in fields if search_query.lower() in f.lower()]
            
        if not display_fields:
            continue
            
        count_found += 1
        
        # Expander (Varsayılan kapalı)
        with st.expander(topic_name, expanded=bool(search_query)):
            for field in display_fields:
                unique_key = f"{topic_name}_{field}"
                if st.checkbox(field, key=unique_key):
                    selected_series.append((topic_name, field))

    if search_query and count_found == 0:
        st.warning("Sonuc bulunamadi.")


# --- SOL SÜTUN (GRAFİK) ---
with col_graph:
    st.subheader(f"Analiz: {selected_file_name}")
    
    if selected_series:
        tab1, tab2 = st.tabs(["Grafik Analizi", "Detayli Istatistikler"])
        
        with tab1:
            fig = go.Figure()
            for topic, field in selected_series:
                data_obj = msg_data_map[topic]
                t = data_obj.data['timestamp'] / 1e6
                y = data_obj.data[field]
                fig.add_trace(go.Scatter(x=t, y=y, name=f"{topic}.{field}", mode='lines'))
            
            fig.update_layout(
                xaxis_title="Zaman (saniye)",
                yaxis_title="Deger",
                height=700,
                template="plotly_white",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=20, b=20)
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
            # İsteğe bağlı etiket 'HTML Olarak İndir' (Mail ibaresi kaldırıldı)
            st.download_button("Grafigi HTML Olarak Indir", buffer.getvalue().encode('utf-8'), f"analiz_{selected_file_name}.html", "text/html")

        with tab2:
            stats_data = []
            for topic, field in selected_series:
                data_obj = msg_data_map[topic]
                y = data_obj.data[field]
                stats_data.append({
                    "Parametre": f"{topic}.{field}",
                    "Min": float(np.nanmin(y)),
                    "Maks": float(np.nanmax(y)),
                    "Ortalama": float(np.nanmean(y)),
                    "Std Sapma": float(np.nanstd(y))
                })
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True)
            
    else:
        st.info("Grafik olusturmak icin sagdaki panelden veri seciniz.")
