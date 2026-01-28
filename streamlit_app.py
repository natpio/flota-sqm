import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja i Wymuszenie Widocznych Suwaków
st.set_page_config(page_title="SQM LOGISTICS | Fleet", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

    /* Tło strony dla kontrastu */
    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }

    /* WYMUSZENIE WIDOCZNYCH I KOLOROWYCH SUWAKÓW - KLUCZOWE */
    ::-webkit-scrollbar {
        width: 16px !important;
        height: 16px !important;
        display: block !important;
    }
    ::-webkit-scrollbar-track {
        background: #cbd5e1 !important; /* Szary tor */
        border-radius: 4px !important;
    }
    ::-webkit-scrollbar-thumb {
        background: #1e40af !important; /* Ciemnoniebieski suwak - musi być widoczny! */
        border-radius: 4px !important;
        border: 2px solid #cbd5e1 !important;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #1d4ed8 !important;
    }

    /* Nagłówek SQM */
    .header-box {
        background-color: #0f172a;
        padding: 1.5rem;
        border-radius: 8px;
        color: white;
        margin-bottom: 20px;
        border-left: 10px solid #2563eb;
    }

    /* Kontener wykresu */
    .stPlotlyChart {
        background-color: white !important;
        padding: 15px !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1) !important;
    }
    </style>

    <div class="header-box">
        <h1 style="margin:0; font-size: 2rem;">SQM LOGISTICS <span style="font-weight:300;">| Control Center</span></h1>
    </div>
    """, unsafe_allow_html=True)

# 2. DEFINICJA ZASOBÓW
RESOURCES = {
    "🚛 FTL / SOLO": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "🚐 BUS / DOSTAWCZE": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68",
        "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF",
        "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45",
        "BOXER DW9WK54 wysoki", "OPEL DW9WK53", "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637"
    ],
    "🚗 OSOBOWE": [
        "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek",
        "05 – Dacia Duster – WH7083A   B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "Chrysler Pacifica PY04266 - MBanasiak", "Seat Ateca WZ445HU  Dynasiuk",
        "Seat Ateca WZ446HU- PM", "SPEDYCJA", "AUTO RENTAL - CARVIDO"
    ],
    "🏠 NOCLEGI": [
        "MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}
ALL_RESOURCES = [item for sublist in RESOURCES.values() for item in sublist]

# 3. POŁĄCZENIE Z DANYMI
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def get_data():
    data = conn.read()
    data.columns = [c.strip().lower() for c in data.columns]
    data['start'] = pd.to_datetime(data['start'], errors='coerce')
    data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
    return data.fillna("")

df = get_data()

# 4. SIDEBAR - TWOJE STEROWANIE WIDOKIEM
with st.sidebar:
    st.header("🔍 Ustawienia widoku")
    
    # Wybór zakresu dat zastępuje suwak poziomy
    today = datetime.now()
    date_range = st.date_input(
        "Wybierz zakres dat na wykresie:",
        value=(today - timedelta(days=2), today + timedelta(days=21)),
        key="date_range_picker"
    )
    
    st.divider()
    st.info("Pasek boczny pozwala precyzyjnie ustawić okno czasowe bez szukania suwaka pod tabelą.")

# Logika zakresu dat
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_v, end_v = date_range
else:
    start_v, end_v = today - timedelta(days=2), today + timedelta(days=21)

# 5. GŁÓWNE ZAKŁADKI
tabs = st.tabs(list(RESOURCES.keys()) + ["📝 ZARZĄDZANIE DANYMI"])

# Kolory eventów
unique_events = sorted(df['event'].unique())
colors = ["#1e40af", "#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd"]
event_colors = {ev: colors[i % len(colors)] for i, ev in enumerate(unique_events)}

for i, category in enumerate(RESOURCES.keys()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(RESOURCES[category])].copy()
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event", color_discrete_map=event_colors,
                category_orders={"pojazd": RESOURCES[category]}, template="plotly_white"
            )
            fig.update_xaxes(
                side="top", showgrid=True, gridcolor="#f1f5f9",
                tickformat="%d\n%b", dtick=86400000.0,
                range=[start_v, end_v]
            )
            fig.update_layout(
                height=len(RESOURCES[category]) * 50 + 100,
                margin=dict(l=10, r=10, t=50, b=10),
                showlegend=False, bargap=0.3
            )
            fig.add_vline(x=today.timestamp()*1000, line_width=3, line_color="#ef4444")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak wpisów dla tej kategorii.")

# 6. ZAKŁADKA ZARZĄDZANIA
with tabs[-1]:
    st.subheader("Edycja Bazy Danych")
    
    # Wymuszamy wysokość i szerokość kolumn, aby suwak musiał się pojawić
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        height=600,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_RESOURCES, width="large"),
            "event": st.column_config.TextColumn("Nazwa Projektu", width="medium"),
            "start": st.column_config.DateColumn("Data Start", width="small"),
            "koniec": st.column_config.DateColumn("Data Koniec", width="small"),
            "kierowca": st.column_config.TextColumn("Kierowca", width="medium"),
            "notatka": st.column_config.TextColumn("Uwagi", width="large")
        },
        key="main_editor_v6"
    )
    
    if st.button("💾 ZAPISZ I SYNCHRONIZUJ ARKUSZ"):
        with st.status("Trwa zapisywanie..."):
            save_df = edited_df.copy()
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
