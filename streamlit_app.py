import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="FLOTA SQM 2026", layout="wide", page_icon="🚚")

# Customowe style CSS dla lepszej czytelności i wyglądu
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    /* Stylizacja osi X - daty */
    [data-testid="stPlotlyChart"] .xtick text { 
        font-family: 'Arial Black', sans-serif !important;
        font-size: 11px !important;
        font-weight: 900 !important;
    }
    /* Nagłówki sekcji */
    .section-header {
        background-color: #1d3557;
        color: white;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. STAŁE I MAPOWANIA (POLSKA LOKALIZACJA) ---
PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}

PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]

# Święta ustawowe 2026
POLISH_HOLIDAYS = {
    "2026-01-01": "Nowy Rok", "2026-01-06": "Trzech Króli",
    "2026-04-05": "Wielkanoc", "2026-04-06": "Poniedziałek Wielkanocny",
    "2026-05-01": "Święto Pracy", "2026-05-03": "Święto Konstytucji",
    "2026-05-24": "Zesłanie Ducha Św.", "2026-06-04": "Boże Ciało",
    "2026-08-15": "Wniebowzięcie", "2026-11-01": "Wszystkich Świętych",
    "2026-11-11": "Święto Niepodległości", "2026-12-25": "Boże Narodzenie",
    "2026-12-26": "Drugi Dzień Świąt"
}

