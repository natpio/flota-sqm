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
# 2. KONFIGURACJA I STYLE
# -----------------------------------------------------------------------------
st.set_page_config(page_title="SQM LOGISTICS", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;900&display=swap');
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    .sqm-header {
        background: #0f172a; padding: 1.5rem; border-radius: 12px; color: white;
        margin-bottom: 1.5rem; border-left: 8px solid #2563eb;
    }
    [data-testid="stDataEditor"] div { font-size: 16px !important; }
    .conflict-box {
        background-color: #fee2e2; border: 2px solid #ef4444; padding: 1rem;
        border-radius: 8px; color: #b91c1c; margin-top: 1rem; margin-bottom: 1rem;
    }
    .stButton>button { border-radius: 8px; font-weight: bold; height: 3rem; }
    </style>
    <div class="sqm-header">
        <h1 style="margin:0; font-size: 2.8rem; letter-spacing: -2px;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.7; font-size: 1rem;">Fleet Management v23.0 | System Kontroli Kolizji</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. ZASOBY I DANE
# -----------------------------------------------------------------------------
RESOURCES = {
    "🚛 CIĘŻAROWE": ["31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS", "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa", "SPEDYCJA", "AUTO RENTAL"],
    "🚐 BUSY": ["25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"],
    "🚗 OSOBOWE": ["01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723", "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek", "05 – Dacia Duster – WH7083A B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N", "FORD Transit Connect PY54635", "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", "Chrysler Pacifica PY04266 - MBanasiak", "Seat Ateca WZ445HU Dynasiuk", "Seat Ateca WZ446HU- PM"],
    "🏠 NOCLEGI": ["MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"]
}

ASSET_TO_CAT_ICON = {a: cat[0] for cat, assets in RESOURCES.items() for a in assets}
ALL_ASSETS_ORDERED = [f"{cat[0]} {a}" for cat, assets in RESOURCES.items() for a in assets]
CLEAN_LIST = [a for sub in RESOURCES.values() for a in sub]

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        raw = conn.read(ttl="0s")
        if raw.empty: return pd.DataFrame(columns=['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka'])
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        return raw.dropna(subset=['pojazd']).fillna("")
    except:
        return pd.DataFrame(columns=['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka'])

if "main_df" not in st.session_state:
    st.session_state.main_df = get_data()

# -----------------------------------------------------------------------------
# 4. FUNKCJA ANALIZY KOLIZJI
# -----------------------------------------------------------------------------
def get_collisions(df):
    conflicts = []
    # Kopia do analizy z poprawnymi formatami
    check_df = df.copy()
    check_df['start'] = pd.to_datetime(check_df['start'], errors='coerce')
    check_df['koniec'] = pd.to_datetime(check_df['koniec'], errors='coerce')
    check_df = check_df.dropna(subset=['start', 'koniec'])
    
    for auto in check_df['pojazd'].unique():
        v_df = check_df[check_df['pojazd'] == auto].sort_values('start')
        if len(v_df) < 2: continue
        
        rows = v_df.to_dict('records')
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                r1, r2 = rows[i], rows[j]
                # Logika nachodzenia na siebie dat
                if r1['start'] < r2['koniec'] and r2['start'] < r1['koniec']:
                    conflicts.append({
                        "auto": auto,
                        "p1": r1['event'], "p2": r2['event'],
                        "k1": r1['kierowca'], "k2": r2['kierowca'],
                        "d1": f"{r1['start'].strftime('%d.%m')} - {r1['koniec'].strftime('%d.%m')}",
                        "d2": f"{r2['start'].strftime('%d.%m')} - {r2['koniec'].strftime('%d.%m')}"
                    })
    return conflicts

# -----------------------------------------------------------------------------
# 5. SIDEBAR I KALENDARZ
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("LOGISTYKA")
    today = datetime.now()
    view_range = st.date_input("ZAKRES WIDOKU:", value=(today - timedelta(days=2), today + timedelta(days=16)))
    if st.button("🔄 POBIERZ Z ARKUSZA"):
        st.session_state.main_df = get_data()
        st.rerun()
    st.divider()
    st.write("Wersja: 23.0 (Collision Guard)")

start_v, end_v = view_range if isinstance(view_range, tuple) and len(view_range) == 2 else (today - timedelta(days=2), today + timedelta(days=16))

def draw_gantt(df_to_plot, assets_to_list, height=600):
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=assets_to_list, x=[None]*len(assets_to_list), showlegend=False))
    
    plot_data = df_to_plot[df_to_plot['start'].notnull()].copy()
    if not plot_data.empty:
        plot_data['y_label'] = plot_data['pojazd'].apply(lambda x: f"{ASSET_TO_CAT_ICON.get(x, '•')} {x}")
        for ev, group in plot_data.groupby('event'):
            dur = (group['koniec'] - group['start']).dt.total_seconds() * 1000
            fig.add_trace(go.Bar(
                y=group['y_label'], x=dur, base=group['start'],
                orientation='h', name=ev, text=group['event'],
                textposition='inside', insidetextanchor='start',
                textfont=dict(size=14, color='white'),
                hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>"
            ))
    
    fig.update_layout(
        height=height, template="plotly_white", margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(type='date', range=[start_v, end_v], side='top', tickformat="%d\n%b", dtick="D1", gridcolor='#e2e8f0'),
        yaxis=dict(categoryorder='array', categoryarray=assets_to_list[::-1], automargin=True, gridcolor='#f1f5f9'),
        showlegend=False
    )
    fig.add_vline(x=today.timestamp()*1000, line_width=3, line_color="red")
    return fig

