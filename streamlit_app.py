import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Konfiguracja strony
st.set_page_config(page_title="SQM FLOTA", layout="wide")

st.title("🚚 System Planowania Transportu SQM")

# Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(worksheet="FLOTA_SQM", ttl="0")

try:
    df = load_data()
except Exception as e:
    st.error("Błąd połączenia z arkuszem FLOTA_SQM.")
    st.stop()

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("➕ Nowy Transport")
    with st.form("add_form"):
        # Pełna lista pojazdów z Twojego Excela dla wygody
        pojazd = st.selectbox("Pojazd", [
            "TIR 31 - P21V388/P22X300 STABLEWSKI", 
            "TIR 2 - W2654FT/P22H972 KOGUS", 
            "TIR 3 - PNT3530A/P24U343 DANIELAK",
            "44 - SOLO PY 73262",
            "25 - Jumper - PY22952",
            "24 - Jumper - PY22954",
            "BOXER - PO 5VT68",
            "SPEDYCJA"
        ])
        projekt = st.text_input("Projekt (np. EuroShop)")
        kierowca = st.text_input("Kierowca")
        
        c1, c2 = st.columns(2)
        d_start = c1.date_input("Start", value=datetime.now())
        d_end = c2.date_input("Koniec", value=datetime.now() + timedelta(days=3))
        
        submitted = st.form_submit_button("Dodaj do grafiku")
        
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
            st.success("Zaktualizowano grafik!")
            st.rerun()

# --- GŁÓWNY PANEL: HARMONOGRAM ---
st.subheader("🗓️ Harmonogram floty (Widok dzienny)")

if not df.empty:
    df['Data_Start'] = pd.to_datetime(df['Data_Start'])
    # Dodajemy 1 dzień do daty końcowej, aby pasek na wykresie obejmował cały ostatni dzień
    df['Data_Koniec_Viz'] = pd.to_datetime(df['Data_Koniec']) + pd.Timedelta(days=1)

    # Tworzenie wykresu
    fig = px.timeline(
        df, 
        x_start="Data_Start", 
        x_end="Data_Koniec_Viz", 
        y="Pojazd", 
        color="Projekt",
        text="Projekt",
        hover_data={"Data_Koniec_Viz": False, "Data_Start": True, "Kierowca": True},
        opacity=0.8
    )

    # --- KLUCZOWE POPRAWKI CZYTELNOŚCI ---
    
    # 1. Wyraźna siatka co 1 dzień (jak w Excelu)
    fig.update_xaxes(
        dtick="D1", 
        tickformat="%d\n%b", 
        gridcolor="LightGrey", 
        showgrid=True,
        side="top" # Daty na górze jak w Twoim Excelu
    )
    
    # 2. Linia "Dzisiaj" dla orientacji w trasach
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=3, line_dash="dash", line_color="red")
    
    # 3. Stała wysokość i sortowanie
    fig.update_yaxes(autorange="reversed", gridcolor="whitesmoke")
    fig.update_layout(
        height=600,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title=None,
        yaxis_title=None,
        showlegend=True,
        clickmode='event+select'
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- EDYCJA DANYCH ---
    st.markdown("---")
    st.subheader("📝 Lista transportów i edycja")
    
    # Formatujemy wyświetlanie dat w tabeli, żeby nie było godziny 00:00:00
    df_display = df.copy()
    df_display['Data_Start'] = df_display['Data_Start'].dt.date
    df_display['Data_Koniec'] = pd.to_datetime(df_display['Data_Koniec']).dt.date
    
    edited_df = st.data_editor(
        df_display.drop(columns=['Data_Koniec_Viz']), 
        num_rows="dynamic", 
        use_container_width=True
    )
    
    if st.button("💾 Zapisz zmiany w bazie"):
        conn.update(worksheet="FLOTA_SQM", data=edited_df)
        st.success("Baza została zaktualizowana!")
        st.rerun()

else:
    st.info("Baza jest pusta. Dodaj pierwszy projekt w panelu bocznym.")
