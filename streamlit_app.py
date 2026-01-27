import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

# ==========================================
# 1. KONFIGURACJA STRONY I ZAAWANSOWANE STYLE CSS
# ==========================================
st.set_page_config(
    page_title="SYSTEM LOGISTYKI SQM MULTIMEDIA",
    layout="wide",
    page_icon="🚚"
)

st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    .sidebar-header {
        color: #1D3557; font-size: 1.2rem; font-weight: bold;
        border-bottom: 2px solid #1D3557; margin-bottom: 1rem; padding-bottom: 0.5rem;
    }
    .conflict-card {
        background-color: #ffe5e5; border-left: 5px solid #d90429;
        padding: 15px; margin: 10px 0; border-radius: 4px; color: #2b2d42;
    }
    .diag-box {
        background-color: #e9ecef; border: 1px solid #ced4da;
        padding: 10px; border-radius: 5px; font-family: monospace; font-size: 0.85rem;
    }
    [data-testid="stPlotlyChart"] .xtick text { 
        font-family: 'Arial Black', sans-serif !important; font-size: 11px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. LOKALIZACJA I STRUKTURA FLOTY SQM
# ==========================================
PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

VEHICLE_STRUCTURE = {
    "OSOBÓWKI": [
        "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek", "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", "Chrysler Pacifica PY04266 - MBanasiak",
        "05 – Dacia Duster – WH7083A B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "Seat Ateca WZ445HU Dynasiuk", "Seat Ateca WZ446HU- PM"
    ],
    "BUSY": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", "BOXER - WZ213GF",
        "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24",
        "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"
    ],
    "CIĘŻARÓWKI / TIR": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "SPEDYCJA / RENTAL": ["SPEDYCJA 1", "SPEDYCJA 2", "SPEDYCJA 3", "SPEDYCJA 4", "SPEDYCJA 5", "AUTO RENTAL"],
    "MIESZKANIA BCN": ["MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"]
}

SORTED_LIST = [v for sub in VEHICLE_STRUCTURE.values() for v in sub]

# ==========================================
# 3. SILNIK DANYCH Z FUNKCJĄ FUZZY CLEANING
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def clean_string(s):
    """Usuwa wszystko co nie jest literą lub cyfrą do porównania"""
    if pd.isna(s): return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(s)).upper()

def get_db_data():
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty: return pd.DataFrame()
        
        # Standaryzacja nazw kolumn
        df.columns = [c.strip() for c in df.columns]
        
        # Konwersja dat
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        
        # Krytyczne czyszczenie: Dopasowanie nazw pojazdów mimo błędów w Excelu
        # Mapujemy uproszczone nazwy z listy SQM na ich pełne brzmienie
        mapping = {clean_string(v): v for v in SORTED_LIST}
        
        def find_correct_name(val):
            cleaned = clean_string(val)
            return mapping.get(cleaned, val) # Zwraca oryginał jeśli nie znajdzie dopasowania
            
        df['Pojazd'] = df['Pojazd'].apply(find_correct_name)
        
        # Usunięcie wierszy bez dat
        df = df.dropna(subset=['Data_Start', 'Data_Koniec'])
        return df
    except Exception as e:
        st.error(f"Błąd bazy: {e}")
        return pd.DataFrame()

df_main = get_db_data()

# ==========================================
# 4. KONSOLA DIAGNOSTYCZNA (PODGLĄD BŁĘDÓW)
# ==========================================
with st.expander("🔍 DIAGNOSTYKA SYNC (Otwórz jeśli nie widzisz danych)"):
    if not df_main.empty:
        st.write("Wykryte kolumny:", list(df_main.columns))
        invalid_cars = df_main[~df_main['Pojazd'].isin(SORTED_LIST)]['Pojazd'].unique()
        if len(invalid_cars) > 0:
            st.error("Poniższe nazwy w Excelu są błędne i nie pasują do grafiku:")
            for ic in invalid_cars:
                st.code(f"'{ic}'")
        else:
            st.success("Wszystkie nazwy pojazdów zsynchronizowane poprawnie.")

# ==========================================
# 5. LOGIKA KOLIZJI (CONFLICT DETECTOR)
# ==========================================
def check_overlapping(df, vehicle, start, end):
    s_dt, e_dt = pd.to_datetime(start), pd.to_datetime(end)
    conflicts = df[
        (df['Pojazd'] == vehicle) & 
        (df['Data_Start'] <= e_dt) & 
        (df['Data_Koniec'] >= s_dt)
    ]
    return conflicts

