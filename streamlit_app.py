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
# 2. DYNAMICZNA KONFIGURACJA I KOLORYSTYKA
# -----------------------------------------------------------------------------
st.set_page_config(page_title="SQM LOGISTICS", layout="wide", initial_sidebar_state="expanded")

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

with st.sidebar:
    st.header("WIDOK")
    theme_choice = st.toggle("TRYB CIEMNY", value=st.session_state.dark_mode)
    if theme_choice != st.session_state.dark_mode:
        st.session_state.dark_mode = theme_choice
        st.rerun()

# Ustalenie palety barw
if st.session_state.dark_mode:
    main_bg = "#0f172a"
    text_color = "#f8fafc"  # Jasna czcionka dla trybu ciemnego
    card_bg = "#1e293b"
    grid_color = "#334155"
    plotly_tmpl = "plotly_dark"
    conflict_box = "rgba(220, 38, 38, 0.3)"
else:
    main_bg = "#f8fafc"
    text_color = "#0f172a"  # Ciemna czcionka dla trybu jasnego
    card_bg = "#ffffff"
    grid_color = "#cbd5e1"
    plotly_tmpl = "plotly_white"
    conflict_box = "#fee2e2"

# Wstrzyknięcie stylów CSS z dynamicznymi kolorami czcionek
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;900&display=swap');
    
    .stApp {{ 
        background-color: {main_bg}; 
        color: {text_color} !important;
        font-family: 'Inter', sans-serif; 
    }}
    
    /* Wymuszenie koloru tekstu dla wszystkich nagłówków i paragrafów */
    h1, h2, h3, p, span, label, .stMarkdown {{
        color: {text_color} !important;
    }}

    .sqm-header {{
        background: #0f172a; 
        padding: 1.5rem; 
        border-radius: 12px; 
        color: white !important;
        margin-bottom: 1.5rem; 
        border-left: 8px solid #2563eb;
    }}
    .sqm-header h1, .sqm-header p {{ color: white !important; }}
    
    [data-testid="stDataEditor"] div {{ font-size: 16px !important; }}
    
    .conflict-box {{
        background-color: {conflict_box}; 
        border: 2px solid #ef4444; 
        padding: 1rem;
        border-radius: 8px; 
        color: #ef4444 !important; 
        margin-bottom: 1rem; 
        font-weight: bold;
    }}
    </style>
    
    <div class="sqm-header">
        <h1 style="margin:0; font-size: 2.8rem; letter-spacing: -2px;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.7; font-size: 1rem;">Fleet Management v32.0 (High Contrast UI)</p>
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
# 4. SIDEBAR - CZAS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("PARAMETRY")
    today = datetime.now()
    view_range = st.date_input("ZAKRES DAT:", value=(today - timedelta(days=2), today + timedelta(days=16)))
    if st.button("🔄 ODSWIEŻ DANE"):
        st.session_state.main_df = get_data()
        st.rerun()

start_v, end_v = view_range if isinstance(view_range, tuple) and len(view_range) == 2 else (today - timedelta(days=2), today + timedelta(days=16))

# -----------------------------------------------------------------------------
# 5. WYKRES GANTTA (DYNAMICZNY TEKST)
# -----------------------------------------------------------------------------
def draw_precision_gantt(df_to_plot, assets_to_list, height=600):
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=assets_to_list, x=[None]*len(assets_to_list), showlegend=False))

    clean_plot = df_to_plot[df_to_plot['start'].notnull()].copy()
    if not clean_plot.empty:
        clean_plot['y_label'] = clean_plot['pojazd'].apply(lambda x: f"{ASSET_TO_CAT_ICON.get(x, '•')} {x}")
        for ev, group in clean_plot.groupby('event'):
            dur = (group['koniec'] - group['start']).dt.total_seconds() * 1000
            fig.add_trace(go.Bar(
                y=group['y_label'], x=dur, base=group['start'],
                orientation='h', name=ev, text=group['event'],
                textposition='inside', insidetextanchor='start',
                textfont=dict(size=14, color='white'), # Tekst wewnątrz słupka zawsze biały dla kontrastu
                marker=dict(line=dict(width=1, color='rgba(255,255,255,0.3)')),
                hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>"
            ))
    
    fig.update_layout(
        barmode='overlay', height=height, showlegend=False, 
        template=plotly_tmpl,
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(
            type='date', range=[start_v, end_v], side='top', tickformat="%d\n%b", 
            tickfont=dict(size=15, weight='bold', color=text_color), 
            showgrid=True, gridcolor=grid_color, dtick="D1"
        ),
        yaxis=dict(
            categoryorder='array', categoryarray=assets_to_list[::-1], 
            automargin=True, 
            tickfont=dict(size=16, weight='bold', color=text_color), 
            fixedrange=True, showgrid=True, gridcolor=grid_color
        )
    )
    fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
    return fig

