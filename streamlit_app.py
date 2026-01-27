import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Konfiguracja strony pod SQM Logistics
st.set_page_config(page_title="SQM Fleet Grid", layout="wide")

# Połączenie z danymi
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"])
        # Standaryzacja nazw kolumn
        data.columns = [c.strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.dropna(subset=['pojazd', 'start', 'koniec'])
    except Exception as e:
        st.error(f"Błąd danych: {e}")
        return pd.DataFrame()

df = load_data()

st.title("🚛 Planner Logistyczny SQM - Widok Siatki")

if not df.empty:
    # 1. Obliczanie zakresu osi czasu
    min_date = df['start'].min() - timedelta(days=2)
    max_date = df['koniec'].max() + timedelta(days=5)
    
    # 2. Tworzenie wykresu
    fig = px.timeline(
        df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="event",
        text="event",
        hover_name="event",
        custom_data=["kierowca", "notatka"],
        template="plotly_white" # Wymuszenie czystego białego tła
    )

    # 3. KONFIGURACJA KRATKI (Grid)
    fig.update_xaxes(
        side="top",
        dtick="D1",             # Linia dla KAŻDEGO dnia
        showgrid=True,          # Wymuszenie widoczności siatki
        gridwidth=1,            # Grubość linii siatki
        gridcolor="#d1d1d1",    # Ciemniejszy szary, żeby był widoczny
        tickformat="%d\n%a",    # Dzień i skrót (np. 27 Tue)
        tickfont=dict(size=11, color="black"),
        title=""
    )

    fig.update_yaxes(
        autorange="reversed", 
        showgrid=True, 
        gridcolor="#e5e5e5", 
        title=""
    )

    # 4. WYRÓŻNIENIE WEEKENDÓW (Błękitny pas w tle)
    curr = min_date
    while curr <= max_date:
        if curr.weekday() >= 5: # Sobota i Niedziela
            fig.add_vrect(
                x0=curr.strftime("%Y-%m-%d"),
                x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                fillcolor="#ebf5ff", # Bardzo jasny niebieski
                opacity=0.6,
                layer="below",
                line_width=0,
            )
        curr += timedelta(days=1)

    # 5. ESTETYKA PASKÓW
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        marker=dict(line=dict(width=1, color='white'))
    )

    fig.update_layout(
        height=600,
        margin=dict(l=10, r=10, t=100, b=10),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

st.divider()

# PANEL EDYCJI
st.subheader("📝 Edycja danych (Live Sync)")
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "start": st.column_config.DateColumn("Start"),
        "koniec": st.column_config.DateColumn("Koniec")
    },
    key="sqm_grid_v2"
)

if st.button("💾 ZAPISZ ZMIANY"):
    save_df = edited_df.copy()
    save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
    save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
    save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
    conn.update(data=save_df)
    st.success("Zapisano!")
    st.rerun()
