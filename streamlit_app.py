import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony i Naprawa Interfejsu (v2.9.3)
st.set_page_config(page_title="SQM FLOTA | Control Tower", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Permanent+Marker&family=Inter:wght@400;900&display=swap');

    /* TŁO: Głęboki fiolet drzwi Moniki #744DA9 */
    .stApp { 
        background-color: #744DA9; 
    }

    /* Logo S·Q·M·FLOTA */
    .friends-title {
        font-family: 'Permanent Marker', cursive;
        font-size: 4.5rem;
        text-align: center;
        color: white;
        text-shadow: 4px 4px 0px #1e1e1e;
        margin-bottom: 0px;
        padding-top: 10px;
    }
    .dot-r { color: #e02424; } .dot-b { color: #2563eb; } .dot-y { color: #facc15; }

    /* Stylizacja Zakładek: Neon Central Perk */
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
        background-color: rgba(0,0,0,0.3);
        padding: 15px;
        border-radius: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 50px;
        color: #744DA9 !important;
        font-weight: 900;
        border: 3px solid transparent;
        padding: 5px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #facc15 !important;
        color: #1e1e1e !important;
        box-shadow: 0 0 20px #facc15;
    }

    /* Stylizacja Wykresów - Żółta Ramka */
    .stPlotlyChart {
        background-color: #ffffff;
        border: 8px solid #facc15 !important;
        border-radius: 20px !important;
        padding: 10px;
        box-shadow: 10px 10px 0px rgba(0,0,0,0.4);
    }

    /* Specjalny kontener na edytor - oddech od tła */
    .editor-container {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border: 5px solid #facc15;
        margin-top: 20px;
    }

    /* Przycisk PIVOT! */
    .stButton>button {
        background-color: #e02424;
        color: white;
        font-family: 'Permanent Marker', cursive;
        font-size: 2.2rem;
        height: 80px;
        border-radius: 15px;
        border: 4px solid #ffffff;
        box-shadow: 6px 6px 0px #1e1e1e;
        width: 100%;
        margin-top: 20px;
    }
    </style>

    <div class="friends-title">
        S<span class="dot-r">·</span>Q<span class="dot-b">·</span>M<span class="dot-y">·</span>FLOTA
    </div>
    <div style="text-align: center; color: white; font-family: 'Inter'; font-weight: 900; margin-bottom: 20px; letter-spacing: 2px;">
        THE ONE WITH THE LOGISTICS SLOTS
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
        expected = ["pojazd", "event", "start", "koniec", "kierowca", "notatka"]
        data = data[expected].copy()
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.fillna(" ")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# 4. GŁÓWNY PANEL
tabs = st.tabs(list(RESOURCES.keys()) + ["🔧 ZARZĄDZANIE"])

friends_palette = ["#e02424", "#2563eb", "#facc15", "#744DA9", "#059669", "#FF851B"]
event_colors = {ev: friends_palette[i % len(friends_palette)] for i, ev in enumerate(sorted(df['event'].unique()))}

for i, category in enumerate(RESOURCES.keys()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(RESOURCES[category])].copy()
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event", color_discrete_map=event_colors,
                category_orders={"pojazd": RESOURCES[category]}, template="plotly_white"
            )
            today = datetime.now()
            fig.update_xaxes(
                side="top", showgrid=True, gridcolor="#eee",
                tickformat="%d\n%a", dtick=86400000.0,
                tickfont=dict(size=11, family="Inter Black", color="#744DA9"),
                range=[today - timedelta(days=2), today + timedelta(days=14)]
            )
            fig.update_yaxes(title="", tickfont=dict(size=11, family="Inter Black"))
            fig.update_traces(textposition='inside', insidetextanchor='middle')
            fig.update_layout(height=len(RESOURCES[category]) * 55 + 150, margin=dict(l=10, r=10, t=80, b=10), showlegend=False)
            fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#e02424")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("How you doin'? Brak danych.")

# 5. ZARZĄDZANIE - Wersja z wymuszonym suwakiem
with tabs[-1]:
    st.markdown('<div class="editor-container">', unsafe_allow_html=True)
    st.subheader("📝 Edycja Bazy Floty")
    
    # Parametr 'height' wymusza suwak boczny, a 'use_container_width' suwak poziomy
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        height=500,  # SZTYWNA WYSOKOŚĆ = GWARANTOWANY SUWAK
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_RESOURCES),
            "start": st.column_config.DateColumn("Start"),
            "koniec": st.column_config.DateColumn("Koniec")
        },
        key="super_scroll_editor_v3"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("PIVOT! PIVOT! PIVOT!"):
        with st.status("Saving..."):
            save_df = edited_df.copy()
            save_df = save_df[["pojazd", "event", "start", "koniec", "kierowca", "notatka"]]
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
