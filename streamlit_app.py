import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony
st.set_page_config(page_title="SQM Fleet & Housing Center", page_icon="🚚", layout="wide")

# 2. DEFINICJA ZASOBÓW (Stała lista osi Y)
# Klucz to kategoria, wartość to lista nazw tak jak w arkuszu
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

# Tworzymy płaską listę do sortowania osi Y na wykresie
ALL_RESOURCES = []
for category in FLOTA_SQM:
    ALL_RESOURCES.extend(FLOTA_SQM[category])

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

st.title("🛰️ SQM Logistics & Housing Control")

if not df.empty:
    # Przypisanie kategorii do danych dla lepszego filtrowania/kolorowania (opcjonalnie)
    def get_category(res):
        for cat, items in FLOTA_SQM.items():
            if res in items: return cat
        return "INNE"
    
    df['kategoria'] = df['pojazd'].apply(get_category)

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
        category_orders={"pojazd": ALL_RESOURCES} # WYMUSZENIE KOLEJNOŚCI OSI Y
    )

    # Oś X
    fig.update_xaxes(
        side="top", dtick="D1", gridcolor="#ccd1d9", showgrid=True,
        tickformat="%d\n%a", tickfont=dict(size=11, family="Arial Black"), title=""
    )

    # Oś Y - Dodanie linii pomocniczych między grupami
    fig.update_yaxes(gridcolor="#f1f3f5", title="", tickfont=dict(size=10))

    # Linia DZISIAJ
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_dash="dash", line_color="red")

    # Wygląd bloków
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=14, color='white', family="Arial Black"),
        marker=dict(line=dict(width=1, color='white'))
    )

    # Layout
    fig.update_layout(
        height=len(ALL_RESOURCES) * 30 + 150, # Wysokość zależna od liczby aut
        margin=dict(l=10, r=10, t=100, b=10),
        showlegend=False,
        bargap=0.4
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- PANEL OPERACYJNY ---
st.divider()
col_left, col_right = st.columns([4, 1])

with col_left:
    st.subheader("📝 Baza Operacyjna")
    edited_df = st.data_editor(
        df, num_rows="dynamic", use_container_width=True,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Zasób", options=ALL_RESOURCES, width="large"),
            "start": st.column_config.DateColumn("Start"),
            "koniec": st.column_config.DateColumn("Koniec")
        },
        key="sqm_v8_final"
    )

with col_right:
    st.subheader("Akcja")
    if st.button("💾 ZAPISZ"):
        save_df = edited_df.drop(columns=['kategoria']).copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d').fillna('')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d').fillna('')
        conn.update(data=save_df)
        st.success("Zrobione!")
        st.rerun()
