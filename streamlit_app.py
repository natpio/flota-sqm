import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA STRONY I ULTRA-CZYTELNY INTERFEJS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SQM LOGISTICS | Fleet Manager",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

    /* Tło aplikacji */
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }

    /* Nagłówek SQM */
    .sqm-header {
        background-color: #0f172a;
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        border-bottom: 6px solid #2563eb;
    }

    /* Powiększenie czcionek w tabeli edytora (Streamlit global) */
    [data-testid="stDataEditor"] div {
        font-size: 16px !important;
    }

    /* Powiększenie czcionek w zakładkach */
    button[data-baseweb="tab"] div p {
        font-size: 18px !important;
        font-weight: 700 !important;
    }

    /* Wymuszenie widoczności suwaków w kontrastowym kolorze */
    ::-webkit-scrollbar { width: 16px !important; height: 16px !important; }
    ::-webkit-scrollbar-track { background: #e2e8f0 !important; }
    ::-webkit-scrollbar-thumb { background: #2563eb !important; border-radius: 4px; border: 3px solid #e2e8f0; }
    </style>

    <div class="sqm-header">
        <h1 style="margin:0; font-weight:900; font-size: 2.5rem;">SQM LOGISTICS <span style="font-weight:300; color:#3b82f6;">| CONTROL TOWER</span></h1>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. AKTUALNA LISTA FLOTY SQM (ZGODNIE ZE SPISEM)
# -----------------------------------------------------------------------------
RESOURCES = {
    "🚛 CIĘŻAROWE": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI",
        "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK",
        "44 - SOLO PY 73262",
        "45 - PY1541M + przyczepa",
        "SPEDYCJA",
        "AUTO RENTAL"
    ],
    "🚐 BUSY": [
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
        "OPEL DW9WK53"
    ],
    "🚗 OSOBOWE": [
        "01 – Caravelle – PO8LC63",
        "Caravelle PY6872M - nowa",
        "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A",
        "06 – Dacia Duster – WH7087A ex T Białek",
        "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN",
        "FORD Transit Connect PY54637",
        "Chrysler Pacifica PY04266 - MBanasiak",
        "05 – Dacia Duster – WH7083A B.Krauze",
        "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "Seat Ateca WZ445HU Dynasiuk",
        "Seat Ateca WZ446HU- PM"
    ],
    "🏠 NOCLEGI": [
        "MIESZKANIE BCN - TORRASA",
        "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}
ALL_RESOURCES_LIST = [item for sublist in RESOURCES.values() for item in sublist]

# -----------------------------------------------------------------------------
# 3. DANE (G-SHEETS)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl="0s")
        data.columns = [str(c).strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.fillna("")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# -----------------------------------------------------------------------------
# 4. NAWIGACJA BOCZNA
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ USTAWIENIA")
    today = datetime.now()
    date_range = st.date_input(
        "Zakres dat widoku:",
        value=(today - timedelta(days=2), today + timedelta(days=21))
    )

if isinstance(date_range, tuple) and len(date_range) == 2:
    s_view, e_view = date_range
else:
    s_view, e_view = today - timedelta(days=2), today + timedelta(days=21)

# -----------------------------------------------------------------------------
# 5. HARMONOGRAM (GANTT) Z POWIĘKSZONĄ CZCIONKĄ
# -----------------------------------------------------------------------------
tabs = st.tabs(list(RESOURCES.keys()) + ["📝 EDYCJA DANYCH"])

colors = ["#1e40af", "#0369a1", "#0891b2", "#0d9488", "#15803d", "#b45309", "#dc2626", "#6d28d9"]
color_map = {ev: colors[i % len(colors)] for i, ev in enumerate(sorted(df['event'].unique()))}

for i, (cat, assets) in enumerate(RESOURCES.items()):
    with tabs[i]:
        c_df = df[df['pojazd'].isin(assets)].copy()
        if not c_df.empty:
            fig = px.timeline(
                c_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event", color_discrete_map=color_map,
                category_orders={"pojazd": assets}, template="plotly_white"
            )
            
            # POWIĘKSZENIE ETYKIET I NAZW
            fig.update_xaxes(
                side="top", range=[s_view, e_view], tickformat="%d\n%b",
                dtick=86400000.0, gridcolor="#e2e8f0",
                tickfont=dict(size=14, weight='bold', color="#0f172a") # DATY NA GÓRZE
            )
            
            fig.update_yaxes(
                title="", 
                tickfont=dict(size=14, weight='bold', color="#0f172a") # NAZWY POJAZDÓW
            )
            
            fig.update_traces(
                textfont_size=13, # NAZWY EVENTÓW NA PASKACH
                textposition="inside",
                insidetextanchor="middle"
            )
            
            fig.update_layout(
                height=len(assets)*50 + 120,
                margin=dict(l=10, r=10, t=60, b=10),
                showlegend=False, bargap=0.3
            )
            
            fig.add_vline(x=today.timestamp()*1000, line_width=4, line_color="#ef4444")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Brak wpisów dla {cat}")

# -----------------------------------------------------------------------------
# 6. EDYCJA BAZY (KOMPAKTOWY UKŁAD POZIOMY)
# -----------------------------------------------------------------------------
with tabs[-1]:
    st.subheader("Centralny Rejestr Floty")
    st.caption("Kliknij w komórkę, aby edytować. Użyj TAB, by przejść do Notatek.")
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_RESOURCES_LIST, width="medium", required=True),
            "event": st.column_config.TextColumn("Event", width="small"),
            "start": st.column_config.DateColumn("Start", width="small"),
            "koniec": st.column_config.DateColumn("Koniec", width="small"),
            "kierowca": st.column_config.TextColumn("Kierowca", width="small"),
            "notatka": st.column_config.TextColumn("Notatki", width="large")
        },
        key="sqm_v71_editor"
    )

    if st.button("💾 ZAPISZ ZMIANY W ARKUSZU", use_container_width=True):
        with st.status("Aktualizacja..."):
            save_df = edited_df.copy()
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=save_df)
            st.rerun()
