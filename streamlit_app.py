import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. LOGOWANIE I KONFIGURACJA
# -----------------------------------------------------------------------------
st.set_page_config(page_title="SQM LOGISTICS", layout="wide")

def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #1e293b;'>SQM LOGISTICS | FLOTA</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Hasło dostępu:", type="password")
        if pwd == "SQM2026":
            st.session_state["password_correct"] = True
            st.rerun()
        return False
    return True

if not check_password():
    st.stop()

# -----------------------------------------------------------------------------
# 2. ZASOBY I STYLE
# -----------------------------------------------------------------------------
RESOURCES = {
    "🚛 CIĘŻAROWE": ["31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS", "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa", "SPEDYCJA", "AUTO RENTAL"],
    "🚐 BUSY": ["25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"],
    "🚗 OSOBOWE": ["01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723", "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek", "05 – Dacia Duster – WH7083A B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N", "FORD Transit Connect PY54635", "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", "Chrysler Pacifica PY04266 - MBanasiak", "Seat Ateca WZ445HU Dynasiuk", "Seat Ateca WZ446HU- PM"],
    "🏠 NOCLEGI": ["MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"]
}
CLEAN_LIST = [a for sub in RESOURCES.values() for a in sub]
ASSET_TO_ICON = {a: cat[0] for cat, assets in RESOURCES.items() for a in assets}

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .header { background: #0f172a; color: white; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; }
    [data-testid="stDataEditor"] div { font-size: 15px !important; }
    .conflict { background: #fee2e2; border: 2px solid #ef4444; padding: 10px; border-radius: 8px; color: #b91c1c; margin: 10px 0; }
    </style>
    <div class="header"><h1>SQM LOGISTICS v27.0</h1><p>Full Fleet Control & Collision Guard</p></div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. OBSŁUGA DANYCH
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        df = conn.read(ttl="0s")
        expected = ['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka']
        df.columns = [str(c).strip().lower() for c in df.columns]
        for c in expected:
            if c not in df.columns: df[c] = ""
        df['start'] = pd.to_datetime(df['start'], errors='coerce')
        df['koniec'] = pd.to_datetime(df['koniec'], errors='coerce')
        return df[expected].dropna(subset=['pojazd']).fillna("")
    except:
        return pd.DataFrame(columns=['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka'])

if "main_df" not in st.session_state:
    st.session_state.main_df = get_data()

# -----------------------------------------------------------------------------
# 4. FUNKCJA WYKRESU GANTTA
# -----------------------------------------------------------------------------
def draw_gantt(df_plot, labels, s_date, e_date):
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=labels, x=[None]*len(labels), showlegend=False))
    
    clean = df_plot[df_plot['start'].notnull()].copy()
    if not clean.empty:
        clean['y_label'] = clean['pojazd'].apply(lambda x: f"{ASSET_TO_ICON.get(x, '•')} {x}")
        for ev, group in clean.groupby('event'):
            dur = (group['koniec'] - group['start']).dt.total_seconds() * 1000
            fig.add_trace(go.Bar(
                y=group['y_label'], x=dur, base=group['start'],
                orientation='h', name=str(ev), text=str(ev),
                textposition='inside', marker=dict(line=dict(width=1, color='white'))
            ))
    
    fig.update_layout(
        height=len(labels)*60 + 100, template="plotly_white", showlegend=False,
        xaxis=dict(type='date', range=[s_date, e_date], side='top', dtick="D1", tickformat="%d\n%b"),
        yaxis=dict(categoryorder='array', categoryarray=labels[::-1]),
        margin=dict(l=10, r=10, t=40, b=10)
    )
    fig.add_vline(x=datetime.now().timestamp()*1000, line_width=2, line_color="red")
    return fig

# -----------------------------------------------------------------------------
# 5. GŁÓWNY INTERFEJS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("WIDOK")
    today = datetime.now()
    v_range = st.date_input("ZAKRES DAT:", value=(today - timedelta(days=2), today + timedelta(days=14)))
    if st.button("🔄 ODSWIEŻ DANE"):
        st.session_state.main_df = get_data()
        st.rerun()

