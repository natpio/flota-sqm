import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA STRONY I ULTRA-CZYTELNEGO INTERFEJSU
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SQM LOGISTICS | Fleet Manager",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }

    .sqm-header {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        border-bottom: 8px solid #2563eb;
    }

    /* POWIĘKSZENIE CZCIONEK DLA CZYTELNOŚCI LOGISTYCZNEJ */
    [data-testid="stDataEditor"] div { font-size: 16px !important; }
    button[data-baseweb="tab"] div p { font-size: 20px !important; font-weight: 800 !important; }

    /* WIDOCZNE I KOLOROWE SUWAKI (SCROLLBARS) */
    ::-webkit-scrollbar { width: 18px !important; height: 18px !important; display: block !important; }
    ::-webkit-scrollbar-track { background: #cbd5e1 !important; }
    ::-webkit-scrollbar-thumb { background: #1e40af !important; border-radius: 5px !important; border: 2px solid #cbd5e1 !important; }
    ::-webkit-scrollbar-thumb:hover { background: #2563eb !important; }
    </style>

    <div class="sqm-header">
        <h1 style="margin:0; font-weight:900; font-size: 3rem; letter-spacing: -2px;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.8; font-size: 1.1rem;">Full Fleet Database & Scheduling v7.3</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. KOMPLETNY SPIS FLOTY (ZGODNIE Z TWOIM ZESTAWIENIEM)
# -----------------------------------------------------------------------------
RESOURCES = {
    "🚛 CIĘŻAROWE": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI",
        "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK",
        "44 - SOLO PY 73262",
        "45 - PY1541M + przyczepa",
        "SPEDYCJA",
        "AUTO RENTAL"
    ],
    "🚐 BUSY": [
        "25 – Jumper – PY22952",
        "24 – Jumper – PY22954",
        "BOXER - PO 5VT68",
        "BOXER - WZ213GF",
        "BOXER - WZ214GF",
        "BOXER - WZ215GF",
        "OPEL DW4WK43",
        "BOXER (WYPAS) DW7WE24",
        "OPEL wysoki DW4WK45",
        "BOXER DW9WK54 wysoki",
        "OPEL DW9WK53"
    ],
    "🚗 OSOBOWE": [
        "01 – Caravelle – PO8LC63",
        "Caravelle PY6872M - nowa",
        "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A",
        "06 – Dacia Duster – WH7087A ex T Białek",
        "05 – Dacia Duster – WH7083A B.Krauze",
        "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN",
        "FORD Transit Connect PY54637",
        "Chrysler Pacifica PY04266 - MBanasiak",
        "Seat Ateca WZ445HU Dynasiuk",
        "Seat Ateca WZ446HU- PM"
    ],
    "🏠 NOCLEGI": [
        "MIESZKANIE BCN - TORRASA",
        "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}
ALL_RESOURCES_LIST = sorted([item for sublist in RESOURCES.values() for item in sublist])

# -----------------------------------------------------------------------------
# 3. DANE (GSHEETS)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl="0s")
        data.columns = [str(c).strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.fillna("")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# -----------------------------------------------------------------------------
# 4. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://www.sqm.eu/wp-content/uploads/2019/02/logo-sqm.png", width=180)
    st.header("USTAWIENIA")
    today = datetime.now()
    date_range = st.date_input("Zakres widoku:", value=(today - timedelta(days=2), today + timedelta(days=21)))

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_v, end_v = date_range
else:
    start_v, end_v = today - timedelta(days=2), today + timedelta(days=21)

# -----------------------------------------------------------------------------
# 5. HARMONOGRAM (GANTT)
# -----------------------------------------------------------------------------
tabs = st.tabs(list(RESOURCES.keys()) + ["⚙️ EDYCJA WSZYSTKICH POJAZDÓW"])

event_colors = ["#1e40af", "#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#0369a1", "#0891b2", "#0d9488"]
unique_events = sorted(df['event'].unique())
color_map = {ev: event_colors[i % len(event_colors)] for i, ev in enumerate(unique_events)}

for i, (category, assets) in enumerate(RESOURCES.items()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(assets)].copy()
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event", color_discrete_map=color_map,
                category_orders={"pojazd": assets}, template="plotly_white"
            )
            fig.update_xaxes(side="top", range=[start_v, end_v], tickformat="%d\n%b", dtick=86400000.0,
                             tickfont=dict(size=15, weight='bold'))
            fig.update_yaxes(title="", tickfont=dict(size=15, weight='bold'))
            fig.update_traces(textfont_size=14, textposition="inside")
            fig.update_layout(height=max(300, len(assets)*55 + 150), margin=dict(l=10, r=10, t=60, b=10), showlegend=False)
            fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Brak wpisów dla: {category}")

# -----------------------------------------------------------------------------
# 6. PANEL EDYCJI - TUTAJ SĄ WSZYSTKIE POJAZDY
# -----------------------------------------------------------------------------
with tabs[-1]:
    # Kontrolka ilościowa
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### 📝 Baza Danych ({len(df)} wpisów)")
    with col2:
        st.metric("Pojazdów w bazie", len(df['pojazd'].unique()))

    st.warning("Poniżej znajduje się PEŁNA lista. Przewijaj w dół, aby zobaczyć wszystkie auta.")
    
    # Edytor z wymuszoną dużą wysokością (1000px), aby nic nie umknęło
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=1000, # BARDZO WYSOKA TABELA
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 Zasób", options=ALL_RESOURCES_LIST, width="medium", required=True),
            "event": st.column_config.TextColumn("📋 Projekt", width="small"),
            "start": st.column_config.DateColumn("📅 Start", width="small"),
            "koniec": st.column_config.DateColumn("🏁 Koniec", width="small"),
            "kierowca": st.column_config.TextColumn("👤 Kierowca", width="small"),
            "notatka": st.column_config.TextColumn("📝 Notatki / Sloty", width="large")
        },
        key="full_fleet_v73"
    )

    if st.button("💾 ZAPISZ WSZYSTKIE POJAZDY DO ARKUSZA", use_container_width=True):
        with st.status("Aktualizacja Google Sheets..."):
            save_df = edited_df.copy()
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
