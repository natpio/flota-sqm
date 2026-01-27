import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony
st.set_page_config(
    page_title="SQM Fleet Manager v5",
    page_icon="🚛",
    layout="wide"
)

# 2. Stylizacja UI
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    div[data-testid="stMetric"] { background-color: white; border-radius: 8px; border: 1px solid #eee; }
    .stButton>button { width: 100%; font-weight: bold; border-radius: 6px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Bezpieczne ładowanie danych
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Pobranie danych z arkusza
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        
        # Standaryzacja nazw kolumn na małe litery
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

st.title("🚛 SQM Logistics Planner")

if not df.empty:
    # --- HARMONOGRAM ---
    # Sortowanie, aby te same eventy miały spójne kolory
    plot_df = df.copy().sort_values('event')
    
    fig = px.timeline(
        plot_df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="event",  # Kolorowanie uzależnione od NAZWY EVENTU
        text="event",
        hover_name="event",
        custom_data=["kierowca", "notatka"],
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Prism # Profesjonalna paleta
    )

    # Ustawienia osi i kratki
    fig.update_xaxes(
        side="top",
        dtick="D1",
        gridcolor="#ccd1d9",
        showgrid=True,
        tickformat="%d\n%a", 
        tickfont=dict(size=11, family="Arial Black"),
        title=""
    )

    fig.update_yaxes(autorange="reversed", gridcolor="#f1f3f5", title="")

    # DODANIE LINII "DZISIAJ"
    now = datetime.now()
    fig.add_vline(x=now.timestamp() * 1000, line_width=2, line_dash="dash", line_color="red")

    # PODKREŚLENIE WEEKENDÓW
    view_min = plot_df['start'].min() - timedelta(days=2)
    view_max = plot_df['koniec'].max() + timedelta(days=10)
    curr = view_min
    while curr <= view_max:
        if curr.weekday() >= 5:
            fig.add_vrect(x0=curr.strftime("%Y-%m-%d"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                          fillcolor="#f1f3f5", opacity=1.0, layer="below", line_width=0)
        curr += timedelta(days=1)

    # KLUCZOWE POPRAWKI WYGLĄDU PROSTOKĄTÓW
    fig.update_traces(
        textposition='inside',
        textfont=dict(size=14, color='white', family="Arial Black"), # WIĘKSZA I GRUBSZA CZCIONKA
        marker=dict(line=dict(width=1, color='white'))
    )

    fig.update_layout(
        height=500,
        bar_gap=0.5,      # ZWIĘKSZENIE ODSTĘPU = SMUKLEJSZE PROSTOKĄTY
        group_gap=0.1,    # Dopasowanie grup
        margin=dict(l=10, r=10, t=80, b=10),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- PANEL EDYCJI ---
st.divider()
st.subheader("📋 Baza Transportów")

# Przygotowanie danych do edytora bez ryzykownych typów
editor_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "start": st.column_config.DateColumn("Start"),
        "koniec": st.column_config.DateColumn("Koniec"),
        "pojazd": st.column_config.TextColumn("Pojazd"),
        "event": st.column_config.TextColumn("Event")
    },
    key="sqm_editor_v5"
)

if st.button("ZAPISZ I SYNCHRONIZUJ"):
    try:
        # Mapowanie na format Google Sheets
        save_df = editor_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d').fillna('')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(data=save_df)
        st.success("Zaktualizowano arkusz Google!")
        st.rerun()
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")
