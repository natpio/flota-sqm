import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. LOGOWANIE
# -----------------------------------------------------------------------------
def check_password():
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
# 2. STYLE CSS
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
    [data-testid="stDataEditor"] div { font-size: 18px !important; }
    div[data-testid="stRadio"] > div { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    ::-webkit-scrollbar { width: 22px !important; height: 22px !important; }
    ::-webkit-scrollbar-track { background: #cbd5e1 !important; }
    ::-webkit-scrollbar-thumb { background: #2563eb !important; border-radius: 10px; border: 4px solid #cbd5e1 !important; }
    </style>
    <div class="sqm-header">
        <h1 style="margin:0; font-size: 3.5rem; letter-spacing: -3px; line-height: 1;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.8; font-size: 1.2rem;">Fleet Manager v9.9 (Sorting & Search Fix)</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. ZASOBY
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
    try:
        raw = conn.read(ttl="0s")
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        # Konwersja dat z obsługą błędów
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        
        # Filtrowanie tylko wierszy z pojazdem (pomijamy puste)
        raw = raw[raw['pojazd'].notna() & (raw['pojazd'] != "")]
        
        # Domyślne sortowanie po dacie startu (najnowsze na górze)
        raw = raw.sort_values(by='start', ascending=False)
        
        return raw.fillna("")
    except:
        return pd.DataFrame(columns=['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka'])

df = get_data()

# -----------------------------------------------------------------------------
# 4. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ USTAWIENIA")
    today = datetime.now()
    view_range = st.date_input("ZAKRES WIDOKU:", value=(today - timedelta(days=2), today + timedelta(days=21)))
    if st.button("WYLOGUJ"):
        st.session_state["password_correct"] = False
        st.rerun()

if isinstance(view_range, tuple) and len(view_range) == 2:
    start_v, end_v = view_range
else:
    start_v, end_v = today - timedelta(days=2), today + timedelta(days=21)

# -----------------------------------------------------------------------------
# 5. NAWIGACJA
# -----------------------------------------------------------------------------
tab_titles = list(RESOURCES.keys()) + ["🔧 EDYCJA / ARKUSZ"]
if "active_tab_index" not in st.session_state:
    st.session_state["active_tab_index"] = 0

active_tab = st.radio("MENU:", tab_titles, index=st.session_state["active_tab_index"], horizontal=True, key="nav_radio")
st.session_state["active_tab_index"] = tab_titles.index(active_tab)
st.divider()

# -----------------------------------------------------------------------------
# 6. WYKRES (go.Bar Bulletproof)
# -----------------------------------------------------------------------------
if active_tab in RESOURCES:
    assets_to_show = RESOURCES[active_tab]
    plot_df = df[df['pojazd'].isin(assets_to_show)].copy()
    plot_df = plot_df[plot_df['start'] != ""].copy()
    
    if not plot_df.empty:
        fig = go.Figure()
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
            xaxis=dict(type='date', range=[start_v, end_v], side='top', tickformat="%d\n%b", tickfont=dict(size=16, weight='bold')),
            yaxis=dict(categoryorder='array', categoryarray=assets_to_show[::-1], tickfont=dict(size=14, weight='bold'))
        )
        fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info(f"Brak projektów dla: {active_tab}")

# -----------------------------------------------------------------------------
# 7. PANEL EDYCJI (FIX SORTOWANIA I WYSZUKIWANIA)
# -----------------------------------------------------------------------------
elif active_tab == "🔧 EDYCJA / ARKUSZ":
    st.subheader("Główny Panel Zarządzania")
    
    # 1. Wyszukiwarka
    search_q = st.text_input("🔍 Szukaj w całej bazie (auto, event, kierowca):", "").lower()
    
    # 2. Przygotowanie danych do tabeli
    display_df = df.copy()
    
    # Rzutowanie na string dla wyszukiwarki
    for col in display_df.columns:
        display_df[col] = display_df[col].astype(str)

    if search_q:
        display_df = display_df[display_df.apply(lambda row: row.astype(str).str.contains(search_q).any(), axis=1)]

    # 3. Edytor danych (Sortowanie działa przez kliknięcie w nagłówek)
    st.info("👆 Kliknij nagłówek kolumny, aby sortować (A-Z, Z-A, Daty).")
    
    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=700,
        key="main_editor",
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 ZASÓB", options=ALL_ASSETS, width=300, required=True),
            "event": st.column_config.TextColumn("📋 PROJEKT", width=180),
            "start": st.column_config.DateColumn("📅 START", width=130),
            "koniec": st.column_config.DateColumn("🏁 KONIEC", width=130),
            "kierowca": st.column_config.TextColumn("👤 KIER.", width=120),
            "notatka": st.column_config.TextColumn("📝 NOTATKI", width=500)
        }
    )

    if st.button("💾 ZAPISZ I SPRAWDŹ KOLIZJE", use_container_width=True):
        # Konwersja dat przed walidacją
        check_df = edited_df[edited_df['event'] != ""].copy()
        check_df['start'] = pd.to_datetime(check_df['start'], errors='coerce')
        check_df['koniec'] = pd.to_datetime(check_df['koniec'], errors='coerce')
        
        # Logika kolizji
        conflicts = []
        for p in check_df['pojazd'].unique():
            v_res = check_df[check_df['pojazd'] == p].sort_values('start')
            res_list = v_res.to_dict('records')
            for i in range(len(res_list)):
                for j in range(i + 1, len(res_list)):
                    r1, r2 = res_list[i], res_list[j]
                    if pd.notnull(r1['start']) and pd.notnull(r2['start']):
                        if (r1['start'] < r2['koniec']) and (r2['start'] < r1['koniec']):
                            conflicts.append(f"🔴 **{p}**: Kolizja '{r1['event']}' vs '{r2['event']}'")

        if conflicts:
            st.error("### ❌ BLOKADA ZAPISU - KOLIZJE DAT!")
            for c in conflicts:
                st.write(c)
        else:
            # Formatowanie do zapisu
            save_df = check_df.copy()
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = save_df['Start'].dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = save_df['Koniec'].dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.success("✅ Dane zapisane w Google Sheets!")
            st.rerun()
