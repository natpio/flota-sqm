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
# 2. STYLE CSS I KONFIGURACJA
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
    ::-webkit-scrollbar { width: 22px !important; height: 22px !important; }
    ::-webkit-scrollbar-track { background: #cbd5e1 !important; }
    ::-webkit-scrollbar-thumb { background: #2563eb !important; border-radius: 10px; border: 4px solid #cbd5e1 !important; }
    </style>
    <div class="sqm-header">
        <h1 style="margin:0; font-size: 3.5rem; letter-spacing: -3px; line-height: 1;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.8; font-size: 1.2rem;">Fleet Manager v13.0 (Grid View & Stability)</p>
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
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        raw = raw.dropna(subset=['pojazd'])
        return raw.fillna("")
    except:
        return pd.DataFrame(columns=['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka'])

if "main_df" not in st.session_state:
    st.session_state.main_df = get_data()

# -----------------------------------------------------------------------------
# 4. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ USTAWIENIA")
    today = datetime.now()
    view_range = st.date_input("ZAKRES WIDOKU:", value=(today - timedelta(days=2), today + timedelta(days=21)))
    
    if st.button("🔄 ODŚWIEŻ Z ARKUSZA"):
        st.session_state.main_df = get_data()
        st.rerun()

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
tabs = list(RESOURCES.keys()) + ["🔧 EDYCJA / ARKUSZ"]
active_tab = st.radio("MENU:", tabs, horizontal=True)
st.divider()

# -----------------------------------------------------------------------------
# 6. WYKRES (Gantt z pionową siatką i "kratką")
# -----------------------------------------------------------------------------
if active_tab in RESOURCES:
    assets_to_show = RESOURCES[active_tab]
    plot_df = st.session_state.main_df[st.session_state.main_df['pojazd'].isin(assets_to_show)].copy()
    plot_df = plot_df[plot_df['start'] != ""].copy()
    
    fig = go.Figure()
    
    # Dodanie wszystkich aut na oś Y (nawet tych bez zadań)
    fig.add_trace(go.Scatter(y=assets_to_show, x=[None]*len(assets_to_show), showlegend=False))

    if not plot_df.empty:
        for event_name, group in plot_df.groupby('event'):
            widths = (group['koniec'] - group['start']).dt.total_seconds() * 1000
            fig.add_trace(go.Bar(
                y=group['pojazd'], x=widths, base=group['start'],
                orientation='h', name=event_name, text=group['event'],
                textposition='inside', insidetextanchor='start',
                textfont=dict(size=14, color='white'),
                constraintext='none',
                hovertemplate="<b>%{y}</b><br>Projekt: %{text}<extra></extra>"
            ))

    fig.update_layout(
        barmode='overlay', height=max(500, len(assets_to_show)*60 + 100),
        showlegend=False, template="plotly_white", margin=dict(l=10, r=20, t=50, b=10),
        xaxis=dict(
            type='date', range=[start_v, end_v], side='top', 
            tickformat="%d\n%b", tickfont=dict(size=14, weight='bold'),
            showgrid=True, gridcolor='rgba(0,0,0,0.1)', gridwidth=1, # Pionowe linie
            dtick="D1" # Linia co każdy 1 dzień
        ),
        yaxis=dict(
            categoryorder='array', categoryarray=assets_to_show[::-1], 
            tickfont=dict(size=14, weight='bold'),
            showgrid=True, gridcolor='rgba(0,0,0,0.05)' # Poziome linie
        )
    )
    # Linia "DZIŚ"
    fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# -----------------------------------------------------------------------------
# 7. PANEL EDYCJI
# -----------------------------------------------------------------------------
else:
    st.subheader("Główny Panel Edycji")
    search_q = st.text_input("🔍 WYSZUKAJ (Pojazd, Projekt, Kierowca):", "").lower()
    
    display_df = st.session_state.main_df.copy()
    if search_q:
        mask = display_df.astype(str).apply(lambda x: x.str.lower().str.contains(search_q).any(), axis=1)
        display_df = display_df[mask]

    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=800,
        key="editor_v13_stable",
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 ZASÓB", options=ALL_ASSETS, width=300, required=True),
            "event": st.column_config.TextColumn("📋 PROJEKT", width=180),
            "start": st.column_config.DateColumn("📅 START", width=130),
            "koniec": st.column_config.DateColumn("🏁 KONIEC", width=130),
            "kierowca": st.column_config.TextColumn("👤 KIER.", width=120),
            "notatka": st.column_config.TextColumn("📝 NOTATKI", width=500)
        }
    )

    if st.button("💾 ZAPISZ ZMIANY I WERYFIKUJ KOLIZJE", use_container_width=True):
        valid_data = edited_df[edited_df['event'] != ""].copy()
        valid_data['start'] = pd.to_datetime(valid_data['start'])
        valid_data['koniec'] = pd.to_datetime(valid_data['koniec'])
        
        conflicts = []
        for p in valid_data['pojazd'].unique():
            v_res = valid_data[valid_data['pojazd'] == p].sort_values('start')
            res_list = v_res.to_dict('records')
            for i in range(len(res_list)-1):
                if res_list[i]['koniec'] > res_list[i+1]['start']:
                    conflicts.append(f"❌ {p}: '{res_list[i]['event']}' nakłada się na '{res_list[i+1]['event']}'")

        if conflicts:
            for c in conflicts: st.error(c)
        else:
            save_df = valid_data.copy()
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = save_df['Start'].dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = save_df['Koniec'].dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.session_state.main_df = get_data()
            st.success("Zapisano!")
            st.rerun()
