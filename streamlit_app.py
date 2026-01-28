import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony i Naprawa Renderowania Suwaków
st.set_page_config(page_title="SQM LOGISTICS | Fleet Manager", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

    /* Globalne ustawienia czcionki i tła */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #f8fafc;
    }

    /* --- FORCE SCROLLBARS --- */
    /* Wymuszenie widoczności suwaków w Chrome, Edge, Safari */
    ::-webkit-scrollbar {
        width: 14px !important;
        height: 14px !important;
        display: block !important;
    }
    ::-webkit-scrollbar-track {
        background: #e2e8f0 !important;
        border-radius: 10px !important;
    }
    ::-webkit-scrollbar-thumb {
        background-color: #64748b !important;
        border-radius: 10px !important;
        border: 3px solid #e2e8f0 !important;
    }
    ::-webkit-scrollbar-thumb:hover {
        background-color: #1e293b !important;
    }

    /* Usunięcie ograniczeń kontenerów Streamlit, które mogą kryć suwaki */
    [data-testid="stExpander"], [data-testid="stTabs"] {
        overflow: visible !important;
    }
    
    .stTabs [data-baseweb="tab-panel"] {
        overflow: auto !important;
    }

    /* Profesjonalny Header */
    .header-bar {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        border-bottom: 4px solid #2563eb;
    }

    /* Styl wykresów */
    .stPlotlyChart {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        padding: 10px;
    }

    /* Przycisk akcji */
    .stButton>button {
        background-color: #2563eb;
        color: white;
        font-weight: 700;
        border-radius: 6px;
        height: 3rem;
        width: 100%;
        border: none;
        transition: 0.2s;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.4);
    }
    </style>

    <div class="header-bar">
        <h1 style="margin:0; font-weight:900; letter-spacing:-1px;">SQM LOGISTICS <span style="color:#2563eb;">|</span> FLOTA</h1>
        <p style="margin:0; opacity:0.7; font-size:0.9rem;">Enterprise Resource Management System v5.1</p>
    </div>
    """, unsafe_allow_html=True)

# 2. DEFINICJA ZASOBÓW
RESOURCES = {
    "TRANSPORT CIĘŻKI": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "DOSTAWCZE / BUS": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68",
        "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF",
        "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45",
        "BOXER DW9WK54 wysoki", "OPEL DW9WK53", "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637"
    ],
    "OSOBOWE / RENTAL": [
        "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek",
        "05 – Dacia Duster – WH7083A   B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "Chrysler Pacifica PY04266 - MBanasiak", "Seat Ateca WZ445HU  Dynasiuk",
        "Seat Ateca WZ446HU- PM", "SPEDYCJA", "AUTO RENTAL - CARVIDO"
    ],
    "ZAKWATEROWANIE": [
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
        expected = ["pojazd", "event", "start", "koniec", "kierowca", "notatka"]
        data = data[expected].copy()
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.fillna("")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# 4. MODUŁ OPERACYJNY (TABS)
tabs = st.tabs(list(RESOURCES.keys()) + ["⚙️ ZARZĄDZANIE BAZĄ"])

# Paleta kolorów projektowych
colors = ["#1e40af", "#0369a1", "#0e7490", "#0f766e", "#15803d", "#a21caf"]
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
            today = datetime.now()
            fig.update_xaxes(
                side="top", showgrid=True, gridcolor="#f1f5f9",
                tickformat="%d\n%b", dtick=86400000.0,
                tickfont=dict(size=11, color="#64748b"),
                range=[today - timedelta(days=2), today + timedelta(days=14)]
            )
            fig.update_yaxes(title="", tickfont=dict(size=10, color="#0f172a"))
            fig.update_layout(
                height=len(RESOURCES[category]) * 45 + 100,
                margin=dict(l=10, r=10, t=50, b=10),
                showlegend=False, bargap=0.3
            )
            fig.add_vline(x=today.timestamp()*1000, line_width=2, line_color="#ef4444")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Brak danych dla kategorii: {category}")

# 5. MODUŁ EDYCJI (Z NAPRAWIONYM SCROLLEM)
with tabs[-1]:
    st.subheader("Edycja parametrów floty")
    
    # Używamy kontenera Streamlit, który natywnie wspiera scroll przy parametrze height
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        height=550, # Kluczowe: Sztywna wysokość wymusza wewnętrzny suwak komponentu
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Zasób SQM", options=ALL_RESOURCES, required=True),
            "start": st.column_config.DateColumn("Start"),
            "koniec": st.column_config.DateColumn("Koniec"),
            "event": st.column_config.TextColumn("Projekt/Event"),
            "kierowca": st.column_config.TextColumn("Kierowca"),
            "notatka": st.column_config.TextColumn("Uwagi dodatkowe")
        },
        key="fleet_editor_v51"
    )
    
    if st.button("AKTUALIZUJ BAZĘ DANYCH"):
        with st.status("Trwa zapisywanie..."):
            save_df = edited_df.copy()
            save_df = save_df[["pojazd", "event", "start", "koniec", "kierowca", "notatka"]]
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
