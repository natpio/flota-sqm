import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja
st.set_page_config(page_title="SQM LOGISTICS | Data Center", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    .header-box {
        background-color: #0f172a;
        padding: 1rem;
        border-radius: 8px;
        color: white;
        margin-bottom: 20px;
    }
    /* Podświetlenie edytora */
    [data-testid="stDataEditor"] {
        border: 2px solid #2563eb !important;
    }
    </style>
    <div class="header-box">
        <h1 style="margin:0; font-size: 1.5rem;">SQM LOGISTICS | System Zarządzania Flotą</h1>
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
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.fillna("")
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

# 4. MODUŁ WIDOKU (GANTT)
tabs = st.tabs(["📊 WIDOK OPERACYJNY", "✏️ EDYCJA DANYCH"])

with tabs[0]:
    # Nawigator dat na górze
    col_a, col_b = st.columns(2)
    with col_a:
        start_v = st.date_input("Od:", datetime.now() - timedelta(days=2))
    with col_b:
        end_v = st.date_input("Do:", datetime.now() + timedelta(days=21))

    for category, assets in RESOURCES.items():
        st.subheader(category)
        cat_df = df[df['pojazd'].isin(assets)].copy()
        if not cat_df.empty:
            fig = px.timeline(cat_df, x_start="start", x_end="koniec", y="pojazd", color="event", template="plotly_white")
            fig.update_xaxes(side="top", range=[start_v, end_v], tickformat="%d\n%b")
            fig.update_layout(height=len(assets)*45 + 100, showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

# 5. MODUŁ EDYCJI (BEZ SCROLLA - FILTROWANIE)
with tabs[1]:
    st.info("🔍 Wybierz pojazd z listy, aby go edytować. Dzięki temu tabela będzie krótka i czytelna.")
    
    selected_asset = st.selectbox("Wybierz zasób do edycji/dodania wpisu:", ["WSZYSTKIE"] + ALL_RESOURCES)
    
    # Filtrujemy dane do edycji
    if selected_asset == "WSZYSTKIE":
        df_to_edit = df.copy()
    else:
        df_to_edit = df[df['pojazd'] == selected_asset].copy()

    edited_df = st.data_editor(
        df_to_edit,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_RESOURCES, width="medium"),
            "event": st.column_config.TextColumn("Event", width="medium"),
            "start": st.column_config.DateColumn("Start", width="small"),
            "koniec": st.column_config.DateColumn("Koniec", width="small"),
            "kierowca": st.column_config.TextColumn("Kierowca", width="medium"),
            "notatka": st.column_config.TextColumn("Notatka", width="large")
        },
        key="filtered_editor"
    )

    if st.button("ZAPISZ ZMIANY"):
        with st.status("Zapisywanie..."):
            # Jeśli edytowaliśmy tylko jeden pojazd, musimy połączyć to z resztą bazy
            if selected_asset != "WSZYSTKIE":
                # Usuwamy stare wpisy dla tego pojazdu i dodajemy nowe
                other_assets_df = df[df['pojazd'] != selected_asset]
                final_df = pd.concat([other_assets_df, edited_df])
            else:
                final_df = edited_df

            # Przygotowanie do zapisu
            final_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            final_df['Start'] = pd.to_datetime(final_df['Start']).dt.strftime('%Y-%m-%d')
            final_df['Koniec'] = pd.to_datetime(final_df['Koniec']).dt.strftime('%Y-%m-%d')
            conn.update(data=final_df)
            st.rerun()
