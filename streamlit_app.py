import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA STRONY I STYLE (Maksymalna czytelność)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SQM LOGISTICS | Full Asset Management",
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

    /* WIĘKSZE CZCIONKI */
    [data-testid="stDataEditor"] div { font-size: 16px !important; }
    button[data-baseweb="tab"] div p { font-size: 20px !important; font-weight: 800 !important; }

    /* WIDOCZNE SUWAKI */
    ::-webkit-scrollbar { width: 18px !important; height: 18px !important; }
    ::-webkit-scrollbar-track { background: #cbd5e1 !important; }
    ::-webkit-scrollbar-thumb { background: #1e40af !important; border-radius: 5px !important; }
    </style>

    <div class="sqm-header">
        <h1 style="margin:0; font-weight:900; font-size: 3rem;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.8; font-size: 1.1rem;">Gwarantowana Lista Wszystkich Zasobów v7.4</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. KOMPLETNA DEFINICJA FLOTY I MIEJSC (STACJONARNA W KODZIE)
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
        "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN",
        "FORD Transit Connect PY54637",
        "Chrysler Pacifica PY04266 - MBanasiak",
        "05 – Dacia Duster – WH7083A B.Krauze",
        "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "Seat Ateca WZ445HU Dynasiuk",
        "Seat Ateca WZ446HU- PM"
    ],
    "🏠 NOCLEGI": [
        "MIESZKANIE BCN - TORRASA",
        "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}

# Spłaszczona lista wszystkich zasobów do inicjalizacji tabeli
ALL_ASSETS = []
for group in RESOURCES.values():
    ALL_ASSETS.extend(group)

# -----------------------------------------------------------------------------
# 3. POBIERANIE DANYCH I ŁĄCZENIE Z PEŁNĄ LISTĄ
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_combined_data():
    try:
        # 1. Pobierz dane z Google Sheets
        raw_data = conn.read(ttl="0s")
        raw_data.columns = [str(c).strip().lower() for c in raw_data.columns]
        raw_data['start'] = pd.to_datetime(raw_data['start'], errors='coerce')
        raw_data['koniec'] = pd.to_datetime(raw_data['koniec'], errors='coerce')
        
        # 2. Stwórz bazowy DataFrame ze wszystkimi pojazdami z kodu
        base_df = pd.DataFrame({'pojazd': ALL_ASSETS})
        
        # 3. Połącz (Left Join) bazę pojazdów z danymi z arkusza
        # Dzięki temu każdy pojazd z kodu pojawi się przynajmniej raz
        combined = pd.merge(base_df, raw_data, on='pojazd', how='left')
        
        # Wypełnij puste kolumny dla nowych/pustych pojazdów
        for col in ['event', 'kierowca', 'notatka']:
            if col not in combined.columns: combined[col] = ""
        
        return combined.fillna("")
    except:
        # Jeśli arkusz jest pusty, zwróć tylko listę pojazdów z kodu
        return pd.DataFrame({
            'pojazd': ALL_ASSETS,
            'event': "", 'start': pd.NaT, 'koniec': pd.NaT, 'kierowca': "", 'notatka': ""
        })

df = get_combined_data()

# -----------------------------------------------------------------------------
# 4. NAWIGACJA
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("USTAWIENIA WIDOKU")
    today = datetime.now()
    dr = st.date_input("Zakres dat:", value=(today - timedelta(days=2), today + timedelta(days=21)))

start_v, end_v = (dr[0], dr[1]) if isinstance(dr, tuple) and len(dr) == 2 else (today-timedelta(2), today+timedelta(21))

# -----------------------------------------------------------------------------
# 5. HARMONOGRAMY
# -----------------------------------------------------------------------------
tabs = st.tabs(list(RESOURCES.keys()) + ["⚙️ EDYCJA (WSZYSTKIE ZASOBY)"])

for i, (category, assets) in enumerate(RESOURCES.items()):
    with tabs[i]:
        # Wyświetlamy tylko te, które mają przypisany start i koniec
        c_df = df[(df['pojazd'].isin(assets)) & (df['start'].notnull())].copy()
        if not c_df.empty:
            fig = px.timeline(
                c_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event", category_orders={"pojazd": assets}, template="plotly_white"
            )
            fig.update_xaxes(side="top", range=[start_v, end_v], tickformat="%d\n%b", tickfont=dict(size=15, weight='bold'))
            fig.update_yaxes(title="", tickfont=dict(size=14, weight='bold'))
            fig.update_layout(height=max(200, len(assets)*50 + 100), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Brak aktywnych zadań dla: {category}. Wszystkie pojazdy są dostępne w zakładce Edycja.")

# -----------------------------------------------------------------------------
# 6. PANEL EDYCJI - GWARANTOWANA PEŁNA LISTA
# -----------------------------------------------------------------------------
with tabs[-1]:
    st.markdown(f"### 📋 Pełna lista zasobów SQM ({len(ALL_ASSETS)} pozycji)")
    st.info("Poniższa lista zawiera wszystkie pojazdy i mieszkania zdefiniowane w systemie, niezależnie od tego, czy mają przypisane zadania.")

    # Edytor z pełną listą
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=1000,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 Zasób", options=ALL_ASSETS, width="medium", required=True),
            "event": st.column_config.TextColumn("📋 Event", width="small"),
            "start": st.column_config.DateColumn("📅 Start", width="small"),
            "koniec": st.column_config.DateColumn("🏁 Koniec", width="small"),
            "kierowca": st.column_config.TextColumn("👤 Kierowca", width="small"),
            "notatka": st.column_config.TextColumn("📝 Notatki / Sloty", width="large")
        },
        key="sqm_fixed_assets_v74"
    )

    if st.button("💾 ZAPISZ CAŁĄ BAZĘ", use_container_width=True):
        with st.status("Synchronizacja z Google Sheets..."):
            # Przed zapisem usuwamy puste wiersze (te, które nie mają daty ani eventu), 
            # aby nie zaśmiecać arkusza, ALE w aplikacji zawsze będą widoczne puste.
            save_df = edited_df.dropna(subset=['start', 'koniec', 'event'], how='all').copy()
            
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            
            conn.update(data=save_df)
            st.success("Zmiany zapisane!")
            st.rerun()
