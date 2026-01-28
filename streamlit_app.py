import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA SYSTEMU I ULTRA-CZYTELNY INTERFEJS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SQM LOGISTICS | Total Fleet Control",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

    /* Globalne tło i czcionka biznesowa */
    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }

    /* Nagłówek SQM Logistics Professional */
    .sqm-header {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        border-bottom: 8px solid #2563eb;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }

    /* POWIĘKSZENIE CZCIONEK DLA WYGODY PLANOWANIA */
    [data-testid="stDataEditor"] div { font-size: 16px !important; }
    button[data-baseweb="tab"] div p { font-size: 20px !important; font-weight: 800 !important; color: #0f172a !important; }

    /* KONTRASTOWE I WIDOCZNE SUWAKI (SCROLLBARS) */
    ::-webkit-scrollbar {
        width: 18px !important;
        height: 18px !important;
        display: block !important;
    }
    ::-webkit-scrollbar-track {
        background: #cbd5e1 !important;
    }
    ::-webkit-scrollbar-thumb {
        background: #1e40af !important;
        border-radius: 5px !important;
        border: 2px solid #cbd5e1 !important;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #2563eb !important;
    }

    /* Stylizacja sekcji informacyjnych */
    .stAlert { border-radius: 10px !important; }
    </style>

    <div class="sqm-header">
        <h1 style="margin:0; font-weight:900; font-size: 3rem; letter-spacing: -2px;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.8; font-size: 1.1rem; font-weight: 400;">Gwarantowana Lista Zasobów & Harmonogram v7.5</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. KOMPLETNA DEFINICJA ZASOBÓW (GWARANTOWANA OBECNOŚĆ W KODZIE)
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

# Pełna lista zasobów do inicjalizacji danych
ALL_ASSETS = []
for items in RESOURCES.values():
    ALL_ASSETS.extend(items)

# -----------------------------------------------------------------------------
# 3. POBIERANIE DANYCH Z SYNCHRONIZACJĄ Z LISTĄ ZASOBÓW
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_and_merge_data():
    try:
        # Pobranie danych surowych z Google Sheets
        raw = conn.read(ttl="0s")
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        
        # Konwersja dat
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        
        # Stworzenie bazy ze wszystkich zdefiniowanych zasobów
        base = pd.DataFrame({'pojazd': ALL_ASSETS})
        
        # Połączenie listy zasobów z danymi z arkusza (Left Join)
        # Gwarantuje, że KAŻDY pojazd z kodu pojawi się w tabeli
        merged = pd.merge(base, raw, on='pojazd', how='left')
        
        # Uzupełnienie brakujących kolumn dla nowych zasobów
        for col in ['event', 'kierowca', 'notatka']:
            if col not in merged.columns: merged[col] = ""
            
        return merged.fillna("")
    except:
        # Awaryjny powrót do samej listy zasobów
        return pd.DataFrame({
            'pojazd': ALL_ASSETS, 'event': "", 'start': pd.NaT, 
            'koniec': pd.NaT, 'kierowca': "", 'notatka': ""
        })

df = fetch_and_merge_data()

# -----------------------------------------------------------------------------
# 4. KONFIGURACJA PANELU BOCZNEGO (SIDEBAR)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://www.sqm.eu/wp-content/uploads/2019/02/logo-sqm.png", width=180)
    st.markdown("---")
    st.header("USTAWIENIA WIDOKU")
    today = datetime.now()
    date_range = st.date_input(
        "Zakres harmonogramu:",
        value=(today - timedelta(days=2), today + timedelta(days=21))
    )
    st.markdown("---")
    st.success(f"Zasobów w systemie: {len(ALL_ASSETS)}")

# Logika zakresu dat dla wykresów
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_v, end_v = date_range
else:
    start_v, end_v = today - timedelta(days=2), today + timedelta(days=21)

# -----------------------------------------------------------------------------
# 5. HARMONOGRAM OPERACYJNY (GANTT)
# -----------------------------------------------------------------------------
tabs = st.tabs(list(RESOURCES.keys()) + ["🔧 ZARZĄDZANIE FLOTĄ (WSZYSTKO)"])

# Kolory dla eventów
colors = ["#1e40af", "#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#0369a1", "#0891b2", "#0d9488"]
unique_events = sorted(df['event'].unique())
color_map = {ev: colors[i % len(colors)] for i, ev in enumerate(unique_events)}

for i, (category, assets) in enumerate(RESOURCES.items()):
    with tabs[i]:
        # Filtrujemy dane dla danej kategorii, które mają przypisane daty
        cat_df = df[(df['pojazd'].isin(assets)) & (df['start'].notnull())].copy()
        
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event", color_discrete_map=color_map,
                category_orders={"pojazd": assets}, template="plotly_white"
            )
            
            # Konfiguracja osi z powiększoną czcionką
            fig.update_xaxes(
                side="top", range=[start_v, end_v], tickformat="%d\n%b",
                dtick=86400000.0, gridcolor="#cbd5e1",
                tickfont=dict(size=15, weight='bold', color="#0f172a")
            )
            fig.update_yaxes(title="", tickfont=dict(size=15, weight='bold', color="#0f172a"))
            
            fig.update_traces(textfont_size=14, textposition="inside")
            
            fig.update_layout(
                height=max(250, len(assets)*55 + 120),
                margin=dict(l=10, r=10, t=60, b=10),
                showlegend=False, bargap=0.35
            )
            
            fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info(f"Wszystkie zasoby w kategorii {category} są obecnie wolne. Przejdź do zakładki edycji, aby przypisać zadania.")

# -----------------------------------------------------------------------------
# 6. PANEL EDYCJI - GWARANTOWANA PEŁNA LISTA (STATYCZNA + DYNAMICZNA)
# -----------------------------------------------------------------------------
with tabs[-1]:
    st.markdown("### 📋 Kompletna Baza Zasobów SQM Logistics")
    st.warning("Lista poniżej zawiera wszystkie pojazdy i mieszkania zdefiniowane w kodzie. Nawet jeśli nie mają wpisów w arkuszu, są tutaj widoczne i gotowe do edycji.")

    # Edytor z wymuszoną dużą wysokością (1000px) i kompletną listą
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=1000,
        column_config={
            "pojazd": st.column_config.SelectboxColumn(
                "🚛 Pojazd / Miejsce", 
                options=ALL_ASSETS, 
                width="medium", 
                required=True
            ),
            "event": st.column_config.TextColumn("📋 Projekt / Event", width="small"),
            "start": st.column_config.DateColumn("📅 Data Start", width="small"),
            "koniec": st.column_config.DateColumn("🏁 Data Koniec", width="small"),
            "kierowca": st.column_config.TextColumn("👤 Kierowca", width="small"),
            "notatka": st.column_config.TextColumn("📝 Notatki / Sloty / Logistyka", width="large")
        },
        key="sqm_total_control_v75"
    )

    st.markdown("---")
    if st.button("💾 ZAPISZ I SYNCHRONIZUJ Z ARKUSZEM GOOGLE", use_container_width=True):
        with st.status("Przesyłanie danych do chmury..."):
            # Przed zapisem czyścimy wiersze, które nie mają żadnych danych (żeby nie robić spamu w arkuszu)
            # Ale w aplikacji puste wiersze zawsze zostaną, bo są w RESOURCES.
            save_df = edited_df.dropna(subset=['event', 'start', 'koniec'], how='all').copy()
            
            # Mapowanie kolumn na format Google Sheets
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            
            # Konwersja dat na format tekstowy YYYY-MM-DD
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            
            conn.update(data=save_df)
            st.success("Synchronizacja zakończona pomyślnie!")
            st.rerun()

# -----------------------------------------------------------------------------
# KONIEC KODU v7.5
# -----------------------------------------------------------------------------
