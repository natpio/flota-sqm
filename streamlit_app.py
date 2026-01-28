import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA STRONY I INTERFEJSU (STRICT CORPORATE)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SQM LOGISTICS | Enterprise Fleet Management",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Wymuszenie stylów CSS dla czytelności i kontrastu
st.markdown("""
    <style>
    /* Import czcionki biznesowej */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* Tło i czcionka */
    .stApp {
        background-color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }

    /* Nagłówek SQM Logistics */
    .sqm-header-container {
        background-color: #0f172a;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 25px;
        border-left: 8px solid #2563eb;
        color: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* Wymuszenie krawędzi w edytorze danych (kontrast) */
    [data-testid="stDataEditor"] {
        border: 2px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }

    /* Powiększenie i kolorowanie suwaków bocznych (pionowych) */
    ::-webkit-scrollbar {
        width: 14px !important;
        height: 14px !important;
    }
    ::-webkit-scrollbar-track {
        background: #f1f5f9 !important;
    }
    ::-webkit-scrollbar-thumb {
        background: #475569 !important;
        border-radius: 10px !important;
        border: 3px solid #f1f5f9 !important;
    }

    /* Optymalizacja zakładek */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #ffffff;
        border-radius: 8px 8px 0px 0px;
        padding: 0px 20px;
        font-weight: 600;
        border: 1px solid #e2e8f0;
    }
    </style>

    <div class="sqm-header-container">
        <h1 style="margin:0; letter-spacing: -1px;">SQM LOGISTICS <span style="font-weight:400; color:#94a3b8;">| FLEET MANAGER</span></h1>
        <p style="margin:0; opacity:0.8; font-size:0.9rem;">Operational Control System v7.0 (Strict Professional)</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DEFINICJA ZASOBÓW (PEŁNA LISTA SQM)
# -----------------------------------------------------------------------------
RESOURCES = {
    "🚛 FTL / SOLO (TRANSPORT)": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", 
        "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", 
        "44 - SOLO PY 73262", 
        "45 - PY1541M + przyczepa"
    ],
    "🚐 BUS / DOSTAWCZE": [
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
        "OPEL DW9WK53", 
        "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", 
        "FORD Transit Connect PY54637"
    ],
    "🚗 OSOBOWE / RENTAL": [
        "01 – Caravelle – PO8LC63", 
        "Caravelle PY6872M - nowa", 
        "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A", 
        "06 – Dacia Duster – WH7087A ex T Białek",
        "05 – Dacia Duster – WH7083A   B.Krauze", 
        "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "Chrysler Pacifica PY04266 - MBanasiak", 
        "Seat Ateca WZ445HU  Dynasiuk",
        "Seat Ateca WZ446HU- PM", 
        "SPEDYCJA", 
        "AUTO RENTAL - CARVIDO"
    ],
    "🏠 NOCLEGI": [
        "MIESZKANIE BCN - TORRASA", 
        "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}
ALL_RESOURCES_LIST = [item for sublist in RESOURCES.values() for item in sublist]

# -----------------------------------------------------------------------------
# 3. OBSŁUGA DANYCH (GOOGLE SHEETS CONNECTION)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_fleet_data():
    try:
        # Pobieranie danych bez cache'owania dla pełnej świeżości
        raw_data = conn.read(ttl="0s")
        # Standaryzacja nazw kolumn do małych liter
        raw_data.columns = [str(c).strip().lower() for c in raw_data.columns]
        
        # Wymuszony format dat
        raw_data['start'] = pd.to_datetime(raw_data['start'], errors='coerce')
        raw_data['koniec'] = pd.to_datetime(raw_data['koniec'], errors='coerce')
        
        # Zapewnienie istnienia wszystkich kolumn
        for col in ["pojazd", "event", "start", "koniec", "kierowca", "notatka"]:
            if col not in raw_data.columns:
                raw_data[col] = ""
                
        return raw_data.fillna("")
    except Exception as e:
        st.error(f"Krytyczny błąd pobierania danych: {e}")
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

main_df = fetch_fleet_data()

# -----------------------------------------------------------------------------
# 4. PANEL BOCZNY (SIDEBAR NAVIGATOR)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://www.sqm.eu/wp-content/uploads/2019/02/logo-sqm.png", width=150)
    st.header("Konfiguracja Widoku")
    
    view_today = datetime.now()
    selected_range = st.date_input(
        "Zakres Harmonogramu:",
        value=(view_today - timedelta(days=2), view_today + timedelta(days=21)),
        help="Wybierz zakres dat widoczny na wykresach Gantta"
    )
    
    st.divider()
    st.markdown("### Status Floty")
    st.success(f"Pojazdy w bazie: {len(ALL_RESOURCES_LIST)}")
    st.info(f"Ostatnia aktualizacja: {view_today.strftime('%H:%M:%S')}")

# Rozpakowanie zakresu dat widoku
if isinstance(selected_range, tuple) and len(selected_range) == 2:
    v_start, v_end = selected_range
else:
    v_start, v_end = view_today - timedelta(days=2), view_today + timedelta(days=21)

# -----------------------------------------------------------------------------
# 5. GŁÓWNY PANEL OPERACYJNY (TABS)
# -----------------------------------------------------------------------------
tab_list = list(RESOURCES.keys()) + ["📝 ADMINISTRACJA / EDYCJA"]
tabs = st.tabs(tab_list)

# Paleta kolorów biznesowych dla Eventów
corporate_colors = ["#1e40af", "#0369a1", "#0e7490", "#0f766e", "#15803d", "#b45309", "#9f1239", "#581c87"]
event_list = sorted(main_df['event'].unique())
color_map = {ev: corporate_colors[i % len(corporate_colors)] for i, ev in enumerate(event_list)}

for i, (category, assets) in enumerate(RESOURCES.items()):
    with tabs[i]:
        # Filtrowanie danych dla danej kategorii
        category_data = main_df[main_df['pojazd'].isin(assets)].copy()
        
        if not category_data.empty:
            # Tworzenie wykresu Gantta
            fig = px.timeline(
                category_data, 
                x_start="start", 
                x_end="koniec", 
                y="pojazd", 
                color="event", 
                text="event",
                color_discrete_map=color_map,
                category_orders={"pojazd": assets},
                template="plotly_white"
            )
            
            # Konfiguracja osi i wyglądu
            fig.update_xaxes(
                side="top", 
                showgrid=True, 
                gridcolor="#f1f5f9",
                tickformat="%d\n%b", 
                dtick=86400000.0, # Co 1 dzień
                range=[v_start, v_end],
                tickfont=dict(size=11, color="#475569")
            )
            
            fig.update_yaxes(title="", tickfont=dict(size=10, weight="bold"))
            
            fig.update_layout(
                height=max(200, len(assets) * 45 + 100),
                margin=dict(l=10, r=10, t=50, b=10),
                showlegend=False,
                bargap=0.3
            )
            
            # Dodanie linii "DZISIAJ"
            fig.add_vline(x=view_today.timestamp()*1000, line_width=3, line_color="#ef4444")
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning(f"Brak zaplanowanych zadań dla kategorii {category}")

# -----------------------------------------------------------------------------
# 6. MODUŁ EDYCJI BAZY (ZERO-SCROLL ARCHITECTURE)
# -----------------------------------------------------------------------------
with tabs[-1]:
    st.subheader("Centralna Baza Zarządzania Transportem")
    st.caption("Wprowadź dane poniżej. Wszystkie kolumny są skompresowane, aby uniknąć przewijania w poziomie.")
    
    # Konfiguracja Edytora Danych - Agresywne dopasowanie szerokości
    edited_full_df = st.data_editor(
        main_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=700,
        column_config={
            "pojazd": st.column_config.SelectboxColumn(
                "🚛 Pojazd", 
                options=ALL_RESOURCES_LIST, 
                width="medium", 
                required=True
            ),
            "event": st.column_config.TextColumn(
                "📋 Projekt", 
                width="small"
            ),
            "start": st.column_config.DateColumn(
                "📅 Start", 
                width="small",
                format="YYYY-MM-DD"
            ),
            "koniec": st.column_config.DateColumn(
                "🏁 Koniec", 
                width="small",
                format="YYYY-MM-DD"
            ),
            "kierowca": st.column_config.TextColumn(
                "👤 Kierowca", 
                width="small"
            ),
            "notatka": st.column_config.TextColumn(
                "📝 Notatki / Slot / Rozładunek", 
                width="large"
            ),
        },
        key="sqm_fleet_ultimate_editor"
    )

    # Przycisk zapisu z pełną logiką synchronizacji
    st.markdown("---")
    if st.button("💾 ZAPISZ I AKTUALIZUJ ARKUSZ GOOGLE", use_container_width=True):
        with st.status("Trwa weryfikacja i przesyłanie danych...", expanded=True) as status:
            try:
                # Przygotowanie ramki danych do wysyłki (mapowanie nazw na format Arkusza)
                final_save_df = edited_full_df.copy()
                final_save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
                
                # Konwersja dat na format tekstowy akceptowany przez Sheets
                final_save_df['Start'] = pd.to_datetime(final_save_df['Start']).dt.strftime('%Y-%m-%d')
                final_save_df['Koniec'] = pd.to_datetime(final_save_df['Koniec']).dt.strftime('%Y-%m-%d')
                
                # Wykonanie aktualizacji
                conn.update(data=final_save_df)
                status.update(label="✅ Dane pomyślnie zapisane!", state="complete", expanded=False)
                
                # Odświeżenie aplikacji
                st.rerun()
            except Exception as e:
                status.update(label="❌ Błąd zapisu!", state="error")
                st.error(f"Nie udało się zapisać zmian: {e}")

# -----------------------------------------------------------------------------
# KONIEC KODU
# -----------------------------------------------------------------------------
