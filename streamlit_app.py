import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA STRONY I LOGOWANIE
# -----------------------------------------------------------------------------
st.set_page_config(page_title="SQM LOGISTICS", layout="wide")

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
# 2. DEFINICJA ZASOBÓW I STYLE
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;900&display=swap');
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    .sqm-header {
        background: #0f172a; padding: 1.5rem; border-radius: 12px; color: white;
        margin-bottom: 1.5rem; border-left: 8px solid #2563eb;
    }
    [data-testid="stDataEditor"] div { font-size: 16px !important; }
    .conflict-box {
        background-color: #fee2e2; border: 2px solid #ef4444; padding: 1rem;
        border-radius: 8px; color: #b91c1c; margin: 1rem 0;
    }
    </style>
    <div class="sqm-header">
        <h1 style="margin:0; font-size: 2.5rem;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.7;">System v26.0 | Pełny Wykres i Kontrola Danych</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. OBSŁUGA DANYCH GOOGLE SHEETS
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        df = conn.read(ttl="0s")
        # Standaryzacja kolumn
        df.columns = [str(c).strip().lower() for c in df.columns]
        df['start'] = pd.to_datetime(df['start'], errors='coerce')
        df['koniec'] = pd.to_datetime(df['koniec'], errors='coerce')
        return df.dropna(subset=['pojazd']).fillna("")
    except Exception:
        return pd.DataFrame(columns=['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka'])

if "main_df" not in st.session_state:
    st.session_state.main_df = get_data()

# -----------------------------------------------------------------------------
# 4. FUNKCJA WYKRESU GANTTA
# -----------------------------------------------------------------------------
def draw_gantt_chart(df_to_plot, asset_list, start_d, end_d):
    fig = go.Figure()
    
    # Dodanie wszystkich osi Y (pojazdów), nawet jeśli są puste
    fig.add_trace(go.Scatter(y=asset_list, x=[None]*len(asset_list), showlegend=False))
    
    valid_data = df_to_plot[df_to_plot['start'].notnull()].copy()
    if not valid_data.empty:
        valid_data['y_label'] = valid_data['pojazd'].apply(lambda x: f"{ASSET_TO_ICON.get(x, '•')} {x}")
        for event_name, group in valid_data.groupby('event'):
            # Obliczanie długości paska w milisekundach dla Plotly
            durations = (group['koniec'] - group['start']).dt.total_seconds() * 1000
            fig.add_trace(go.Bar(
                y=group['y_label'], 
                x=durations, 
                base=group['start'],
                orientation='h', 
                name=str(event_name),
                text=str(event_name),
                textposition='inside',
                textfont=dict(color='white', size=12),
                marker=dict(line=dict(width=1, color='rgba(255,255,255,0.5)'))
            ))
    
    fig.update_layout(
        height=len(asset_list) * 55 + 100,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(type='date', range=[start_d, end_d], side='top', dtick="D1", tickformat="%d\n%b", gridcolor='#f1f5f9'),
        yaxis=dict(categoryorder='array', categoryarray=asset_list[::-1], gridcolor='#f1f5f9'),
        template="plotly_white",
        showlegend=False,
        barmode='overlay'
    )
    # Linia "Dzisiaj"
    fig.add_vline(x=datetime.now().timestamp()*1000, line_width=2, line_color="red", line_dash="dot")
    return fig

# -----------------------------------------------------------------------------
# 5. SIDEBAR I FILTRY
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("USTAWIENIA")
    today = datetime.now()
    view_range = st.date_input("ZAKRES CZASU:", value=(today - timedelta(days=2), today + timedelta(days=14)))
    st.divider()
    if st.button("🔄 ODSWIEŻ Z BAZY"):
        st.session_state.main_df = get_data()
        st.rerun()

start_view, end_view = view_range if isinstance(view_range, tuple) and len(view_range) == 2 else (today, today + timedelta(days=7))

# -----------------------------------------------------------------------------
# 6. GŁÓWNY PANEL
# -----------------------------------------------------------------------------
tabs = list(RESOURCES.keys()) + ["🔧 EDYCJA I PLANOWANIE"]
active_tab = st.radio("WYBIERZ WIDOK:", tabs, horizontal=True)

