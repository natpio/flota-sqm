import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="FLOTA SQM 2026", layout="wide", page_icon="🚚")

# Custom CSS dla nowoczesnego wyglądu
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stSidebar { background-color: #1e293b; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 FLOTA SQM 2026 | Panel Logistyczny")

# 2. POŁĄCZENIE Z GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    df = conn.read(worksheet="FLOTA_SQM", ttl="0")
    df = df.dropna(how='all').copy()
    # Konwersja dat z zabezpieczeniem przed błędami w arkuszu
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    return df.dropna(subset=['Data_Start', 'Data_Koniec'])

try:
    df = get_data()
except Exception:
    st.error("Błąd pobierania danych. Upewnij się, że kolumny to: Pojazd, Projekt, Data_Start, Data_Koniec, Kierowca, Status.")
    st.stop()

# 3. STATYSTYKI NA ŻYWO
today = datetime.now()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Pojazdy w trasie", len(df[(df['Data_Start'] <= today) & (df['Data_Koniec'] >= today)]))
with col2:
    st.metric("Nadchodzące wyjazdy", len(df[df['Data_Start'] > today]))
with col3:
    st.metric("Pojazdy w serwisie", len(df[df['Status'] == "Serwis"]))
with col4:
    st.metric("Zrealizowane (rok 2026)", len(df[df['Data_Koniec'] < today]))

# 4. PANEL BOCZNY - ZARZĄDZANIE
with st.sidebar:
    st.header("⚙️ Nowy Transport")
    with st.form("add_form", clear_on_submit=True):
        pojazd = st.selectbox("Wybierz Auto", [
            "31 - TIR P21V388/P22X300 STABLEWSKI",
            "TIR 2 - W2654FT/P22H972 KOGUS",
            "TIR 3 - PNT3530A/P24U343 DANIELAK",
            "44 - SOLO PY 73262",
            "25 - Jumper - PY22952",
            "24 - Jumper - PY22954",
            "BOXER - PO 5VT68",
            "OPEL DW4W443",
            "SPEDYCJA"
        ])
        projekt = st.text_input("Nazwa Projektu / Targi")
        kierowca = st.text_input("Kierowca / Spedytor")
        c_v1, c_v2 = st.columns(2)
        d_s = c_v1.date_input("Wyjazd", value=today)
        d_e = c_v2.date_input("Powrót", value=today + timedelta(days=2))
        status = st.selectbox("Status", ["Planowanie", "Potwierdzone", "W trasie", "Serwis"])
        
        if st.form_submit_button("DODAJ DO GRAFIKU"):
            new_row = pd.DataFrame([{
                "Pojazd": pojazd, "Projekt": projekt, "Data_Start": d_s.strftime('%Y-%m-%d'),
                "Data_Koniec": d_e.strftime('%Y-%m-%d'), "Kierowca": kierowca, "Status": status
            }])
            # Pobranie aktualnego stanu i dopisanie
            full_df = pd.concat([conn.read(worksheet="FLOTA_SQM", ttl="0"), new_row], ignore_index=True)
            conn.update(worksheet="FLOTA_SQM", data=full_df)
            st.success("Zapisano!")
            st.rerun()

# 5. GRAFIK GANTTA (PODRASOWANY)
st.subheader("🗓️ Harmonogram Dzienny")

# Suwak zakresu dat
date_range = st.date_input("Zakres widoku grafiku:", [today - timedelta(days=3), today + timedelta(days=14)])

if len(date_range) == 2:
    # Korekta wizualna - pasek musi kończyć się na końcu dnia powrotu
    df_viz = df.copy()
    df_viz['Viz_End'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)
    
    fig = px.timeline(
        df_viz, x_start="Data_Start", x_end="Viz_End", y="Pojazd", color="Status",
        text="Projekt", hover_data=["Kierowca", "Data_Start", "Data_Koniec"],
        color_discrete_map={
            "Planowanie": "#FAD02E", "Potwierdzone": "#45B6FE", 
            "W trasie": "#37BC61", "Serwis": "#E1341E"
        }
    )
    
    # Wyraźna siatka co 1 dzień
    fig.update_xaxes(
        dtick="D1", tickformat="%d\n%b", gridcolor="#e5e7eb", side="top",
        range=[date_range[0], date_range[1]]
    )
    fig.update_yaxes(autorange="reversed", gridcolor="#f3f4f6")
    
    # Czerwona linia 'DZIŚ'
    fig.add_vline(x=today.timestamp() * 1000, line_width=3, line_color="red", opacity=0.7)
    
    fig.update_layout(
        height=600, margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor="white", showlegend=True, legend_orientation="h"
    )
    
    st.plotly_chart(fig, use_container_width=True)

# 6. TABELA EDYCJI
with st.expander("📝 Edytuj bazę danych bezpośrednio"):
    df_edit = df.copy()
    df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
    df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
    
    edited_df = st.data_editor(
        df_edit, num_rows="dynamic", use_container_width=True,
        column_config={
            "Data_Start": st.column_config.DateColumn("Start"),
            "Data_Koniec": st.column_config.DateColumn("Koniec"),
            "Status": st.column_config.SelectboxColumn("Status", options=["Planowanie", "Potwierdzone", "W trasie", "Serwis"])
        }
    )
    
    if st.button("💾 ZAPISZ ZMIANY"):
        conn.update(worksheet="FLOTA_SQM", data=edited_df)
        st.success("Baza zaktualizowana!")
        st.rerun()
