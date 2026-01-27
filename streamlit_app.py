import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony
st.set_page_config(page_title="SQM Fleet & Housing Center", page_icon="🚛", layout="wide")

# 2. DEFINICJA ZASOBÓW (Stała lista osi Y)
FLOTA_SQM = {
    "FTL / SOLO": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI",
        "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK",
        "44 - SOLO PY 73262",
        "45 - PY1541M + przyczepa"
    ],
    "BUS / DOSTAWCZE": [
        "25 – Jumper – PY22952",
        "24 – Jumper – PY22954",
        "BOXER - PO 5VT68",
        "BOXER - WZ213GF",
        "BOXER - WZ214GF",
        "BOXER - WZ215GF",
        "OPEL DW4WK43",
        "BOXER (WYPAS) DW7WE24",
        "OPEL wysoki DW4WK45",
        "BOXER DW9WK54 wysoki",
        "OPEL DW9WK53",
        "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN",
        "FORD Transit Connect PY54637"
    ],
    "OSOBOWE": [
        "01 – Caravelle – PO8LC63",
        "Caravelle PY6872M - nowa",
        "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A",
        "06 – Dacia Duster – WH7087A ex T Białek",
        "05 – Dacia Duster – WH7083A   B.Krauze",
        "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "Chrysler Pacifica PY04266 - MBanasiak",
        "Seat Ateca WZ445HU  Dynasiuk",
        "Seat Ateca WZ446HU- PM",
        "SPEDYCJA",
        "AUTO RENTAL -  CARVIDO"
    ],
    "MIESZKANIA": [
        "MIESZKANIE BCN - TORRASA",
        "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}

ALL_RESOURCES = []
for items in FLOTA_SQM.values():
    ALL_RESOURCES.extend(items)

# 3. Połączenie i ładowanie danych
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

st.title("🛰️ SQM Fleet & Housing Control")

if not df.empty:
    # --- LOGIKA KOLORÓW DLA EVENTÓW ---
    unique_events = sorted(df['event'].unique())
    color_palette = px.colors.qualitative.Prism
    event_color_map = {event: color_palette[i % len(color_palette)] for i, event in enumerate(unique_events)}

    # --- WYKRES GANTT ---
    fig = px.timeline(
        df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="event",
        color_discrete_map=event_color_map,
        text="event",
        hover_name="event",
        template="plotly_white",
        category_orders={"pojazd": ALL_RESOURCES}
    )

    # KONFIGURACJA OSI X (Daty, Suwak, Przyciski)
    fig.update_xaxes(
        side="top", # Etykiety na górze
        dtick="D1",
        gridcolor="#ccd1d9",
        showgrid=True,
        tickformat="%d\n%a", 
        tickfont=dict(size=11, family="Arial Black"),
        title="",
        # DODANIE SUWAKA I PRZYCISKÓW
        rangeslider=dict(visible=True, thickness=0.05),
        rangeselector=dict(
            buttons=list([
                dict(count=7, label="TYDZIEŃ", step="day", stepmode="backward"),
                dict(count=1, label="1 MIESIĄC", step="month", stepmode="backward"),
                dict(count=6, label="6 MIESIĘCY", step="month", stepmode="backward"),
                dict(step="all", label="CAŁY ROK")
            ]),
            y=1.1 # Pozycja przycisków nad osią
        )
    )

    fig.update_yaxes(gridcolor="#f1f3f5", title="", tickfont=dict(size=10))

    # Linia DZISIAJ
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_dash="dash", line_color="red")

    # Weekendy
    min_date = datetime(2026, 1, 1)
    max_date = datetime(2026, 12, 31)
    curr = min_date
    while curr <= max_date:
        if curr.weekday() >= 5:
            fig.add_vrect(x0=curr.strftime("%Y-%m-%d"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                          fillcolor="#f8f9fa", opacity=1.0, layer="below", line_width=0)
        curr += timedelta(days=1)

    # Wygląd bloków
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=14, color='white', family="Arial Black"),
        marker=dict(line=dict(width=1, color='white'))
    )

    # Layout z uwzględnieniem suwaka
    fig.update_layout(
        height=len(ALL_RESOURCES) * 35 + 250,
        margin=dict(l=10, r=10, t=150, b=50),
        showlegend=False,
        bargap=0.4
    )

    # WYŚWIETLANIE WYKRESU
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- PANEL OPERACYJNY ---
st.divider()
st.subheader("📝 Edycja i Rezerwacje")
edited_df = st.data_editor(
    df, num_rows="dynamic", use_container_width=True,
    column_config={
        "pojazd": st.column_config.SelectboxColumn("Zasób SQM", options=ALL_RESOURCES, width="large"),
        "start": st.column_config.DateColumn("Start"),
        "koniec": st.column_config.DateColumn("Koniec")
    },
    key="sqm_v9_sticky"
)

if st.button("💾 ZAPISZ ZMIANY"):
    save_df = edited_df.copy()
    save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
    save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d').fillna('')
    save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d').fillna('')
    conn.update(data=save_df)
    st.success("Baza zaktualizowana!")
    st.rerun()
