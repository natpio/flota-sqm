import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. LOGOWANIE (Bezpieczeństwo SQM)
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
# 2. KONFIGURACJA STRONY I STYLE
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
    .stButton>button { border-radius: 8px; font-weight: bold; height: 3.5rem; width: 100%; }
    </style>
    <div class="sqm-header">
        <h1 style="margin:0; font-size: 2.8rem; letter-spacing: -2px;">SQM LOGISTICS</h1>
        <p style="margin:0; opacity:0.7; font-size: 1rem;">Fleet Management v24.0 | Full Recovery & Collision Guard</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. DEFINICJA ZASOBÓW
# -----------------------------------------------------------------------------
RESOURCES = {
    "🚛 CIĘŻAROWE": ["31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS", "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa", "SPEDYCJA", "AUTO RENTAL"],
    "🚐 BUSY": ["25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"],
    "🚗 OSOBOWE": ["01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723", "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek", "05 – Dacia Duster – WH7083A B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N", "FORD Transit Connect PY54635", "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", "Chrysler Pacifica PY04266 - MBanasiak", "Seat Ateca WZ445HU Dynasiuk", "Seat Ateca WZ446HU- PM"],
    "🏠 NOCLEGI": ["MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"]
}

ASSET_TO_CAT_ICON = {a: cat[0] for cat, assets in RESOURCES.items() for a in assets}
ALL_ASSETS_LABELS = [f"{cat[0]} {a}" for cat, assets in RESOURCES.items() for a in assets]
CLEAN_ASSETS_LIST = [a for sub in RESOURCES.values() for a in sub]

# -----------------------------------------------------------------------------
# 4. OBSŁUGA GOOGLE SHEETS
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        raw = conn.read(ttl="0s")
        if raw.empty: 
            return pd.DataFrame(columns=['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka'])
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        raw['start'] = pd.to_datetime(raw['start'], errors='coerce')
        raw['koniec'] = pd.to_datetime(raw['koniec'], errors='coerce')
        return raw.dropna(subset=['pojazd']).fillna("")
    except:
        return pd.DataFrame(columns=['pojazd', 'event', 'start', 'koniec', 'kierowca', 'notatka'])

if "main_df" not in st.session_state:
    st.session_state.main_df = get_data()

# -----------------------------------------------------------------------------
# 5. LOGIKA WYKRYWANIA KOLIZJI
# -----------------------------------------------------------------------------
def check_for_conflicts(df):
    conflicts = []
    temp = df.copy()
    temp['start'] = pd.to_datetime(temp['start'], errors='coerce')
    temp['koniec'] = pd.to_datetime(temp['koniec'], errors='coerce')
    temp = temp.dropna(subset=['start', 'koniec', 'pojazd'])
    
    for vehicle in temp['pojazd'].unique():
        v_data = temp[temp['pojazd'] == vehicle].sort_values('start')
        if len(v_data) < 2: continue
        
        recs = v_data.to_dict('records')
        for i in range(len(recs)):
            for j in range(i + 1, len(recs)):
                r1, r2 = recs[i], recs[j]
                if r1['start'] < r2['koniec'] and r2['start'] < r1['koniec']:
                    conflicts.append({
                        "auto": vehicle,
                        "e1": r1['event'], "e2": r2['event'],
                        "d1": f"{r1['start'].strftime('%d.%m')} - {r1['koniec'].strftime('%d.%m')}",
                        "d2": f"{r2['start'].strftime('%d.%m')} - {r2['koniec'].strftime('%d.%m')}"
                    })
    return conflicts

# -----------------------------------------------------------------------------
# 6. SIDEBAR I FILTRY CZASU
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("LOGISTYKA SQM")
    today = datetime.now()
    view_range = st.date_input("ZAKRES WIDOKU:", value=(today - timedelta(days=2), today + timedelta(days=16)))
    if st.button("🔄 ODSWIEŻ DANE"):
        st.session_state.main_df = get_data()
        st.rerun()
    st.divider()
    st.info("Status: Ochrona danych aktywna (v24)")

start_v, end_v = view_range if isinstance(view_range, tuple) and len(view_range) == 2 else (today - timedelta(days=2), today + timedelta(days=16))

# -----------------------------------------------------------------------------
# 7. FUNKCJA WYKRESU GANTTA
# -----------------------------------------------------------------------------
def draw_gantt(df_to_plot, assets_to_list, height=600):
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=assets_to_list, x=[None]*len(assets_to_list), showlegend=False))
    
    plot_df = df_to_plot[df_to_plot['start'].notnull()].copy()
    if not plot_df.empty:
        plot_df['y_label'] = plot_df['pojazd'].apply(lambda x: f"{ASSET_TO_CAT_ICON.get(x, '•')} {x}")
        for ev, group in plot_df.groupby('event'):
            dur = (group['koniec'] - group['start']).dt.total_seconds() * 1000
            fig.add_trace(go.Bar(
                y=group['y_label'], x=dur, base=group['start'],
                orientation='h', name=ev, text=group['event'],
                textposition='inside', insidetextanchor='start',
                textfont=dict(size=14, color='white'),
                hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>"
            ))
    
    fig.update_layout(
        height=height, template="plotly_white", margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(type='date', range=[start_v, end_v], side='top', tickformat="%d\n%b", dtick="D1", gridcolor='#e5e7eb'),
        yaxis=dict(categoryorder='array', categoryarray=assets_to_list[::-1], automargin=True, gridcolor='#f3f4f6'),
        showlegend=False
    )
    fig.add_vline(x=today.timestamp()*1000, line_width=3, line_color="#ef4444")
    return fig

