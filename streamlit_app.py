import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# 1. Konfiguracja i Wstrzyknięcie Naprawy Suwaka przez JS
st.set_page_config(page_title="SQM LOGISTICS | Data Center", layout="wide")

# Skrypt JS, który co 1 sekundę sprawdza czy tabela jest widoczna i wymusza scroll
components.html(
    """
    <script>
    const fixScroll = () => {
        const editors = window.parent.document.querySelectorAll('[data-testid="stDataEditor"]');
        editors.forEach(editor => {
            const container = editor.querySelector('.st-emotion-cache-1wrc664') || editor;
            container.style.overflow = 'auto';
            container.style.minWidth = '100%';
        });
    }
    setInterval(fixScroll, 1000);
    </script>
    """,
    height=0,
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }

    /* Nagłówek */
    .header-bar {
        background: #0f172a;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        color: white;
    }

    /* Wymuszenie widoczności suwaków przez CSS (Metoda pomocnicza) */
    [data-testid="stDataEditor"] div {
        overflow: auto !important;
    }

    /* Stylizacja zakładek */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #f1f5f9;
        padding: 5px;
        border-radius: 10px;
    }
    </style>

    <div class="header-bar">
        <h2 style="margin:0;">SQM LOGISTICS <span style="color:#2563eb;">|</span> CONTROL CENTER</h2>
        <p style="margin:0; opacity:0.6; font-size:0.8rem;">Build 2026.01.28 | Stability Update</p>
    </div>
    """, unsafe_allow_html=True)

# 2. DEFINICJA ZASOBÓW
RESOURCES = {
    "🚛 TRANSPORT CIĘŻKI": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "🚐 DOSTAWCZE / BUS": [
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
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.fillna("")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# 4. DASHBOARD
tabs = st.tabs(list(RESOURCES.keys()) + ["🛠️ ZARZĄDZANIE"])

for i, category in enumerate(RESOURCES.keys()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(RESOURCES[category])].copy()
        if not cat_df.empty:
            fig = px.timeline(cat_df, x_start="start", x_end="koniec", y="pojazd", color="event", template="plotly_white")
            fig.update_layout(height=len(RESOURCES[category])*45 + 100, showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak aktywnych zadań.")

# 5. ZARZĄDZANIE - WYMUSZONY SCROLL PRZEZ SZTYWNE SZEROKOŚCI
with tabs[-1]:
    st.markdown("### Edycja bazy danych (Użyj Shift + Scroll, jeśli suwak boczny nie reaguje)")
    
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        height=500,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_RESOURCES, width="large"),
            "event": st.column_config.TextColumn("Projekt / Event", width="medium"),
            "start": st.column_config.DateColumn("Start", width="small"),
            "koniec": st.column_config.DateColumn("Koniec", width="small"),
            "kierowca": st.column_config.TextColumn("Kierowca", width="medium"),
            "notatka": st.column_config.TextColumn("Notatki", width="large")
        },
        key="js_scroll_fix_editor"
    )
    
    if st.button("ZAPISZ WSZYSTKIE ZMIANY"):
        with st.status("Aktualizacja arkusza..."):
            save_df = edited_df.copy()
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
