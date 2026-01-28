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
# 2. KONFIGURACJA I STYLE (Powiększony edytor i scrollbar)
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
    /* Powiększenie czcionki w tabeli edycji */
    [data-testid="stDataEditor"] div { font-size: 18px !important; }
    ::-webkit-scrollbar { width: 18px !important; height: 18px !important; }
    ::-webkit-scrollbar-thumb { background: #2563eb; border-radius: 10px; }
    </style>
    <div class="sqm-header">
        <h1 style="margin:0; font-size: 3.5rem; letter-spacing: -3px; line-height: 1;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.8; font-size: 1.2rem;">Fleet Manager v16.0 (High Visibility Mode)</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. ZASOBY I MAPOWANIE
# -----------------------------------------------------------------------------
RESOURCES = {
    "🚛 CIĘŻAROWE": ["31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS", "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa", "SPEDYCJA", "AUTO RENTAL"],
    "🚐 BUSY": ["25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"],
    "🚗 OSOBOWE": ["01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723", "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek", "05 – Dacia Duster – WH7083A B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N", "FORD Transit Connect PY54635", "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", "Chrysler Pacifica PY04266 - MBanasiak", "Seat Ateca WZ445HU Dynasiuk", "Seat Ateca WZ446HU- PM"],
    "🏠 NOCLEGI": ["MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"]
}

ALL_ASSETS_ORDERED = []
CATEGORY_BREAKS = {}
ASSET_TO_CAT = {}
current_pos = 0

for cat, assets in RESOURCES.items():
    CATEGORY_BREAKS[cat] = current_pos
    for a in assets:
        prefix = cat[0]
        label = f"{prefix} {a}"
        ALL_ASSETS_ORDERED.append(label)
        ASSET_TO_CAT[a] = cat
    current_pos += len(assets)

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        raw = conn.read(ttl="0s")
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        raw = raw.dropna(subset=['pojazd'])
        return raw.sort_values('start', ascending=False).fillna("")
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
    view_range = st.date_input("ZAKRES KALENDARZA:", value=(today - timedelta(days=2), today + timedelta(days=21)))
    if st.button("🔄 ODŚWIEŻ DANE"):
        st.session_state.main_df = get_data()
        st.rerun()

start_v, end_v = view_range if isinstance(view_range, tuple) and len(view_range) == 2 else (today - timedelta(days=2), today + timedelta(days=21))

# -----------------------------------------------------------------------------
# FUNKCJA WYKRESU (ZWIĘKSZONA CZCIONKA)
# -----------------------------------------------------------------------------
def draw_categorized_gantt(df_to_plot, assets_to_list, height=600):
    fig = go.Figure()
    
    # Separatory
    for cat, start_idx in CATEGORY_BREAKS.items():
        fig.add_hline(y=len(ALL_ASSETS_ORDERED) - start_idx - 0.5, 
                      line_width=2, line_dash="dash", line_color="#94a3b8")

    fig.add_trace(go.Scatter(y=assets_to_list, x=[None]*len(assets_to_list), showlegend=False))
    
    clean_plot = df_to_plot[df_to_plot['start'] != ""].copy()
    if not clean_plot.empty:
        clean_plot['y_label'] = clean_plot['pojazd'].apply(lambda x: f"{ASSET_TO_CAT[x][0]} {x}")
        
        for ev, group in clean_plot.groupby('event'):
            dur = (group['koniec'] - group['start']).dt.total_seconds() * 1000
            fig.add_trace(go.Bar(
                y=group['y_label'], x=dur, base=group['start'],
                orientation='h', name=ev, text=group['event'],
                textposition='inside', insidetextanchor='start',
                # Zwiększona czcionka wewnątrz pasków
                textfont=dict(size=14, color='white', family="Inter, sans-serif"),
                hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>"
            ))
    
    fig.update_layout(
        barmode='overlay', height=height, showlegend=False, template="plotly_white",
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis=dict(
            type='date', range=[start_v, end_v], side='top', 
            tickformat="%d\n%b", 
            tickfont=dict(size=16, weight='bold', color="#0f172a"), # Powiększone daty
            showgrid=True, gridcolor='rgba(0,0,0,0.1)', dtick="D1"
        ),
        yaxis=dict(
            categoryorder='array', categoryarray=assets_to_list[::-1], 
            showgrid=True, gridcolor='rgba(0,0,0,0.05)', 
            tickfont=dict(size=15, weight='bold', color="#1e293b") # Powiększone nazwy aut
        )
    )
    fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
    return fig

# -----------------------------------------------------------------------------
# 5. NAWIGACJA
# -----------------------------------------------------------------------------
tabs = list(RESOURCES.keys()) + ["🔧 EDYCJA I PLANOWANIE"]
active_tab = st.radio("MENU:", tabs, horizontal=True)
st.divider()

if active_tab in RESOURCES:
    prefix = active_tab[0]
    group_labels = [f"{prefix} {a}" for a in RESOURCES[active_tab]]
    df_filtered = st.session_state.main_df[st.session_state.main_df['pojazd'].isin(RESOURCES[active_tab])]
    st.plotly_chart(draw_categorized_gantt(df_filtered, group_labels, height=max(500, len(group_labels)*55)), use_container_width=True)

# -----------------------------------------------------------------------------
# 6. PANEL EDYCJI (PODGLĄD + TABELA)
# -----------------------------------------------------------------------------
else:
    st.subheader("Planowanie i Edycja")
    search_q = st.text_input("🔍 FILTRUJ ZASOBY:", "").lower()
    
    display_df = st.session_state.main_df.copy()
    if search_q:
        mask = display_df.astype(str).apply(lambda x: x.str.lower().str.contains(search_q).any(), axis=1)
        display_df = display_df[mask]
        current_assets_labels = [label for label in ALL_ASSETS_ORDERED if search_q in label.lower()]
    else:
        current_assets_labels = ALL_ASSETS_ORDERED

    with st.expander("📊 PODGLĄD GRAFICZNY (WIĘKSZA CZCIONKA)", expanded=True):
        st.plotly_chart(draw_categorized_gantt(display_df, current_assets_labels, height=max(400, len(current_assets_labels)*45)), use_container_width=True)

    st.markdown("### ✏️ TABELA EDYCJI")
    CLEAN_ASSETS_LIST = [a for sub in RESOURCES.values() for a in sub]
    
    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=500,
        key="editor_v16",
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 ZASÓB", options=CLEAN_ASSETS_LIST, width=250, required=True),
            "event": st.column_config.TextColumn("📋 PROJEKT", width=150),
            "start": st.column_config.DateColumn("📅 OD", width=110),
            "koniec": st.column_config.DateColumn("🏁 DO", width=110),
            "kierowca": st.column_config.TextColumn("👤 KIER.", width=100),
            "notatka": st.column_config.TextColumn("📝 NOTATKI", width=400)
        }
    )

    if st.button("💾 ZAPISZ I WERYFIKUJ", use_container_width=True):
        valid_data = edited_df[edited_df['event'] != ""].copy()
        valid_data['start'] = pd.to_datetime(valid_data['start'])
        valid_data['koniec'] = pd.to_datetime(valid_data['koniec'])
        
        conflicts = []
        for p in valid_data['pojazd'].unique():
            v_res = valid_data[valid_data['pojazd'] == p].sort_values('start')
            reks = v_res.to_dict('records')
            for i in range(len(reks)-1):
                if reks[i]['koniec'] > reks[i+1]['start']:
                    conflicts.append(f"❌ {p}: '{reks[i]['event']}' nakłada się na '{reks[i+1]['event']}'")

        if conflicts:
            for c in conflicts: st.error(c)
        else:
            save_df = valid_data.copy()
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = save_df['Start'].dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = save_df['Koniec'].dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.session_state.main_df = get_data()
            st.success("Zapisano pomyślnie!")
            st.rerun()