s_view, e_view = v_range if isinstance(v_range, tuple) and len(v_range) == 2 else (today, today+timedelta(days=7))

t1, t2 = st.tabs(["📊 PODGLĄD GRAFICZNY", "🔧 EDYCJA I PLANOWANIE"])

with t1:
    cat = st.radio("KATEGORIA:", list(RESOURCES.keys()), horizontal=True)
    grp = RESOURCES[cat]
    lbls = [f"{ASSET_TO_ICON[a]} {a}" for a in grp]
    df_v = st.session_state.main_df[st.session_state.main_df['pojazd'].isin(grp)]
    st.plotly_chart(draw_gantt(df_v, lbls, s_view, e_view), use_container_width=True)

with t2:
    c1, c2 = st.columns([3, 1])
    with c1:
        search = st.text_input("🔍 SZUKAJ (auto/projekt):", "").lower()
    with c2:
        csv = st.session_state.main_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 BACKUP CSV", csv, f"sqm_log_{datetime.now().strftime('%H%M')}.csv", use_container_width=True)

    # Filtracja do edycji
    if search:
        mask = st.session_state.main_df.astype(str).apply(lambda x: x.str.lower().str.contains(search).any(), axis=1)
        to_edit = st.session_state.main_df[mask]
    else:
        to_edit = st.session_state.main_df

    edited = st.data_editor(
        to_edit, num_rows="dynamic", use_container_width=True, height=500,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Pojazd", options=CLEAN_LIST, required=True),
            "event": st.column_config.TextColumn("Projekt"),
            "start": st.column_config.DateColumn("Start"),
            "koniec": st.column_config.DateColumn("Koniec"),
            "kierowca": st.column_config.TextColumn("Kierowca"),
            "notatka": st.column_config.TextColumn("Notatki")
        }
    )

    # --- KONTROLA KOLIZJI I ZAPIS ---
    full_db = get_data()
    if search:
        m_others = ~full_db.astype(str).apply(lambda x: x.str.lower().str.contains(search).any(), axis=1)
        others = full_db[m_others]
    else:
        others = pd.DataFrame(columns=full_db.columns)

    final_db = pd.concat([others, edited], ignore_index=True).dropna(subset=['pojazd'])
    
    # Sprawdzanie kolizji
    check = final_db.copy()
    check['start'] = pd.to_datetime(check['start'], errors='coerce')
    check['koniec'] = pd.to_datetime(check['koniec'], errors='coerce')
    check = check.dropna(subset=['start', 'koniec'])
    conflicts = []
    for a in check['pojazd'].unique():
        v = check[check['pojazd'] == a].sort_values('start')
        recs = v.to_dict('records')
        for i in range(len(recs)-1):
            for j in range(i+1, len(recs)):
                if recs[i]['start'] < recs[j]['koniec'] and recs[j]['start'] < recs[i]['koniec']:
                    conflicts.append(f"❌ {a}: {recs[i]['event']} ({recs[i]['start'].strftime('%d.%m')}) / {recs[j]['event']} ({recs[j]['start'].strftime('%d.%m')})")

    if conflicts:
        st.markdown('<div class="conflict">⚠️ KOLIZJA TERMINÓW:</div>', unsafe_allow_html=True)
        for c in conflicts: st.write(c)

    if st.button("💾 ZAPISZ DO GOOGLE SHEETS", type="primary", use_container_width=True):
        ready = final_db.copy()
        ready['start'] = pd.to_datetime(ready['start']).dt.strftime('%Y-%m-%d')
        ready['koniec'] = pd.to_datetime(ready['koniec']).dt.strftime('%Y-%m-%d')
        ready.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        conn.update(data=ready)
        st.success("Zsynchronizowano z Google Sheets!")
        st.session_state.main_df = get_data()
        st.rerun()
