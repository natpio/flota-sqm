import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA ŚRODOWISKA I INTERFEJSU (WYSOKA CZYTELNOŚĆ)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SQM LOGISTICS | Enterprise Fleet Manager",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Wstrzyknięcie pełnych stylów CSS dla czytelności i eliminacji scrolla
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;900&display=swap');
    
    /* Globalne ustawienia bazy */
    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
    
    /* Profesjonalny Header SQM */
    .sqm-header {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        padding: 2.5rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        border-bottom: 10px solid #2563eb;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2);
    }

    /* WIELKIE CZCIONKI DO TABELI I TABÓW */
    [data-testid="stDataEditor"] div { font-size: 18px !important; }
    button[data-baseweb="tab"] div p { font-size: 24px !important; font-weight: 900 !important; color: #0f172a !important; }

    /* WIDOCZNE I GRUBE SUWAKI DLA SZYBKIEJ NAWIGACJI */
    ::-webkit-scrollbar { width: 22px !important; height: 22px !important; display: block !important; }
    ::-webkit-scrollbar-track { background: #cbd5e1 !important; }
    ::-webkit-scrollbar-thumb { background: #2563eb !important; border-radius: 10px !important; border: 4px solid #cbd5e1 !important; }
    ::-webkit-scrollbar-thumb:hover { background: #1e40af !important; }

    /* Usuwanie zbędnych marginesów Streamlit */
    .block-container { padding-top: 1.5rem; }
    </style>

    <div class="sqm-header">
        <h1 style="margin:0; font-size: 4rem; letter-spacing: -3px; line-height: 1;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.8; font-size: 1.4rem; font-weight: 400; margin-top: 10px;">
            Full Asset Deployment & Multi-Event Management System v8.1
        </p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DEFINICJA WSZYSTKICH ZASOBÓW (GWARANTOWANA KOMPLETNOŚĆ)
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

# Spłaszczona lista wszystkich zasobów do selekcji w edytorze
ALL_ASSETS_LIST = sorted([item for sublist in RESOURCES.values() for item in sublist])

# -----------------------------------------------------------------------------
# 3. ŁĄCZNOŚĆ Z DANYMI (GOOGLE SHEETS)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Odczyt bezpośredni bez cache'owania (ttl=0s)
        raw_df = conn.read(ttl="0s")
        # Standaryzacja nazw kolumn
        raw_df.columns = [str(c).strip().lower() for c in raw_df.columns]
        # Konwersja dat
        raw_df['start'] = pd.to_datetime(raw_df['start'], errors='coerce')
        raw_df['koniec'] = pd.to_datetime(raw_df['koniec'], errors='coerce')
        
        if raw_df.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        
        return raw_df.fillna("")
    except Exception:
        # Zwróć pusty szablon, jeśli arkusz nie odpowiada
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

# Inicjalizacja danych bieżących
df_main = load_data()

# -----------------------------------------------------------------------------
# 4. MODUŁ WIZUALIZACJI (HARMONOGRAMY GANTTA)
# -----------------------------------------------------------------------------
# Zakres czasowy widoku
today = datetime.now()
view_start = today - timedelta(days=2)
view_end = today + timedelta(days=21)

tabs = st.tabs(list(RESOURCES.keys()) + ["📝 EDYCJA I NOWE EVENTY"])

for i, (category, assets) in enumerate(RESOURCES.items()):
    with tabs[i]:
        # Filtrujemy dane dla konkretnej grupy zasobów
        mask = (df_main['pojazd'].isin(assets)) & (df_main['start'].notnull())
        plot_df = df_main[mask].copy()
        
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
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            
            # Konfiguracja osi X i Y pod kątem czytelności logistycznej
            fig.update_xaxes(
                side="top", 
                range=[view_start, view_end], 
                tickformat="%d\n%b",
                dtick=86400000.0,
                tickfont=dict(size=16, weight='bold', color="#0f172a"),
                gridcolor="#e2e8f0"
            )
            
            fig.update_yaxes(
                title="", 
                tickfont=dict(size=16, weight='bold', color="#0f172a"),
                gridcolor="#f1f5f9"
            )
            
            fig.update_traces(
                textfont_size=14, 
                textposition="inside",
                insidetextanchor="middle"
            )
            
            fig.update_layout(
                height=max(300, len(assets)*55 + 100),
                margin=dict(l=10, r=10, t=60, b=10),
                showlegend=False,
                bargap=0.35
            )
            
            # Pionowa linia "DZISIAJ"
            fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info(f"Brak zaplanowanych zadań w kategorii: {category}")

# -----------------------------------------------------------------------------
# 5. MODUŁ ZARZĄDZANIA (PEŁNY EDYTOR DANYCH)
# -----------------------------------------------------------------------------
with tabs[-1]:
    st.markdown("### 📋 Panel Planowania Przejazdów i Noclegów")
    st.markdown("""
    💡 **Wskazówka:** Aby przypisać kolejny projekt do tego samego pojazdu, po prostu dodaj nowy wiersz na dole tabeli i wybierz pojazd z listy.
    """)

    # Edytor z obsługą dynamicznych wierszy i sztywną szerokością kolumn
    edited_df = st.data_editor(
        df_main,
        num_rows="dynamic",  # Pozwala na dopisywanie wielu projektów do jednego auta
        use_container_width=True,
        hide_index=True,
        height=850,
        column_config={
            "pojazd": st.column_config.SelectboxColumn(
                "🚛 ZASÓB SQM", 
                options=ALL_ASSETS_LIST, 
                width="medium", 
                required=True
            ),
            "event": st.column_config.TextColumn("📋 PROJEKT", width="small"),
            "start": st.column_config.DateColumn("📅 START", width="small"),
            "koniec": st.column_config.DateColumn("🏁 KONIEC", width="small"),
            "kierowca": st.column_config.TextColumn("👤 KIEROWCA", width="small"),
            "notatka": st.column_config.TextColumn("📝 UWAGI / SLOTY / TRANSPORT", width="large")
        },
        key="sqm_ultimate_v81"
    )

    st.markdown("---")
    
    # Przycisk zapisu z logiką czyszczenia danych
    if st.button("💾 ZAPISZ HARMONOGRAM W ARKUSZU GOOGLE", use_container_width=True):
        with st.status("Trwa aktualizacja bazy danych..."):
            try:
                # Filtracja: usuwamy wiersze bez wybranego pojazdu lub bez nazwy eventu
                to_save = edited_df.dropna(subset=['pojazd']).copy()
                to_save = to_save[to_save['event'].astype(str).str.strip() != ""]
                
                # Zmiana nazw kolumn na format arkusza
                to_save.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
                
                # Konwersja dat na format ISO dla Google Sheets
                to_save['Start'] = pd.to_datetime(to_save['Start']).dt.strftime('%Y-%m-%d')
                to_save['Koniec'] = pd.to_datetime(to_save['Koniec']).dt.strftime('%Y-%m-%d')
                
                # Wysłanie danych do arkusza
                conn.update(data=to_save)
                st.success("Synchronizacja zakończona pomyślnie!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd podczas zapisu: {e}")

# -----------------------------------------------------------------------------
# KONIEC KOMPLETNEGO KODU v8.1
# -----------------------------------------------------------------------------