# ==========================================
# 6. SIDEBAR - DODAWANIE
# ==========================================
with st.sidebar:
    st.markdown('<p class="sidebar-header">⚙️ NOWY TRANSPORT</p>', unsafe_allow_html=True)
    with st.form("transport_form"):
        v_choice = st.selectbox("Pojazd", SORTED_LIST)
        p_name = st.text_input("Projekt / Event")
        k_name = st.text_input("Kierowca / Załadunek")
        c1, c2 = st.columns(2)
        d_s = c1.date_input("Start")
        d_e = c2.date_input("Koniec", value=datetime.now() + timedelta(days=2))
        
        conflict_exists = False
        if not df_main.empty:
            conflicts = check_overlapping(df_main, v_choice, d_s, d_e)
            if not conflicts.empty:
                conflict_exists = True
                st.error(f"❌ KOLIZJA: {conflicts.iloc[0]['Projekt']}")
        
        if st.form_submit_button("DODAJ DO GRAFIKU"):
            if not p_name or conflict_exists:
                st.warning("Uzupełnij projekt lub napraw kolizję!")
            else:
                new_row = pd.DataFrame([{
                    "Pojazd": v_choice, "Projekt": p_name, "Kierowca": k_name,
                    "Data_Start": d_s.strftime('%Y-%m-%d'), 
                    "Data_Koniec": d_e.strftime('%Y-%m-%d')
                }])
                current = conn.read(worksheet="FLOTA_SQM", ttl="0")
                conn.update(worksheet="FLOTA_SQM", data=pd.concat([current, new_row], ignore_index=True))
                st.rerun()

# ==========================================
# 7. PANEL GŁÓWNY - GRAFIK GANTTA
# ==========================================
st.title("🚚 GRAFIK OPERACYJNY SQM 2026")

# Alerty o istniejących nałożeniach
if not df_main.empty:
    found_conflicts = []
    for car in df_main['Pojazd'].unique():
        subset = df_main[df_main['Pojazd'] == car].sort_values('Data_Start')
        for i in range(len(subset)-1):
            if subset.iloc[i]['Data_Koniec'] >= subset.iloc[i+1]['Data_Start']:
                found_conflicts.append(f"<b>{car}</b>: {subset.iloc[i]['Projekt']} i {subset.iloc[i+1]['Projekt']}")
    
    if found_conflicts:
        st.subheader("⚠️ Konflikty w datach!")
        for fc in found_conflicts:
            st.markdown(f'<div class="conflict-card">{fc}</div>', unsafe_allow_html=True)

# Suwak zakresu czasu
slider_days = [d.date() for d in pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')]
v_range = st.select_slider("Widok:", options=slider_days, value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=18)))

if not df_main.empty:
    df_plot = df_main.copy()
    # Korekta wizualna: dodanie 1 dnia do końca, by pasek obejmował cały ostatni dzień
    df_plot['Data_Koniec_Viz'] = df_plot['Data_Koniec'] + pd.Timedelta(days=1)
    
    # Sortowanie osi Y
    df_plot['Pojazd'] = pd.Categorical(df_plot['Pojazd'], categories=SORTED_LIST, ordered=True)
    df_plot = df_plot.sort_values('Pojazd')

    fig = px.timeline(
        df_plot, x_start="Data_Start", x_end="Data_Koniec_Viz", y="Pojazd", color="Projekt", text="Projekt",
        hover_data={"Kierowca": True, "Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m", "Data_Koniec_Viz": False},
        template="plotly_white"
    )

    fig.update_traces(
        textposition='inside', insidetextanchor='middle',
        textfont=dict(size=13, family="Arial Black", color="white"),
        marker=dict(line=dict(width=1, color="white"))
    )

    # Budowa osi X
    timeline_range = pd.date_range(start=v_range[0], end=v_range[1])
    t_vals, t_text, last_m = [], [], -1
    for d in timeline_range:
        t_vals.append(d)
        is_we, is_hol = d.weekday() >= 5, d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        col = "#d90429" if is_hol else ("#8d99ae" if is_we else "#2b2d42")
        lbl = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
        if d.month != last_m:
            lbl = f"<span style='color:#1D3557'><b>{PL_MONTHS[d.month]}</b></span><br>{lbl}"
            last_m = d.month
        t_text.append(f"<span style='color:{col}'>{lbl}</span>")
        if is_we or is_hol:
            fig.add_vrect(x0=d, x1=d + timedelta(days=1), fillcolor="rgba(200,200,200,0.15)", layer="below", line_width=0)

    # Linie separatorów grup
    y_pos = 0
    for grp, vlist in VEHICLE_STRUCTURE.items():
        y_pos += len(vlist)
        fig.add_hline(y=y_pos - 0.5, line_width=2, line_color="#edf2f4")

    fig.update_xaxes(tickmode='array', tickvals=t_vals, ticktext=t_text, side="top", range=[v_range[0], v_range[1]])
    fig.update_yaxes(autorange="reversed", title="")
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=3, line_color="#d90429", line_dash="dash")
    
    fig.update_layout(height=1200, margin=dict(l=10, r=10, t=110, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 8. EDYCJA I ZARZĄDZANIE
# ==========================================
st.markdown("---")
with st.expander("📋 EDYTOR BAZY DANYCH"):
    if not df_main.empty:
        df_edit = df_main.copy()
        df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
        df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
        edited_df = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
        if st.button("ZAPISZ ZMIANY W GOOGLE"):
            conn.update(worksheet="FLOTA_SQM", data=edited_df)
            st.rerun()
