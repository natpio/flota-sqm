import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja i Stylizacja Ultra-Kompaktowa
st.set_page_config(page_title="SQM LOGISTICS | Full Fleet", layout="wide")

st.markdown("""
    <style>
    /* Globalne zagęszczenie interfejsu */
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    
    /* Wymuszenie kontrastu tabeli */
    [data-testid="stDataEditor"] {
        border: 1px solid #0f172a !important;
        background-color: #ffffff !important;
    }

    /* Nagłówek SQM */
    .sqm-header {
        background-color: #0f172a;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    </style>
    
    <div class="sqm-header">
        <div style="font-size: 1.5rem; font-weight: 900;">SQM LOGISTICS | FLOTA</div>
        <div style="font-size: 0.8rem; opacity: 0.7;">Status: LIVE (Wszystkie Pojazdy)</div>
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

# 3. POBIERANIE DANYCH
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

# 4. UKŁAD STRONY
tab_gantt, tab_edit = st.tabs(["📊 HARMONOGRAM FLOTY", "📝 EDYCJA CAŁEJ BAZY"])

with tab_gantt:
    # Kompaktowy wybór daty
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        s_date = st.date_input("Widok od:", datetime.now() - timedelta(days=2))
    with c2:
        e_date = st.date_input("Widok do:", datetime.now() + timedelta(days=21))
    
    for cat, assets in RESOURCES.items():
        st.markdown(f"**{cat}**")
        c_df = df[df['pojazd'].isin(assets)].copy()
        if not c_df.empty:
            fig = px.timeline(c_df, x_start="start", x_end="koniec", y="pojazd", color="event", template="plotly_white")
            fig.update_xaxes(side="top", range=[s_date, e_date], tickformat="%d\n%b")
            fig.update_layout(height=len(assets)*40 + 80, showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

with tab_edit:
    st.markdown("### Pełna lista pojazdów")
    
    # KONTROLA SZEROKOŚCI: Ustawiamy tak, by całość mieściła się w poziomie
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        height=700,
        hide_index=True,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_RESOURCES, width="medium", required=True),
            "event": st.column_config.TextColumn("Event/Projekt", width="small"),
            "start": st.column_config.DateColumn("Start", width="small"),
            "koniec": st.column_config.DateColumn("Koniec", width="small"),
            "kierowca": st.column_config.TextColumn("Kierowca", width="small"),
            "notatka": st.column_config.TextColumn("Notatki (widoczne bez przewijania)", width="large"),
        },
        key="full_fleet_editor"
    )

    if st.button("💾 ZAPISZ CAŁĄ BAZĘ"):
        with st.status("Zapisywanie danych do arkusza..."):
            save_df = edited_df.copy()
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
