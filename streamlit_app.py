import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony
st.set_page_config(page_title="SQM Control Tower", layout="wide")

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

# 3. POŁĄCZENIE I DANE
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl="0s")
        # Standaryzacja nazw do małych liter dla kodu
        data.columns = [c.strip().lower() for c in data.columns]
        
        # Zapewnienie, że mamy dokładnie te kolumny, których oczekujemy
        expected = ["pojazd", "event", "start", "koniec", "kierowca", "notatka"]
        for col in expected:
            if col not in data.columns:
                data[col] = ""
        
        data = data[expected] # Zachowaj tylko te 6 kolumn
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        
        for col in ['pojazd', 'event', 'kierowca', 'notatka']:
            data[col] = data[col].astype(str).replace(['nan', 'None', ''], ' ')
        return data
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

st.title("🛰️ SQM Logistics Control Center")

tabs = st.tabs(list(RESOURCES.keys()) + ["🔧 ZARZĄDZANIE"])

# Stałe kolory
all_events = sorted(df['event'].unique())
color_palette = px.colors.qualitative.Prism
event_colors = {event: color_palette[i % len(color_palette)] for i, event in enumerate(all_events)}

for i, category in enumerate(RESOURCES.keys()):
    with tabs[i]:
        cat_df = df[df['pojazd'].isin(RESOURCES[category])].copy()
        
        if not cat_df.empty:
            fig = px.timeline(
                cat_df, x_start="start", x_end="koniec", y="pojazd",
                color="event", text="event",
                color_discrete_map=event_colors,
                category_orders={"pojazd": RESOURCES[category]},
                template="plotly_white"
            )
            
            today = datetime.now()
            fig.update_xaxes(
                side="top", showgrid=True, gridcolor="#E5E5E5",
                tickformat="%d %b\n%a", dtick=86400000.0,
                tickfont=dict(size=10, family="Arial Black"),
                range=[today - timedelta(days=3), today + timedelta(days=18)],
                rangeslider=dict(visible=True, thickness=0.03)
            )
            
            # Weekendy
            start_cal = datetime(2026, 1, 1)
            for d in range(365):
                curr = start_cal + timedelta(days=d)
                if curr.weekday() >= 5:
                    fig.add_vrect(
                        x0=curr.strftime("%Y-%m-%d"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                        fillcolor="#F5F5F5", opacity=1.0, layer="below", line_width=0
                    )

            fig.update_yaxes(title="", tickfont=dict(size=11))
            fig.update_traces(
                textposition='inside', insidetextanchor='middle',
                textfont=dict(size=12, family="Arial Black"),
                marker=dict(line=dict(width=1, color='white'))
            )
            fig.update_layout(
                height=len(RESOURCES[category]) * 42 + 150,
                margin=dict(l=10, r=10, t=80, b=10), showlegend=False, bargap=0.35
            )
            fig.add_vline(x=today.timestamp()*1000, line_width=2, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info(f"Brak danych dla sekcji {category}")

# 5. PANEL EDYCJI (Naprawa błędu ValueError)
with tabs[-1]:
    st.subheader("📝 Edycja Bazy danych")
    
    # Edytujemy kopię głównego DF, który ma dokładnie 6 kolumn
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "pojazd": st.column_config.SelectboxColumn("Zasób SQM", options=ALL_RESOURCES, width="large"),
            "start": st.column_config.DateColumn("Start"),
            "koniec": st.column_config.DateColumn("Koniec")
        },
        key="editor_v2.3"
    )
    
    if st.button("💾 ZAPISZ ZMIANY"):
        try:
            # Tworzymy kopię do zapisu
            save_df = edited_df.copy()
            
            # Upewniamy się, że nie ma żadnych dodatkowych kolumn (np. indeksów)
            save_df = save_df[["pojazd", "event", "start", "koniec", "kierowca", "notatka"]]
            
            # Przywracamy oryginalne nazwy kolumn z Arkusza Google (Wielkie litery)
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            
            # Konwersja dat na tekst
            save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
            save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
            
            conn.update(data=save_df)
            st.success("Zapisano pomyślnie w Google Sheets!")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd podczas zapisu: {e}")
