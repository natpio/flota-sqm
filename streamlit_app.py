import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="FLOTA SQM 2026", layout="wide", page_icon="🚚")

# Słowniki pomocnicze
PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]

POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

# 2. DEFINICJA STRUKTURY FLOTY
VEHICLE_STRUCTURE = {
    "--- OSOBÓWKI ---": [
        "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek", "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", "Chrysler Pacifica PY04266 - MBanasiak",
        "05 – Dacia Duster – WH7083A B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "Seat Ateca WZ445HU Dynasiuk", "Seat Ateca WZ446HU- PM"
    ],
    "--- BUSY ---": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", "BOXER - WZ213GF",
        "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24",
        "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"
    ],
    "--- CIĘŻARÓWKI / TIR ---": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "--- SPEDYCJA / RENTAL ---": [
        "SPEDYCJA 1", "SPEDYCJA 2", "SPEDYCJA 3", "SPEDYCJA 4", "AUTO RENTAL"
    ],
    "--- MIESZKANIA BCN ---": [
        "MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}

# Lista bazowa do sortowania
BASE_ORDER = []
for group, vehicles in VEHICLE_STRUCTURE.items():
    BASE_ORDER.append(group)
    BASE_ORDER.extend(vehicles)

# 3. POŁĄCZENIE Z BAZĄ I DANE
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(worksheet="FLOTA_SQM", ttl="0")
    df = df.dropna(how='all').copy()
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    return df.dropna(subset=['Data_Start', 'Data_Koniec', 'Pojazd'])

df = load_data()

# Dodajemy ewentualne brakujące auta z GS do listy, by się wyświetliły
gs_vehicles = df['Pojazd'].unique().tolist()
FINAL_ORDER = BASE_ORDER + [v for v in gs_vehicles if v not in BASE_ORDER]

# 4. SIDEBAR - FORMULARZ
with st.sidebar:
    st.header("⚙️ Nowy Event")
    with st.form("add_form", clear_on_submit=True):
        pojazd = st.selectbox("Wybierz Pojazd", [v for v in BASE_ORDER if not v.startswith("---")])
        event_name = st.text_input("Nazwa Eventu")
        kierowca = st.text_input("Kierowca / Uwagi")
        d_start = st.date_input("Wyjazd", value=datetime.now().date())
        d_end = st.date_input("Powrót", value=(datetime.now() + timedelta(days=2)).date())
        
        if st.form_submit_button("DODAJ DO GRAFIKU"):
            new_row = pd.DataFrame([{"Pojazd": pojazd, "Projekt": event_name, "Kierowca": kierowca,
                                     "Data_Start": d_start.strftime('%Y-%m-%d'), 
                                     "Data_Koniec": d_end.strftime('%Y-%m-%d')}])
            current = conn.read(worksheet="FLOTA_SQM", ttl="0")
            conn.update(worksheet="FLOTA_SQM", data=pd.concat([current, new_row], ignore_index=True))
            st.rerun()

# 5. GŁÓWNY PANEL - WYKRES
st.title("🚚 GRAFIK FLOTY SQM 2026")

# Suwak zakresu
slider_opts = [d.date() for d in pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')]
selected_range = st.select_slider("Zakres podglądu:", options=slider_opts, 
                                  value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=21)))

if not df.empty:
    df_viz = df.copy()
    df_viz['Viz_End'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)
    
    # Sortowanie wg struktury
    df_viz['Pojazd'] = pd.Categorical(df_viz['Pojazd'], categories=FINAL_ORDER, ordered=True)
    df_viz = df_viz.sort_values('Pojazd')

    fig = px.timeline(
        df_viz, x_start="Data_Start", x_end="Viz_End", y="Pojazd", 
        color="Projekt", text="Projekt",
        hover_data={"Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m", "Kierowca": True, "Projekt": False, "Viz_End": False}
    )

    # Stylizacja etykiet na paskach
    fig.update_traces(
        textposition='inside', 
        insidetextanchor='middle',
        textfont=dict(size=14, family="Arial Black", color="white")
    )

    # Oś X: Polskie daty, miesiące i weekendy
    view_days = pd.date_range(start=selected_range[0], end=selected_range[1])
    tick_vals, tick_text, last_m = [], [], -1

    for d in view_days:
        tick_vals.append(d)
        is_we = d.weekday() >= 5
        is_hol = d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        
        color = "black"
        if is_hol: color = "red"
        elif is_we: color = "#999999"

        label = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
        if d.month != last_m:
            label = f"<span style='color:blue'><b>{PL_MONTHS[d.month]}</b></span><br>{label}"
            last_m = d.month
            
        tick_text.append(f"<span style='color:{color}'>{label}</span>")
        if is_we or is_hol:
            fig.add_vrect(x0=d, x1=d + timedelta(days=1), fillcolor="rgba(200,200,200,0.15)", layer="below", line_width=0)

    # Linie oddzielające grupy
    current_y = 0
    for group, vehicles in VEHICLE_STRUCTURE.items():
        current_y += len(vehicles)
        fig.add_hline(y=current_y - 0.5, line_width=1, line_color="#cccccc")

    fig.update_xaxes(tickmode='array', tickvals=tick_vals, ticktext=tick_text, side="top", range=[selected_range[0], selected_range[1]])
    fig.update_yaxes(autorange="reversed", title="", showgrid=True, gridcolor="#f9f9f9")
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_color="red", line_dash="dash")

    fig.update_layout(height=1100, margin=dict(l=10, r=10, t=110, b=10), showlegend=False, plot_bgcolor="white")

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Brak aktywnych eventów w arkuszu FLOTA_SQM.")

# 6. TABELA EDYCJI
with st.expander("📝 Tabela pomocnicza (Edycja i Podgląd surowych danych)"):
    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("Zapisz zmiany w tabeli"):
        conn.update(worksheet="FLOTA_SQM", data=edited_df)
        st.rerun()
