import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony i Zaawansowany Styl UI
st.set_page_config(page_title="SQM LOGISTICS | Control Tower", layout="wide")

st.markdown("""
    <style>
    /* Globalne tło i czcionka */
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    
    /* Stylizacja Zakładek (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #161b22;
        padding: 10px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #21262d;
        border-radius: 5px;
        color: #8b949e;
        border: none;
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #238636 !important;
        color: white !important;
        font-weight: bold;
    }
    
    /* Nagłówki i teksty */
    h1 { color: #58a6ff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-weight: 800; }
    .stMarkdown { line-height: 1.2; }
    
    /* Schowanie zbędnych elementów Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Kontener Wykresu */
    .plot-container {
        border: 1px solid #30363d;
        border-radius: 12px;
        background-color: #161b22;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. DEFINICJA ZASOBÓW
RESOURCES = {
    "🚛 FTL / SOLO": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "🚐 BUS / DOSTAWCZE": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68",
        "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF",
        "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45",
        "BOXER DW9WK54 wysoki", "OPEL DW9WK53", "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637"
    ],
    "🚗 OSOBOWE": [
        "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek",
        "05 – Dacia Duster – WH7083A   B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "Chrysler Pacifica PY04266 - MBanasiak", "Seat Ateca WZ445HU  Dynasiuk",
        "Seat Ateca WZ446HU- PM", "SPEDYCJA", "AUTO RENTAL - CARVIDO"
    ],
    "🏠 NOCLEGI": [
        "MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}

ALL_RESOURCES = [item for sublist in RESOURCES.values() for item in sublist]

# 3. DANE
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl="0s")
        data.columns = [c.strip().lower() for c in data.columns]
        expected = ["pojazd", "event", "start", "koniec", "kierowca", "notatka"]
        data = data[expected].copy()
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.fillna(" ")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# 4. UI
st.title("🛰️ SQM LOGISTICS | CONTROL TOWER")

tabs = st.tabs([f" {k}" for k in RESOURCES.keys()] + ["⚙️ USTAWIENIA"])

# Kolory Neonowe dla Eventów
color_palette = ["#00f2ff", "#7000ff", "#ff007a", "#ccff00", "#ff8a00", "#00ff85"]
unique_events = sorted(df['event'].unique())
event_colors = {ev: color_palette[i % len(color_palette)] for i, ev in enumerate(unique_events)}

for i, (category, items) in enumerate(RESOURCES.items()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(items)].copy()
        
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event",
                color_discrete_map=event_colors,
                category_orders={"pojazd": items},
                template="plotly_dark"
            )
            
            # Stylizacja osi
            today = datetime.now()
            fig.update_xaxes(
                side="top", showgrid=True, gridcolor="#30363d",
                tickformat="%d %b\n%a", dtick=86400000.0,
                tickfont=dict(size=10, family="Monospace", color="#8b949e"),
                range=[today - timedelta(days=2), today + timedelta(days=14)],
                rangeslider=dict(visible=True, thickness=0.02, bgcolor="#161b22")
            )
            
            # Weekendy - Ciemniejsze tło
            start_cal = datetime(2026, 1, 1)
            for d in range(366):
                curr = start_cal + timedelta(days=d)
                if curr.weekday() >= 5:
                    fig.add_vrect(
                        x0=curr.strftime("%Y-%m-%d"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                        fillcolor="#0d1117", opacity=0.5, layer="below", line_width=0
                    )

            fig.update_yaxes(title="", tickfont=dict(size=11, color="#c9d1d9"), gridcolor="#30363d")
            
            # Wygląd pasków - "Glow" effect
            fig.update_traces(
                textposition='inside', insidetextanchor='middle',
                textfont=dict(size=12, family="Arial Black", color="white"),
                marker=dict(line=dict(width=0))
            )
            
            fig.update_layout(
                height=len(items) * 45 + 120,
                margin=dict(l=10, r=10, t=70, b=0),
                showlegend=False, bargap=0.4,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            # Linia DZIŚ
            fig.add_vline(x=today.timestamp()*1000, line_width=2, line_dash="solid", line_color="#ff3e3e")
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info(f"Kategoria {category} jest obecnie pusta.")

# 5. PANEL ZARZĄDZANIA
with tabs[-1]:
    st.subheader("🛠️ Administracja Flotą")
    with st.expander("📝 Edytuj dane w tabeli", expanded=True):
        edited_df = st.data_editor(
            df, num_rows="dynamic", use_container_width=True,
            column_config={
                "pojazd": st.column_config.SelectboxColumn("Zasób", options=ALL_RESOURCES),
                "start": st.column_config.DateColumn("Początek"),
                "koniec": st.column_config.DateColumn("Koniec")
            },
            key="sqm_v25_dark"
        )
    
    if st.button("💾 SYNCHRONIZUJ I ODŚWIEŻ"):
        with st.status("Trwa zapisywanie danych..."):
            save_df = edited_df.copy()
            save_df = save_df[["pojazd", "event", "start", "koniec", "kierowca", "notatka"]]
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
