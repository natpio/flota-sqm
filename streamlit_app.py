import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. STYLE I KONFIGURACJA (ULTRA-CZYTELNOŚĆ)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="SQM LOGISTICS", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;900&display=swap');
    .stApp { background-color: #f1f5f9; }
    
    /* POWIĘKSZENIE CZCIONEK */
    html, body, [class*="st-"] { font-size: 16px; font-family: 'Inter', sans-serif; }
    
    /* Nagłówek */
    .header { background: #0f172a; padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px; border-bottom: 8px solid #2563eb; }
    
    /* Tabela edycji - czcionka komórek */
    [data-testid="stDataEditor"] div { font-size: 18px !important; }
    
    /* Zakładki - czcionka */
    button[data-baseweb="tab"] div p { font-size: 22px !important; font-weight: 900 !important; }

    /* Suwaki - jaskrawe, by były widoczne */
    ::-webkit-scrollbar { width: 20px; height: 20px; }
    ::-webkit-scrollbar-thumb { background: #2563eb; border-radius: 10px; border: 4px solid #f1f5f9; }
    </style>
    <div class="header">
        <h1 style="margin:0; font-size: 3rem;">SQM LOGISTICS | PANEL OPERACYJNY</h1>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. LISTA FLOTY (STAŁA)
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
ALL_ASSETS = [item for sublist in RESOURCES.values() for item in sublist]

# -----------------------------------------------------------------------------
# 3. LOGIKA DANYCH (POŁĄCZENIE Z LISTĄ ZASOBÓW)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_clean_data():
    try:
        raw = conn.read(ttl="0s")
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        
        # Tworzymy czystą bazę z floty i dołączamy dane z arkusza
        base = pd.DataFrame({'pojazd': ALL_ASSETS})
        # Usuwamy duplikaty z arkusza przed złączeniem (tylko najnowszy wpis na pojazd)
        raw_unique = raw.drop_duplicates(subset=['pojazd'], keep='last')
        merged = pd.merge(base, raw_unique, on='pojazd', how='left')
        return merged.fillna("")
    except:
        return pd.DataFrame({'pojazd': ALL_ASSETS, 'event': '', 'start': pd.NaT, 'koniec': pd.NaT, 'kierowca': '', 'notatka': ''})

df = get_clean_data()

# -----------------------------------------------------------------------------
# 4. WIDOKI I EDYCJA
# -----------------------------------------------------------------------------
tabs = st.tabs(list(RESOURCES.keys()) + ["📝 EDYCJA"])

for i, (cat, assets) in enumerate(RESOURCES.items()):
    with tabs[i]:
        c_df = df[(df['pojazd'].isin(assets)) & (df['start'] != "")].copy()
        if not c_df.empty:
            fig = px.timeline(c_df, x_start="start", x_end="koniec", y="pojazd", color="event", text="event", template="plotly_white")
            fig.update_xaxes(side="top", tickfont=dict(size=16, weight='bold'))
            fig.update_yaxes(title="", tickfont=dict(size=16, weight='bold'), categoryorder="array", categoryarray=assets)
            fig.update_layout(height=max(200, len(assets)*50+100), showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Pojazdy {cat} są obecnie wolne.")

with tabs[-1]:
    st.subheader("Panel wprowadzania danych (Wszystkie pojazdy)")
    
    # EDYTOR - KLUCZ DO BRAKU SCROLLA
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        height=800,
        column_config={
            "pojazd": st.column_config.TextColumn("🚛 POJAZD", width=250, disabled=True),
            "event": st.column_config.TextColumn("📋 EVENT", width=150),
            "start": st.column_config.DateColumn("📅 START", width=120),
            "koniec": st.column_config.DateColumn("🏁 KONIEC", width=120),
            "kierowca": st.column_config.TextColumn("👤 KIER.", width=100),
            "notatka": st.column_config.TextColumn("📝 NOTATKI / SLOTY", width=400)
        },
        key="sqm_editor_v76"
    )

    if st.button("💾 ZAPISZ ZMIANY", use_container_width=True):
        # Zapisujemy tylko wiersze, które mają wpisany chociaż event lub datę
        to_save = edited_df[edited_df['event'] != ""].copy()
        to_save.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        to_save['Start'] = pd.to_datetime(to_save['Start']).dt.strftime('%Y-%m-%d')
        to_save['Koniec'] = pd.to_datetime(to_save['Koniec']).dt.strftime('%Y-%m-%d')
        conn.update(data=to_save)
        st.success("Zapisano!")
        st.rerun()