if active_tab in RESOURCES:
    group_assets = RESOURCES[active_tab]
    labels = [f"{ASSET_TO_ICON[a]} {a}" for a in group_assets]
    df_filtered = st.session_state.main_df[st.session_state.main_df['pojazd'].isin(group_assets)]
    st.plotly_chart(draw_gantt_chart(df_filtered, labels, start_view, end_view), use_container_width=True)

else:
    st.subheader("Panel Planowania i Edycji")
    
    col_search, col_backup = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("🔍 Filtruj tabelę (wpisz auto lub projekt):", "").lower()
    with col_backup:
        csv_data = st.session_state.main_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 POBIERZ KOPIĘ CSV", data=csv_data, file_name=f"SQM_BACKUP_{datetime.now().strftime('%H%M')}.csv", use_container_width=True)

    # Przygotowanie danych do edytora
    if search_query:
        mask = st.session_state.main_df.astype(str).apply(lambda x: x.str.lower().str.contains(search_query).any(), axis=1)
        display_df = st.session_state.main_df[mask]
    else:
        display_df = st.session_state.main_df

    # TABELA EDYCJI
    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 POJAZD", options=CLEAN_LIST, required=True),
            "event": st.column_config.TextColumn("📋 PROJEKT / EVENT"),
            "start": st.column_config.DateColumn("📅 START"),
            "koniec": st.column_config.DateColumn("🏁 KONIEC"),
            "kierowca": st.column_config.TextColumn("👤 KIEROWCA"),
            "notatka": st.column_config.TextColumn("📝 NOTATKI")
        }
    )

    # --- BEZPIECZNY ZAPIS ---
    # Musimy połączyć to co edytowane z tym, czego nie widać (bo jest odfiltrowane)
    full_db = get_data()
    if search_query:
        other_mask = ~full_db.astype(str).apply(lambda x: x.str.lower().str.contains(search_query).any(), axis=1)
        others = full_db[other_mask]
    else:
        others = pd.DataFrame(columns=full_db.columns)

    # Składamy całość do weryfikacji i zapisu
    final_to_save = pd.concat([others, edited_df], ignore_index=True).dropna(subset=['pojazd'])
    
    # KONTROLA KOLIZJI
    conflicts = []
    check_df = final_to_save.copy()
    check_df['start'] = pd.to_datetime(check_df['start'], errors='coerce')
    check_df['koniec'] = pd.to_datetime(check_df['koniec'], errors='coerce')
    check_df = check_df.dropna(subset=['start', 'koniec'])

    for auto in check_df['pojazd'].unique():
        v_df = check_df[check_df['pojazd'] == auto].sort_values('start')
        recs = v_df.to_dict('records')
        for i in range(len(recs)):
            for j in range(i + 1, len(recs)):
                r1, r2 = recs[i], recs[j]
                if r1['start'] < r2['koniec'] and r2['start'] < r1['koniec']:
                    conflicts.append(f"🔴 **{auto}**: Kolizja projektów **{r1['event']}** oraz **{r2['event']}**")

    if conflicts:
        st.markdown('<div class="conflict-box">', unsafe_allow_html=True)
        st.error("⚠️ UWAGA: WYKRYTO KONFLIKTY TERMINÓW!")
        for c in conflicts: st.write(c)
        st.markdown('</div>', unsafe_allow_html=True)

    # PRZYCISK ZAPISU
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY DO ARKUSZA GOOGLE", use_container_width=True, type="primary"):
        # Formatowanie pod Google Sheets
        ready_df = final_to_save.copy()
        ready_df['start'] = pd.to_datetime(ready_df['start']).dt.strftime('%Y-%m-%d')
        ready_df['koniec'] = pd.to_datetime(ready_df['koniec']).dt.strftime('%Y-%m-%d')
        ready_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        
        try:
            conn.update(data=ready_df)
            st.session_state.main_df = get_data()
            st.success("✅ Dane pomyślnie zsynchronizowane z Google Sheets!")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")