# -----------------------------------------------------------------------------
# 6. WIDOKI
# -----------------------------------------------------------------------------
tabs = list(RESOURCES.keys()) + ["🔧 EDYCJA I PLANOWANIE"]
active_tab = st.radio("WYBIERZ GRUPĘ:", tabs, horizontal=True)
st.divider()

if active_tab in RESOURCES:
    group_assets = RESOURCES[active_tab]
    icon = active_tab[0]
    labels = [f"{icon} {a}" for a in group_assets]
    df_f = st.session_state.main_df[st.session_state.main_df['pojazd'].isin(group_assets)]
    st.plotly_chart(draw_precision_gantt(df_f, labels, height=len(labels)*65 + 100), use_container_width=True)

else:
    st.subheader("Panel Administracyjny")
    search_q = st.text_input("🔍 SZUKAJ (Pojazd / Projekt / Kierowca):", "").lower()
    
    if search_q:
        mask = st.session_state.main_df.astype(str).apply(lambda x: x.str.lower().str.contains(search_q).any(), axis=1)
        display_df = st.session_state.main_df[mask].copy()
        current_labels = [f"{ASSET_TO_CAT_ICON.get(p, '•')} {p}" for p in display_df['pojazd'].unique()]
    else:
        display_df = st.session_state.main_df.copy()
        current_labels = ALL_ASSETS_ORDERED

    with st.expander("📊 PODGLĄD GRAFICZNY", expanded=True):
        if not display_df.empty:
            st.plotly_chart(draw_precision_gantt(display_df, current_labels, height=len(current_labels)*55 + 150), use_container_width=True)

    st.markdown("### ✏️ TABELA OPERACYJNA")
    CLEAN_LIST = [a for sub in RESOURCES.values() for a in sub]
    
    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=500,
        key="editor_v32",
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 ZASÓB", options=CLEAN_LIST, width=280, required=True),
            "event": st.column_config.TextColumn("📋 PROJEKT", width=180),
            "start": st.column_config.DateColumn("📅 OD", width=120),
            "koniec": st.column_config.DateColumn("🏁 DO", width=120),
            "kierowca": st.column_config.TextColumn("👤 KIER.", width=120),
            "notatka": st.column_config.TextColumn("📝 NOTATKI", width=400)
        }
    )

    # Kolizje
    conflicts = []
    check_df = edited_df.dropna(subset=['pojazd', 'start', 'koniec']).copy()
    check_df['start'] = pd.to_datetime(check_df['start'])
    check_df['koniec'] = pd.to_datetime(check_df['koniec'])
    
    for auto in check_df['pojazd'].unique():
        v_df = check_df[check_df['pojazd'] == auto].sort_values('start')
        if len(v_df) > 1:
            recs = v_df.to_dict('records')
            for i in range(len(recs)-1):
                for j in range(i+1, len(recs)):
                    if recs[i]['start'] < recs[j]['koniec'] and recs[j]['start'] < recs[i]['koniec']:
                        conflicts.append(f"⚠️ KOLIZJA: {auto} -> {recs[i]['event']} / {recs[j]['event']}")

    if conflicts:
        st.markdown('<div class="conflict-box">', unsafe_allow_html=True)
        for c in conflicts: st.write(c)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("💾 ZAPISZ ZMIANY W BAZIE", use_container_width=True):
        full_current_db = get_data()
        if search_q:
            mask_to_keep = ~full_current_db.astype(str).apply(lambda x: x.str.lower().str.contains(search_q).any(), axis=1)
            remaining_data = full_current_db[mask_to_keep]
            final_to_save = pd.concat([remaining_data, edited_df], ignore_index=True)
        else:
            final_to_save = edited_df

        final_to_save = final_to_save.dropna(subset=['pojazd'])
        final_to_save = final_to_save[final_to_save['event'] != ""]
        final_to_save['start'] = pd.to_datetime(final_to_save['start']).dt.strftime('%Y-%m-%d')
        final_to_save['koniec'] = pd.to_datetime(final_to_save['koniec']).dt.strftime('%Y-%m-%d')
        final_to_save.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        
        conn.update(data=final_to_save)
        st.session_state.main_df = get_data()
        st.success("Zsynchronizowano z Google Sheets!")
        st.rerun()
