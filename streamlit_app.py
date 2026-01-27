import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURACJA STRONY I ZAAWANSOWANE STYLE CSS
# ==========================================
st.set_page_config(
    page_title="SYSTEM LOGISTYKI SQM MULTIMEDIA",
    layout="wide",
    page_icon="🚚"
)

# Customowy CSS dla poprawy czytelności grafiku i alertów
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    
    /* Nagłówki sekcji w Sidebarze */
    .sidebar-header {
        color: #1D3557;
        font-size: 1.2rem;
        font-weight: bold;
        border-bottom: 2px solid #1D3557;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
    }
    
    /* Stylizacja alertu konfliktu */
    .conflict-card {
        background-color: #ffe5e5;
        border-left: 5px solid #d90429;
        padding: 15px;
        margin: 10px 0;
        border-radius: 4px;
        color: #2b2d42;
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* Poprawa czytelności osi X w Plotly */
    [data-testid="stPlotlyChart"] .xtick text { 
        font-family: 'Arial Black', sans-serif !important;
        font-size: 11px !important;
    }
    
    /* Stylizacja przycisków */
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #1D3557;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. STAŁE, LOKALIZACJA I ŚWIĘTA
# ==========================================
PL_MONTHS = {
    1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
    7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"
}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]

# Święta 2026 ważne dla transportu i slotów
POLISH_HOLIDAYS = {
    "2026-01-01": "Nowy Rok", "2026-01-06": "Trzech Króli",
    "2026-04-05": "Wielkanoc", "2026-04-06": "Poniedziałek Wielkanocny",
    "2026-05-01": "Święto Pracy", "2026-05-03": "Święto Konstytucji",
    "2026-06-04": "Boże Ciało", "2026-08-15": "Wniebowzięcie",
    "2026-11-01": "Wszystkich Świętych", "2026-11-11": "Święto Niepodległości",
    "2026-12-25": "Boże Narodzenie", "2026-12-26": "Drugi Dzień Świąt"
}

# ==========================================
# 3. PEŁNA STRUKTURA FLOTY SQM
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

SORTED_LIST = [v for sub in VEHICLE_STRUCTURE.values() for v in sub]

# ==========================================
# 4. FUNKCJE DANYCH I ANALIZA KOLIZJI
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_db_data():
    """Pobiera dane i wymusza poprawne formaty"""
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty: return pd.DataFrame()
        df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec']).copy()
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        df = df.dropna(subset=['Data_Start', 'Data_Koniec'])
        return df
    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
        return pd.DataFrame()

def check_overlapping(df, vehicle, start, end):
    """Logika Double Booking: sprawdza czy auto jest zajęte w danym terminie"""
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    car_df = df[df['Pojazd'] == vehicle]
    conflicts = car_df[
        (car_df['Data_Start'] <= end_dt) & 
        (car_df['Data_Koniec'] >= start_dt)
    ]
    return conflicts

# Wczytanie danych globalnych
df_main = get_db_data()

# ==========================================
# 5. SIDEBAR - KOMPLEKSOWY FORMULARZ
# ==========================================
with st.sidebar:
    st.markdown('<p class="sidebar-header">⚙️ PLANOWANIE ZASOBÓW</p>', unsafe_allow_html=True)
    
    with st.form("main_transport_form"):
        v_choice = st.selectbox("Pojazd", SORTED_LIST)
        p_name = st.text_input("Nazwa Projektu / Eventu")
        d_name = st.text_input("Kierowca / Odpowiedzialny")
        
        c1, c2 = st.columns(2)
        d_s = c1.date_input("Data Wyjazdu")
        d_e = c2.date_input("Data Powrotu", value=datetime.now() + timedelta(days=2))
        
        notes = st.text_area("Uwagi do transportu (sloty, naczepy)")
        
        # WALIDACJA KONFLIKTU W LOCIE
        conflict_exists = False
        if not df_main.empty:
            conflicts = check_overlapping(df_main, v_choice, d_s, d_e)
            if not conflicts.empty:
                conflict_exists = True
                st.error(f"❌ AUTO ZAJĘTE! Projekt: {conflicts.iloc[0]['Projekt']}")
        
        submitted = st.form_submit_button("ZAPISZ W HARMONOGRAMIE")
        
        if submitted:
            if conflict_exists:
                st.warning("Nie można zapisać - występuje kolizja dat!")
            elif not p_name:
                st.error("Podaj nazwę projektu!")
            else:
                new_entry = pd.DataFrame([{
                    "Pojazd": v_choice, "Projekt": p_name, "Kierowca": d_name,
                    "Data_Start": d_s.strftime('%Y-%m-%d'), 
                    "Data_Koniec": d_e.strftime('%Y-%m-%d'),
                    "Uwagi": notes
                }])
                current = conn.read(worksheet="FLOTA_SQM", ttl="0")
                updated = pd.concat([current, new_entry], ignore_index=True)
                conn.update(worksheet="FLOTA_SQM", data=updated)
                st.success("Dodano do bazy!")
                st.rerun()

