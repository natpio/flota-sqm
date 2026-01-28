import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA I STYLE (BRAK SCROLLA, DUŻA CZCIONKA)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="SQM LOGISTICS", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;900&display=swap');
    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
    .sqm-header {
        background: #0f172a; padding: 2rem; border-radius: 15px; color: white;
        margin-bottom: 2rem; border-bottom: 10px solid #2563eb;
    }
    [data-testid="stDataEditor"] div { font-size: 18px !important; }
    button[data-baseweb="tab"] div p { font-size: 22px !important; font-weight: 900 !important; }
    ::-webkit-scrollbar { width: 20px; height: 20px; }
    ::-webkit-scrollbar-thumb { background: #2563eb; border-radius: 10px; border: 4px solid #f1f5f9; }
    </style>
    <div class="sqm-header">
        <h1 style="margin:0; font-size: 3.5rem; letter-spacing: -3px;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.8;">Permanent Asset Visibility v8.5</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. KOMPLETNA LISTA ZASOBÓW (TWOJA BAZA)
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
# 3. LOGIKA DANYCH (POŁĄCZENIE STAŁEJ LISTY Z ARKUSZEM)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_integrated_data():
    try:
        raw = conn.read(ttl="0s")
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        
        # Klucz do sukcesu: Tworzymy szkielet ze wszystkich zasobów
        skeleton = pd.DataFrame({'pojazd': ALL_ASSETS})
        
        # Łączymy (Outer Join), aby zachować puste auta I wszystkie projekty z arkusza
        merged = pd.merge(skeleton, raw, on='pojazd', how='outer')
        
        # Usuwamy ewentualne wiersze z arkusza, które nie pasują do naszej listy RESOURCES (opcjonalnie)
        merged = merged[merged['pojazd'].isin(ALL_ASSETS)]
        
        return merged.fillna("")
    except:
        return pd.DataFrame({'pojazd': ALL_ASSETS, 'event': '', 'start': pd.NaT, 'koniec': pd.NaT, 'kierowca': '', 'notatka': ''})

df = get_integrated_data()

# -----------------------------------------------------------------------------
# 4. HARMONOGRAMY I EDYCJA
# -----------------------------------------------------------------------------
today = datetime.now()
tabs = st.tabs(list(RESOURCES.keys()) + ["🔧 EDYCJA WSZYSTKICH ZASOBÓW"])

for i, (cat, assets) in enumerate(RESOURCES.items()):
    with tabs[i]:
        # Wyświetlamy wykres tylko jeśli są jakiekolwiek daty
        plot_df = df[(df['pojazd'].isin(assets)) & (df['start'] != "")].copy()
        if not plot_df.empty:
            fig = px.timeline(plot_df, x_start="start", x_end="koniec", y="pojazd", color="event", text="event", 
                             category_orders={"pojazd": assets}, template="plotly_white")
            fig.update_xaxes(side="top", tickfont=dict(size=16, weight='bold'))
            fig.update_yaxes(title="", tickfont=dict(size=16, weight='bold'))
            fig.update_layout(height=max(400, len(assets)*55 + 100), showlegend=False)
            fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Nawet jeśli nie ma wykresu, wypisujemy listę wolnych aut
            st.success(f"Wszystkie pojazdy {cat} są obecnie WOLNE (Dostępne: {', '.join(assets)})")

with tabs[-1]:
    st.subheader("Główny Arkusz Zarządzania")
    st.info("Poniżej widnieje każdy zasób SQM. Możesz edytować istniejące lub dodawać nowe wiersze na dole.")
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=900,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 ZASÓB", options=ALL_ASSETS, width=300, required=True),
            "event": st.column_config.TextColumn("📋 PROJEKT", width=180),
            "start": st.column_config.DateColumn("📅 START", width=130),
            "koniec": st.column_config.DateColumn("🏁 KONIEC", width=130),
            "kierowca": st.column_config.TextColumn("👤 KIER.", width=120),
            "notatka": st.column_config.TextColumn("📝 NOTATKI / SLOTY", width=500)
        }
    )

    if st.button("💾 ZAPISZ WSZYSTKO", use_container_width=True):
        save_df = edited_df[edited_df['event'] != ""].copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
        conn.update(data=save_df)
        st.success("Zapisano pomyślnie!")
        st.rerun()
