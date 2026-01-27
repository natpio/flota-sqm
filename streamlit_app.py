import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja i Stylistyka "Friends High-End"
st.set_page_config(page_title="SQM | The One with the Logistics", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Permanent+Marker&family=Inter:wght@400;900&display=swap');

    /* Tło kawiarniane */
    .stApp { 
        background-color: #f4ece1; 
        background-image: radial-gradient(#e5d5c0 1px, transparent 1px);
        background-size: 20px 20px;
    }

    /* Logo z kropkami */
    .friends-header {
        font-family: 'Permanent Marker', cursive;
        font-size: 4rem;
        text-align: center;
        color: #262626;
        padding: 20px;
        text-shadow: 2px 2px #fff;
    }
    .dot-1 { color: #e02424; } .dot-2 { color: #2563eb; } .dot-3 { color: #facc15; }

    /* Żółta ramka Moniki dla wykresów */
    .stPlotlyChart {
        border: 8px solid #facc15;
        border-radius: 10px;
        box-shadow: 10px 10px 0px #6b46c1;
        background-color: white;
    }

    /* Tabs w kolorze fioletowym */
    .stTabs [data-baseweb="tab-list"] { background-color: #6b46c1; padding: 10px; border-radius: 15px 15px 0 0; }
    .stTabs [data-baseweb="tab"] { color: #f4ece1 !important; font-family: 'Inter', sans-serif; font-weight: 900; }
    .stTabs [aria-selected="true"] { background-color: #facc15 !important; color: #6b46c1 !important; border-radius: 10px; }

    /* Customowe Info Boxy */
    .stAlert { background-color: #6b46c1; color: white; border: none; border-radius: 15px; }

    /* Przycisk PIVOT! */
    .stButton>button {
        width: 100%;
        background-color: #e02424;
        color: white;
        font-family: 'Permanent Marker', cursive;
        font-size: 1.5rem;
        border: 3px solid #000;
        box-shadow: 5px 5px 0px #facc15;
        transition: 0.2s;
    }
    .stButton>button:hover { transform: translate(-2px, -2px); box-shadow: 7px 7px 0px #facc15; }
    </style>
    
    <div class="friends-header">
        F<span class="dot-1">·</span>R<span class="dot-2">·</span>I<span class="dot-3">·</span>E<span class="dot-1">·</span>N<span class="dot-2">·</span>D<span class="dot-3">·</span>S
        <div style="font-size: 1.5rem; margin-top: -15px; color: #6b46c1;">OF SQM LOGISTICS</div>
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
        return data.fillna(" ")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# 4. DASHBOARD - "The One where Joey Plans Transport"
tabs = st.tabs([f"📺 {k}" for k in RESOURCES.keys()] + ["☕ CENTRAL PERK (EDIT)"])

# Kultowe kolory eventów (Koszula Joey'ego, Sukienka Rachel, Kanapa)
friends_colors = ["#FF4136", "#0074D9", "#FFDC00", "#B10DC9", "#2ECC40", "#FF851B"]
event_colors = {ev: friends_colors[i % len(friends_colors)] for i, ev in enumerate(sorted(df['event'].unique()))}

for i, (category, items) in enumerate(RESOURCES.items()):
    with tabs[i]:
        st.write(f"### 🎬 The One with {category}")
        cat_df = df[df['pojazd'].isin(items)].copy()
        
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event", color_discrete_map=event_colors,
                category_orders={"pojazd": items}, template="plotly_white"
            )
            
            today = datetime.now()
            fig.update_xaxes(
                side="top", showgrid=True, gridcolor="#eee",
                tickformat="%d %b\n%a", dtick=86400000.0,
                range=[today - timedelta(days=2), today + timedelta(days=14)],
                tickfont=dict(size=10, family="Inter", color="#6b46c1")
            )
            
            # Weekendy - "Smelly Cat" Grey
            for d in range(366):
                curr = datetime(2026, 1, 1) + timedelta(days=d)
                if curr.weekday() >= 5:
                    fig.add_vrect(
                        x0=curr.strftime("%Y-%m-%d"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                        fillcolor="#6b46c1", opacity=0.05, layer="below", line_width=0
                    )

            fig.update_yaxes(title="", tickfont=dict(size=11, family="Inter Black"))
            fig.update_traces(
                marker=dict(line=dict(width=2, color='white')),
                textfont=dict(family="Inter", size=12, color="white")
            )
            
            fig.update_layout(
                height=len(items) * 50 + 120, margin=dict(l=10, r=10, t=80, b=10),
                showlegend=False, bargap=0.4
            )
            
            # Linia Dziś - Czerwona jak usta Rachel
            fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#e02424")
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning("How you doin'? No runs planned here yet!")

# 5. PANEL CENTRAL PERK (ZAPIS)
with tabs[-1]:
    st.write("### ☕ The One where Gunther Updates the Spreadsheet")
    edited_df = st.data_editor(
        df, num_rows="dynamic", use_container_width=True,
        column_config={"pojazd": st.column_config.SelectboxColumn("Zasób", options=ALL_RESOURCES)},
        key="friends_final_v1"
    )
    
    if st.button("🚀 PIVOT! PIVOT! PIVOT!"):
        with st.status("Smelly Cat is singing... (Saving)"):
            save_df = edited_df.copy()
            save_df = save_df[["pojazd", "event", "start", "koniec", "kierowca", "notatka"]]
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
