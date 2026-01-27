import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Konfiguracja strony - Logistyka SQM Premium
st.set_page_config(
    page_title="SQM LOGISTICS | Fleet Intelligence",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Zaawansowana stylizacja UI
st.markdown("""
    <style>
    /* Główny tło i fonty */
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    
    /* Nowoczesne karty metryk */
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #00d4ff !important; font-weight: 700; }
    div[data-testid="stMetric"] {
        background-color: #1a1c24;
        border: 1px solid #2d2f39;
        padding: 15px 20px;
        border-radius: 12px;
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-5px); border-color: #00d4ff; }
    
    /* Stylizacja tabeli i edytora */
    div.stDataEditor { border: 1px solid #2d2f39 !important; border-radius: 10px !important; overflow: hidden; }
    
    /* Przycisk zapisu */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #00d4ff 0%, #0055ff 100%);
        color: white;
        border: none;
        padding: 12px;
        font-weight: 600;
        border-radius: 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Zarządzanie danymi
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        
        data.columns = [c.strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        
        # Oczyszczanie tekstów
        for col in ['pojazd', 'event', 'kierowca', 'notatka']:
            if col in data.columns:
                data[col] = data[col].astype(str).replace(['nan', 'None'], '')
        return data
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = load_data()

# --- HEADER SEKCA ---
col_logo, col_title = st.columns([1, 4])
with col_title:
    st.title("FLEET INTELLIGENCE PLATFORM")
    st.caption("SQM Multimedia Solutions | Global Logistics Management")

# --- DASHBOARD STATS ---
today = datetime.now()
total_v = df['pojazd'].nunique() if not df.empty else 0
active_v = df[(df['start'] <= today) & (df['koniec'] >= today)].shape[0] if not df.empty else 0
upcoming = df[df['start'] > today].shape[0] if not df.empty else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Wszystkie Pojazdy", f"{total_v}")
m2.metric("W Trasie (Dzisiaj)", f"{active_v}")
m3.metric("Nadchodzące Zadania", f"{upcoming}")
m4.metric("Status Systemu", "ONLINE", delta="Cloud Sync")

st.markdown("<br>", unsafe_allow_html=True)

# --- VISUALIZATION (GANTT) ---
if not df.empty and df['start'].notnull().any():
    # Grupowanie i sortowanie dla czytelności
    plot_df = df.dropna(subset=['start', 'koniec', 'pojazd'])
    plot_df = plot_df[plot_df['pojazd'] != ""].sort_values('pojazd')

    # Wykres w nowoczesnej palecie
    fig = px.timeline(
        plot_df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="pojazd", # Każdy pojazd ma swój kolor bazowy
        hover_name="event",
        text="event",
        custom_data=["kierowca", "notatka"],
        color_discrete_sequence=px.colors.sequential.GnBu_r
    )

    fig.update_yaxes(autorange="reversed", title="", gridcolor="#2d2f39", tickfont=dict(color="#a0a0a0"))
    fig.update_xaxes(
        title="", 
        side="top", 
        gridcolor="#2d2f39", 
        tickfont=dict(color="#a0a0a0"),
        dtick="D1", 
        tickformat="%d %b"
    )

    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        marker=dict(line=dict(width=0), borderround=10), # Zaokrąglone krawędzie (symulowane)
        hovertemplate="<b>%{hovertext}</b><br>Kierowca: %{customdata[0]}<br>Notatka: %{customdata[1]}<extra></extra>"
    )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=500,
        showlegend=False,
        margin=dict(l=10, r=10, t=50, b=10),
        font=dict(family="Inter, sans-serif", size=11)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- DATA MANAGEMENT ---
st.markdown("### 🛠 CENTRALNY PANEL OPERACYJNY")

tab1, tab2 = st.tabs(["📝 Planowanie Floty", "⚠️ Analiza Konfliktów"])

with tab1:
    editor_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "pojazd": st.column_config.TextColumn("🚛 POJAZD", help="Nazwa lub rejestracja", width="medium"),
            "event": st.column_config.TextColumn("🏷 NAZWA EVENTU", width="large"),
            "start": st.column_config.DateColumn("📆 DATA STARTU"),
            "koniec": st.column_config.DateColumn("🏁 DATA KOŃCA"),
            "kierowca": st.column_config.TextColumn("👤 KIEROWCA"),
            "notatka": st.column_config.TextColumn("💬 UWAGI / NOTATKA")
        },
        key="sqm_premium_v5"
    )

    if st.button("Zapisz i Synchronizuj Dane"):
        save_df = editor_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d').fillna('')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(data=save_df)
        st.toast("Dane zsynchronizowane z chmurą SQM!", icon="🚀")
        st.rerun()

with tab2:
    # Zaawansowana detekcja konfliktów
    if not editor_df.empty:
        conf_df = editor_df.sort_values(['pojazd', 'start'])
        conflicts_found = False
        for v in conf_df['pojazd'].unique():
            if not v: continue
            v_data = conf_df[conf_df['pojazd'] == v]
            for i in range(len(v_data)-1):
                if v_data.iloc[i]['koniec'] > v_data.iloc[i+1]['start']:
                    st.error(f"❌ KONFLIKT POJAZDU: {v} | Nakładają się eventy: '{v_data.iloc[i]['event']}' oraz '{v_data.iloc[i+1]['event']}'")
                    conflicts_found = True
        if not conflicts_found:
            st.success("✅ Brak kolizji w obecnym planie floty.")
