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
        if st.session_state["password"] == "KOMORNIKIsqm":
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
    </style>
    <div class="sqm-header">
        <h1 style="margin:0; font-size: 2.8rem; letter-spacing: -2px;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.7; font-size: 1rem;">Fleet Management v17.0</p>
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

# Budowa mapy etykiet dla lepszego wyrównania
ALL_ASSETS_ORDERED = []
ASSET_TO_CAT_ICON = {}
for cat, assets in RESOURCES.items():
    icon = cat[0]
    for a in assets:
        label = f"{icon} {a}"
        ALL_ASSETS_ORDERED.append(label)
        ASSET_TO_CAT_ICON[a] = icon

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        raw = conn.read(ttl="0s")
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        return raw.dropna(subset=['pojazd']).fillna("")
    except:
        return pd.DataFrame(columns=['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka'])

if "main_df" not in st.session_state:
    st.session_state.main_df = get_data()

# -----------------------------------------------------------------------------
# 4. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("PLANOWANIE")
    today = datetime.now()
    view_range = st.date_input("ZAKRES CZASU:", value=(today - timedelta(days=2), today + timedelta(days=16)))
    if st.button("🔄 ODŚWIEŻ"):
        st.session_state.main_df = get_data()
        st.rerun()

start_v, end_v = view_range if isinstance(view_range, tuple) and len(view_range) == 2 else (today - timedelta(days=2), today + timedelta(days=16))

# -----------------------------------------------------------------------------
# 5. NOWA FUNKCJA WYKRESU (Poprawiona czytelność)
# -----------------------------------------------------------------------------
def draw_precision_gantt(df_to_plot, assets_to_list, height=600):
    fig = go.Figure()
    
    # Podkładka dla wszystkich aut - zapewnia idealne wyrównanie napisów na osi Y
    fig.add_trace(go.Scatter(
        y=assets_to_list, x=[None]*len(assets_to_list), 
        showlegend=False, cliponaxis=False
    ))

    # Paski zadań
    clean_plot = df_to_plot[df_to_plot['start'] != ""].copy()
    if not clean_plot.empty:
        # Konwersja nazw pojazdów na etykiety z ikonami
        clean_plot['y_label'] = clean_plot['pojazd'].apply(lambda x: f"{ASSET_TO_CAT_ICON.get(x, '•')} {x}")
        
        for ev, group in clean_plot.groupby('event'):
            dur = (group['koniec'] - group['start']).dt.total_seconds() * 1000
            fig.add_trace(go.Bar(
                y=group['y_label'], 
                x=dur, 
                base=group['start'],
                orientation='h', 
                name=ev, 
                text=group['event'],
                textposition='inside', 
                insidetextanchor='start',
                # Zwiększona czcionka wewnątrz paska
                textfont=dict(size=14, color='white', family="Inter"),
                marker=dict(line=dict(width=1, color='rgba(255,255,255,0.3)')),
                hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>"
            ))
    
    fig.update_layout(
        barmode='overlay', 
        height=height, 
        showlegend=False, 
        template="plotly_white",
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(
            type='date', 
            range=[start_v, end_v], 
            side='top', 
            tickformat="%d\n%b", 
            tickfont=dict(size=15, weight='bold', color="#1e293b"),
            showgrid=True, 
            gridcolor='#cbd5e1', # Wyraźniejsza siatka pionowa
            gridwidth=1,
            dtick="D1"
        ),
        yaxis=dict(
            categoryorder='array', 
            categoryarray=assets_to_list[::-1], 
            automargin=True, # Zapobiega ucinaniu długich nazw aut
            tickfont=dict(size=16, weight='bold', color="#0f172a"),
            fixedrange=True,
            showgrid=True,
            gridcolor='#f1f5f9'
        )
    )
    # Dzisiejsza data - czerwona gruba linia
    fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
    
    return fig

# -----------------------------------------------------------------------------
# 6. WIDOKI
# -----------------------------------------------------------------------------
tabs = list(RESOURCES.keys()) + ["🔧 EDYCJA I PLANOWANIE"]
active_tab = st.radio("MENU:", tabs, horizontal=True)
st.divider()

if active_tab in RESOURCES:
    group_assets = RESOURCES[active_tab]
    icon = active_tab[0]
    labels = [f"{icon} {a}" for a in group_assets]
    df_f = st.session_state.main_df[st.session_state.main_df['pojazd'].isin(group_assets)]
    # Zwiększony mnożnik wysokości: 65px na auto
    st.plotly_chart(draw_precision_gantt(df_f, labels, height=len(labels)*65 + 100), use_container_width=True)

else:
    st.subheader("Planowanie i Edycja")
    search_q = st.text_input("🔍 SZUKAJ POJAZDU LUB PROJEKTU:", "").lower()
    
    # Filtrowanie
    display_df = st.session_state.main_df.copy()
    if search_q:
        mask = display_df.astype(str).apply(lambda x: x.str.lower().str.contains(search_q).any(), axis=1)
        display_df = display_df[mask]
        current_labels = [l for l in ALL_ASSETS_ORDERED if search_q in l.lower()]
    else:
        current_labels = ALL_ASSETS_ORDERED

    with st.expander("📊 PODGLĄD GRAFIZNY (WYSOKA CZYTELNOŚĆ)", expanded=True):
        st.plotly_chart(draw_precision_gantt(display_df, current_labels, height=len(current_labels)*55 + 150), use_container_width=True)

    st.markdown("### ✏️ TABELA DANYCH")
    CLEAN_LIST = [a for sub in RESOURCES.values() for a in sub]
    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=500,
        key="editor_v17",
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 ZASÓB", options=CLEAN_LIST, width=280, required=True),
            "event": st.column_config.TextColumn("📋 PROJEKT", width=180),
            "start": st.column_config.DateColumn("📅 OD", width=120),
            "koniec": st.column_config.DateColumn("🏁 DO", width=120),
            "kierowca": st.column_config.TextColumn("👤 KIER.", width=120),
            "notatka": st.column_config.TextColumn("📝 NOTATKI", width=400)
        }
    )

    if st.button("💾 ZAPISZ ZMIANY", use_container_width=True):
        # ... (Logika zapisu pozostaje niezmienna, jest sprawdzona)
        valid_data = edited_df[edited_df['event'] != ""].copy()
        valid_data['start'] = pd.to_datetime(valid_data['start'])
        valid_data['koniec'] = pd.to_datetime(valid_data['koniec'])
        save_df = valid_data.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = save_df['Start'].dt.strftime('%Y-%m-%d')
        save_df['Koniec'] = save_df['Koniec'].dt.strftime('%Y-%m-%d')
        conn.update(data=save_df)
        st.session_state.main_df = get_data()
        st.success("Zapisano!")
        st.rerun()
