import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony i CSS dla maksymalnej czytelności
st.set_page_config(page_title="SQM Control Tower", layout="wide")

st.markdown("""
    <style>
    /* Usunięcie zbędnych marginesów */
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    
    /* Stylizacja zakładki (Active Tab) */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] { background-color: #1a73e8 !important; color: white !important; }
    
    /* Tabela edycji */
    [data-testid="stDataEditor"] { border: 1px solid #1a73e8; }
    </style>
    """, unsafe_allow_html=True)

# 2. DEFINICJA ZASOBÓW (Zgodnie z Twoją listą)
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

# 3. POŁĄCZENIE Z DANYMI
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl="0s")
        data.columns = [c.strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        for col in ['pojazd', 'event', 'kierowca', 'notatka']:
            data[col] = data[col].astype(str).replace(['nan', 'None', ''], ' ')
        return data
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# 4. DASHBOARD - WIDOKI
st.title("🛰️ SQM Logistics Control Center")

tabs = st.tabs(list(RESOURCES.keys()) + ["🔧 ZARZĄDZANIE"])

# Inteligentne mapowanie kolorów (spójne dla całej aplikacji)
all_events = sorted(df['event'].unique())
color_palette = px.colors.qualitative.Dark24
event_colors = {event: color_palette[i % len(color_palette)] for i, event in enumerate(all_events)}

for i, category in enumerate(RESOURCES.keys()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(RESOURCES[category])]
        
        # Wykres Gantta dla kategorii
        fig = px.timeline(
            cat_df, x_start="start", x_end="koniec", y="pojazd",
            color="event", text="event",
            color_discrete_map=event_colors,
            category_orders={"pojazd": RESOURCES[category]},
            template="plotly_white"
        )
        
        # Oś X - Konfiguracja czytelności
        today = datetime.now()
        fig.update_xaxes(
            side="top",
            dtick="86400000.0", # Dni
            tickformat="%d\n%a", # Dzień i skrót dnia
            tickfont=dict(size=11, family="Arial Black", color="#333"),
            gridcolor="#dddddd",
            range=[today - timedelta(days=5), today + timedelta(days=20)], # Widok 25 dni na start
            rangeslider=dict(visible=True, thickness=0.02)
        )
        
        # Oś Y - Pojazdy
        fig.update_yaxes(
            title="",
            tickfont=dict(size=12, family="Arial", color="black"),
            gridcolor="#f0f0f0"
        )
        
        # Stylizacja bloków (Events)
        fig.update_traces(
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(size=13, family="Arial Black", color="white"),
            marker=dict(line=dict(width=1, color='white'))
        )
        
        # Layout i marginesy
        fig.update_layout(
            height=len(RESOURCES[category]) * 40 + 180,
            margin=dict(l=10, r=10, t=100, b=20),
            showlegend=False,
            bargap=0.3
        )
        
        # Linia "DZISIAJ"
        fig.add_vline(x=today.timestamp()*1000, line_width=3, line_dash="dash", line_color="#FF0000")
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# 5. PANEL EDYCJI
with tabs[-1]:
    st.subheader("📝 Edycja Bazy Transportowej")
    st.info("Wprowadź zmiany poniżej i kliknij ZAPISZ. Wybierz pojazd z listy rozwijanej.")
    
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 Pojazd / Zasób", options=ALL_RESOURCES, width="large"),
            "event": st.column_config.TextColumn("🏷️ Nazwa Eventu"),
            "start": st.column_config.DateColumn("📅 Start"),
            "koniec": st.column_config.DateColumn("🏁 Koniec"),
            "kierowca": st.column_config.TextColumn("👤 Kierowca"),
            "notatka": st.column_config.TextColumn("ℹ️ Notatki")
        },
        key="editor_v2"
    )
    
    if st.button("💾 ZAPISZ I SYNCHRONIZUJ Z ARKUSZEM"):
        # Mapowanie z powrotem do Google Sheets
        save_df = edited_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
        
        conn.update(data=save_df)
        st.success("Zaktualizowano pomyślnie!")
        st.rerun()
