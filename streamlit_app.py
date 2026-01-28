import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA INTERFEJSU (ULTRA-CZYTELNOŚĆ I BRAK SCROLLA)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SQM LOGISTICS | Enterprise Fleet",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;900&display=swap');
    
    /* Globalne ustawienia tła i czcionki */
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Nagłówek SQM */
    .sqm-header {
        background: #0f172a;
        padding: 25px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
        border-bottom: 8px solid #2563eb;
    }

    /* POWIĘKSZENIE CZCIONEK W EDYTORZE I TABACH */
    [data-testid="stDataEditor"] div { font-size: 18px !important; }
    button[data-baseweb="tab"] div p { font-size: 22px !important; font-weight: 900 !important; color: #0f172a !important; }

    /* WIDOCZNE I GRUBE SUWAKI */
    ::-webkit-scrollbar { width: 20px !important; height: 20px !important; }
    ::-webkit-scrollbar-track { background: #e2e8f0 !important; }
    ::-webkit-scrollbar-thumb { background: #2563eb !important; border-radius: 10px; border: 4px solid #e2e8f0; }
    
    /* Usunięcie zbędnych odstępów */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    </style>

    <div class="sqm-header">
        <h1 style="margin:0; font-size: 3.5rem; letter-spacing: -2px;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.7; font-size: 1.2rem;">System Zarządzania Flotą i Noclegami v7.7</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. KOMPLETNA LISTA ZASOBÓW SQM (DEFINICJA STACJARNARNA)
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

# Spłaszczona lista wszystkich zasobów
ALL_ASSETS_LIST = []
for group in RESOURCES.values():
    ALL_ASSETS_LIST.extend(group)

# -----------------------------------------------------------------------------
# 3. POBIERANIE I ŁĄCZENIE DANYCH (GWARANCJA PEŁNEJ LISTY)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_integrated_data():
    try:
        # Pobierz dane z Google Sheets
        raw = conn.read(ttl="0s")
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        
        # Tworzymy bazę na podstawie listy zasobów z kodu
        base_df = pd.DataFrame({'pojazd': ALL_ASSETS_LIST})
        
        # Łączymy, aby każdy pojazd z kodu był w tabeli tylko RAZ (najnowszy wpis)
        raw_clean = raw.drop_duplicates(subset=['pojazd'], keep='last')
        merged = pd.merge(base_df, raw_clean, on='pojazd', how='left')
        
        return merged.fillna("")
    except:
        # Jeśli arkusz jest niedostępny/pusty
        return pd.DataFrame({
            'pojazd': ALL_ASSETS_LIST, 'event': '', 'start': pd.NaT, 
            'koniec': pd.NaT, 'kierowca': '', 'notatka': ''
        })

df = get_integrated_data()

# -----------------------------------------------------------------------------
# 4. KONFIGURACJA WIDOKU (ZAKRES DAT)
# -----------------------------------------------------------------------------
col_d1, col_d2 = st.columns([1, 3])
with col_d1:
    today = datetime.now()
    d_range = st.date_input("ZAKRES WIDOKU:", value=(today - timedelta(days=2), today + timedelta(days=21)))

if isinstance(d_range, tuple) and len(d_range) == 2:
    v_s, v_e = d_range
else:
    v_s, v_e = today - timedelta(2), today + timedelta(21)

# -----------------------------------------------------------------------------
# 5. MODUŁY WIDOKU (TABY)
# -----------------------------------------------------------------------------
tabs = st.tabs(list(RESOURCES.keys()) + ["📝 EDYCJA I ZAPIS"])

# Kolory dla eventów
event_map = {ev: px.colors.qualitative.Bold[i % 10] for i, ev in enumerate(sorted(df['event'].unique()))}

for i, (cat_name, cat_list) in enumerate(RESOURCES.items()):
    with tabs[i]:
        # Filtrujemy dane, które mają przypisane daty dla tej kategorii
        plot_df = df[(df['pojazd'].isin(cat_list)) & (df['start'] != "")].copy()
        
        if not plot_df.empty:
            fig = px.timeline(
                plot_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event", color_discrete_map=event_map,
                category_orders={"pojazd": cat_list}, template="plotly_white"
            )
            fig.update_xaxes(side="top", range=[v_s, v_e], tickformat="%d\n%b", tickfont=dict(size=16, weight='bold'))
            fig.update_yaxes(title="", tickfont=dict(size=16, weight='bold'))
            fig.update_traces(textfont_size=14, textposition="inside")
            fig.update_layout(height=max(250, len(cat_list)*55 + 100), margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
            fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Wszystkie zasoby w kategorii {cat_name} są obecnie wolne.")

# -----------------------------------------------------------------------------
# 6. CENTRALNY PANEL EDYCJI (BEZ SCROLLA POZIOMEGO)
# -----------------------------------------------------------------------------
with tabs[-1]:
    st.markdown("### 📝 Arkusz Zarządzania Flotą SQM")
    st.caption("Poniżej znajduje się pełna lista zasobów. Wypełnij dane i kliknij ZAPISZ.")

    # Edytor z wymuszonymi szerokościami kolumn
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        height=850,
        column_config={
            "pojazd": st.column_config.TextColumn("🚛 POJAZD / MIESZKANIE", width=300, disabled=True),
            "event": st.column_config.TextColumn("📋 PROJEKT", width=180),
            "start": st.column_config.DateColumn("📅 START", width=130),
            "koniec": st.column_config.DateColumn("🏁 KONIEC", width=130),
            "kierowca": st.column_config.TextColumn("👤 KIEROWCA", width=120),
            "notatka": st.column_config.TextColumn("📝 NOTATKI / SLOTY", width=500)
        },
        key="sqm_v77_final"
    )

    st.divider()
    if st.button("💾 ZAPISZ ZMIANY W ARKUSZU GOOGLE", use_container_width=True):
        with st.status("Trwa zapisywanie danych..."):
            # Zapisujemy tylko wiersze, które mają przypisany event lub daty
            save_data = edited_df[edited_df['event'] != ""].copy()
            
            # Mapowanie nazw na arkusz
            save_data.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            
            # Formatowanie dat
            save_data['Start'] = pd.to_datetime(save_data['Start']).dt.strftime('%Y-%m-%d')
            save_data['Koniec'] = pd.to_datetime(save_data['Koniec']).dt.strftime('%Y-%m-%d')
            
            conn.update(data=save_data)
            st.success("Zasoby zaktualizowane pomyślnie!")
            st.rerun()

# -----------------------------------------------------------------------------
# KONIEC KODU v7.7
# -----------------------------------------------------------------------------
