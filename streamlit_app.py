import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Konfiguracja strony
st.set_page_config(page_title="FLOTA SQM 2026", layout="wide")

st.title("🚚 FLOTA SQM 2026")
st.markdown("---")

# Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(worksheet="FLOTA_SQM", ttl="0")
    # Czyścimy dane: usuwamy całkowicie puste wiersze
    data = data.dropna(how='all')
    # Wymuszamy format daty, błędy zamieniamy na NaT (Not a Time)
    data['Data_Start'] = pd.to_datetime(data['Data_Start'], errors='coerce')
    data['Data_Koniec'] = pd.to_datetime(data['Data_Koniec'], errors='coerce')
    # Usuwamy wiersze, które mają niepoprawne daty (np. napisy zamiast dat)
    data = data.dropna(subset=['Data_Start', 'Data_Koniec'])
    return data

try:
    df = load_data()
except Exception as e:
    st.error("Błąd połączenia lub formatu danych. Sprawdź czy arkusz 'FLOTA_SQM' nie zawiera błędnych wpisów.")
    st.stop()

# --- PANEL BOCZNY: FORMULARZ ---
with st.sidebar:
    st.header("➕ Dodaj Transport")
    with st.form("add_form", clear_on_submit=True):
        pojazd = st.selectbox("Wybierz Pojazd", [
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
        kierowca = st.text_input("Kierowca")
        
        c1, c2 = st.columns(2)
        d_start = c1.date_input("Data Wyjazdu", value=datetime.now())
        d_end = c2.date_input("Data Powrotu", value=datetime.now() + timedelta(days=2))
        
        status = st.selectbox("Status", ["Planowanie", "Potwierdzone", "W trasie", "Serwis"])
        
        submitted = st.form_submit_button("ZAPISZ")
        
        if submitted:
            new_row = pd.DataFrame([{
                "Pojazd": pojazd,
                "Projekt": projekt,
                "Data_Start": d_start.strftime('%Y-%m-%d'),
                "Data_Koniec": d_end.strftime('%Y-%m-%d'),
                "Kierowca": kierowca,
                "Status": status
            }])
            # Pobieramy świeże dane przed zapisem, aby nie nadpisać cudzej pracy
            current_df = conn.read(worksheet="FLOTA_SQM", ttl="0")
            updated_df = pd.concat([current_df, new_row], ignore_index=True)
            conn.update(worksheet="FLOTA_SQM", data=updated_df)
            st.success("Zapisano!")
            st.rerun()

# --- GŁÓWNY PANEL ---
if not df.empty:
    # Przygotowanie do wykresu
    df['Viz_End'] = df['Data_Koniec'] + pd.Timedelta(days=1)

    st.subheader("🗓️ Widok Dzienny Floty")
    
    # Wykres Gantta
    fig = px.timeline(
        df, 
        x_start="Data_Start", 
        x_end="Viz_End", 
        y="Pojazd", 
        color="Status",
        text="Projekt",
        color_discrete_map={
            "Planowanie": "#FAD02E", "Potwierdzone": "#45B6FE", 
            "W trasie": "#37BC61", "Serwis": "#E1341E"
        }
    )

    fig.update_xaxes(dtick="D1", tickformat="%d\n%b", gridcolor="LightGrey", side="top")
    fig.update_yaxes(autorange="reversed")
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_color="red")
    fig.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=10))

    st.plotly_chart(fig, use_container_width=True)

    # --- EDYCJA TABELI (Tutaj był błąd) ---
    st.markdown("---")
    st.subheader("📋 Edycja danych")
    
    # Przygotowanie tabeli do edycji - konwersja na czyste daty bez godzin
    df_editor = df.copy()
    df_editor['Data_Start'] = df_editor['Data_Start'].dt.date
    df_editor['Data_Koniec'] = df_editor['Data_Koniec'].dt.date
    # Usuwamy kolumnę techniczną dla wykresu
    if 'Viz_End' in df_editor.columns:
        df_editor = df_editor.drop(columns=['Viz_End'])

    edited_df = st.data_editor(
        df_editor, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Data_Start": st.column_config.DateColumn("Start"),
            "Data_Koniec": st.column_config.DateColumn("Koniec"),
            "Status": st.column_config.SelectboxColumn("Status", options=["Planowanie", "Potwierdzone", "W trasie", "Serwis"])
        }
    )
    
    if st.button("💾 ZAPISZ ZMIANY W ARKUSZU"):
        conn.update(worksheet="FLOTA_SQM", data=edited_df)
        st.success("Zaktualizowano!")
        st.rerun()
else:
    st.info("Baza jest pusta lub zawiera błędne dane.")