# ==========================================
# 6. PANEL WIZUALIZACJI (GANTT)
# ==========================================
st.title("🚚 GRAFIK OPERACYJNY FLOTY SQM")

# Weryfikacja błędów w bazie (stare wpisy nakładające się)
st.subheader("⚠️ Alerty Logistyczne")
found_any_conflict = False
if not df_main.empty:
    for car in df_main['Pojazd'].unique():
        subset = df_main[df_main['Pojazd'] == car].sort_values('Data_Start')
        for i in range(len(subset)-1):
            if subset.iloc[i]['Data_Koniec'] >= subset.iloc[i+1]['Data_Start']:
                st.markdown(f"""<div class="conflict-card">
                    <b>KONFLIKT DAT:</b> {car}<br>
                    {subset.iloc[i]['Projekt']} ({subset.iloc[i]['Data_Start'].strftime('%d.%m')}) 
                    <-> {subset.iloc[i+1]['Projekt']} ({subset.iloc[i+1]['Data_Start'].strftime('%d.%m')})
                    </div>""", unsafe_allow_html=True)
                found_any_conflict = True

if not found_any_conflict:
    st.info("Brak konfliktów w grafiku. Wszystkie auta zaplanowane poprawnie.")

# Suwak zakresu
all_days = [d.date() for d in pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')]
view_range = st.select_slider(
    "Zakres widoku grafiku:",
    options=all_days,
    value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=21))
)

if not df_main.empty:
    df_plot = df_main.copy()
    df_plot['Viz_End'] = df_plot['Data_Koniec'] + pd.Timedelta(days=1)
    df_plot['Pojazd'] = pd.Categorical(df_plot['Pojazd'], categories=SORTED_LIST, ordered=True)
    df_plot = df_plot.sort_values('Pojazd')

    fig = px.timeline(
        df_plot, x_start="Data_Start", x_end="Viz_End", y="Pojazd", color="Projekt", text="Projekt",
        hover_data={"Kierowca": True, "Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m", "Viz_End": False},
        template="plotly_white"
    )

    fig.update_traces(
        textposition='inside', insidetextanchor='middle',
        textfont=dict(size=14, family="Arial Black", color="white"),
        marker=dict(line=dict(width=1, color="white"))
    )

    # Oś X i polskie daty
    view_days = pd.date_range(start=view_range[0], end=view_range[1])
    tick_v, tick_t, last_m = [], [], -1
    for d in view_days:
        tick_v.append(d)
        is_we, is_hol = d.weekday() >= 5, d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        clr = "#d90429" if is_hol else ("#8d99ae" if is_we else "#2b2d42")
        lbl = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
        if d.month != last_m:
            lbl = f"<span style='color:#1D3557'><b>{PL_MONTHS[d.month]}</b></span><br>{lbl}"
            last_m = d.month
        tick_t.append(f"<span style='color:{clr}'>{lbl}</span>")
        if is_we or is_hol:
            fig.add_vrect(x0=d, x1=d + timedelta(days=1), fillcolor="rgba(200,200,200,0.15)", layer="below", line_width=0)

    # Linie oddzielające grupy floty
    sep_y = 0
    for group, v_list in VEHICLE_STRUCTURE.items():
        sep_y += len(v_list)
        fig.add_hline(y=sep_y - 0.5, line_width=2, line_color="#edf2f4")

    fig.update_xaxes(tickmode='array', tickvals=tick_v, ticktext=tick_t, side="top", range=[view_range[0], view_range[1]])
    fig.update_yaxes(autorange="reversed", title="")
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=3, line_color="#d90429", line_dash="dash")
    
    fig.update_layout(height=1200, margin=dict(l=10, r=10, t=110, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. TABELA EDYCJI I ZARZĄDZANIA BAZĄ
# ==========================================
st.markdown("---")
st.subheader("📋 BAZA DANYCH - PEŁNA EDYCJA")
with st.expander("Otwórz panel zarządzania wierszami"):
    if not df_main.empty:
        df_edit = df_main.copy()
        df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
        df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
        
        edited = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
        if st.button("💾 ZAPISZ ZMIANY W GOOGLE SHEETS"):
            conn.update(worksheet="FLOTA_SQM", data=edited)
            st.rerun()
    else:
        st.info("Baza danych jest pusta.")