# -----------------------------------------------------------------------------
# 8. GŁÓWNY INTERFEJS (ZAKŁADKI)
# -----------------------------------------------------------------------------
tabs = list(RESOURCES.keys()) + ["🔧 EDYCJA I PLANOWANIE"]
choice = st.radio("WIDOK FLOTY:", tabs, horizontal=True)
st.divider()

if choice in RESOURCES:
    grp = RESOURCES[choice]
    lbls = [f"{choice[0]} {a}" for a in grp]
    filtered = st.session_state.main_df[st.session_state.main_df['pojazd'].isin(grp)]
    st.plotly_chart(draw_gantt(filtered, lbls, height=len(lbls)*65 + 100), use_container_width=True)

else:
    st.subheader("Panel Zarządzania Danymi")
    
    # Eksport i Szukanie
    c1, c2 = st.columns([3, 1])
    with c1:
        sq = st.text_input("🔍 SZUKAJ POJAZDU LUB PROJEKTU (Filtr edycji):", "").lower()
    with c2:
        csv_backup = st.session_state.main_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 POBIERZ KOPIĘ CSV", data=csv_backup, file_name=f"SQM_LOG_{datetime.now().strftime('%H%M')}.csv", use_container_width=True)

    # Logika wyświetlania w edytorze
    if sq:
        mask = st.session_state.main_df.astype(str).apply(lambda x: x.str.lower().str.contains(sq).any(), axis=1)
        df_for_editor = st.session_state.main_df[mask]
    else:
        df_for_editor = st.session_state.main_df

    # EDYTOR TABELI (Pełna konfiguracja)
    new_edited_df = st.data_editor(
        df_for_editor,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=600,
        key="editor_v24_final",
        column_config={
            "pojazd": st.column_config.SelectboxColumn("🚛 POJAZD", options=CLEAN_ASSETS_LIST, required=True, width="medium"),
            "event": st.column_config.TextColumn("📋 PROJEKT", width="medium"),
            "start": st.column_config.DateColumn("📅 OD", width="small"),
            "koniec": st.column_config.DateColumn("🏁 DO", width="small"),
            "kierowca": st.column_config.TextColumn("👤 KIEROWCA", width="small"),
            "notatka": st.column_config.TextColumn("📝 NOTATKI", width="large"),
        }
    )

    # --- WALIDACJA KOLIZJI ---
    # Musimy połączyć nową edycję z tym, czego nie widać (bo jest odfiltrowane)
    current_sheet_data = get_data()
    if sq:
        # Zostawiamy te wiersze, które NIE pasują do filtra szukania
        keep_mask = ~current_sheet_data.astype(str).apply(lambda x: x.str.lower().str.contains(sq).any(), axis=1)
        untouched_data = current_sheet_data[keep_mask]
    else:
        untouched_data = pd.DataFrame(columns=current_sheet_data.columns)

    # Łączymy "niedotykane" z "wyedytowanymi"
    full_data_to_verify = pd.concat([untouched_data, new_edited_df], ignore_index=True)
    full_data_to_verify = full_data_to_verify[full_data_to_verify['pojazd'] != ""]
    
    conflicts = check_for_conflicts(full_data_to_verify)

    if conflicts:
        st.markdown('<div class="conflict-box">', unsafe_allow_html=True)
        st.error(f"⚠️ WYKRYTO KOLIZJE ({len(conflicts)}) - Auto zajęte w tym samym czasie!")
        for c in conflicts:
            st.write(f"❌ **{c['auto']}**: {c['e1']} ({c['d1']}) ↔️ {c['e2']} ({c['d2']})")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- PRZYCISK ZAPISU ---
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY DO ARKUSZA GOOGLE"):
        try:
            # Przygotowanie do wysyłki (formatowanie nazw kolumn jak w GSheets)
            df_to_save = full_data_to_verify.copy()
            df_to_save['start'] = pd.to_datetime(df_to_save['start']).dt.strftime('%Y-%m-%d')
            df_to_save['koniec'] = pd.to_datetime(df_to_save['koniec']).dt.strftime('%Y-%m-%d')
            
            # Mapowanie na nazwy z arkusza: Pojazd, EVENT, Start, Koniec, Kierowca, Notatka
            df_to_save.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            
            conn.update(data=df_to_save)
            st.session_state.main_df = get_data() # Odświeżenie lokalnej pamięci
            st.success("✅ Dane zostały pomyślnie zapisane i zsynchronizowane!")
            st.balloons()
            st.rerun()
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")
