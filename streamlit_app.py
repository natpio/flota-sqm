import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. SYSTEM LOGOWANIA
# -----------------------------------------------------------------------------
def check_password():
    """Zwraca True, jeśli hasło jest poprawne."""
    def password_entered():
        if st.session_state["password"] == "SQM2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>SQM LOGISTICS | LOGOWANIE</h2>", unsafe_allow_html=True)
        st.text_input("Hasło dostępu:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Hasło dostępu:", type="password", on_change=password_entered, key="password")
        st.error("❌ Błędne hasło.")
        return False
    return True

if not check_password():
    st.stop()

# -----------------------------------------------------------------------------
# 2. KONFIGURACJA STRONY I STYLE CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="SQM LOGISTICS", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;900&display=swap');
    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
    .sqm-header {
        background: #0f172a; padding: 2rem; border-radius: 15px; color: white;
        margin-bottom: 2rem; border-bottom: 10px solid #2563eb;
    }
    /* Powiększenie czcionki w edytorze dla lepszej czytelności */
    [data-testid="stDataEditor"] div { font-size: 18px !important; }
    /* Stylizacja radia (menu) */
    div[data-testid="stRadio"] > div { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    /* Grubsze paski przewijania */
    ::-webkit-scrollbar { width: 22px !important; height: 22px !important; }
    ::-webkit-scrollbar-track { background: #cbd5e1 !important; }
    ::-webkit-scrollbar-thumb { background: #2563eb !important; border-radius: 10px; border: 4px solid #cbd5e1 !important; }
    </style>
    <div class="sqm-header">
        <h1 style="margin:0; font-size: 3.5rem; letter-spacing: -3px; line-height: 1;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.8; font-size: 1.2rem;">Fleet Manager v10.1 (Full Stable Version)</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. DEFINICJA ZASOBÓW I POŁĄCZENIE Z GSHEETS
# -----------------------------------------------------------------------------
RESOURCES = {
    "🚛 CIĘŻAROWE": ["31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS", "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa", "SPEDYCJA", "AUTO RENTAL"],
    "🚐 BUSY": ["25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"],
    "🚗 OSOBOWE": ["01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723", "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek", "05 – Dacia Duster – WH7083A B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N", "FORD Transit Connect PY54635", "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", "Chrysler Pacifica PY04266 - MBanasiak", "Seat Ateca WZ445HU Dynasiuk", "Seat Ateca WZ446HU- PM"],
    "🏠 NOCLEGI": ["MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"]
}
ALL_ASSETS = [item for sublist in RESOURCES.values() for item in sublist]

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    """Pobiera i formatuje dane z arkusza."""
    try:
        raw = conn.read(ttl="0s")
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        # Konwersja dat
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        # Filtrujemy tylko wiersze mające wpisany pojazd
        raw = raw[raw['pojazd'].notna() & (raw['pojazd'] != "")]
        # Domyślne sortowanie od najświeższych
        return raw.sort_values(by='start', ascending=False).fillna("")
    except Exception as e:
        st.error(f"Błąd pobierania danych: {e}")
        return pd.DataFrame(columns=['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka'])

# Inicjalizacja danych w sesji
if "df_fleet" not in st.session_state:
    st.session_state.df_fleet = get_data()

# -----------------------------------------------------------------------------
# 4. SIDEBAR - USTAWIENIA WIDOKU
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ USTAWIENIA")
    today = datetime.now()
    # Zakres domyślny: -2 dni do +21 dni
    view_range = st.date_input("ZAKRES WIDOKU:", value=(today - timedelta(days=2), today + timedelta(days=21)))
    
    if st.button("🔄 ODŚWIEŻ Z ARKUSZA"):
        st.session_state.df_fleet = get_data()
        st.rerun()
        
    if st.button("🚪 WYLOGUJ"):
        st.session_state["password_correct"] = False
        st.rerun()

# Obsługa błędu wyboru tylko jednej daty w date_input
if isinstance(view_range, tuple) and len(view_range) == 2:
    start_v, end_v = view_range
else:
    start_v, end_v = today - timedelta(days=2), today + timedelta(days=21)

# -----------------------------------------------------------------------------
# 5. NAWIGACJA (Taby)
# -----------------------------------------------------------------------------
tab_titles = list(RESOURCES.keys()) + ["🔧 EDYCJA / ARKUSZ"]
if "active_tab_index" not in st.session_state:
    st.session_state["active_tab_index"] = 0

active_tab = st.radio("WYBIERZ WIDOK:", tab_titles, index=st.session_state["active_tab_index"], horizontal=True)
st.session_state["active_tab_index"] = tab_titles.index(active_tab)
st.divider()

# -----------------------------------------------------------------------------
# 6. GENEROWANIE WYKRESU (Metoda go.Bar - stabilny tekst)
# -----------------------------------------------------------------------------
if active_tab in RESOURCES:
    assets_to_show = RESOURCES[active_tab]
    # Filtrujemy dane tylko dla wybranej grupy
    plot_df = st.session_state.df_fleet[st.session_state.df_fleet['pojazd'].isin(assets_to_show)].copy()
    plot_df = plot_df[plot_df['start'].notna()].copy()
    
    if not plot_df.empty:
        fig = go.Figure()
        
        # Grupowanie po evencie, żeby każdy projekt miał swój kolor
        for event_name, group in plot_df.groupby('event'):
            widths = (group['koniec'] - group['start']).dt.total_seconds() * 1000
            
            fig.add_trace(go.Bar(
                y=group['pojazd'],
                x=widths,
                base=group['start'],
                orientation='h',
                name=event_name,
                text=group['event'],
                textposition='inside',
                insidetextanchor='start',
                textfont=dict(size=14, color='white', family="Inter"),
                constraintext='none',
                hovertemplate="<b>%{y}</b><br>Projekt: %{text}<br>Start: %{base|%d %b}<extra></extra>"
            ))

        fig.update_layout(
            barmode='overlay',
            height=max(500, len(assets_to_show)*60 + 100),
            showlegend=False,
            template="plotly_white",
            margin=dict(l=10, r=20, t=50, b=10),
            xaxis=dict(
                type='date',
                range=[start_v, end_v],
                side='top',
                tickformat="%d\n%b",
                tickfont=dict(size=16, weight='bold')
            ),
            yaxis=dict(
                categoryorder='array',
                categoryarray=assets_to_show[::-1],
                tickfont=dict(size=14, weight='bold')
            )
        )
        # Linia "DZIŚ"
        fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info(f"Brak zaplanowanych projektów dla kategorii: {active_tab}")

# -----------------------------------------------------------------------------
# 7. PANEL EDYCJI Z WYSZUKIWARKĄ, SORTOWANIEM I WALIDACJĄ
# -----------------------------------------------------------------------------
elif active_tab == "🔧 EDYCJA / ARKUSZ":
    st.subheader("Główny Panel Zarządzania Danymi")
    
    # Wyszukiwarka
    search_query = st.text_input("🔍 WYSZUKAJ (wpisz pojazd, nazwę projektu lub kierowcę):", "").lower()
    
    # Przygotowanie danych do wyświetlenia (z uwzględnieniem filtra)
    if search_query:
        mask = st.session_state.df_fleet.astype(str).apply(lambda x: x.str.lower().str.contains(search_query).any(), axis=1)
        display_df = st.session_state.df_fleet[mask].copy()
    else:
        display_df = st.session_state.df_fleet.copy()

    st.info("💡 Kliknij w nagłówek kolumny (np. START), aby posortować całą tabelę.")

    # Edytor - tutaj używamy stabilnego klucza 'fleet_editor_v10'
    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=700,
        key="fleet_editor_v10",
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 ZASÓB", options=ALL_ASSETS, width=300, required=True),
            "event": st.column_config.TextColumn("📋 PROJEKT", width=180),
            "start": st.column_config.DateColumn("📅 START", width=130),
            "koniec": st.column_config.DateColumn("🏁 KONIEC", width=130),
            "kierowca": st.column_config.TextColumn("👤 KIER.", width=120),
            "notatka": st.column_config.TextColumn("📝 NOTATKI / SLOTY", width=500)
        }
    )

    # Przyciski akcji
    col_save, col_clear = st.columns([1, 4])
    with col_save:
        if st.button("💾 ZAPISZ ZMIANY", use_container_width=True):
            # 1. Czyszczenie danych (tylko wiersze z eventem)
            clean_df = edited_df[edited_df['event'] != ""].copy()
            clean_df['start'] = pd.to_datetime(clean_df['start'], errors='coerce')
            clean_df['koniec'] = pd.to_datetime(clean_df['koniec'], errors='coerce')
            
            # 2. Walidacja kolizji (Overbooking)
            conflicts = []
            for vehicle in clean_df['pojazd'].unique():
                v_data = clean_df[clean_df['pojazd'] == vehicle].sort_values('start')
                res_list = v_data.to_dict('records')
                for i in range(len(res_list)):
                    for j in range(i + 1, len(res_list)):
                        r1, r2 = res_list[i], res_list[j]
                        if pd.notnull(r1['start']) and pd.notnull(r2['start']):
                            # Warunek nakładania się zakresów
                            if (r1['start'] < r2['koniec']) and (r2['start'] < r1['koniec']):
                                conflicts.append(f"🔴 **{vehicle}**: Kolizja '{r1['event']}' vs '{r2['event']}'")

            if conflicts:
                st.error("### ❌ NIE MOŻNA ZAPISAĆ - KONFLIKTY DAT!")
                for c in conflicts:
                    st.write(c)
                st.info("Zmień daty dla powyższych pojazdów i spróbuj ponownie.")
            else:
                # 3. Formatowanie do Google Sheets i wysyłka
                save_df = clean_df.copy()
                save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
                save_df['Start'] = save_df['Start'].dt.strftime('%Y-%m-%d')
                save_df['Koniec'] = save_df['Koniec'].dt.strftime('%Y-%m-%d')
                
                try:
                    conn.update(data=save_df)
                    st.session_state.df_fleet = get_data() # Odświeżenie danych w sesji
                    st.success("✅ Dane zapisane pomyślnie w arkuszu!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")
