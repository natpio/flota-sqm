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
    .stApp { background-color: #f1f5f9; font-family: 'Inter', sans-serif; }
    .sqm-header {
        background: #0f172a; padding: 1.5rem; border-radius: 15px; color: white;
        margin-bottom: 2rem; border-bottom: 8px solid #2563eb;
    }
    [data-testid="stDataEditor"] div { font-size: 16px !important; }
    .st-emotion-cache-1kyx60r { background-color: #ffffff; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
    ::-webkit-scrollbar { width: 18px; height: 18px; }
    ::-webkit-scrollbar-thumb { background: #2563eb; border-radius: 10px; border: 4px solid #f1f5f9; }
    </style>
    <div class="sqm-header">
        <h1 style="margin:0; font-size: 3rem; letter-spacing: -2px;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.7;">Fleet & Transport Management System v11.0</p>
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
ALL_ASSETS = [item for sublist in RESOURCES.values() for item in sublist]

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        data.columns = [str(c).strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.dropna(subset=['pojazd']).sort_values('start', ascending=False)
    except:
        return pd.DataFrame(columns=['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka'])

if "fleet_db" not in st.session_state:
    st.session_state.fleet_db = load_data()

# -----------------------------------------------------------------------------
# 4. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ FILTRY WIDOKU")
    t = datetime.now()
    v_range = st.date_input("ZAKRES KALENDARZA:", value=(t - timedelta(days=2), t + timedelta(days=30)))
    
    st.divider()
    if st.button("🔄 POBIERZ ŚWIEŻE DANE", use_container_width=True):
        st.session_state.fleet_db = load_data()
        st.rerun()
    
    if st.button("🚪 WYLOGUJ", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# -----------------------------------------------------------------------------
# 5. PANEL STATYSTYK (NOWOŚĆ)
# -----------------------------------------------------------------------------
today_events = st.session_state.fleet_db[
    (st.session_state.fleet_db['start'].dt.date <= t.date()) & 
    (st.session_state.fleet_db['koniec'].dt.date >= t.date())
]
c1, c2, c3 = st.columns(3)
c1.metric("AUTA W TRASIE (DZIŚ)", len(today_events['pojazd'].unique()))
c2.metric("AKTYWNE PROJEKTY", len(today_events['event'].unique()))
c3.metric("DOSTĘPNE ZASOBY", len(ALL_ASSETS) - len(today_events['pojazd'].unique()))

# -----------------------------------------------------------------------------
# 6. NAWIGACJA I WYKRESY
# -----------------------------------------------------------------------------
tabs = list(RESOURCES.keys()) + ["🔧 PANEL EDYCJI"]
sel_tab = st.radio("NAWIGACJA:", tabs, horizontal=True)

if sel_tab in RESOURCES:
    group = RESOURCES[sel_tab]
    df_p = st.session_state.fleet_db[st.session_state.fleet_db['pojazd'].isin(group)].copy()
    df_p = df_p.dropna(subset=['start', 'koniec'])
    
    fig = go.Figure()
    for ev, g in df_p.groupby('event'):
        dur = (g['koniec'] - g['start']).dt.total_seconds() * 1000
        fig.add_trace(go.Bar(
            y=g['pojazd'], x=dur, base=g['start'],
            orientation='h', name=ev, text=g['event'],
            textposition='inside', insidetextanchor='start',
            textfont=dict(size=14, color='white'),
            constraintext='none',
            hovertemplate="<b>%{y}</b><br>Projekt: %{text}<extra></extra>"
        ))
    
    fig.update_layout(
        barmode='overlay', height=max(400, len(group)*55),
        margin=dict(l=10, r=10, t=40, b=10), template="plotly_white",
        xaxis=dict(type='date', range=v_range, side='top', tickformat="%d %b"),
        yaxis=dict(categoryorder='array', categoryarray=group[::-1]),
        showlegend=False
    )
    fig.add_vline(x=t.timestamp()*1000, line_width=3, line_color="red")
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 7. EDYCJA (PEŁNA FUNKCJONALNOŚĆ)
# -----------------------------------------------------------------------------
else:
    st.subheader("Centralna Baza Transportowa")
    sq = st.text_input("🔍 Wyszukaj (np. nr rejestracyjny, projekt, kierowca):", "").lower()
    
    d_edit = st.session_state.fleet_db.copy()
    if sq:
        d_edit = d_edit[d_edit.astype(str).apply(lambda x: x.str.lower().str.contains(sq).any(), axis=1)]

    st.caption("Sortuj klikając w nagłówki. Aby dodać nowy wpis, zjedź na sam dół.")
    
    res_edit = st.data_editor(
        d_edit,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=600,
        key="editor_v11",
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 POJAZD", options=ALL_ASSETS, width="medium", required=True),
            "event": st.column_config.TextColumn("📋 PROJEKT / CEL", width="medium"),
            "start": st.column_config.DateColumn("📅 OD", width="small"),
            "koniec": st.column_config.DateColumn("🏁 DO", width="small"),
            "kierowca": st.column_config.TextColumn("👤 KIEROWCA", width="small"),
            "notatka": st.column_config.TextColumn("📝 NOTATKI / SLOTY", width="large")
        }
    )

    if st.button("💾 ZAPISZ DO ARKUSZA I WERYFIKUJ", use_container_width=True):
        # Walidacja
        valid = res_edit.dropna(subset=['pojazd', 'event', 'start', 'koniec']).copy()
        valid['start'] = pd.to_datetime(valid['start'])
        valid['koniec'] = pd.to_datetime(valid['koniec'])
        
        conflicts = []
        for p in valid['pojazd'].unique():
            subset = valid[valid['pojazd'] == p].sort_values('start')
            reks = subset.to_dict('records')
            for i in range(len(reks)-1):
                if reks[i]['koniec'] > reks[i+1]['start']:
                    conflicts.append(f"❌ {p}: '{reks[i]['event']}' nakłada się na '{reks[i+1]['event']}'")
        
        if conflicts:
            for c in conflicts: st.error(c)
        else:
            save_df = valid.copy()
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = save_df['Start'].dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = save_df['Koniec'].dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.session_state.fleet_db = load_data()
            st.success("Zapisano pomyślnie!")
            st.rerun()
