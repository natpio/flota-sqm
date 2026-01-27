import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony
st.set_page_config(
    page_title="SQM Logistics Planner",
    page_icon="🚛",
    layout="wide"
)

# 2. Stylizacja UI (Clean SaaS Style)
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    div[data-testid="stMetric"] { background-color: white; border-radius: 8px; border: 1px solid #eee; }
    .stButton>button { width: 100%; font-weight: bold; border-radius: 6px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Połączenie i ładowanie danych
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        
        # Standaryzacja nazw kolumn
        data.columns = [c.strip().lower() for c in data.columns]
        
        # Konwersja dat
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        
        # Czyszczenie tekstów (usuwanie NaN dla st.data_editor)
        for col in ['pojazd', 'event', 'kierowca', 'notatka']:
            if col in data.columns:
                data[col] = data[col].astype(str).replace(['nan', 'None', '<NA>'], '')
        
        return data[data['pojazd'] != ""].reset_index(drop=True)
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = load_data()

st.title("🚛 SQM Logistics: Harmonogram Floty")

if not df.empty:
    # --- LOGIKA KOLORÓW DLA EVENTÓW ---
    # Gwarantuje, że eventy o tej samej nazwie mają ten sam kolor
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
        custom_data=["kierowca", "notatka"],
        template="plotly_white"
    )

    # Oś X: Daty i Kratka
    fig.update_xaxes(
        side="top",
        dtick="D1",
        gridcolor="#ccd1d9",
        showgrid=True,
        tickformat="%d\n%a", 
        tickfont=dict(size=12, family="Arial Black", color="#333"),
        title=""
    )

    fig.update_yaxes(autorange="reversed", gridcolor="#f1f3f5", title="")

    # Linia "DZISIAJ"
    now = datetime.now()
    fig.add_vline(x=now.timestamp() * 1000, line_width=2, line_dash="dash", line_color="red")

    # Weekendy
    min_view = df['start'].min() - timedelta(days=2)
    max_view = df['koniec'].max() + timedelta(days=10)
    curr = min_view
    while curr <= max_view:
        if curr.weekday() >= 5:
            fig.add_vrect(x0=curr.strftime("%Y-%m-%d"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                          fillcolor="#f1f3f5", opacity=1.0, layer="below", line_width=0)
        curr += timedelta(days=1)

    # WYGLĄD BLOKÓW I CZCIONKI (Poprawione)
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=14, color='white', family="Arial Black"), # Duża, pogrubiona czcionka
        marker=dict(line=dict(width=1, color='white'))
    )

    # STABILNY LAYOUT (Naprawa ValueError)
    fig.update_layout(
        height=400 + (len(df['pojazd'].unique()) * 35), # Skalowanie wysokości
        margin=dict(l=10, r=10, t=100, b=10),
        showlegend=False,
        bargap=0.5 # SMUKŁE PROSTOKĄTY (zwiększ do 0.7 jeśli mają być jeszcze cieńsze)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- PANEL OPERACYJNY ---
st.divider()
st.subheader("📋 Baza Transportowa")

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "start": st.column_config.DateColumn("Start"),
        "koniec": st.column_config.DateColumn("Koniec"),
        "pojazd": st.column_config.TextColumn("Pojazd"),
        "event": st.column_config.TextColumn("Event")
    },
    key="sqm_v7_final"
)

if st.button("ZAPISZ I SYNCHRONIZUJ Z ARKUSZEM"):
    try:
        save_df = edited_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d').fillna('')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d').fillna('')
        conn.update(data=save_df)
        st.success("Synchronizacja zakończona pomyślnie!")
        st.rerun()
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")
