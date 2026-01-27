import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

# ==========================================
# 1. KONFIGURACJA STRONY (GŁÓWNE USTAWIENIA)
# ==========================================
st.set_page_config(
    page_title="LOGISTYKA SQM - ZARZĄDZANIE FLOTĄ",
    layout="wide",
    page_icon="🚚",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. ZAAWANSOWANE STYLE CSS (INTERFEJS)
# ==========================================
st.markdown("""
    <style>
    /* Tło i czcionki */
    .stApp { background-color: #f4f7f9; }
    
    /* Sidebar - Panel Logistyka */
    section[data-testid="stSidebar"] {
        background-color: #1e293b !important;
        color: white !important;
        width: 450px !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h2, 
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] label {
        color: #f8fafc !important;
    }
    
    /* Karty alertów i konfliktów */
    .conflict-alert {
        background-color: #fef2f2;
        border: 2px solid #dc2626;
        padding: 20px;
        border-radius: 10px;
        color: #991b1b;
        font-weight: bold;
        margin-bottom: 25px;
    }
    
    /* Formatowanie wykresu Plotly */
    .plot-container {
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        background: white;
        padding: 10px;
    }
    
    /* Stylizacja tabeli edycji */
    [data-testid="stTable"] {
        background-color: white;
    }
    
    /* Nagłówek grupy pojazdów */
    .group-header {
        background-color: #334155;
        color: white;
        padding: 8px 15px;
        border-radius: 5px;
        margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. DEFINICJA STRUKTURY FLOTY (DANE SQM)
# ==========================================
VEHICLE_STRUCTURE = {
    "OSOBÓWKI": [
        "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", 
        "03 – Dacia Duster (biedak) – WE5A723", "04 – Dacia Jogger – WH6802A", 
        "06 – Dacia Duster – WH7087A ex T Białek", "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", 
        "Chrysler Pacifica PY04266 - MBanasiak", "05 – Dacia Duster – WH7083A B.Krauze", 
        "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N", "Seat Ateca WZ445HU Dynasiuk", 
        "Seat Ateca WZ446HU- PM"
    ],
    "BUSY": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", 
        "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", 
        "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"
    ],
    "CIĘŻARÓWKI / TIR": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "SPEDYCJA / RENTAL": [
        "SPEDYCJA 1", "SPEDYCJA 2", "SPEDYCJA 3", "SPEDYCJA 4", "SPEDYCJA 5", "AUTO RENTAL"
    ],
    "MIESZKANIA BCN": [
        "MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}

# Tworzenie płaskiej listy do walidacji i sortowania
ALL_VEHICLES_ORDERED = []
for cat, v_list in VEHICLE_STRUCTURE.items():
    ALL_VEHICLES_ORDERED.extend(v_list)

# ==========================================
# 4. LOKALIZACJA I DATY (POLSKA)
# ==========================================
PL_MONTHS = {
    1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
    7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"
}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]

# Święta 2026 - krytyczne dla slotów i transportu międzynarodowego
POLISH_HOLIDAYS = [
    "2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
    "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
    "2026-12-25", "2026-12-26"
]

# ==========================================
# 5. OBSŁUGA DANYCH (GOOGLE SHEETS)
# ==========================================
def safe_clean_name(name):
    """Usuwa zbędne znaki dla poprawnego mapowania nazw pojazdów"""
    if pd.isna(name): return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(name)).upper()

# Połączenie
conn = st.connection("gsheets", type=GSheetsConnection)

def load_transport_data():
    """Wczytuje i czyści dane z arkusza FLOTA_SQM"""
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty: return pd.DataFrame(columns=["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Uwagi"])
        
        # Standaryzacja kolumn
        df.columns = [c.strip() for c in df.columns]
        
        # Konwersja i walidacja dat
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        
        # Automatyczna korekta nazw (Fuzzy Match)
        clean_map = {safe_clean_name(v): v for v in ALL_VEHICLES_ORDERED}
        df['Pojazd'] = df['Pojazd'].apply(lambda x: clean_map.get(safe_clean_name(x), str(x).strip()))
        
        # Filtrowanie tylko kompletnych wpisów
        df = df.dropna(subset=['Data_Start', 'Data_Koniec'])
        return df
    except Exception as e:
        st.error(f"Błąd krytyczny połączenia z Google Sheets: {e}")
        return pd.DataFrame()

# Pobranie danych
df_raw = load_transport_data()

# ==========================================
# 6. LOGIKA KONFLIKTÓW (WALIDACJA)
# ==========================================
def get_conflicts(df, vehicle, start, end):
    """Sprawdza czy auto nie jest zajęte w podanym oknie czasowym"""
    s_dt = pd.to_datetime(start)
    e_dt = pd.to_datetime(end)
    
    overlapping = df[
        (df['Pojazd'] == vehicle) & 
        (df['Data_Start'] <= e_dt) & 
        (df['Data_Koniec'] >= s_dt)
    ]
    return overlapping

# ==========================================
# 7. SIDEBAR - PANEL OPERACYJNY LOGISTYKA
# ==========================================
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/uploads/2019/02/logo-sqm.png", width=120)
    st.markdown("## 🛠️ ZAPLANUJ TRANSPORT")
    
    with st.form("add_transport_form", clear_on_submit=True):
        f_car = st.selectbox("Pojazd / Zasób", ALL_VEHICLES_ORDERED)
        f_proj = st.text_input("Nazwa Eventu (Projekt)")
        f_driver = st.text_input("Kierowca (lub dane naczepy)")
        
        col1, col2 = st.columns(2)
        f_start = col1.date_input("Data Wyjazdu", value=datetime.now())
        f_end = col2.date_input("Data Powrotu", value=datetime.now() + timedelta(days=3))
        
        f_notes = st.text_area("Uwagi: Sloty / Rozładunek / Pakowanie")
        
        # Sprawdzanie dostępności w locie
        has_conflict = False
        if not df_raw.empty:
            conflicts = get_conflicts(df_raw, f_car, f_start, f_end)
            if not conflicts.empty:
                has_conflict = True
                st.error(f"🛑 KONFLIKT! Auto zajęte przez: {conflicts.iloc[0]['Projekt']}")
        
        submit_btn = st.form_submit_button("DODAJ DO HARMONOGRAMU", use_container_width=True)
        
        if submit_btn:
            if has_conflict:
                st.warning("Nie zapisano! Rozwiąż kolizję dat.")
            elif not f_proj:
                st.error("Wpisz nazwę projektu!")
            else:
                new_data = pd.DataFrame([{
                    "Pojazd": f_car, "Projekt": f_proj, "Kierowca": f_driver,
                    "Data_Start": f_start.strftime('%Y-%m-%d'),
                    "Data_Koniec": f_end.strftime('%Y-%m-%d'),
                    "Uwagi": f_notes
                }])
                current_gsheet = conn.read(worksheet="FLOTA_SQM", ttl="0")
                updated_gsheet = pd.concat([current_gsheet, new_data], ignore_index=True)
                conn.update(worksheet="FLOTA_SQM", data=updated_gsheet)
                st.success("Zapisano pomyślnie w bazie.")
                st.rerun()

# ==========================================
# 8. WIZUALIZACJA - GRAFIK OPERACYJNY
# ==========================================
st.title("🚚 PANEL LOGISTYKI I TRANSPORTU SQM 2026")

# Powiadomienia o błędach w bazie
if not df_raw.empty:
    global_errors = []
    for car in df_raw['Pojazd'].unique():
        v_data = df_raw[df_raw['Pojazd'] == car].sort_values('Data_Start')
        for i in range(len(v_data)-1):
            if v_data.iloc[i]['Data_Koniec'] >= v_data.iloc[i+1]['Data_Start']:
                global_errors.append(f"Nakładanie: **{car}** ({v_data.iloc[i]['Projekt']} / {v_data.iloc[i+1]['Projekt']})")
    
    if global_errors:
        with st.container():
            st.markdown('<div class="conflict-alert">⚠️ UWAGA: WYKRYTO KONFLIKTY W GRAFIKU!</div>', unsafe_allow_html=True)
            for err in global_errors:
                st.write(f"- {err}")

# Suwak zakresu
days_range = [d.date() for d in pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')]
selected_view = st.select_slider(
    "Ustaw zakres podglądu grafiku:",
    options=days_range,
    value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=21))
)

if not df_raw.empty:
    # Przygotowanie danych do Plotly
    df_viz = df_raw.copy()
    df_viz['Data_Koniec_Plot'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)
    df_viz['Pojazd'] = pd.Categorical(df_viz['Pojazd'], categories=ALL_VEHICLES_ORDERED, ordered=True)
    df_viz = df_viz.sort_values('Pojazd')

    # Wykres Gantta
    fig = px.timeline(
        df_viz, 
        x_start="Data_Start", 
        x_end="Data_Koniec_Plot", 
        y="Pojazd", 
        color="Projekt", 
        text="Projekt",
        hover_data={"Kierowca": True, "Uwagi": True, "Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m", "Data_Koniec_Plot": False},
        template="plotly_white"
    )

    # Stylizacja etykiet na paskach
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=14, family="Arial Black", color="white"),
        marker=dict(line=dict(width=1, color="white"))
    )

    # Budowa dynamicznej osi X (Dni, Miesiące, Święta)
    view_days = pd.date_range(start=selected_view[0], end=selected_view[1])
    tick_vals, tick_text, current_m = [], [], -1
    
    for day in view_days:
        tick_vals.append(day)
        is_we = day.weekday() >= 5
        is_hol = day.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        
        color = "#e63946" if is_hol else ("#adb5bd" if is_we else "#1e293b")
        label = f"<b>{day.day}</b><br>{PL_WEEKDAYS[day.weekday()]}"
        
        if day.month != current_m:
            label = f"<span style='color:#0077b6'><b>{PL_MONTHS[day.month]}</b></span><br>{label}"
            current_m = day.month
            
        tick_text.append(f"<span style='color:{color}'>{label}</span>")
        
        if is_we or is_hol:
            fig.add_vrect(x0=day, x1=day + timedelta(days=1), fillcolor="rgba(200,200,200,0.15)", layer="below", line_width=0)

    # Linie oddzielające grupy (Osobówki / Busy / Ciężarówki)
    y_line = 0
    for group, items in VEHICLE_STRUCTURE.items():
        y_line += len(items)
        fig.add_hline(y=y_line - 0.5, line_width=2, line_color="#dee2e6", line_dash="solid")

    # Finalny Layout
    fig.update_xaxes(
        tickmode='array', tickvals=tick_vals, ticktext=tick_text, 
        side="top", range=[selected_view[0], selected_view[1]], gridcolor="#f1f3f5"
    )
    fig.update_yaxes(autorange="reversed", title="", showgrid=True, gridcolor="#f1f3f5")
    
    # Linia czasu "DZISIAJ"
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=3, line_color="#d00000", line_dash="dash")

    fig.update_layout(
        height=1300,
        margin=dict(l=10, r=10, t=120, b=10),
        showlegend=False,
        plot_bgcolor="white"
    )

    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 9. TABELA ZARZĄDZANIA I EDYCJI MASOWEJ
# ==========================================
st.markdown("---")
st.subheader("📋 REJESTR TRANSPORTÓW - EDYCJA I SZCZEGÓŁY")

with st.expander("Otwórz Panel Zarządzania Bazą (Excel Mode)"):
    if not df_raw.empty:
        # Przygotowanie do edytora
        df_edit = df_raw.copy()
        df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
        df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
        
        # Interaktywny edytor
        edited_data = st.data_editor(
            df_edit,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_VEHICLES_ORDERED, width="large"),
                "Data_Start": st.column_config.DateColumn("Wyjazd"),
                "Data_Koniec": st.column_config.DateColumn("Powrót"),
                "Uwagi": st.column_config.TextColumn("Szczegóły Logistyczne (Sloty)", width="max")
            }
        )
        
        col_btn1, col_btn2 = st.columns([1, 4])
        if col_btn1.button("💾 ZAPISZ ZMIANY"):
            conn.update(worksheet="FLOTA_SQM", data=edited_data)
            st.success("Baza została zaktualizowana.")
            st.rerun()
    else:
        st.info("Baza danych jest pusta. Dodaj pierwszy transport w panelu bocznym.")

# ==========================================
# 10. STOPKA DIAGNOSTYCZNA
# ==========================================
st.markdown("""<div style="text-align: right; color: #94a3b8; font-size: 0.8rem;">
    System Floty SQM v2.1 | Rok Operacyjny 2026 | Status Połączenia: OK</div>""", unsafe_allow_html=True)
