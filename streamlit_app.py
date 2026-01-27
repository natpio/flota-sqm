import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

# ==========================================
# 1. KONFIGURACJA I STYLE (TYLKO NIEZBĘDNE)
# ==========================================
st.set_page_config(
    page_title="LOGISTYKA SQM",
    layout="wide",
    page_icon="🚚"
)

st.markdown("""
    <style>
    .stApp { background-color: #f4f4f4; }
    [data-testid="stSidebar"] { background-color: #111827 !important; min-width: 400px !important; }
    .stSelectbox label, .stTextInput label, .stDateInput label { color: white !important; }
    .conflict-alert {
        background-color: #ffcccc; border: 1px solid red;
        padding: 10px; border-radius: 5px; color: black; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. PEŁNA STRUKTURA FLOTY SQM
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
    "SPEDYCJA / RENTAL": ["SPEDYCJA 1", "SPEDYCJA 2", "SPEDYCJA 3", "SPEDYCJA 4", "AUTO RENTAL"],
    "MIESZKANIA BCN": ["MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"]
}

ALL_VEHICLES = [v for sub in VEHICLE_STRUCTURE.values() for v in sub]

# Stałe czasu
PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

# ==========================================
# 3. POŁĄCZENIE I POBIERANIE DANYCH
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty:
            return pd.DataFrame(columns=["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Uwagi"])
        # Czyszczenie
        df.columns = [str(c).strip() for c in df.columns]
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
        return df
    except Exception as e:
        st.error(f"Błąd bazy: {e}")
        return pd.DataFrame()

df_main = get_data()

# Sprawdzanie kolizji
def has_collision(df, veh, start, end):
    if df.empty: return None
    s, e = pd.to_datetime(start), pd.to_datetime(end)
    collision = df[(df['Pojazd'] == veh) & (df['Data_Start'] <= e) & (df['Data_Koniec'] >= s)]
    return collision if not collision.empty else None

# ==========================================
# 4. SIDEBAR - DODAWANIE
# ==========================================
with st.sidebar:
    st.header("➕ NOWY TRANSPORT")
    with st.form("add_form", clear_on_submit=True):
        f_veh = st.selectbox("Pojazd", ALL_VEHICLES)
        f_proj = st.text_input("Projekt")
        f_driver = st.text_input("Kierowca / Załadunek")
        c1, c2 = st.columns(2)
        f_s = c1.date_input("Start")
        f_e = c2.date_input("Koniec", value=datetime.now() + timedelta(days=2))
        f_u = st.text_area("Uwagi")
        
        conflict = has_collision(df_main, f_veh, f_s, f_e)
        if conflict is not None:
            st.error(f"KOLIZJA: {conflict.iloc[0]['Projekt']}")
            
        if st.form_submit_button("DODAJ", use_container_width=True):
            if not f_proj:
                st.warning("Wpisz projekt")
            elif conflict is not None:
                st.error("Nie można zapisać - kolizja")
            else:
                new_row = pd.DataFrame([{
                    "Pojazd": f_veh, "Projekt": f_proj, "Kierowca": f_driver,
                    "Data_Start": f_s.strftime('%Y-%m-%d'),
                    "Data_Koniec": f_e.strftime('%Y-%m-%d'),
                    "Uwagi": f_u
                }])
                actual = conn.read(worksheet="FLOTA_SQM", ttl="0")
                updated = pd.concat([actual, new_row], ignore_index=True)
                conn.update(worksheet="FLOTA_SQM", data=updated)
                st.rerun()

# ==========================================
# 5. WIZUALIZACJA - GANTT
# ==========================================
st.title("🚚 GRAFIK FLOTY SQM")

# Alerty konfliktów w bazie
if not df_main.empty:
    for v in df_main['Pojazd'].unique():
        v_df = df_main[df_main['Pojazd'] == v].sort_values('Data_Start')
        for i in range(len(v_df)-1):
            if v_df.iloc[i]['Data_Koniec'] >= v_df.iloc[i+1]['Data_Start']:
                st.markdown(f'<div class="conflict-alert">⚠️ Kolizja: {v} ({v_df.iloc[i]["Projekt"]} / {v_df.iloc[i+1]["Projekt"]})</div>', unsafe_allow_html=True)

# Suwak zakresu
time_opts = [d.date() for d in pd.date_range("2026-01-01", "2026-12-31")]
v_range = st.select_slider("Zakres:", options=time_opts, value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=21)))

if not df_main.empty:
    df_v = df_main.copy()
    df_v['Plot_End'] = df_v['Data_Koniec'] + pd.Timedelta(days=1)
    df_v['Pojazd'] = pd.Categorical(df_v['Pojazd'], categories=ALL_VEHICLES, ordered=True)
    df_v = df_v.sort_values('Pojazd')

    fig = px.timeline(
        df_v, x_start="Data_Start", x_end="Plot_End", y="Pojazd", color="Projekt", text="Projekt",
        hover_data={"Kierowca": True, "Uwagi": True, "Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m"},
        template="plotly_white"
    )
    
    fig.update_traces(textposition='inside', insidetextanchor='middle', textfont=dict(size=14, family="Arial Black", color="white"))

    # Oś X i polskie daty
    t_days = pd.date_range(v_range[0], v_range[1])
    tick_v, tick_t, last_m = [], [], -1
    for d in t_days:
        tick_v.append(d)
        is_we, is_ho = d.weekday() >= 5, d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        clr = "red" if is_ho else ("gray" if is_we else "black")
        lbl = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
        if d.month != last_m:
            lbl = f"<b>{PL_MONTHS[d.month]}</b><br>{lbl}"
            last_m = d.month
        tick_t.append(f"<span style='color:{clr}'>{lbl}</span>")
        if is_we or is_ho:
            fig.add_vrect(x0=d, x1=d+timedelta(days=1), fillcolor="rgba(0,0,0,0.05)", layer="below", line_width=0)

    # Separatory
    y_sep = 0
    for g, m in VEHICLE_STRUCTURE.items():
        y_sep += len(m)
        fig.add_hline(y=y_sep - 0.5, line_width=1, line_color="lightgray")

    fig.update_xaxes(tickmode='array', tickvals=tick_v, ticktext=tick_t, side="top", range=[v_range[0], v_range[1]])
    fig.update_yaxes(autorange="reversed", title="")
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_color="red", line_dash="dash")
    fig.update_layout(height=1200, margin=dict(l=10, r=10, t=100, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. PANEL EDYCJI (ROZWIĄZANIE BŁĘDU)
# ==========================================
st.markdown("---")
st.subheader("⚙️ EDYCJA REJESTRU")

if not df_main.empty:
    # Kluczowe dla StreamlitAPIException:
    df_ed = df_main.copy()
    df_ed['Data_Start'] = df_ed['Data_Start'].dt.date
    df_ed['Data_Koniec'] = df_ed['Data_Koniec'].dt.date

    try:
        edited = st.data_editor(
            df_ed,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_VEHICLES, required=True),
                "Data_Start": st.column_config.DateColumn("Wyjazd", required=True),
                "Data_Koniec": st.column_config.DateColumn("Powrót", required=True)
            }
        )
        
        if st.button("ZAPISZ ZMIANY W GOOGLE SHEETS"):
            # Konwersja do stringów dla GSheets
            save_df = edited.copy()
            save_df['Data_Start'] = save_df['Data_Start'].apply(lambda x: x.strftime('%Y-%m-%d'))
            save_df['Data_Koniec'] = save_df['Data_Koniec'].apply(lambda x: x.strftime('%Y-%m-%d'))
            conn.update(worksheet="FLOTA_SQM", data=save_df)
            st.success("Zapisano")
            st.rerun()
    except Exception as e:
        st.error(f"Błąd edytora: {e}")
else:
    st.info("Baza jest pusta")
