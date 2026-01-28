import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA INTERFEJSU - WYSOKI KONTRAST I DUŻA CZCIONKA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SQM LOGISTICS | Enterprise Fleet Manager",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Wstrzyknięcie stylów CSS dla czytelności logistycznej
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;900&display=swap');
    
    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
    
    /* Nagłówek SQM Logistics Professional */
    .sqm-header {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        padding: 2.5rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        border-bottom: 10px solid #2563eb;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2);
    }

    /* POWIĘKSZENIE CZCIONEK DLA WYGODY PLANOWANIA */
    [data-testid="stDataEditor"] div { font-size: 18px !important; }
    button[data-baseweb="tab"] div p { font-size: 24px !important; font-weight: 900 !important; color: #0f172a !important; }

    /* WIDOCZNE I KOLOROWE SUWAKI (SCROLLBARS) */
    ::-webkit-scrollbar { width: 22px !important; height: 22px !important; display: block !important; }
    ::-webkit-scrollbar-track { background: #cbd5e1 !important; }
    ::-webkit-scrollbar-thumb { background: #2563eb !important; border-radius: 10px !important; border: 4px solid #cbd5e1 !important; }
    ::-webkit-scrollbar-thumb:hover { background: #1e40af !important; }

    /* Ukrycie menu Streamlit dla profesjonalnego wyglądu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>

    <div class="sqm-header">
        <h1 style="margin:0; font-size: 4rem; letter-spacing: -3px; line-height: 1;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.8; font-size: 1.4rem; font-weight: 400; margin-top: 10px;">
            Full Fleet Deployment & Asset Management System v8.0
        </p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DEFINICJA ZASOBÓW (PEŁNY SPIS ZGODNIE Z DOKUMENTACJĄ)
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

# Spłaszczona lista do Selectboxów i sprawdzania spójności
ALL_ASSETS_LIST = sorted([item for sublist in RESOURCES.values() for item in sublist])

# -----------------------------------------------------------------------------
# 3. OBSŁUGA DANYCH (GOOGLE SHEETS)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Odczyt danych z arkusza w czasie rzeczywistym
        raw_df = conn.read(ttl="0s")
        # Standaryzacja nazw kolumn na małe litery
        raw_df.columns = [str(c).strip().lower() for c in raw_df.columns]
        # Konwersja na typy daty
        raw_df['start'] = pd.to_datetime(raw_df['start'], errors='coerce')
        raw_df['koniec'] = pd.to_datetime(raw_df['koniec'], errors='coerce')
        
        # Jeśli arkusz jest zupełnie pusty, przygotuj strukturę
        if raw_df.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        
        return raw_df.fillna("")
    except Exception as e:
        # W przypadku błędu (np. brak kolumn) zwróć pusty szablon
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

# Inicjalizacja danych
df_current = load_data()

# -----------------------------------------------------------------------------
# 4. KONFIGURACJA WIDOKU HARMONOGRAMU
# -----------------------------------------------------------------------------
today = datetime.now()
v_start = today - timedelta(days=3)
v_end = today + timedelta(days=24)

tabs = st.tabs(list(RESOURCES.keys()) + ["🔧 ZARZĄDZANIE I DOPISYWANIE"])

# Renderowanie wykresów dla każdej kategorii
for i, (category, assets) in enumerate(RESOURCES.items()):
    with tabs[i]:
        # Filtrujemy tylko wiersze, które mają datę startu i są w danej kategorii
        mask = (df_current['pojazd'].isin(assets)) & (df_current['start'].notnull())
        plot_df = df_current[mask].copy()
        
        if not plot_df.empty:
            fig = px.timeline(
                plot_df, 
                x_start="start", 
                x_end="koniec", 
                y="pojazd",
                color="event", 
                text="event",
                category_orders={"pojazd": assets},
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Dark24
            )
            
            # Stylizacja osi X (Daty na górze)
            fig.update_xaxes(
                side="top", 
                range=[v_start, v_end], 
                tickformat="%d\n%b",
                dtick=86400000.0,
                tickfont=dict(size=16, weight='bold', color="#0f172a"),
                gridcolor="#e2e8f0"
            )
            
            # Stylizacja osi Y (Pojazdy)
            fig.update_yaxes(
                title="", 
                tickfont=dict(size=16, weight='bold', color="#0f172a"),
                gridcolor="#f1f5f9"
            )
            
            # Stylizacja pasków eventów
            fig.update_traces(
                textfont_size=14, 
                textfont_color="white",
                textposition="inside",
                insidetextanchor="middle",
                marker_line_width=1,
                marker_line_color="white"
            )
            
            fig.update_layout(
                height=max(350, len(assets)*55 + 120),
                margin=dict(l=10, r=10, t=60, b=10),
                showlegend=False,
                bargap=0.3
            )
            
            # Linia "DZISIAJ"
            fig.add_vline(x=today.timestamp()*1000, line_width=5, line_color="#ef4444")
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info(f"Kategoria {category} nie ma obecnie przypisanych żadnych zadań.")

# -----------------------------------------------------------------------------
# 5. PANEL CENTRALNY - EDYCJA, DODAWANIE EVENTÓW I ZAPIS
# -----------------------------------------------------------------------------
with tabs[-1]:
    st.markdown("### 📝 Arkusz Operacyjny Floty")
    st.markdown("""
        **Instrukcja:**
        1. Aby dodać kolejny projekt dla tego samego pojazdu, zjedź na sam dół i wybierz go w nowym wierszu.
        2. Po zakończeniu edycji kliknij duży przycisk **ZAPISZ** na dole strony.
    """)

    # Główny edytor danych z dynamicznymi wierszami
    edited_df = st.data_editor(
        df_current,
        num_rows="dynamic",  # POZWALA NA DODAWANIE KOLEJNYCH EVENTÓW
        use_container_width=True,
        hide_index=True,
        height=900,
        column_config={
            "pojazd": st.column_config.SelectboxColumn(
                "🚛 POJAZD / ZASÓB", 
                options=ALL_ASSETS_LIST, 
                width="medium", 
                required=True
            ),
            "event": st.column_config.TextColumn("📋 PROJEKT", width="small"),
            "start": st.column_config.DateColumn("📅 START", width="small"),
            "koniec": st.column_config.DateColumn("🏁 KONIEC", width="small"),
            "kierowca": st.column_config.TextColumn("👤 KIEROWCA", width="small"),
            "notatka": st.column_config.TextColumn("📝 LOGISTYKA / SLOTY / UWAGI", width="large")
        },
        key="sqm_master_v8"
    )

    st.markdown("---")
    
    # Przycisk zapisu
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY W CHMURZE", use_container_width=True):
        with st.status("Trwa synchronizacja z Google Sheets..."):
            try:
                # Oczyszczanie danych przed zapisem
                save_df = edited_df.dropna(subset=['pojazd']).copy()
                # Usuń całkowicie puste wiersze
                save_df = save_df[save_df['event'].astype(str).str.strip() != ""]
                
                # Formatowanie kolumn pod strukturę arkusza
                save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
                
                # Konwersja dat do formatu tekstowego akceptowanego przez Sheets
                save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
                save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
                
                # Aktualizacja
                conn.update(data=save_df)
                st.success("DANE ZAPISANE POMYŚLNIE!")
                st.rerun()
            except Exception as e:
                st.error(f"Wystąpił błąd podczas zapisu: {e}")

# -----------------------------------------------------------------------------
# KONIEC KOMPLETNEGO KODU v8.0
# -----------------------------------------------------------------------------
