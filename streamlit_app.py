import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY - MUSI BYĆ NA POCZĄTKU
st.set_page_config(
    page_title="SQM Dashboard",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. ZAAWANSOWANY CSS DLA EFEKTU DASHBOARDU
st.markdown("""
    <style>
    /* Stylizacja tła i głównego kontenera */
    .stApp { background-color: #F4F7F9; }
    
    /* Panel boczny - Ciemny motyw */
    [data-testid="stSidebar"] {
        background-color: #1E293B !important;
        color: white !important;
    }
    [data-testid="stSidebar"] * { color: white !important; }
    
    /* Karty metryk (KPIs) */
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #E2E8F0;
    }
    
    /* Stylowanie zakładek (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        border: 1px solid #E2E8F0;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important;
        color: white !important;
        border-color: #2563EB !important;
    }

    /* Nagłówek sekcji */
    .section-header {
        font-size: 20px;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 20px;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. POŁĄCZENIE Z DANYMI
conn = st.connection("gsheets", type=GSheetsConnection)

def load_clean_data():
    df = conn.read(ttl="2s")
    df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
    df['Data_Start'] = pd.to_datetime(df['Data_Start'])
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'])
    return df

try:
    df = load_clean_data()

    # --- PANEL BOCZNY (SIDEBAR) ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>SQM LOGISTICS</h2>", unsafe_allow_html=True)
        st.divider()
        st.markdown("### 📋 PANEL STEROWANIA")
        
        # Filtry w panelu bocznym
        search = st.text_input("🔍 Szukaj projektu/auta")
        
        status_filter = st.multiselect(
            "Filtruj status:",
            options=df['Status'].unique(),
            default=df['Status'].unique()
        )
        
        st.divider()
        if st.button("🔄 Odśwież system", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.caption("SQM Fleet Management v3.0")

    # --- NAGŁÓWEK GŁÓWNY ---
    st.markdown("<div class='section-header'>Pulpit Logistics Dashboard</div>", unsafe_allow_html=True)
    st.caption(f"Ostatnia synchronizacja: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

    # --- METRYKI (KPI CARDS) ---
    m1, m2, m3, m4 = st.columns(4)
    
    today = pd.Timestamp.now().normalize()
    active_today = df[(df['Data_Start'] <= today) & (df['Data_Koniec'] >= today)].shape[0]
    upcoming = df[df['Data_Start'] > today].shape[0]
    
    with m1: st.metric("Łączna flota", df['Pojazd'].nunique())
    with m2: st.metric("Aktywne projekty", df['Projekt'].nunique())
    with m3: st.metric("Pojazdy w trasie", active_today)
    with m4: st.metric("Zaplanowane (7d)", upcoming)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- FILTROWANIE DANYCH ---
    filtered_df = df[
        (df['Projekt'].str.contains(search, case=False) | df['Pojazd'].str.contains(search, case=False)) &
        (df['Status'].isin(status_filter))
    ]

    # --- GŁÓWNA SEKCJA Z TABAMI ---
    t1, t2, t3 = st.tabs(["📊 Harmonogram Gantt", "📑 Tabela Operacyjna", "⚠️ Konflikty"])

    with t1:
        st.markdown("<div style='background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
        if not filtered_df.empty:
            fig = px.timeline(
                filtered_df,
                x_start="Data_Start",
                x_end="Data_Koniec",
                y="Pojazd",
                color="Projekt",
                text="Projekt",
                hover_data=["Kierowca", "Status"],
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            
            # Linia "TERAZ"
            fig.add_vline(x=datetime.now(), line_width=3, line_dash="solid", line_color="#EF4444", 
                         annotation_text="TERAZ", annotation_position="top left")
            
            fig.update_yaxes(autorange="reversed", title="", gridcolor="#F1F5F9")
            fig.update_xaxes(title="Oś czasu (dni)", gridcolor="#F1F5F9")
            
            fig.update_layout(
                height=500,
                margin=dict(l=0, r=0, t=20, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            fig.update_traces(marker_line_color='white', marker_line_width=2, opacity=0.9)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning("Brak danych do wyświetlenia.")
        st.markdown("</div>", unsafe_allow_html=True)

    with t2:
        st.dataframe(
            filtered_df.sort_values("Data_Start"),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Data_Start": st.column_config.DateColumn("Data Start"),
                "Data_Koniec": st.column_config.DateColumn("Data Koniec"),
                "Pojazd": st.column_config.TextColumn("🚚 Pojazd"),
                "Status": st.column_config.SelectboxColumn("Status", options=["Zaplanowane", "W trasie", "Auto", "Zakończone"])
            }
        )

    with t3:
        # Logika konfliktów
        df_conf = filtered_df.sort_values(['Pojazd', 'Data_Start'])
        conflicts = []
        for i in range(len(df_conf)-1):
            if df_conf.iloc[i]['Pojazd'] == df_conf.iloc[i+1]['Pojazd']:
                if df_conf.iloc[i]['Data_Koniec'] > df_conf.iloc[i+1]['Data_Start']:
                    conflicts.append(df_conf.iloc[i:i+2])
        
        if conflicts:
            st.error("🚨 Wykryto kolizje w rezerwacji pojazdów!")
            st.table(pd.concat(conflicts).drop_duplicates())
        else:
            st.success("Wszystkie zasoby są poprawnie zaplanowane.")

except Exception as e:
    st.error(f"Błąd krytyczny: {e}")
