import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Konfiguracja strony
st.set_page_config(page_title="SQM FLOTA", layout="wide")

st.title("🚚 System Planowania Transportu SQM")

# Połączenie z Google Sheets przy użyciu Service Account skonfigurowanego w Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Odczyt arkusza. Upewnij się, że nazwa arkusza (zakładki) to "FLOTA_SQM"
    return conn.read(worksheet="FLOTA_SQM", ttl="0")

try:
    df = load_data()
except Exception as e:
    st.error("Błąd połączenia. Upewnij się, że arkusz nazywa się 'FLOTA_SQM' i udostępniłeś go na adres e-mail konta usługowego.")
    st.stop()

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("➕ Nowy Transport")
    with st.form("add_form"):
        pojazd = st.selectbox("Pojazd", [
            "TIR 31 - P21V388/P22X300", 
            "TIR 2 - W2654FT/P22H972", 
            "Jumper - PY22952", 
            "Boxer - PO 5VT68",
            "SPEDYCJA"
        ])
        projekt = st.text_input("Projekt (np. EuroShop)")
        kierowca = st.text_input("Kierowca")
        
        c1, c2 = st.columns(2)
        d_start = c1.date_input("Start")
        d_end = c2.date_input("Koniec")
        
        submitted = st.form_submit_button("Dodaj")
        
        if submitted:
            new_row = pd.DataFrame([{
                "Pojazd": pojazd,
                "Projekt": projekt,
                "Data_Start": d_start.strftime('%Y-%m-%d'),
                "Data_Koniec": d_end.strftime('%Y-%m-%d'),
                "Kierowca": kierowca,
                "Status": "Zaplanowane"
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="FLOTA_SQM", data=df)
            st.success("Zaktualizowano arkusz!")
            st.rerun()

# --- WIZUALIZACJA ---
st.subheader("🗓️ Harmonogram")

if not df.empty:
    df['Data_Start'] = pd.to_datetime(df['Data_Start'])
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'])

    fig = px.timeline(
        df, 
        x_start="Data_Start", 
        x_end="Data_Koniec", 
        y="Pojazd", 
        color="Projekt",
        text="Projekt",
        hover_data=["Kierowca"]
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

    # Tabela edycji
    st.markdown("---")
    st.subheader("📝 Edytuj dane bezpośrednio")
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    
    if st.button("Zapisz zmiany w tabeli"):
        conn.update(worksheet="FLOTA_SQM", data=edited_df)
        st.success("Zmiany zapisane w Google Sheets!")
        st.rerun()
