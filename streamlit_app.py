import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony
st.set_page_config(page_title="SQM Fleet Control", page_icon="🚛", layout="wide")

# 2. DEFINICJA ZASOBÓW (Stała lista osi Y)
FLOTA_SQM = {
    "FTL / SOLO": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "BUS / DOSTAWCZE": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68",
        "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF",
        "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45",
        "BOXER DW9WK54 wysoki", "OPEL DW9WK53", "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637"
    ],
    "OSOBOWE": [
        "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa",
        "03 – Dacia Duster (biedak) – WE5A723", "04 – Dacia Jogger – WH6802A",
        "06 – Dacia Duster – WH7087A ex T Białek", "05 – Dacia Duster – WH7083A   B.Krauze",
        "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N", "Chrysler Pacifica PY04266 - MBanasiak",
        "Seat Ateca WZ445HU  Dynasiuk", "Seat Ateca WZ446HU- PM", "SPEDYCJA", "AUTO RENTAL - CARVIDO"
    ],
    "MIESZKANIA": [
        "MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}

ALL_RESOURCES = []
for items in FLOTA_SQM.values():
    ALL_RESOURCES.extend(items)

# 3. Połączenie z danymi
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        data.columns = [c.strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        for col in ['pojazd', 'event', 'kierowca', 'notatka']:
            data[col] = data[col].astype(str).replace(['nan', 'None', '<NA>'], '')
        return data[data['pojazd'] != ""].reset_index(drop=True)
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = load_data()

st.title("🛰️ SQM Logistics Control Center")

if not df.empty:
    # --- KOLORY ---
    unique_events = sorted(df['event'].unique())
    color_map = {ev: px.colors.qualitative.Prism[i % len(px.colors.qualitative.Prism)] for i, ev in enumerate(unique_events)}

    # --- GANTT ---
    fig = px.timeline(
        df, x_start="start", x_end="koniec", y="pojazd", 
        color="event", color_discrete_map=color_map,
        text="event", hover_name="event",
        template="plotly_white",
        category_orders={"pojazd": ALL_RESOURCES}
    )

    # DYNAMIKA OSI X (Rozwiązanie problemu nakładania się dat)
    today = datetime.now()
    initial_start = today - timedelta(days=7)
    initial_end = today + timedelta(days=21)

    fig.update_xaxes(
        side="top",
        gridcolor="#ccd1d9",
        showgrid=True,
        # Automatyczne dostosowanie: dni przy zbliżeniu, miesiące przy oddaleniu
        tickformatstops=[
            dict(dtickrange=[None, 86400000 * 30], value="%d %b"), # Poniżej 30 dni: Dzień + Miesiąc
            dict(dtickrange=[86400000 * 30, None], value="%B %Y")  # Powyżej 30 dni: Pełny Miesiąc
        ],
        tickfont=dict(size=12, family="Arial Black"),
        title="",
        range=[initial_start, initial_end], # Domyślne powiększenie na "teraz"
        rangeslider=dict(visible=True, thickness=0.04),
        rangeselector=dict(
            buttons=list([
                dict(count=14, label="2 TYG", step="day", stepmode="backward"),
                dict(count=1, label="1 MIES", step="month", stepmode="backward"),
                dict(count=6, label="6 MIES", step="month", stepmode="backward"),
                dict(step="all", label="ROK")
            ])
        )
    )

    fig.update_yaxes(gridcolor="#f1f3f5", title="", tickfont=dict(size=11))

    # Linia DZISIAJ
    fig.add_vline(x=today.timestamp() * 1000, line_width=3, line_dash="dash", line_color="red")

    # Wygląd pasków
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=14, color='white', family="Arial Black"),
        marker=dict(line=dict(width=1, color='white'))
    )

    fig.update_layout(
        height=len(ALL_RESOURCES) * 35 + 250,
        margin=dict(l=10, r=10, t=100, b=50),
        showlegend=False,
        bargap=0.4
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- PANEL EDYCJI ---
st.divider()
st.subheader("📝 Zarządzanie i Rezerwacje")
edited_df = st.data_editor(
    df, num_rows="dynamic", use_container_width=True,
    column_config={
        "pojazd": st.column_config.SelectboxColumn("Zasób", options=ALL_RESOURCES, width="large"),
        "start": st.column_config.DateColumn("Start"),
        "koniec": st.column_config.DateColumn("Koniec")
    },
    key="sqm_v11_stable"
)

if st.button("💾 ZAPISZ I SYNCHRONIZUJ"):
    save_df = edited_df.copy()
    save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
    save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
    save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
    conn.update(data=save_df)
    st.toast("Dane zapisane!", icon="✅")
    st.rerun()
