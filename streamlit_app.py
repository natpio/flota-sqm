import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="FLOTA SQM 2026", layout="wide", page_icon="🚚")

# Custom CSS dla ekstremalnej czytelności
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    /* Stylizacja nagłówka osi X w Plotly */
    .xtick text { font-size: 14px !important; font-weight: bold !important; fill: black !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 FLOTA SQM 2026")

# 2. POŁĄCZENIE Z BAZĄ
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(worksheet="FLOTA_SQM", ttl="0")
    df = df.dropna(how='all').copy()
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    # Upewnienie się, że mamy kolumnę LDM (ładunek)
    if 'LDM' not in df.columns:
        df['LDM'] = ""
    return df.dropna(subset=['Data_Start', 'Data_Koniec'])

df = load_data()

# 3. SIDEBAR - DODAWANIE TRANSPORTU
with st.sidebar:
    st.header("⚙️ Nowy Transport")
    with st.form("add_form", clear_on_submit=True):
        pojazd = st.selectbox("Pojazd", [
            "31 - TIR P21V388/P22X300 STABLEWSKI", "TIR 2 - W2654FT/P22H972 KOGUS",
            "TIR 3 - PNT3530A/P24U343 DANIELAK", "44 - SOLO PY 73262",
            "25 - Jumper - PY22952", "24 - Jumper - PY22954", "BOXER - PO 5VT68",
            "OPEL DW4W443", "SPEDYCJA"
        ])
        projekt = st.text_input("Nazwa Projektu / Targi")
        kierowca = st.text_input("Kierowca")
        ldm = st.text_input("Ładunek (np. 13.6 LDM, 24t)", help="Planowanie przestrzeni na naczepie")
        
        c1, c2 = st.columns(2)
        d_start = c1.date_input("Wyjazd", value=datetime.now())
        d_end = c2.date_input("Powrót", value=datetime.now() + timedelta(days=2))
        
        status = st.selectbox("Status", ["Planowanie", "Potwierdzone", "W trasie", "Serwis"])
        
        if st.form_submit_button("ZAPISZ"):
            new_row = pd.DataFrame([{
                "Pojazd": pojazd, "Projekt": projekt, "Data_Start": d_start.strftime('%Y-%m-%d'),
                "Data_Koniec": d_end.strftime('%Y-%m-%d'), "Kierowca": kierowca, "Status": status, "LDM": ldm
            }])
            full_df = pd.concat([conn.read(worksheet="FLOTA_SQM", ttl="0"), new_row], ignore_index=True)
            conn.update(worksheet="FLOTA_SQM", data=full_df)
            st.rerun()

# 4. GRAFIK GANTTA - POPRAWIONA WIDOCZNOŚĆ
st.subheader("🗓️ Harmonogram Dzienny")

today = datetime.now()
df_viz = df.copy()
df_viz['Viz_End'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)

# Tworzenie wykresu
fig = px.timeline(
    df_viz, 
    x_start="Data_Start", 
    x_end="Viz_End", 
    y="Pojazd", 
    color="Status",
    text="Projekt", # Projekt wyświetla się na pasku
    hover_data=["Kierowca", "LDM"],
    color_discrete_map={
        "Planowanie": "#FAD02E", "Potwierdzone": "#45B6FE", 
        "W trasie": "#37BC61", "Serwis": "#E1341E"
    }
)

# --- KLUCZOWE USTAWIENIA WIDOCZNOŚCI ---
fig.update_xaxes(
    dtick="D1",             # Pionowa linia dla każdego dnia
    tickformat="%d\n%b",    # Dzień i Skrót Miesiąca (np. 27 Jan)
    tickfont=dict(size=14, color="black", family="Arial Black"), # Duże, czarne napisy
    gridcolor="LightGrey", 
    showgrid=True,
    side="top",             # Etykiety na górze (lepiej widoczne przy skrolowaniu)
    title_text="KALENDARZ LOGISTYCZNY 2026"
)

fig.update_yaxes(
    autorange="reversed", 
    tickfont=dict(size=12, color="black", family="Arial"),
    gridcolor="whitesmoke"
)

# Czerwona linia 'DZIŚ'
fig.add_vline(x=today.timestamp() * 1000, line_width=3, line_color="red")

fig.update_layout(
    height=600,
    margin=dict(l=10, r=10, t=80, b=10), # Większy margines na górze dla dat
    plot_bgcolor="white",
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
)

st.plotly_chart(fig, use_container_width=True)

# 5. TABELA EDYCJI Z LDM
st.markdown("---")
with st.expander("📝 Zarządzanie slotami i przestrzenią (LDM)", expanded=True):
    df_edit = df.copy()
    df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
    df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
    
    edited_df = st.data_editor(
        df_edit, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "LDM": st.column_config.TextColumn("Ładunek / LDM", placeholder="np. 13.6 LDM"),
            "Status": st.column_config.SelectboxColumn("Status", options=["Planowanie", "Potwierdzone", "W trasie", "Serwis"]),
            "Data_Start": st.column_config.DateColumn("Wyjazd"),
            "Data_Koniec": st.column_config.DateColumn("Powrót")
        }
    )
    
    if st.button("💾 AKTUALIZUJ ARKUSZ GOOGLE"):
        conn.update(worksheet="FLOTA_SQM", data=edited_df)
        st.success("Dane zapisane!")
        st.rerun()
