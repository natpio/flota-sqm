import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja i Styl "Friends"
st.set_page_config(page_title="SQM | The One with the Logistics", layout="wide")

st.markdown("""
    <style>
    /* Import czcionki przypominającej styl czołówki */
    @import url('https://fonts.googleapis.com/css2?family=Permanent+Marker&family=Inter:wght@400;700&display=swap');

    .stApp { background-color: #f4ece1; } /* Beż Central Perk */

    /* Nagłówek w stylu Friends */
    .friends-logo {
        font-family: 'Permanent+Marker', cursive;
        font-size: 3rem;
        text-align: center;
        color: #1e1e1e;
        letter-spacing: 5px;
        margin-bottom: 20px;
    }
    .dot-red { color: #e02424; } .dot-blue { color: #2563eb; } .dot-yellow { color: #facc15; }

    /* Zakładki - Fiolet Moniki */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #6b46c1; /* Fioletowe drzwi */
        color: white;
        border-radius: 20px;
        padding: 10px 25px;
        border: 2px solid #4c1d95;
    }
    .stTabs [aria-selected="true"] {
        background-color: #facc15 !important; /* Żółta ramka wizjera */
        color: #1e1e1e !important;
        font-weight: bold;
    }

    /* Kontener wykresu */
    .stPlotlyChart {
        background-color: #ffffff;
        border: 5px solid #6b46c1;
        border-radius: 15px;
        padding: 10px;
    }

    /* Przycisk zapisu */
    .stButton>button {
        background-color: #e02424;
        color: white;
        border-radius: 50px;
        font-family: 'Permanent Marker', cursive;
        border: none;
        padding: 10px 30px;
    }
    </style>
    
    <div class="friends-logo">
        S<span class="dot-red">·</span>Q<span class="dot-blue">·</span>M<span class="dot-yellow">·</span> LOGISTICS
    </div>
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
        return data.fillna("")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# 4. DASHBOARD - "The One with the Fleet"
tabs = st.tabs([f"🎬 {k}" for k in RESOURCES.keys()] + ["☕ CENTRAL PERK"])

# Paleta kolorów "Friends" (Kultowa Kanapa, Ściany, Neon)
friends_palette = ["#e02424", "#2563eb", "#facc15", "#6b46c1", "#059669", "#d97706"]
unique_events = sorted(df['event'].unique())
event_colors = {ev: friends_palette[i % len(friends_palette)] for i, ev in enumerate(unique_events)}

for i, (category, items) in enumerate(RESOURCES.items()):
    with tabs[i]:
        st.subheader(f"The One with {category}")
        cat_df = df[df['pojazd'].isin(items)].copy()
        
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event",
                color_discrete_map=event_colors,
                category_orders={"pojazd": items},
                template="plotly_white"
            )
            
            today = datetime.now()
            fig.update_xaxes(
                side="top", showgrid=True, gridcolor="#e2e8f0",
                tickformat="%d\n%a", dtick=86400000.0,
                tickfont=dict(size=10, family="Inter", color="#4b5563"),
                range=[today - timedelta(days=2), today + timedelta(days=14)]
            )
            
            # Weekendy - Kolor Kanapy Central Perk (lekko wyblakły)
            for d in range(366):
                curr = datetime(2026, 1, 1) + timedelta(days=d)
                if curr.weekday() >= 5:
                    fig.add_vrect(
                        x0=curr.strftime("%Y-%m-%d"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                        fillcolor="#d97706", opacity=0.1, layer="below", line_width=0
                    )

            fig.update_yaxes(title="", tickfont=dict(size=11, family="Inter", color="#1f2937"))
            fig.update_traces(
                textposition='inside', insidetextanchor='middle',
                textfont=dict(size=12, family="Inter Black", color="white"),
                marker=dict(line=dict(width=2, color='white'))
            )
            
            fig.update_layout(
                height=len(items) * 50 + 100,
                margin=dict(l=10, r=10, t=60, b=0),
                showlegend=False, bargap=0.3,
                paper_bgcolor='white', plot_bgcolor='white'
            )
            
            # Linia "PIVOT!" (Dziś)
            fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#e02424")
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("How you doin'? Tu jeszcze nic nie ma.")

# 5. ZAPIS - "The One where we save data"
with tabs[-1]:
    st.subheader("☕ The One with the Editor")
    edited_df = st.data_editor(
        df, num_rows="dynamic", use_container_width=True,
        column_config={"pojazd": st.column_config.SelectboxColumn("Zasób", options=ALL_RESOURCES)},
        key="friends_v27"
    )
    
    if st.button("💾 SAVE THE EPISODE"):
        with st.status("PIVOT! PIVOT! (Zapisywanie...)"):
            save_df = edited_df.copy()
            save_df = save_df[["pojazd", "event", "start", "koniec", "kierowca", "notatka"]]
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
