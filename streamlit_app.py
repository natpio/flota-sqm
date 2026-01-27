import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY I STYLIZACJA
st.set_page_config(page_title="SQM LOGISTICS | FLOTA 2026", layout="wide", page_icon="🚚")

# Custom CSS dla lepszego wyglądu tabel i formularzy
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .main-header { font-size: 32px; font-weight: bold; color: #1e1e1E; margin-bottom: 20px; }
    .metric-container { background: white; padding: 15px; border-radius: 10px; border: 1px solid #e1e4e8; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-header">🚚 FLOTA SQM MULTIMEDIA SOLUTIONS 2026</p>', unsafe_allow_html=True)

# 2. POŁĄCZENIE Z BAZĄ
conn = st.connection("gsheets", type=GSheetsConnection)

def load_and_clean_data():
    raw_data = conn.read(worksheet="FLOTA_SQM", ttl="0")
    # Czyszczenie
    df = raw_data.dropna(how='all').copy()
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    df = df.dropna(subset=['Data_Start', 'Data_Koniec'])
    return df

try:
    df = load_and_clean_data()
except Exception as e:
    st.error("Problem z połączeniem. Sprawdź czy arkusz FLOTA_SQM jest udostępniony.")
    st.stop()

# 3. STATYSTYKI OPERACYJNE (KPI)
today = datetime.now()
active_trips = df[(df['Data_Start'] <= today) & (df['Data_Koniec'] >= today)]
in_service = df[df['Status'] == "Serwis"]

col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
with col_kpi1:
    st.metric("Pojazdy w trasie", len(active_trips))
with col_kpi2:
    st.metric("Zaplanowane (nadchodzące)", len(df[df['Data_Start'] > today]))
with col_kpi3:
    st.metric("W serwisie", len(in_service), delta_color="inverse")
with col_kpi4:
    st.metric("Łącznie transportów", len(df))

st.markdown("---")

# 4. SIDEBAR - DODAWANIE TRANSPORTU
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/uploads/2021/01/sqm_logo_black.png", width=150) # Przykładowe logo
    st.header("⚙️ Zarządzanie Trasą")
    
    with st.form("add_form", clear_on_submit=True):
        pojazd = st.selectbox("Pojazd", [
            "31 - TIR P21V388/P22X300 STABLEWSKI", "TIR 2 - W2654FT/P22H972 KOGUS",
            "TIR 3 - PNT3530A/P24U343 DANIELAK", "44 - SOLO PY 73262",
            "25 - Jumper - PY22952", "24 - Jumper - PY22954", "BOXER - PO 5VT68",
            "OPEL DW4W443", "SPEDYCJA"
        ])
        projekt = st.text_input("Nazwa Projektu / Targi", placeholder="np. MWC Barcelona")
        kierowca = st.text_input("Kierowca")
        
        c1, c2 = st.columns(2)
        d_start = c1.date_input("Wyjazd", value=today)
        d_end = c2.date_input("Powrót", value=today + timedelta(days=3))
        
        status = st.selectbox("Status", ["Planowanie", "Potwierdzone", "W trasie", "Serwis"])
        
        if st.form_submit_button("DODAJ DO GRAFIKU"):
            new_entry = pd.DataFrame([{
                "Pojazd": pojazd, "Projekt": projekt, "Kierowca": kierowca,
                "Data_Start": d_start.strftime('%Y-%m-%d'),
                "Data_Koniec": d_end.strftime('%Y-%m-%d'),
                "Status": status
            }])
            # Zapisz i odśwież
            all_data = pd.concat([conn.read(worksheet="FLOTA_SQM", ttl="0"), new_entry], ignore_index=True)
            conn.update(worksheet="FLOTA_SQM", data=all_data)
            st.rerun()

# 5. GRAFIK GANTTA (PODRASOWANY)
if not df.empty:
    # Przygotowanie do viz - paski muszą kończyć się na końcu dnia
    df['Viz_End'] = df['Data_Koniec'] + pd.Timedelta(days=1)
    
    # Stały porządek pojazdów (TIR -> BUS -> RESZTA)
    order = sorted(df['Pojazd'].unique())
    
    fig = px.timeline(
        df, 
        x_start="Data_Start", x_end="Viz_End", y="Pojazd", 
        color="Status", text="Projekt",
        hover_data={"Data_Start": "|%d %b", "Data_Koniec": "|%d %b", "Kierowca": True, "Viz_End": False},
        color_discrete_map={
            "Planowanie": "#ffcc00", "Potwierdzone": "#00aaff", 
            "W trasie": "#28a745", "Serwis": "#dc3545"
        },
        category_orders={"Pojazd": order}
    )

    # Styling wykresu
    fig.update_layout(
        height=500,
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(side="top", dtick="D1", tickformat="%d\n%b", gridcolor="#eeeeee"),
        yaxis=dict(title="", autorange="reversed", gridcolor="#eeeeee"),
        plot_bgcolor="white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # Dzisiejsza data - czerwona linia
    fig.add_vline(x=today.timestamp() * 1000, line_width=2, line_dash="dash", line_color="#ff4b4b")

    st.plotly_chart(fig, use_container_width=True)

# 6. TABELA Z PODGLĄDEM I EDYCJĄ
st.markdown("---")
with st.expander("🔍 ZOBACZ I EDYTUJ PEŁNĄ LISTĘ TRANSPORTÓW", expanded=True):
    # Czysty podgląd dla użytkownika
    df_editor = df.copy()
    df_editor['Data_Start'] = df_editor['Data_Start'].dt.date
    df_editor['Data_Koniec'] = df_editor['Data_Koniec'].dt.date
    if 'Viz_End' in df_editor.columns:
        df_editor = df_editor.drop(columns=['Viz_End'])

    edited_df = st.data_editor(
        df_editor,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["Planowanie", "Potwierdzone", "W trasie", "Serwis"]),
            "Data_Start": st.column_config.DateColumn("Start"),
            "Data_Koniec": st.column_config.DateColumn("Koniec"),
        }
    )

    if st.button("💾 ZAPISZ ZMIANY W BAZIE GOOGLE"):
        conn.update(worksheet="FLOTA_SQM", data=edited_df)
        st.success("Zapisano pomyślnie!")
        st.rerun()
