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
    return conn.read(worksheet="FLOTA_SQM", ttl="0")

try:
    df = load_data()
except Exception as e:
    st.error("Błąd połączenia z arkuszem FLOTA_SQM. Sprawdź nazwę zakładki i uprawnienia.")
    st.stop()

# --- PANEL BOCZNY: FORMULARZ DODAWANIA ---
with st.sidebar:
    st.header("➕ Dodaj Transport")
    with st.form("add_form"):
        # Grupowanie pojazdów zgodnie z Twoim Excelem
        pojazd = st.selectbox("Wybierz Pojazd", [
            "--- CIĘŻAROWE ---",
            "31 - TIR P21V388/P22X300 STABLEWSKI",
            "TIR 2 - W2654FT/P22H972 KOGUS",
            "TIR 3 - PNT3530A/P24U343 DANIELAK",
            "44 - SOLO PY 73262",
            "45 - PY1541M + przyczepa",
            "--- BUSY ---",
            "25 - Jumper - PY22952",
            "24 - Jumper - PY22954",
            "BOXER - PO 5VT68",
            "BOXER - WZ211GF",
            "BOXER - WZ214GF",
            "--- OSOBOWE / INNE ---",
            "OPEL DW4W443",
            "OPEL wysoki DW4WK45",
            "SPEDYCJA"
        ])
        projekt = st.text_input("Nazwa Projektu / Targi")
        kierowca = st.text_input("Kierowca / Spedytor")
        
        c1, c2 = st.columns(2)
        d_start = c1.date_input("Data Wyjazdu", value=datetime.now())
        d_end = c2.date_input("Data Powrotu", value=datetime.now() + timedelta(days=2))
        
        status = st.selectbox("Status", ["Planowanie", "Potwierdzone", "W trasie", "Serwis"])
        
        submitted = st.form_submit_button("ZAPISZ")
        
        if submitted:
            if "---" in pojazd:
                st.error("Wybierz konkretny pojazd, nie nazwę sekcji!")
            else:
                new_row = pd.DataFrame([{
                    "Pojazd": pojazd,
                    "Projekt": projekt,
                    "Data_Start": d_start.strftime('%Y-%m-%d'),
                    "Data_Koniec": d_end.strftime('%Y-%m-%d'),
                    "Kierowca": kierowca,
                    "Status": status
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="FLOTA_SQM", data=df)
                st.success("Zapisano w bazie!")
                st.rerun()

# --- GŁÓWNY PANEL: HARMONOGRAM ---

if not df.empty:
    # Przygotowanie danych do wykresu
    df['Data_Start'] = pd.to_datetime(df['Data_Start'])
    # Viz_End musi być o 1 dzień większa, żeby pasek wypełnił cały dzień w kalendarzu
    df['Viz_End'] = pd.to_datetime(df['Data_Koniec']) + pd.Timedelta(days=1)

    st.subheader("🗓️ Widok Dzienny Floty")
    
    # Suwak zakresu dat dla lepszej nawigacji
    col_date1, col_date2 = st.columns(2)
    start_view = col_date1.date_input("Widok od:", datetime.now().date() - timedelta(days=7))
    end_view = col_date2.date_input("Widok do:", datetime.now().date() + timedelta(days=30))

    fig = px.timeline(
        df, 
        x_start="Data_Start", 
        x_end="Viz_End", 
        y="Pojazd", 
        color="Status",
        text="Projekt",
        hover_data=["Kierowca", "Data_Start", "Data_Koniec"],
        color_discrete_map={
            "Planowanie": "#FAD02E",
            "Potwierdzone": "#45B6FE",
            "W trasie": "#37BC61",
            "Serwis": "#E1341E"
        },
        category_orders={"Pojazd": [
            "31 - TIR P21V388/P22X300 STABLEWSKI", "TIR 2 - W2654FT/P22H972 KOGUS", 
            "TIR 3 - PNT3530A/P24U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa",
            "25 - Jumper - PY22952", "24 - Jumper - PY22954", "BOXER - PO 5VT68", 
            "BOXER - WZ211GF", "BOXER - WZ214GF", "OPEL DW4W443", "OPEL wysoki DW4WK45", "SPEDYCJA"
        ]}
    )

    # Ustawienie osi czasu na dni
    fig.update_xaxes(
        dtick="D1", 
        tickformat="%d\n%b", 
        gridcolor="LightGrey", 
        showgrid=True,
        side="top",
        range=[start_view, end_view]
    )
    
    fig.update_yaxes(autorange="reversed", gridcolor="WhiteSmoke")
    
    # Pionowa linia "Dzisiaj"
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_dash="solid", line_color="red")

    fig.update_layout(
        height=700,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title=None,
        yaxis_title=None,
        legend_orientation="h",
        legend_y=-0.1
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- TABELA EDYCJI ---
    st.markdown("---")
    st.subheader("📋 Edycja Tabelaryczna")
    
    # Przygotowanie czytelnej tabeli bez godzin
    df_table = df.drop(columns=['Viz_End'])
    
    edited_df = st.data_editor(
        df_table, 
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
        st.success("Dane zostały zaktualizowane!")
        st.rerun()

else:
    st.warning("Brak danych w arkuszu FLOTA_SQM. Dodaj pierwszy transport w panelu bocznym.")