# -----------------------------------------------------------------------------
# 6. OBSŁUGA ZAKŁADEK
# -----------------------------------------------------------------------------
tabs = list(RESOURCES.keys()) + ["🔧 EDYCJA I PLANOWANIE"]
active_tab = st.radio("WYBIERZ WIDOK:", tabs, horizontal=True)
st.divider()

if active_tab in RESOURCES:
    group_assets = RESOURCES[active_tab]
    labels = [f"{active_tab[0]} {a}" for a in group_assets]
    df_f = st.session_state.main_df[st.session_state.main_df['pojazd'].isin(group_assets)]
    st.plotly_chart(draw_gantt(df_f, labels, height=len(labels)*65 + 100), use_container_width=True)

else:
    st.subheader("Panel Edycji z Kontrolą Dubli")
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        search_q = st.text_input("🔍 FILTRUJ POJAZDY (edytuj swobodnie):", "").lower()
    with col_b:
        # BACKUP CSV
        csv = st.session_state.main_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 POBIERZ KOPIĘ (CSV)", data=csv, file_name=f"SQM_BACKUP_{datetime.now().strftime('%H%M')}.csv", use_container_width=True)

    # Przygotowanie danych do edycji
    if search_q:
        mask = st.session_state.main_df.astype(str).apply(lambda x: x.str.lower().str.contains(search_q).any(), axis=1)
        display_df = st.session_state.main_df[mask]
    else:
        display_df = st.session_state.main_df

    # Edytor danych
    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=500,
        key="editor_final_v23",
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 POJAZD", options=CLEAN_LIST, required=True),
            "start": st.column_config.DateColumn("📅 OD"),
            "koniec": st.column_config.DateColumn("🏁 DO"),
        }
    )

    # --- ANALIZA KOLIZJI ---
    # Musimy sprawdzić nową edycję na tle całej bazy (również tej ukrytej)
    fresh_db = get_data()
    if search_q:
        mask_keep = ~fresh_db.astype(str).apply(lambda x: x.str.lower().str.contains(search_q).any(), axis=1)
        static_data = fresh_db[mask_keep]
    else:
        static_data = pd.DataFrame(columns=fresh_db.columns)
    
    # Łączymy wszystko w jeden zbiór do testu kolizji
    full_to_check = pd.concat([static_data, edited_df], ignore_index=True)
    full_to_check = full_to_check[full_to_check['pojazd'] != ""]
    
    conflicts = get_collisions(full_to_check)

    if conflicts:
        st.markdown('<div class="conflict-box">', unsafe_allow_html=True)
        st.error(f"⚠️ ZNALEZIONO {len(conflicts)} KOLIZJI!")
        for c in conflicts:
            st.write(f"❌ **{c['auto']}**: Projekt **{c['p1']}** ({c['d1']}) pokrywa się z **{c['p2']}** ({c['d2']})")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ZAPIS ---
    if st.button("💾 ZAPISZ WSZYSTKO W ARKUSZU GOOGLE", use_container_width=True, type="primary"):
        # Przygotowanie do wysyłki
        save_df = full_to_check.copy()
        save_df['start'] = pd.to_datetime(save_df['start']).dt.strftime('%Y-%m-%d')
        save_df['koniec'] = pd.to_datetime(save_df['koniec']).dt.strftime('%Y-%m-%d')
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        
        conn.update(data=save_df)
        st.session_state.main_df = get_data()
        st.success("Dane zapisane pomyślnie. Kolizje zostały sprawdzone.")
        st.rerun()
