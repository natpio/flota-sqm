import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. STYLE I KONFIGURACJA (ULTRA-CZYTELNOŚĆ, ZERO-SCROLL)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SQM LOGISTICS | Multi-Event System",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;900&display=swap');
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    .sqm-header {
        background: #0f172a;
        padding: 25px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
        border-bottom: 8px solid #2563eb;
    }

    /* POWIĘKSZENIE CZCIONEK DLA CZYTELNOŚCI */
    [data-testid="stDataEditor"] div { font-size: 18px !important; }
    button[data-baseweb="tab"] div p { font-size: 22px !important; font-weight: 900 !important; color: #0f172a !important; }

    /* WIDOCZNE I GRUBE SUWAKI */
    ::-webkit-scrollbar { width: 20px !important; height: 20px !important; }
    ::-webkit-scrollbar-track { background: #e2e8f0 !important; }
    ::-webkit-scrollbar-thumb { background: #2563eb !important; border-radius: 10px; border: 4px solid #e2e8f0; }
    </style>

    <div class="sqm-header">
        <h1 style="margin:0; font-size: 3.5rem; letter-spacing: -2px;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.7; font-size: 1.2rem;">Multi-Event Scheduling v7.8</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. KOMPLETNA LISTA ZASOBÓW SQM
# -----------------------------------------------------------------------------
RESOURCES = {
    "🚛 CIĘŻAROWE": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa",
        "SPEDYCJA", "AUTO RENTAL"
    ],
    "🚐 BUSY": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68",
        "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF",
        "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45",
        "BOXER DW9WK54 wysoki", "OPEL DW9WK53"
    ],
    "🚗 OSOBOWE": [
        "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek",
        "05 – Dacia Duster – WH7083A B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "FORD Transit Connect PY54635", "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637",
        "Chrysler Pacifica PY04266 - MBanasiak", "Seat Ateca WZ445HU Dynasiuk", "Seat Ateca WZ446HU- PM"
    ],
    "🏠 NOCLEGI": [
        "MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}
ALL_ASSETS_LIST = sorted([item for sublist in RESOURCES.values() for item in sublist])

# -----------------------------------------------------------------------------
# 3. POBIERANIE DANYCH (MULTI-ROW LOGIC)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        raw = conn.read(ttl="0s")
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        
        # Jeśli arkusz jest pusty, zainicjuj listę bazową
        if raw.empty or len(raw.columns) < 2:
            return pd.DataFrame({'pojazd': ALL_ASSETS_LIST, 'event': '', 'start': pd.NaT, 'koniec': pd.NaT, 'kierowca': '', 'notatka': ''})
            
        # Wyświetlamy dokładnie to co w arkuszu (pozwalamy na wiele wierszy dla jednego auta)
        return raw.fillna("")
    except:
        return pd.DataFrame({'pojazd': ALL_ASSETS_LIST, 'event': '', 'start': pd.NaT, 'koniec': pd.NaT, 'kierowca': '', 'notatka': ''})

df = get_data()

# -----------------------------------------------------------------------------
# 4. HARMONOGRAM (GANTT) - GRUPOWANIE PO POJEŹDZIE
# -----------------------------------------------------------------------------
tabs = st.tabs(list(RESOURCES.keys()) + ["📝 EDYCJA I NOWE EVENTY"])

today = datetime.now()
v_s = today - timedelta(days=2)
v_e = today + timedelta(days=21)

for i, (cat_name, cat_list) in enumerate(RESOURCES.items()):
    with tabs[i]:
        plot_df = df[(df['pojazd'].isin(cat_list)) & (df['start'] != "")].copy()
        if not plot_df.empty:
            fig = px.timeline(
                plot_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event",
                category_orders={"pojazd": cat_list}, template="plotly_white"
            )
            fig.update_xaxes(side="top", range=[v_s, v_e], tickformat="%d\n%b", tickfont=dict(size=16, weight='bold'))
            fig.update_yaxes(title="", tickfont=dict(size=16, weight='bold'))
            fig.update_layout(height=max(300, len(cat_list)*55 + 100), margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
            fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Brak zaplanowanych tras dla {cat_name}.")

# -----------------------------------------------------------------------------
# 5. PANEL EDYCJI (DODAWANIE WIERSZY DLA KOLEJNYCH EVENTÓW)
# -----------------------------------------------------------------------------
with tabs[-1]:
    st.markdown("### 📝 Zarządzanie Trasami i Noclegami")
    st.info("Aby dodać kolejny projekt dla tego samego auta: zjedź na sam dół tabeli i wpisz dane w nowym wierszu, wybierając pojazd z listy.")

    # Edytor z włączonym dodawaniem wierszy (num_rows="dynamic")
    edited_df = st.data_editor(
        df,
        num_rows="dynamic", # KLUCZOWE: Pozwala dodawać nowe eventy
        use_container_width=True,
        hide_index=True,
        height=800,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 POJAZD", options=ALL_ASSETS_LIST, width=300, required=True),
            "event": st.column_config.TextColumn("📋 PROJEKT", width=180),
            "start": st.column_config.DateColumn("📅 START", width=130),
            "koniec": st.column_config.DateColumn("🏁 KONIEC", width=130),
            "kierowca": st.column_config.TextColumn("👤 KIEROWCA", width=120),
            "notatka": st.column_config.TextColumn("📝 NOTATKI / SLOTY", width=500)
        },
        key="sqm_v78_multi"
    )

    if st.button("💾 ZAPISZ HARMONOGRAM", use_container_width=True):
        with st.status("Aktualizacja arkusza..."):
            # Czyścimy puste wiersze przed zapisem
            save_data = edited_df.dropna(subset=['pojazd']).copy()
            save_data = save_data[save_data['event'] != ""]
            
            save_data.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_data['Start'] = pd.to_datetime(save_data['Start']).dt.strftime('%Y-%m-%d')
            save_data['Koniec'] = pd.to_datetime(save_data['Koniec']).dt.strftime('%Y-%m-%d')
            
            conn.update(data=save_data)
            st.success("Zapisano! Kolejne eventy pojawią się na wykresie.")
            st.rerun()
