import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="FLOTA SQM 2026", layout="wide", page_icon="🚚")

PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

# TWOJA LISTA POJAZDÓW
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
    "SPEDYCJA / RENTAL": ["SPEDYCJA 1", "SPEDYCJA 2", "SPEDYCJA 3", "SPEDYCJA 4", "AUTO RENTAL"],
    "MIESZKANIA BCN": ["MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"]
}

BASE_LIST = [item for sublist in VEHICLE_STRUCTURE.values() for item in sublist]

# 2. POŁĄCZENIE
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(worksheet="FLOTA_SQM", ttl="0")
    df = df.dropna(how='all').copy()
    # Konwersja dat z wymuszeniem formatu
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    df = df.dropna(subset=['Data_Start', 'Data_Koniec', 'Pojazd'])
    return df

df = load_data()

# DYNAMICZNA LISTA (Jeśli w GS są inne nazwy, dodaj je na koniec)
existing_in_gs = df['Pojazd'].unique().tolist()
DYNAMIC_VEHICLE_LIST = BASE_LIST + [v for v in existing_in_gs if v not in BASE_LIST]

# 3. SIDEBAR
with st.sidebar:
    st.header("⚙️ Nowy Event")
    with st.form("add_form", clear_on_submit=True):
        pojazd = st.selectbox("Pojazd", DYNAMIC_VEHICLE_LIST)
        event_name = st.text_input("Nazwa Eventu")
        kierowca = st.text_input("Kierowca")
        d_start = st.date_input("Od", value=datetime.now().date())
        d_end = st.date_input("Do", value=(datetime.now() + timedelta(days=2)).date())
        if st.form_submit_button("ZAPISZ"):
            new_row = pd.DataFrame([{"Pojazd": pojazd, "Projekt": event_name, "Kierowca": kierowca,
                                     "Data_Start": d_start.strftime('%Y-%m-%d'), 
                                     "Data_Koniec": d_end.strftime('%Y-%m-%d')}])
            conn.update(worksheet="FLOTA_SQM", data=pd.concat([conn.read(worksheet="FLOTA_SQM", ttl="0"), new_row], ignore_index=True))
            st.rerun()

# 4. GRAFIK
st.title("🚚 FLOTA SQM 2026")

slider_options = [d.date() for d in pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')]
selected_range = st.select_slider("Zakres podglądu:", options=slider_options, 
                                  value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=21)))

if not df.empty:
    df_viz = df.copy()
    # Filtracja danych pod zakres suwaka, żeby nie muliło
    mask = (df_viz['Data_Koniec'] >= pd.Timestamp(selected_range[0])) & (df_viz['Data_Start'] <= pd.Timestamp(selected_range[1]))
    df_viz = df_viz[mask]
    
    df_viz['Viz_End'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)
    df_viz['Pojazd'] = pd.Categorical(df_viz['Pojazd'], categories=DYNAMIC_VEHICLE_LIST, ordered=True)
    df_viz = df_viz.sort_values('Pojazd')

    fig = px.timeline(
        df_viz, x_start="Data_Start", x_end="Viz_End", y="Pojazd", color="Projekt", text="Projekt",
        hover_data={"Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m", "Kierowca": True, "Projekt": False}
    )

    fig.update_traces(textposition='inside', insidetextanchor='middle', 
                      textfont=dict(size=14, family="Arial Black", color="white"))

    # Oś X
    tick_days = pd.date_range(start=selected_range[0], end=selected_range[1])
    tick_vals, tick_text, last_m = [], [], -1
    for d in tick_days:
        tick_vals.append(d)
        is_we = d.weekday() >= 5
        is_hol = d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        label = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
        if d.month != last_m:
            label = f"<span style='color:blue'><b>{PL_MONTHS[d.month]}</b></span><br>{label}"
            last_m = d.month
        tick_text.append(f"<span style='color:{'red' if is_hol else ('#888' if is_we else 'black')}'>{label}</span>")
        if is_we or is_hol:
            fig.add_vrect(x0=d, x1=d + timedelta(days=1), fillcolor="rgba(200,200,200,0.15)", layer="below", line_width=0)

    fig.update_xaxes(tickmode='array', tickvals=tick_vals, ticktext=tick_text, side="top", range=[selected_range[0], selected_range[1]])
    fig.update_yaxes(autorange="reversed", title="")
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_color="red", line_dash="dash")
    fig.update_layout(height=1100, showlegend=False, plot_bgcolor="white", margin=dict(l=10, r=10, t=100, b=10))

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Brak danych do wyświetlenia w wybranym zakresie.")

with st.expander("📝 Edycja"):
    st.data_editor(df, use_container_width=True)