# --- 3. STRUKTURA FLOTY I ZASOBÓW ---
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
    "SPEDYCJA / RENTAL / INNE": [
        "SPEDYCJA 1", "SPEDYCJA 2", "SPEDYCJA 3", "SPEDYCJA 4", "SPEDYCJA 5", "AUTO RENTAL"
    ],
    "MIESZKANIA BCN": [
        "MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}

# Tworzenie płaskiej listy dla kategoryzacji i selectboxów
SORTED_VEHICLES = []
for cat, vehicles in VEHICLE_STRUCTURE.items():
    SORTED_VEHICLES.extend(vehicles)

# --- 4. FUNKCJE DANYCH ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_auto_status(start, end):
    today = datetime.now().date()
    s = start.date() if hasattr(start, 'date') else start
    e = end.date() if hasattr(end, 'date') else end
    if today < s: return "Oczekuje"
    elif s <= today <= e: return "W trasie"
    else: return "Wróciło"

def load_data():
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        df = df.dropna(how='all').copy()
        # Konwersja na datetime
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        # Filtrowanie błędnych dat
        df = df.dropna(subset=['Data_Start', 'Data_Koniec', 'Pojazd'])
        # Obliczanie statusu
        df['Status'] = df.apply(lambda x: get_auto_status(x['Data_Start'], x['Data_Koniec']), axis=1)
        return df
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        return pd.DataFrame()

# --- 5. LOGIKA APLIKACJI ---
st.title("🚚 SYSTEM LOGISTYCZNY SQM MULTIMEDIA")

df = load_data()

# Sidebar - Formularz dodawania
with st.sidebar:
    st.markdown('<div class="section-header">➕ DODAJ NOWY TRANSPORT</div>', unsafe_allow_html=True)
    with st.form("main_form", clear_on_submit=True):
        f_pojazd = st.selectbox("Pojazd / Zasób", SORTED_VEHICLES)
        f_projekt = st.text_input("Nazwa Projektu / Eventu")
        f_kierowca = st.text_input("Kierowca / Najemca")
        
        col1, col2 = st.columns(2)
        f_start = col1.date_input("Data Wyjazdu", value=datetime.now().date())
        f_end = col2.date_input("Data Powrotu", value=(datetime.now() + timedelta(days=3)).date())
        
        if st.form_submit_button("ZAPISZ W GRAFIKU"):
            new_entry = pd.DataFrame([{
                "Pojazd": f_pojazd, "Projekt": f_projekt, 
                "Kierowca": f_kierowca, "Data_Start": f_start, 
                "Data_Koniec": f_end
            }])
            current_df = conn.read(worksheet="FLOTA_SQM", ttl="0")
            updated_df = pd.concat([current_df, new_entry], ignore_index=True)
            conn.update(worksheet="FLOTA_SQM", data=updated_df)
            st.success("Zapisano!")
            st.rerun()

# --- 6. GŁÓWNY WYKRES GANTTA ---
st.subheader("🗓️ HARMONOGRAM OPERACYJNY 2026")

# Suwak zakresu czasu (Slider)
slider_range = [d.date() for d in pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')]
selected_dates = st.select_slider(
    "Ustaw zakres podglądu (przesuwaj oba końce suwaka):",
    options=slider_range,
    value=(datetime.now().date() - timedelta(days=3), datetime.now().date() + timedelta(days=18))
)
start_v, end_v = selected_dates

if not df.empty:
    df_viz = df.copy()
    # Margines 1 dnia dla Plotly, żeby paski kończyły się na końcowej dacie
    df_viz['Viz_End'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)
    
    # Sortowanie Kategoriami według zdefiniowanej struktury
    df_viz['Pojazd'] = pd.Categorical(df_viz['Pojazd'], categories=SORTED_VEHICLES, ordered=True)
    df_viz = df_viz.sort_values('Pojazd')

    # Tworzenie wykresu
    fig = px.timeline(
        df_viz, 
        x_start="Data_Start", x_end="Viz_End", y="Pojazd", 
        color="Projekt", # Każdy projekt ma unikalny kolor
        text="Projekt",
        hover_data={
            "Data_Start": "|%d %b", 
            "Data_Koniec": "|%d %b", 
            "Kierowca": True, 
            "Status": True,
            "Viz_End": False
        },
        template="plotly_white"
    )

    # Stylizacja etykiet na paskach (Długie, wyraźne napisy)
    fig.update_traces(
        textposition='inside', 
        insidetextanchor='middle',
        textfont=dict(size=14, family="Arial Black", color="white"),
        marker=dict(line=dict(width=1, color="white"))
    )

    # --- KONFIGURACJA OSI X (DATY, DNI, MIESIĄCE) ---
    view_days = pd.date_range(start=start_v, end=end_v)
    tick_vals = []
    tick_text = []
    last_m = -1

    for d in view_days:
        tick_vals.append(d)
        wd = PL_WEEKDAYS[d.weekday()]
        is_we = d.weekday() >= 5
        date_iso = d.strftime('%Y-%m-%d')
        is_hol = date_iso in POLISH_HOLIDAYS
        
        # Kolorystyka etykiet
        t_color = "black"
        if is_hol: t_color = "#e63946"
        elif is_we: t_color = "#8d99ae"

        # Etykieta: Dzień + Nazwa Dnia
        label = f"<b>{d.day}</b><br>{wd}"
        
        # Nazwa Miesiąca (tylko przy zmianie)
        if d.month != last_m:
            label = f"<span style='color:#1d3557'><b>{PL_MONTHS[d.month]}</b></span><br>{label}"
            last_m = d.month
            
        tick_text.append(f"<span style='color:{t_color}'>{label}</span>")

        # Cieniowanie weekendów i świąt w tle
        if is_we or is_hol:
            fig.add_vrect(
                x0=d, x1=d + timedelta(days=1),
                fillcolor="rgba(200, 200, 200, 0.15)" if is_we else "rgba(230, 57, 70, 0.1)",
                layer="below", line_width=0
            )

    # Linie oddzielające grupy pojazdów
    current_idx = 0
    for group_name, vehicles in VEHICLE_STRUCTURE.items():
        current_idx += len(vehicles)
        fig.add_hline(y=current_idx - 0.5, line_width=2, line_color="#ced4da")

    fig.update_xaxes(
        tickmode='array', 
        tickvals=tick_vals, 
        ticktext=tick_text, 
        side="top", 
        range=[pd.to_datetime(start_v), pd.to_datetime(end_v)],
        gridcolor="#f1f3f5"
    )

    fig.update_yaxes(
        autorange="reversed", 
        title="", 
        showgrid=True, 
        gridcolor="#f1f3f5",
        tickfont=dict(size=12)
    )

    # Linia "DZISIAJ"
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=3, line_color="#e63946", line_dash="dash")

    fig.update_layout(
        height=1100, 
        margin=dict(l=10, r=10, t=110, b=10), 
        showlegend=False,
        plot_bgcolor="white"
    )

    st.plotly_chart(fig, use_container_width=True)

# --- 7. TABELA EDYCJI I ZARZĄDZANIA ---
st.markdown("---")
with st.expander("🛠️ ZARZĄDZANIE DANYMI (EDYCJA / USUWANIE)"):
    if not df.empty:
        df_edit = df.copy()
        # Przygotowanie do edycji (czyste daty bez godziny)
        df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
        df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
        
        # Edytor tabeli
        edited_df = st.data_editor(
            df_edit, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "Status": st.column_config.TextColumn("Status (Auto)", disabled=True),
                "Data_Start": st.column_config.DateColumn("Wyjazd"),
                "Data_Koniec": st.column_config.DateColumn("Powrót"),
                "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=SORTED_VEHICLES)
            }
        )
        
        if st.button("💾 ZAPISZ ZMIANY W BAZIE"):
            # Przed zapisem upewniamy się, że nazwy kolumn się zgadzają z GS
            save_df = edited_df.drop(columns=['Status']) if 'Status' in edited_df else edited_df
            conn.update(worksheet="FLOTA_SQM", data=save_df)
            st.success("Baza została zaktualizowana!")
            st.rerun()
    else:
        st.info("Brak danych w arkuszu.")
