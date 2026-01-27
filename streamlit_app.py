import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja i Stylistyka "Tablicy Kredowej"
st.set_page_config(page_title="SQM FLOTA | Chalkboard", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Permanent+Marker&family=Gochi+Hand&family=Inter:wght@400;900&display=swap');

    /* TŁO: Czarna tablica barowa */
    .stApp { 
        background-color: #1a1a1a;
        background-image: url("https://www.transparenttextures.com/patterns/black-chalkboard.png");
    }

    /* Nagłówek SQM FLOTA jako napis kredą */
    .chalk-title {
        font-family: 'Permanent Marker', cursive;
        font-size: 5rem;
        text-align: center;
        color: #ffffff;
        text-shadow: 2px 2px 10px rgba(255,255,255,0.4), -1px -1px 0 #444;
        margin-bottom: 0px;
    }
    .chalk-dot { color: #facc15; opacity: 0.8; }

    /* Stylizacja Zakładek - kolorowa kreda */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
        padding: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255,255,255,0.05);
        border: 2px dashed rgba(255,255,255,0.3) !important;
        color: #eee !important;
        font-family: 'Gochi Hand', cursive;
        font-size: 1.5rem;
        border-radius: 5px;
        padding: 5px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(255,255,255,0.1) !important;
        border: 2px solid #facc15 !important;
        color: #facc15 !important;
        transform: rotate(-1deg);
    }

    /* Wykres w ramce rysowanej kredą */
    .stPlotlyChart {
        background-color: rgba(0,0,0,0.4) !important;
        border: 3px solid #eee !important;
        border-radius: 5px !important;
        box-shadow: 0 0 15px rgba(255,255,255,0.1);
        padding: 5px;
    }

    /* EDYTOR - NAPRAWA SUWAKA I STYLU */
    [data-testid="stDataEditor"] {
        border: 2px solid #facc15 !important;
        background-color: #222 !important;
        border-radius: 10px;
    }
    
    /* Wymuszenie widoczności paska przewijania w Chrome/Safari/Edge */
    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }
    ::-webkit-scrollbar-track {
        background: #1a1a1a;
    }
    ::-webkit-scrollbar-thumb {
        background: #444;
        border-radius: 6px;
        border: 2px solid #1a1a1a;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #facc15;
    }

    /* Przycisk PIVOT! - Czerwona kreda */
    .stButton>button {
        background-color: transparent;
        color: #ff4b4b;
        font-family: 'Permanent Marker', cursive;
        font-size: 2.5rem;
        border: 4px double #ff4b4b;
        border-radius: 0px;
        transition: 0.3s;
        width: 100%;
        margin-top: 30px;
    }
    .stButton>button:hover {
        color: white;
        background-color: #ff4b4b;
        box-shadow: 0 0 20px #ff4b4b;
    }
    </style>

    <div class="chalk-title">
        S<span class="chalk-dot">·</span>Q<span class="chalk-dot">·</span>M<span class="chalk-dot">·</span>FLOTA
    </div>
    <div style="text-align: center; color: #aaa; font-family: 'Gochi Hand'; font-size: 1.5rem; margin-bottom: 20px;">
        The One with the Blackboard Menu
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

# 4. DASHBOARD - Wykresy jako rysunki kredą
tabs = st.tabs(list(RESOURCES.keys()) + ["🖍️ EDYCJA"])

# Kolory "kredowe"
chalk_palette = ["#FF7F7F", "#7FBFFF", "#FFFF7F", "#BF7FFF", "#7FFF7F", "#FFBF7F"]
event_colors = {ev: chalk_palette[i % len(chalk_palette)] for i, ev in enumerate(sorted(df['event'].unique()))}

for i, category in enumerate(RESOURCES.keys()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(RESOURCES[category])].copy()
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event", color_discrete_map=event_colors,
                category_orders={"pojazd": RESOURCES[category]}, template="plotly_dark"
            )
            today = datetime.now()
            fig.update_xaxes(
                side="top", showgrid=True, gridcolor="rgba(255,255,255,0.1)",
                tickformat="%d\n%a", dtick=86400000.0,
                tickfont=dict(size=11, family="Gochi Hand", color="#eee"),
                range=[today - timedelta(days=2), today + timedelta(days=14)]
            )
            fig.update_yaxes(title="", tickfont=dict(size=12, family="Gochi Hand", color="#eee"))
            fig.update_traces(marker=dict(line=dict(width=1, color='rgba(255,255,255,0.5)')))
            fig.update_layout(
                height=len(RESOURCES[category]) * 55 + 150,
                margin=dict(l=10, r=10, t=80, b=10),
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            # Linia "Today" jako biała kreda
            fig.add_vline(x=today.timestamp()*1000, line_width=3, line_color="white", line_dash="dash")
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# 5. ZARZĄDZANIE - Naprawiony suwak w ciemnym edytorze
with tabs[-1]:
    st.markdown('<div style="background-color: rgba(255,255,255,0.05); padding: 20px; border-radius: 10px;">', unsafe_allow_html=True)
    st.subheader("🖍️ Napisz kredą zmiany w planie")
    
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        height=500, # Wymusza suwak boczny
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_RESOURCES),
            "start": st.column_config.DateColumn("Start"),
            "koniec": st.column_config.DateColumn("Koniec")
        },
        key="chalkboard_editor"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("PIVOT! (ZAPISZ NA TABLICY)"):
        with st.spinner("Ścieranie starej kredy..."):
            save_df = edited_df.copy()
            save_df = save_df[["pojazd", "event", "start", "koniec", "kierowca", "notatka"]]
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
