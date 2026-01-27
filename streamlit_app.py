import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony i Styl "Purple Door"
st.set_page_config(page_title="SQM LOGISTICS | Control Tower", layout="wide")

st.markdown("""
    <style>
    /* Główne tło - Fiolet Moniki */
    .stApp { 
        background-color: #6b46c1; 
        color: #ffffff;
    }

    /* Nagłówek */
    h1 { 
        color: #facc15; 
        font-family: 'Inter', sans-serif; 
        font-weight: 800;
        text-shadow: 2px 2px 0px #1e1e1e;
    }

    /* Stylizacja Zakładek */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: rgba(0,0,0,0.2);
        padding: 10px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 8px;
        color: #6b46c1;
        font-weight: bold;
        padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #facc15 !important;
        color: #1e1e1e !important;
    }

    /* Kontener Wykresu z Żółtą Ramką */
    .stPlotlyChart {
        background-color: #ffffff;
        border: 6px solid #facc15;
        border-radius: 15px;
        padding: 10px;
        box-shadow: 10px 10px 20px rgba(0,0,0,0.3);
    }

    /* Sekcja Zarządzania (Data Editor) */
    .stDataEditor {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 5px;
    }

    /* Przycisk zapisu */
    .stButton>button {
        background-color: #facc15;
        color: #1e1e1e;
        border: none;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 25px;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. DEFINICJA ZASOBÓW (Oryginalna)
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

# 4. INTERFEJS
st.title("🛰️ SQM LOGISTICS CONTROL TOWER")

tabs = st.tabs(list(RESOURCES.keys()) + ["⚙️ ZARZĄDZANIE"])

# Kolory eventów (Wyraźne na białym tle)
log_colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]
unique_events = sorted(df['event'].unique())
event_colors = {ev: log_colors[i % len(log_colors)] for i, ev in enumerate(unique_events)}

for i, category in enumerate(RESOURCES.keys()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(RESOURCES[category])].copy()
        
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event",
                color_discrete_map=event_colors,
                category_orders={"pojazd": RESOURCES[category]},
                template="plotly_white"
            )
            
            today = datetime.now()
            fig.update_xaxes(
                side="top", showgrid=True, gridcolor="#f1f5f9",
                tickformat="%d\n%a", dtick=86400000.0,
                tickfont=dict(size=10, family="Inter", color="#64748b"),
                range=[today - timedelta(days=2), today + timedelta(days=14)],
                rangeslider=dict(visible=True, thickness=0.02)
            )
            
            # Weekendy
            for d in range(366):
                curr = datetime(2026, 1, 1) + timedelta(days=d)
                if curr.weekday() >= 5:
                    fig.add_vrect(
                        x0=curr.strftime("%Y-%m-%d"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                        fillcolor="#f8fafc", opacity=1, layer="below", line_width=0
                    )

            fig.update_yaxes(title="", tickfont=dict(size=11, family="Inter Black"))
            fig.update_traces(
                textposition='inside', insidetextanchor='middle',
                textfont=dict(size=11, color="white"),
                marker=dict(line=dict(width=1, color='white'))
            )
            fig.update_layout(
                height=len(RESOURCES[category]) * 45 + 120,
                margin=dict(l=10, r=10, t=70, b=0),
                showlegend=False, bargap=0.3
            )
            fig.add_vline(x=today.timestamp()*1000, line_width=2, line_color="#ef4444")
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info(f"Brak zaplanowanych zadań dla: {category}")

# 5. ZARZĄDZANIE
with tabs[-1]:
    st.subheader("🛠️ Panel Edycji Danych")
    edited_df = st.data_editor(
        df, num_rows="dynamic", use_container_width=True,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Zasób", options=ALL_RESOURCES),
            "start": st.column_config.DateColumn("Początek"),
            "koniec": st.column_config.DateColumn("Koniec")
        },
        key="sqm_v28_purple"
    )
    
    if st.button("💾 ZAPISZ I SYNCHRONIZUJ"):
        with st.status("Trwa aktualizacja bazy..."):
            save_df = edited_df.copy()
            save_df = save_df[["pojazd", "event", "start", "koniec", "kierowca", "notatka"]]
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
