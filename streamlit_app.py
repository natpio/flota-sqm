import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- KONFIGURACJA ---
st.set_page_config(page_title="SQM Logistics", layout="wide")

# Stylizacja
st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] * { color: #F8FAFC !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DANE ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    def get_sqm_data():
        # Pobranie danych bezpośrednio z Twojego arkusza
        df = conn.read(ttl="0")
        # Usuwanie pustych rekordów, które psują wykres
        df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec']).copy()
        
        # Konwersja wszystkiego na tekst i daty - zabezpieczenie przed 'float' vs 'str'
        df['Pojazd'] = df['Pojazd'].astype(str)
        df['Projekt'] = df['Projekt'].astype(str)
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        df['Kierowca'] = df['Kierowca'].fillna("").astype(str)
        
        return df.dropna(subset=['Data_Start', 'Data_Koniec'])

    df = get_sqm_data()

    # --- PANEL BOCZNY ---
    with st.sidebar:
        st.header("Zarządzanie Transportem")
        with st.form("new_log_entry", clear_on_submit=True):
            f_proj = st.text_input("Projekt")
            v_options = sorted(df['Pojazd'].unique().tolist()) if not df.empty else ["Auto 1"]
            f_veh = st.selectbox("Pojazd", options=v_options)
            f_range = st.date_input("Termin", value=(datetime.now(), datetime.now() + timedelta(days=2)))
            f_driver = st.text_input("Kierowca")
            f_submit = st.form_submit_button("Zapisz", use_container_width=True)

        if f_submit and len(f_range) == 2:
            s, e = pd.to_datetime(f_range[0]), pd.to_datetime(f_range[1])
            # Sprawdzenie kolizji
            collision = df[(df['Pojazd'] == f_veh) & (df['Data_Start'] < e) & (df['Data_Koniec'] > s)]
            
            if not collision.empty:
                st.error(f"Kolizja: {f_veh} jest w tym czasie na projekcie: {collision.iloc[0]['Projekt']}")
            else:
                new_row = pd.DataFrame([{"Pojazd": f_veh, "Projekt": f_proj, "Data_Start": s, "Data_Koniec": e, "Kierowca": f_driver}])
                conn.update(data=pd.concat([df, new_row], ignore_index=True))
                st.success("Dodano do arkusza!")
                st.rerun()

    # --- WIDOK GŁÓWNY ---
    st.title("Pulpit SQM Multimedia Solutions")

    tab1, tab2 = st.tabs(["📅 Harmonogram", "📋 Edycja danych"])

    with tab1:
        if not df.empty:
            fig = px.timeline(df, x_start="Data_Start", x_end="Data_Koniec", y="Pojazd", color="Projekt", text="Projekt", template="plotly_white")
            fig.update_xaxes(dtick="D1", tickformat="%d\n%a", side="top")
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("Zapisz zmiany zbiorcze"):
            conn.update(data=edited)
            st.success("Zaktualizowano bazę danych!")
            st.rerun()

except Exception as e:
    st.error(f"Błąd: {e}")
