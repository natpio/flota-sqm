import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony i Modern Business UI
st.set_page_config(page_title="SQM LOGISTICS | Fleet Center", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

    /* Tło z większym kontrastem dla suwaków */
    .stApp { 
        background-color: #f1f5f9; 
        font-family: 'Inter', sans-serif;
    }

    /* Profesjonalny Granatowy Header */
    .header-container {
        background-color: #0f172a;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    /* Kontener wykresu z wyraźną krawędzią */
    .stPlotlyChart {
        background-color: #ffffff;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Stylizacja Suwaka Daty */
    div[data-baseweb="slider"] {
        margin-top: 10px;
        margin-bottom: 20px;
    }

    /* Przyciski systemowe */
    .stButton>button {
        background-color: #2563eb;
        color: white;
        font-weight: 700;
        border-radius: 8px;
        border: none;
        padding: 0.75rem 2rem;
        width: 100%;
    }
    </style>
    
    <div class="header-container">
        <h2 style="margin:0; font-weight:900;">SQM LOGISTICS CONTROL</h2>
        <p style="margin:0; opacity:0.7; font-size:0.85rem;">ASSET & FLEET NAVIGATOR v5.3</p>
    </div>
    """, unsafe_allow_html=True)

# 2. DEFINICJA ZASOBÓW
RESOURCES = {
    "🚛 TRANSPORT CIĘŻKI": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "🚐 DOSTAWCZE / BUS": [
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

# 3. DANE
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl="0s")
        data.columns = [c.strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.fillna("")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# 4. NOWOŚĆ: INTERAKTYWNY NAWIGATOR DAT (Slider)
st.sidebar.header("🛠️ USTAWIENIA WIDOKU")
min_date = datetime(2026, 1, 1)
max_date = datetime(2026, 12, 31)

date_range = st.sidebar.date_input(
    "Zakres dat widoku:",
    value=(datetime.now() - timedelta(days=2), datetime.now() + timedelta(days=14)),
    min_value=min_date,
    max_value=max_date,
    key="navigator_slider"
)

# Walidacja wyboru daty
if len(date_range) == 2:
    start_view, end_view = date_range
else:
    start_view, end_view = datetime.now(), datetime.now() + timedelta(days=14)

# 5. MODUŁ OPERACYJNY
tabs = st.tabs(list(RESOURCES.keys()) + ["⚙️ ZARZĄDZANIE"])

colors = ["#1e40af", "#0369a1", "#0891b2", "#0d9488", "#16a34a", "#ca8a04", "#dc2626"]
event_colors = {ev: colors[i % len(colors)] for i, ev in enumerate(sorted(df['event'].unique()))}

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
                range=[start_view, end_view] # TU DZIAŁA TWÓJ SUWAK
            )
            fig.update_layout(
                height=len(RESOURCES[category]) * 45 + 100,
                margin=dict(l=10, r=10, t=50, b=10),
                showlegend=False, bargap=0.3
            )
            fig.add_vline(x=datetime.now().timestamp()*1000, line_width=2, line_color="#ef4444")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Brak danych dla: {category}")

# 6. ZARZĄDZANIE (Naprawione wizualnie)
with tabs[-1]:
    st.subheader("Baza Danych Floty")
    st.markdown("💡 *Wskazówka: Jeśli nie widzisz suwaków bocznych, kliknij wewnątrz tabeli i użyj strzałek na klawiaturze.*")
    
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        hide_index=True, # Więcej miejsca w poziomie
        height=500,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Zasób", options=ALL_RESOURCES, width="medium"),
            "event": st.column_config.TextColumn("Projekt", width="medium"),
            "start": st.column_config.DateColumn("Start", width="small"),
            "koniec": st.column_config.DateColumn("Koniec", width="small"),
        },
        key="navigator_editor"
    )
    
    if st.button("ZAPISZ I SYNCHRONIZUJ"):
        with st.status("Aktualizacja danych..."):
            save_df = edited_df.copy()
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
