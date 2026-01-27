import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony i Clean UI Style
st.set_page_config(page_title="SQM LOGISTICS | Control Tower", layout="wide")

st.markdown("""
    <style>
    /* Tło strony - jasny, profesjonalny szary */
    .stApp { background-color: #f8f9fa; }
    
    /* Nagłówek aplikacji */
    h1 { 
        color: #1e293b; 
        font-family: 'Inter', sans-serif; 
        font-weight: 700; 
        padding-bottom: 1rem;
    }

    /* Stylizacja Zakładek - Nowoczesne i lekkie */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        color: #64748b;
        padding: 8px 16px;
        transition: all 0.3s;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
        border-color: #3b82f6 !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }

    /* Karta wykresu */
    .stPlotlyChart {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
        border: 1px solid #e2e8f0;
    }
    
    /* Ukrycie menu Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
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

# 3. LOGIKA DANYCH
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def get_data():
    try:
        data = conn.read()
        data.columns = [c.strip().lower() for c in data.columns]
        expected = ["pojazd", "event", "start", "koniec", "kierowca", "notatka"]
        data = data[expected].copy()
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.fillna("")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# 4. DASHBOARD UI
st.title("🛰️ SQM Logistics Control")

tabs = st.tabs([f" {k}" for k in RESOURCES.keys()] + ["⚙️ Zarządzanie"])

# Pastelowa paleta - wysoka czytelność czarnego tekstu
logistics_colors = ["#93c5fd", "#86efac", "#fde68a", "#f9a8d4", "#c4b5fd", "#fdba74"]
unique_events = sorted(df['event'].unique())
event_colors = {ev: logistics_colors[i % len(logistics_colors)] for i, ev in enumerate(unique_events)}

for i, (category, items) in enumerate(RESOURCES.items()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(items)].copy()
        
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event",
                color_discrete_map=event_colors,
                category_orders={"pojazd": items},
                template="plotly_white"
            )
            
            today = datetime.now()
            fig.update_xaxes(
                side="top", showgrid=True, gridcolor="#f1f5f9",
                tickformat="%d\n%a", dtick=86400000.0,
                tickfont=dict(size=10, family="Inter, sans-serif", color="#64748b"),
                range=[today - timedelta(days=2), today + timedelta(days=14)],
                rangeslider=dict(visible=True, thickness=0.02, bgcolor="#f8f9fa")
            )
            
            # Weekendy - bardzo jasny niebieski/szary
            start_cal = datetime(2026, 1, 1)
            for d in range(366):
                curr = start_cal + timedelta(days=d)
                if curr.weekday() >= 5:
                    fig.add_vrect(
                        x0=curr.strftime("%Y-%m-%d"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                        fillcolor="#f1f5f9", opacity=1, layer="below", line_width=0
                    )

            fig.update_yaxes(
                title="", 
                tickfont=dict(size=11, family="Inter", color="#1e293b"),
                gridcolor="#f1f5f9"
            )
            
            fig.update_traces(
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(size=11, family="Inter Black", color="#1e293b"), # Ciemny tekst na pastelach
                marker=dict(line=dict(width=1, color='white'))
            )
            
            fig.update_layout(
                height=len(items) * 45 + 100,
                margin=dict(l=10, r=10, t=60, b=0),
                showlegend=False, bargap=0.3,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            # Linia DZIŚ - wyraźny niebieski
            fig.add_vline(x=today.timestamp()*1000, line_width=2, line_color="#3b82f6")
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info(f"Brak zaplanowanych zadań dla sekcji {category}")

# 5. ZARZĄDZANIE
with tabs[-1]:
    st.subheader("🛠️ Edycja i Synchronizacja")
    edited_df = st.data_editor(
        df, num_rows="dynamic", use_container_width=True,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Zasób", options=ALL_RESOURCES),
            "start": st.column_config.DateColumn("Początek"),
            "koniec": st.column_config.DateColumn("Koniec")
        },
        key="sqm_v26_bright"
    )
    
    if st.button("💾 ZAPISZ ZMIANY W BAZIE"):
        with st.status("Aktualizacja danych..."):
            save_df = edited_df.copy()
            save_df = save_df[["pojazd", "event", "start", "koniec", "kierowca", "notatka"]]
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
