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
    page_title="LOGISTYKA SQM - HARMONOGRAM",
    layout="wide",
    page_icon="🚚"
)

# Custom CSS dla uzyskania wyglądu "Excel-like"
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        min-width: 350px !important;
    }
    /* Stylizacja tabeli edycji */
    .stDataEditor {
        border: 1px solid #cbd5e1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DEFINICJE I STRUKTURA (ZGODNIE ZE SCREENEM)
# ==========================================
VEHICLE_STRUCTURE = {
    "MIESZKANIA": {
        "color": "#ff00ff", # Magenta
        "list": ["MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"]
    },
    "OSOBÓWKI": {
        "color": "#94a3b8", # Szary
        "list": [
            "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", 
            "03 – Dacia Duster (biedak) – WE5A723", "04 – Dacia Jogger – WH6802A", 
            "06 – Dacia Duster – WH7087A ex T Białek", "FORD Transit Connect PY54635",
            "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", 
            "Chrysler Pacifica PY04266 - MBanasiak", "05 – Dacia Duster – WH7083A B.Krauze", 
            "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N", "Seat Ateca WZ445HU Dynasiuk", 
            "Seat Ateca WZ446HU- PM"
        ]
    },
    "BUSY": {
        "color": "#fdba74", # Pomarańczowy
        "list": [
            "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", 
            "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", 
            "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"
        ]
    },
    "CIĘŻARÓWKI": {
        "color": "#93c5fd", # Błękitny
        "list": [
            "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
            "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
        ]
    },
    "SPEDYCJA": {
        "color": "#6366f1", # Indigo
        "list": [f"SPEDYCJA {i}" for i in range(1, 11)]
    }
}

ALL_VEHICLES = []
for cat in VEHICLE_STRUCTURE.values():
    ALL_VEHICLES.extend(cat["list"])

PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["pon.", "wt.", "śr.", "czw.", "pt.", "sob.", "niedz."]

# ==========================================
# 3. POBIERANIE DANYCH
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty:
            return pd.DataFrame(columns=["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Kolor_Projektu"])
        
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        return df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
    except:
        return pd.DataFrame()

df_main = get_data()

# ==========================================
# 4. SIDEBAR - FORMULARZ
# ==========================================
with st.sidebar:
    st.header("➕ DODAJ WPIS")
    with st.form("add_event"):
        f_v = st.selectbox("Pojazd", ALL_VEHICLES)
        f_p = st.text_input("Nazwa Projektu / Kierowca")
        f_s = st.date_input("Start")
        f_e = st.date_input("Koniec")
        f_c = st.color_picker("Kolor na wykresie", "#3b82f6")
        
        if st.form_submit_button("ZAPISZ"):
            new_row = pd.DataFrame([{
                "Pojazd": f_v, "Projekt": f_p, 
                "Data_Start": f_s.strftime('%Y-%m-%d'), 
                "Data_Koniec": f_e.strftime('%Y-%m-%d'),
                "Kolor_Projektu": f_c
            }])
            old_df = conn.read(worksheet="FLOTA_SQM", ttl="0")
            updated_df = pd.concat([old_df, new_row], ignore_index=True)
            conn.update(worksheet="FLOTA_SQM", data=updated_df)
            st.rerun()

# ==========================================
# 5. GENEROWANIE WYKRESU (GANTT EXCEL STYLE)
# ==========================================
st.title("📊 HARMONOGRAM TRANSPORTU SQM")

# Wybór zakresu dat
col1, col2 = st.columns(2)
with col1:
    view_start = st.date_input("Widok od:", datetime.now().date() - timedelta(days=7))
with col2:
    view_end = st.date_input("Widok do:", view_start + timedelta(days=60))

if not df_main.empty:
    # Przygotowanie danych pod Timeline
    df_viz = df_main.copy()
    # Plotly potrzebuje daty końcowej o 1 dzień większej, by "domknąć" kwadrat dnia
    df_viz['Data_Koniec_Plot'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)
    
    # Sortowanie zgodnie z listą ALL_VEHICLES (kolejność z Excela)
    df_viz['Pojazd'] = pd.Categorical(df_viz['Pojazd'], categories=ALL_VEHICLES[::-1], ordered=True)
    df_viz = df_viz.sort_values('Pojazd')

    fig = px.timeline(
        df_viz, 
        x_start="Data_Start", 
        x_end="Data_Koniec_Plot", 
        y="Pojazd",
        text="Projekt",
        hover_data=["Projekt", "Data_Start", "Data_Koniec"]
    )

    # Mapowanie kolorów z kolumny Kolor_Projektu
    fig.update_traces(
        marker_color=df_viz['Kolor_Projektu'],
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=11, color="black", family="Arial Black"),
        marker_line_color="rgb(50,50,50)",
        marker_line_width=1
    )

    # --- OSI I SIATKA ---
    date_range = pd.date_range(view_start, view_end)
    
    # Budowa etykiet osi X (Dzień + Nazwa dnia)
    tick_vals = [d for d in date_range]
    tick_text = []
    for d in date_range:
        label = f"{d.day}<br>{PL_WEEKDAYS[d.weekday()]}"
        # Dodaj nazwę miesiąca nad pierwszym dniem miesiąca
        if d.day == 1 or d == date_range[0]:
            label = f"<b>{PL_MONTHS[d.month]}</b><br>{label}"
        tick_text.append(label)

    fig.update_layout(
        xaxis=dict(
            side="top",
            tickmode='array',
            tickvals=tick_vals,
            ticktext=tick_text,
            range=[view_start, view_end],
            gridcolor="#e2e8f0",
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            gridcolor="#e2e8f0",
            showgrid=True,
            title=""
        ),
        height=len(ALL_VEHICLES) * 30 + 150,
        margin=dict(l=10, r=10, t=100, b=20),
        plot_bgcolor="white",
        showlegend=False
    )

    # Dodanie pasów tła dla kategorii (jak w Excelu)
    y_idx = 0
    for cat_name, cat_data in VEHICLE_STRUCTURE.items():
        n_vehicles = len(cat_data["list"])
        # Dodajemy prostokąt w tle dla nazw pojazdów (opcjonalnie)
        fig.add_hrect(
            y0=y_idx - 0.5, 
            y1=y_idx + n_vehicles - 0.5, 
            fillcolor=cat_data["color"], 
            opacity=0.15, 
            layer="below", 
            line_width=0
        )
        y_idx += n_vehicles

    # Linia "Dzisiaj"
    fig.add_vline(x=datetime.now().date(), line_width=3, line_color="red", line_dash="dash")

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# 6. TABELA EDYCJI (POD WYKRESEM)
# ==========================================
st.markdown("---")
st.subheader("📋 ZARZĄDZANIE DANYMI")

if not df_main.empty:
    # Przygotowanie do edytora
    df_editor = df_main.copy()
    df_editor['Data_Start'] = df_editor['Data_Start'].dt.date
    df_editor['Data_Koniec'] = df_editor['Data_Koniec'].dt.date
    
    edited_df = st.data_editor(
        df_editor,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_VEHICLES),
            "Kolor_Projektu": st.column_config.ColorColumn("Kolor"),
            "Data_Start": st.column_config.DateColumn("Start"),
            "Data_Koniec": st.column_config.DateColumn("Koniec")
        }
    )

    if st.button("💾 ZAPISZ ZMIANY W ARKUSZU"):
        # Konwersja z powrotem na stringi przed zapisem
        final_save = edited_df.copy()
        final_save['Data_Start'] = final_save['Data_Start'].apply(lambda x: x.strftime('%Y-%m-%d'))
        final_save['Data_Koniec'] = final_save['Data_Koniec'].apply(lambda x: x.strftime('%Y-%m-%d'))
        conn.update(worksheet="FLOTA_SQM", data=final_save)
        st.success("Zapisano!")
        st.rerun()
