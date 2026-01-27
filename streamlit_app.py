import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="FLOTA SQM 2026", layout="wide", page_icon="🚚")

# Słownik polskich miesięcy i dni
PL_MONTHS = {
    1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 
    5: "MAJ", 6: "CZERWIEC", 7: "LIPIEC", 8: "SIERPIEŃ", 
    9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"
}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]

# Lista świąt ustawowych w Polsce 2026
POLISH_HOLIDAYS = {
    "2026-01-01": "Nowy Rok", "2026-01-06": "Trzech Króli",
    "2026-04-05": "Wielkanoc", "2026-04-06": "Poniedziałek Wielkanocny",
    "2026-05-01": "Święto Pracy", "2026-05-03": "Święto Konstytucji",
    "2026-05-24": "Zesłanie Ducha Św.", "2026-06-04": "Boże Ciało",
    "2026-08-15": "Wniebowzięcie / Wojska Polskiego", "2026-11-01": "Wszystkich Świętych",
    "2026-11-11": "Święto Niepodległości", "2026-12-25": "Boże Narodzenie",
    "2026-12-26": "Drugi Dzień Świąt"
}

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stPlotlyChart"] .xtick text { 
        font-family: 'Arial Black', sans-serif !important;
        font-size: 11px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 FLOTA SQM 2026")

# 2. POŁĄCZENIE Z BAZĄ
conn = st.connection("gsheets", type=GSheetsConnection)

def get_auto_status(start, end):
    today = datetime.now().date()
    s = start.date() if hasattr(start, 'date') else start
    e = end.date() if hasattr(end, 'date') else end
    if today < s: return "Oczekuje"
    elif s <= today <= e: return "W trakcie"
    else: return "Wróciło"

def load_data():
    df = conn.read(worksheet="FLOTA_SQM", ttl="0")
    df = df.dropna(how='all').copy()
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    df = df.dropna(subset=['Data_Start', 'Data_Koniec'])
    df['Status'] = df.apply(lambda x: get_auto_status(x['Data_Start'], x['Data_Koniec']), axis=1)
    return df

df = load_data()

# 3. SIDEBAR
with st.sidebar:
    st.header("⚙️ Nowy Event")
    with st.form("add_form", clear_on_submit=True):
        pojazd = st.selectbox("Pojazd", [
            "31 - TIR P21V388/P22X300 STABLEWSKI", "TIR 2 - W2654FT/P22H972 KOGUS",
            "TIR 3 - PNT3530A/P24U343 DANIELAK", "44 - SOLO PY 73262",
            "25 - Jumper - PY22952", "24 - Jumper - PY22954", "BOXER - PO 5VT68",
            "OPEL DW4W443", "SPEDYCJA"
        ])
        event_name = st.text_input("Nazwa Eventu")
        kierowca = st.text_input("Kierowca")
        d_start = st.date_input("Wyjazd", value=datetime.now().date())
        d_end = st.date_input("Powrót", value=(datetime.now() + timedelta(days=2)).date())
        
        if st.form_submit_button("ZAPISZ"):
            new_row = pd.DataFrame([{"Pojazd": pojazd, "Projekt": event_name, "Kierowca": kierowca,
                                     "Data_Start": d_start.strftime('%Y-%m-%d'), 
                                     "Data_Koniec": d_end.strftime('%Y-%m-%d')}])
            current = conn.read(worksheet="FLOTA_SQM", ttl="0")
            conn.update(worksheet="FLOTA_SQM", data=pd.concat([current, new_row], ignore_index=True))
            st.rerun()

# 4. FILTR ZAKRESU DAT (SUWAK)
st.subheader("🗓️ Harmonogram Operacyjny")

slider_options = [d.date() for d in pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')]
default_start = datetime.now().date() - timedelta(days=2)
default_end = datetime.now().date() + timedelta(days=21)

col_slider, _ = st.columns([0.6, 0.4])
with col_slider:
    selected_range = st.select_slider(
        "Przesuń, aby zmienić zakres podglądu:",
        options=slider_options,
        value=(default_start, default_end)
    )
    start_view, end_view = selected_range

if not df.empty:
    start_dt = pd.to_datetime(start_view)
    end_dt = pd.to_datetime(end_view)
    
    df_viz = df.copy()
    df_viz['Viz_End'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)

    fig = px.timeline(
        df_viz, x_start="Data_Start", x_end="Viz_End", y="Pojazd", 
        color="Projekt", text="Projekt",
        hover_data={"Data_Start": "|%d.%m (%a)", "Data_Koniec": "|%d.%m (%a)", "Status": True, "Projekt": False, "Viz_End": False}
    )

    # --- GENEROWANIE ZAAWANSOWANEJ OSI X ---
    current_range = pd.date_range(start=start_view, end=end_view)
    tick_vals = []
    tick_text = []
    last_month = -1

    for d in current_range:
        tick_vals.append(d)
        wd = PL_WEEKDAYS[d.weekday()]
        date_str = d.strftime('%Y-%m-%d')
        
        # Kolor i styl dla weekendów i świąt
        is_holiday = date_str in POLISH_HOLIDAYS
        is_weekend = d.weekday() >= 5 # 5=Sb, 6=Nd
        
        color = "black"
        if is_holiday: color = "#D62828" # Czerwony dla świąt
        elif is_weekend: color = "#666666" # Szary dla weekendu
        
        # Budowa etykiety (Dzień + Nazwa dnia)
        label = f"<b>{d.day}</b><br>{wd}"
        
        # Dodanie nazwy miesiąca na początku
        if d.month != last_month:
            label = f"<span style='color:#1D3557'><b>{PL_MONTHS[d.month]}</b></span><br>" + label
            last_month = d.month
            
        tick_text.append(f"<span style='color:{color}'>{label}</span>")

        # Zaznaczenie weekendów i świąt w tle wykresu (vrect)
        if is_holiday or is_weekend:
            fig.add_vrect(
                x0=d, x1=d + timedelta(days=1),
                fillcolor="rgba(200, 200, 200, 0.2)" if is_weekend else "rgba(255, 0, 0, 0.1)",
                layer="below", line_width=0,
            )

    fig.update_xaxes(
        tickmode='array',
        tickvals=tick_vals,
        ticktext=tick_text,
        gridcolor="#EEEEEE",
        side="top",
        range=[start_dt, end_dt]
    )

    fig.update_yaxes(autorange="reversed", gridcolor="#F5F5F5", title="")
    
    # Pionowa linia DZISIAJ
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=3, line_color="#E63946", line_dash="dash")

    fig.update_layout(
        height=600,
        margin=dict(l=10, r=10, t=110, b=10),
        showlegend=False,
        plot_bgcolor="white"
    )

    st.plotly_chart(fig, use_container_width=True)

# 5. TABELA EDYCJI
st.markdown("---")
with st.expander("📝 Lista Eventów i Edycja danych"):
    df_edit = df.copy()
    df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
    df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
    df_edit = df_edit.rename(columns={"Projekt": "Event"})
    
    edited = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
    if st.button("💾 ZAPISZ ZMIANY W BAZIE"):
        conn.update(worksheet="FLOTA_SQM", data=edited.rename(columns={"Event": "Projekt"}))
        st.success("Baza zaktualizowana!")
        st.rerun()
