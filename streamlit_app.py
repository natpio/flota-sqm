import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony i profesjonalny styl Corporate
st.set_page_config(page_title="SQM LOGISTICS | Enterprise Fleet", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

    /* Główne tło - Light Gray / Slate */
    .stApp { 
        background-color: #f8fafc; 
        font-family: 'Inter', sans-serif;
    }

    /* Nagłówek systemowy */
    .enterprise-header {
        background-color: #0f172a;
        padding: 2rem;
        border-radius: 0 0 15px 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-title {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        margin: 0;
    }
    .header-subtitle {
        color: #94a3b8;
        font-size: 0.875rem;
        font-weight: 400;
    }

    /* Stylizacja Zakładek - Modern Nav */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f1f5f9;
        padding: 6px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        color: #64748b !important;
        font-weight: 600;
        padding: 10px 20px;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
    }

    /* Wykresy i kontenery danych */
    .stPlotlyChart {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
    }

    /* Edytor tabeli */
    [data-testid="stDataEditor"] {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
    }

    /* Przyciski systemowe */
    .stButton>button {
        background-color: #2563eb;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 2rem;
        width: 100%;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
        box-shadow: 0 4px 6px -1px rgb(37 99 235 / 0.2);
    }

    /* Pasek przewijania */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #f1f5f9; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
    </style>
    
    <div class="enterprise-header">
        <div>
            <p class="header-title">SQM LOGISTICS</p>
            <p class="header-subtitle">Control Tower v5.0 | Enterprise Asset Management</p>
        </div>
        <div style="text-align: right; color: #ffffff;">
            <p style="font-size: 0.75rem; margin: 0; opacity: 0.6;">CURRENT STATUS</p>
            <p style="font-size: 1rem; font-weight: 600; color: #22c55e;">● OPERATIONAL</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 2. DEFINICJA ZASOBÓW
RESOURCES = {
    "FLOTA CIĘŻKA (FTL/SOLO)": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "POJAZDY DOSTAWCZE": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68",
        "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF",
        "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45",
        "BOXER DW9WK54 wysoki", "OPEL DW9WK53", "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637"
    ],
    "FLOTA LEKKA": [
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
        return data.fillna("")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# 4. DASHBOARD OPERACYJNY
tabs = st.tabs(list(RESOURCES.keys()) + ["⚙️ KONFIGURACJA BAZY"])

# Profesjonalna paleta barw (Stonowane)
corporate_colors = ["#1e40af", "#0f766e", "#b45309", "#be123c", "#6d28d9", "#334155"]
unique_events = sorted(df['event'].unique())
event_colors = {ev: corporate_colors[i % len(corporate_colors)] for i, ev in enumerate(unique_events)}

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
                tickfont=dict(size=11, family="Inter", color="#64748b"),
                range=[today - timedelta(days=2), today + timedelta(days=14)]
            )
            fig.update_yaxes(title="", tickfont=dict(size=10, weight="bold", color="#1e293b"))
            fig.update_traces(
                textposition='inside', 
                insidetextanchor='middle',
                textfont=dict(size=11, weight="bold", color="white")
            )
            fig.update_layout(
                height=len(RESOURCES[category]) * 40 + 120,
                margin=dict(l=10, r=10, t=60, b=10),
                showlegend=False, bargap=0.25
            )
            # Linia czasu (Dziś)
            fig.add_vline(x=today.timestamp()*1000, line_width=2, line_color="#ef4444", line_dash="solid")
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info(f"Brak zarejestrowanych operacji dla kategorii: {category}")

# 5. ADMINISTRACJA DANYMI
with tabs[-1]:
    st.subheader("Modyfikacja planu logistycznego")
    with st.container():
        edited_df = st.data_editor(
            df, 
            num_rows="dynamic", 
            use_container_width=True,
            height=600,
            column_config={
                "pojazd": st.column_config.SelectboxColumn("Zasób", options=ALL_RESOURCES, required=True),
                "start": st.column_config.DateColumn("Data rozpoczęcia"),
                "koniec": st.column_config.DateColumn("Data zakończenia"),
                "event": st.column_config.TextColumn("Nazwa projektu"),
                "kierowca": st.column_config.TextColumn("Personel"),
            },
            key="enterprise_editor"
        )
    
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button("ZAPISZ ZMIANY W BAZIE"):
            with st.status("Trwa synchronizacja danych..."):
                save_df = edited_df.copy()
                save_df = save_df[["pojazd", "event", "start", "koniec", "kierowca", "notatka"]]
                save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
                save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
                save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
                conn.update(data=save_df)
                st.rerun()
