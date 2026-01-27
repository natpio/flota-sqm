import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Konfiguracja strony - SQM LOGISTICS PREMIUM
st.set_page_config(
    page_title="SQM LOGISTICS | Fleet Intelligence",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Zaawansowana stylizacja UI (Modern Dark Mode)
st.markdown("""
    <style>
    .stApp { background-color: #0b0d11; color: #e0e0e0; }
    
    /* Karty statystyk */
    div[data-testid="stMetric"] {
        background-color: #161920;
        border: 1px solid #2d3139;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricValue"] { color: #00d4ff !important; font-family: 'JetBrains Mono', monospace; }
    
    /* Przycisk zapisu */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #00d4ff 0%, #0055ff 100%);
        color: white; border: none; padding: 15px;
        font-weight: 700; border-radius: 10px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(0,212,255,0.4); }
    
    /* Edytor danych */
    div.stDataEditor { border: 1px solid #2d3139 !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. Połączenie z danymi
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        
        data.columns = [c.strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        
        # Usuwanie nan/None z tekstów
        for col in ['pojazd', 'event', 'kierowca', 'notatka']:
            if col in data.columns:
                data[col] = data[col].astype(str).replace(['nan', 'None'], '')
        return data
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = load_data()

# --- HEADER ---
st.title("🛰️ FLEET INTELLIGENCE PLATFORM")
st.caption("SQM Multimedia Solutions | Global Logistics Center")

# --- DASHBOARD METRYK ---
today = datetime.now()
total_v = df['pojazd'].nunique() if not df.empty else 0
active_tasks = df[(df['start'] <= today) & (df['koniec'] >= today)].shape[0] if not df.empty else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("FLOTA OGÓŁEM", total_v)
m2.metric("W REALIZACJI", active_tasks)
m3.metric("AKTYWNE EVENTY", len(df))
m4.metric("SYSTEM STATUS", "OPERATIONAL")

st.markdown("<br>", unsafe_allow_html=True)

# --- WIZUALIZACJA GANTT (Poprawiona) ---
if not df.empty and df['start'].notnull().any():
    plot_df = df.dropna(subset=['start', 'koniec', 'pojazd'])
    plot_df = plot_df[plot_df['pojazd'] != ""].sort_values('pojazd')

    # Tworzenie wykresu
    fig = px.timeline(
        plot_df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="pojazd", # Każdy pojazd ma swój kolor
        hover_name="event",
        text="event",
        custom_data=["kierowca", "notatka"],
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Safe # Czytelna paleta kolorów
    )

    # Poprawione parametry śladów (usunięty błąd borderround)
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        marker=dict(line=dict(width=1, color='#2d3139')),
        hovertemplate="<b>%{hovertext}</b><br>Kierowca: %%{customdata[0]}<br>Notatka: %{customdata[1]}<extra></extra>"
    )

    fig.update_yaxes(autorange="reversed", title="", gridcolor="#1f2229")
    fig.update_xaxes(side="top", gridcolor="#1f2229", dtick="D1", tickformat="%d %b")

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=600,
        showlegend=False,
        margin=dict(l=10, r=10, t=50, b=10)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- OPERACJE ---
st.markdown("### 🛠 PANEL ZARZĄDZANIA")

tab_edit, tab_conflicts = st.tabs(["📝 Harmonogram", "⚠️ Konflikty i Kolizje"])

with tab_edit:
    editor_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "pojazd": st.column_config.TextColumn("🚛 POJAZD"),
            "event": st.column_config.TextColumn("🏷 EVENT"),
            "start": st.column_config.DateColumn("📆 START"),
            "koniec": st.column_config.DateColumn("🏁 KONIEC"),
            "kierowca": st.column_config.TextColumn("👤 KIEROWCA"),
            "notatka": st.column_config.TextColumn("💬 UWAGI")
        },
        key="sqm_final_v1"
    )

    if st.button("ZAPISZ I SYNCHRONIZUJ Z CHMURĄ"):
        save_df = editor_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d').fillna('')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(data=save_df)
        st.toast("Dane przesłane do Google Sheets!", icon="🚀")
        st.rerun()

with tab_conflicts:
    if not editor_df.empty:
        c_df = editor_df.sort_values(['pojazd', 'start'])
        conflicts = []
        for v in c_df['pojazd'].unique():
            if not v: continue
            v_data = c_df[c_df['pojazd'] == v]
            for i in range(len(v_data)-1):
                if v_data.iloc[i]['koniec'] > v_data.iloc[i+1]['start']:
                    conflicts.append(f"**{v}**: '{v_data.iloc[i]['event']}' nakłada się na '{v_data.iloc[i+1]['event']}'")
        
        if conflicts:
            for c in conflicts: st.error(c)
        else:
            st.success("Brak kolizji w obecnym planie.")
