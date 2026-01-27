import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. SETUP I STYLIZACJA "DARK MODE / HIGH CONTRAST"
st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide")

st.markdown("""
    <style>
    /* Sticky Header dla osi czasu */
    .stTabs [data-baseweb="tab-list"] {
        position: sticky;
        top: 0;
        z-index: 999;
        background: white;
    }
    /* Podświetlenie wierszy edytora */
    [data-testid="stDataEditor"] { border: 2px solid #1a73e8 !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. DEFINICJA ZASOBÓW
RESOURCES = {
    "🚛 FTL / SOLO": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "🚐 BUS": [
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
        "Seat Ateca WZ446HU- PM", "SPEDYCJA", "AUTO RENTAL -  CARVIDO"
    ],
    "🏠 NOCLEGI": [
        "MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}

ALL_RESOURCES = [item for sublist in RESOURCES.values() for item in sublist]

# 3. LOGIKA DANYCH
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def get_clean_data():
    data = conn.read()
    data.columns = [c.strip().lower() for c in data.columns]
    data['start'] = pd.to_datetime(data['start'], errors='coerce')
    data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
    for col in ['pojazd', 'event', 'kierowca', 'notatka']:
        data[col] = data[col].astype(str).replace(['nan', 'None'], '')
    return data

df = get_clean_data()

# 4. INTERFEJS UŻYTKOWNIKA
st.title("🛰️ SQM LOGISTICS 2.0")

# Podział na kategorie
tab_names = list(RESOURCES.keys()) + ["📝 EDYCJA I BAZA"]
tabs = st.tabs(tab_names)

for i, cat in enumerate(RESOURCES.keys()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(RESOURCES[cat])]
        
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event",
                category_orders={"pojazd": RESOURCES[cat]},
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            
            # Konfiguracja osi X - zawsze na górze w każdej zakładce
            fig.update_xaxes(
                side="top", dtick="86400000", # Co 1 dzień
                tickformat="%d\n%a", gridcolor="#eee",
                tickfont=dict(size=10, family="Arial Black")
            )
            
            fig.update_layout(
                height=len(RESOURCES[cat]) * 45 + 150,
                margin=dict(l=10, r=10, t=100, b=20),
                showlegend=False,
                bargap=0.3
            )
            
            # Linia Dnia Dzisiejszego
            fig.add_vline(x=datetime.now().timestamp()*1000, line_color="red", line_width=2)
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Brak zaplanowanych zadań dla kategorii {cat}")

with tabs[-1]:
    st.subheader("Centralna Baza Transportowa")
    edited_df = st.data_editor(
        df, num_rows="dynamic", use_container_width=True,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Zasób", options=ALL_RESOURCES),
            "start": st.column_config.DateColumn("Start"),
            "koniec": st.column_config.DateColumn("Koniec")
        },
        key="main_editor"
    )
    
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY"):
        save_df = edited_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
        conn.update(data=save_df)
        st.success("Baza SQM zsynchronizowana!")
        st.rerun()
