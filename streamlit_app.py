import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja i EKSTREMALNY KONTRAST dla suwaków
st.set_page_config(page_title="SQM LOGISTICS | Fleet Center", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }

    /* --- GIGANTYCZNE I KOLOROWE SUWAKI (SCROLLBARS) --- */
    /* Robimy je na tyle duże i jaskrawe, by nie mogły się zlać z tabelą */
    ::-webkit-scrollbar {
        width: 22px !important;
        height: 22px !important;
    }
    ::-webkit-scrollbar-track {
        background: #1e293b !important; /* Bardzo ciemny tor */
    }
    ::-webkit-scrollbar-thumb {
        background: #f97316 !important; /* Jaskrawy pomarańczowy suwak */
        border-radius: 4px !important;
        border: 4px solid #1e293b !important;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #fb923c !important;
    }

    /* Stylizacja nagłówka i kontenerów */
    .header-bar {
        background: #0f172a;
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        border-bottom: 5px solid #f97316;
    }
    
    .stPlotlyChart {
        background-color: white !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
    }

    /* Instrukcja sterowania */
    .nav-hint {
        background-color: #ffedd5;
        border-left: 5px solid #f97316;
        padding: 10px;
        margin-bottom: 15px;
        color: #9a3412;
        font-weight: 600;
        font-size: 0.9rem;
    }
    </style>

    <div class="header-bar">
        <h1 style="margin:0;">SQM LOGISTICS <span style="font-weight:300;">| Fleet Control</span></h1>
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

# 4. SIDEBAR - Sterowanie datą (Zamiast scrolla poziomego na wykresie)
with st.sidebar:
    st.header("⚙️ Widok Czasowy")
    today = datetime.now()
    date_range = st.date_input(
        "Wybierz okno czasowe:",
        value=(today - timedelta(days=2), today + timedelta(days=21)),
        key="global_date_range"
    )

# Wyznaczanie zakresu
if isinstance(date_range, tuple) and len(date_range) == 2:
    s_view, e_view = date_range
else:
    s_view, e_view = today - timedelta(days=2), today + timedelta(days=21)

# 5. MODUŁ OPERACYJNY
tabs = st.tabs(list(RESOURCES.keys()) + ["🔧 EDYCJA BAZY"])

for i, category in enumerate(RESOURCES.keys()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(RESOURCES[category])].copy()
        if not cat_df.empty:
            fig = px.timeline(cat_df, x_start="start", x_end="koniec", y="pojazd", color="event", template="plotly_white")
            fig.update_xaxes(side="top", range=[s_view, e_view], tickformat="%d\n%b", dtick=86400000.0)
            fig.update_layout(height=len(RESOURCES[category])*50 + 100, showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak zadań w wybranym zakresie.")

# 6. ZARZĄDZANIE - Sterowanie klawiaturą
with tabs[-1]:
    st.markdown('<div class="nav-hint">⌨️ NAWIGACJA: Kliknij w komórkę i używaj STRZAŁEK, aby się poruszać. Użyj TAB, aby przejść do kolejnej kolumny (np. Notatki).</div>', unsafe_allow_html=True)
    
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        height=550,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 Pojazd", options=ALL_RESOURCES, width="large"),
            "event": st.column_config.TextColumn("📋 Event", width="medium"),
            "start": st.column_config.DateColumn("📅 Start", width="small"),
            "koniec": st.column_config.DateColumn("🏁 Koniec", width="small"),
            "kierowca": st.column_config.TextColumn("👤 Kierowca", width="medium"),
            "notatka": st.column_config.TextColumn("📝 Notatki", width="large")
        },
        key="keyboard_editor_v6"
    )
    
    if st.button("ZAPISZ ZMIANY W ARKUSZU"):
        with st.status("Synchronizacja..."):
            save_df = edited_df.copy()
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
