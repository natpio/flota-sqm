import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURACJA STRONY
# ==========================================
st.set_page_config(
    page_title="LOGISTYKA SQM",
    layout="wide",
    page_icon="🚚"
)

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #1e293b !important; min-width: 350px !important; }
    .stDataEditor { border: 1px solid #cbd5e1 !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DEFINICJE I STRUKTURA
# ==========================================
VEHICLE_STRUCTURE = {
    "MIESZKANIA": {"color": "#ff00ff", "list": ["MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"]},
    "OSOBÓWKI": {"color": "#e2e8f0", "list": [
        "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723", 
        "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek", "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", "Chrysler Pacifica PY04266 - MBanasiak", 
        "05 – Dacia Duster – WH7083A B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N", 
        "Seat Ateca WZ445HU Dynasiuk", "Seat Ateca WZ446HU- PM"
    ]},
    "BUSY": {"color": "#ffedd5", "list": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", "BOXER - WZ213GF", 
        "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", 
        "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"
    ]},
    "CIĘŻARÓWKI": {"color": "#dbeafe", "list": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ]},
    "SPEDYCJA": {"color": "#e0e7ff", "list": [f"SPEDYCJA {i}" for i in range(1, 11)]}
}

ALL_VEHICLES = []
for cat in VEHICLE_STRUCTURE.values():
    ALL_VEHICLES.extend(cat["list"])

PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["pon.", "wt.", "śr.", "czw.", "pt.", "sob.", "niedz."]

# ==========================================
# 3. POBIERANIE DANYCH (Z FIXEM KEYERROR)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data_safe():
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df is None or df.empty:
            return pd.DataFrame(columns=["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Kolor_Projektu"])
        
        # Zabezpieczenie przed brakiem kolumn
        required_columns = ["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Kolor_Projektu"]
        for col in required_columns:
            if col not in df.columns:
                df[col] = "#3b82f6" if col == "Kolor_Projektu" else ""
        
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        return df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
    except Exception as e:
        st.error(f"Błąd danych: {e}")
        return pd.DataFrame()

df_main = get_data_safe()

# ==========================================
# 4. SIDEBAR
# ==========================================
with st.sidebar:
    st.header("➕ NOWY TRANSPORT")
    with st.form("add_event"):
        f_v = st.selectbox("Pojazd", ALL_VEHICLES)
        f_p = st.text_input("Nazwa Projektu / Miejsce")
        f_k = st.text_input("Kierowca")
        f_s = st.date_input("Start")
        f_e = st.date_input("Koniec", value=datetime.now() + timedelta(days=3))
        f_c = st.color_picker("Kolor paska", "#facc15") # Domyślnie żółty jak w Excelu
        
        if st.form_submit_button("DODAJ DO HARMONOGRAMU"):
            new_row = pd.DataFrame([{
                "Pojazd": f_v, "Projekt": f_p, "Kierowca": f_k,
                "Data_Start": f_s.strftime('%Y-%m-%d'), 
                "Data_Koniec": f_e.strftime('%Y-%m-%d'),
                "Kolor_Projektu": f_c
            }])
            # Pobierz aktualne, doklej nowe i wyślij
            current_df = conn.read(worksheet="FLOTA_SQM", ttl="0")
            updated_df = pd.concat([current_df, new_row], ignore_index=True)
            conn.update(worksheet="FLOTA_SQM", data=updated_df)
            st.success("Dodano!")
            st.rerun()

# ==========================================
# 5. WYKRES GANTT
# ==========================================
st.title("🚚 LOGISTYKA SQM: HARMONOGRAM")

col1, col2 = st.columns(2)
with col1:
    view_start = st.date_input("Widok od:", datetime.now().date() - timedelta(days=5))
with col2:
    view_end = st.date_input("Widok do:", view_start + timedelta(days=45))

if not df_main.empty:
    df_viz = df_main.copy()
    df_viz['Data_Koniec_Plot'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)
    
    # Kolejność pojazdów zgodna z Twoją listą (od góry do dołu)
    df_viz['Pojazd'] = pd.Categorical(df_viz['Pojazd'], categories=ALL_VEHICLES[::-1], ordered=True)
    df_viz = df_viz.sort_values('Pojazd')

    fig = px.timeline(
        df_viz, 
        x_start="Data_Start", x_end="Data_Koniec_Plot", y="Pojazd",
        text="Projekt",
        hover_data=["Kierowca", "Data_Start", "Data_Koniec"]
    )

    # Aplikacja kolorów z arkusza
    fig.update_traces(
        marker_color=df_viz['Kolor_Projektu'],
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=12, color="black", family="Arial Black"),
        marker_line_color="black",
        marker_line_width=0.5
    )

    # Ustawienia kalendarza (Oś X)
    date_range = pd.date_range(view_start, view_end)
    tick_vals = [d for d in date_range]
    tick_text = []
    for d in date_range:
        day_info = f"{d.day}<br>{PL_WEEKDAYS[d.weekday()]}"
        if d.day == 1 or d == date_range[0]:
            day_info = f"<b>{PL_MONTHS[d.month]}</b><br>{day_info}"
        tick_text.append(day_info)

    fig.update_layout(
        xaxis=dict(
            side="top", tickmode='array', tickvals=tick_vals, ticktext=tick_text,
            range=[view_start, view_end], gridcolor="#f1f5f9", showgrid=True
        ),
        yaxis=dict(gridcolor="#f1f5f9", showgrid=True, title=""),
        height=len(ALL_VEHICLES) * 35 + 150,
        margin=dict(l=10, r=10, t=100, b=20),
        plot_bgcolor="white"
    )

    # Linia dnia dzisiejszego
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_color="red")

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# 6. EDYCJA
# ==========================================
st.markdown("---")
with st.expander("🛠️ EDYCJA DANYCH I KOLORÓW"):
    df_editor = df_main.copy()
    df_editor['Data_Start'] = df_editor['Data_Start'].dt.date
    df_editor['Data_Koniec'] = df_editor['Data_Koniec'].dt.date
    
    edited_df = st.data_editor(
        df_editor,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_VEHICLES),
            "Kolor_Projektu": st.column_config.ColorColumn("Kolor paska"),
            "Data_Start": st.column_config.DateColumn("Start"),
            "Data_Koniec": st.column_config.DateColumn("Koniec")
        }
    )

    if st.button("💾 ZAPISZ ZMIANY W BAZIE"):
        final_save = edited_df.copy()
        for col in ['Data_Start', 'Data_Koniec']:
            final_save[col] = pd.to_datetime(final_save[col]).dt.strftime('%Y-%m-%d')
        conn.update(worksheet="FLOTA_SQM", data=final_save)
        st.success("Zaktualizowano arkusz!")
        st.rerun()
