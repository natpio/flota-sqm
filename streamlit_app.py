import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony
st.set_page_config(
    page_title="SQM Fleet Management",
    page_icon="🚛",
    layout="wide"
)

# 2. Stylistyka Enterprise
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="stMetric"] { background-color: white; border-radius: 10px; border: 1px solid #dee2e6; }
    .stButton>button { background: #1a73e8; color: white; border-radius: 6px; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# 3. Bezpieczne połączenie i czyszczenie danych
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        
        # Standaryzacja
        data.columns = [c.strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        
        # Czyszczenie tekstów pod edytor (usuwamy NaN)
        for col in ['pojazd', 'event', 'kierowca', 'notatka']:
            if col in data.columns:
                data[col] = data[col].astype(str).replace(['nan', 'None', '<NA>'], '')
        
        return data[data['pojazd'] != ""].reset_index(drop=True)
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = get_data()

st.title("🛰️ SQM Fleet Logistics Center")

if not df.empty:
    # --- LOGIKA KOLORÓW DLA EVENTÓW ---
    # Tworzymy unikalną listę eventów, aby kolory były stałe
    unique_events = sorted(df['event'].unique())
    color_map = {event: px.colors.qualitative.Prism[i % len(px.colors.qualitative.Prism)] 
                 for i, event in enumerate(unique_events)}

    # --- WYKRES GANTTA ---
    fig = px.timeline(
        df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="event",
        color_discrete_map=color_map, # STAŁE KOLORY DLA TYCH SAMYCH NAZW
        text="event",
        hover_name="event",
        custom_data=["kierowca", "notatka"],
        template="plotly_white"
    )

    # Oś X i Kratka
    fig.update_xaxes(
        side="top",
        dtick="D1",
        gridcolor="#cfd4da",
        showgrid=True,
        tickformat="%d\n%a", 
        tickfont=dict(size=12, family="Arial Black", color="#333"),
        title=""
    )

    fig.update_yaxes(autorange="reversed", gridcolor="#f1f3f5", title="")

    # Linia "DZISIAJ"
    now = datetime.now()
    fig.add_vline(x=now.timestamp() * 1000, line_width=2, line_dash="dash", line_color="#ff4b4b")

    # Weekendy
    min_d = df['start'].min() - timedelta(days=2)
    max_d = df['koniec'].max() + timedelta(days=14)
    curr = min_d
    while curr <= max_d:
        if curr.weekday() >= 5:
            fig.add_vrect(x0=curr.strftime("%Y-%m-%d"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                          fillcolor="#f1f3f5", opacity=1.0, layer="below", line_width=0)
        curr += timedelta(days=1)

    # DOPRACOWANIE BLOKÓW I CZCIONKI
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=14, color='white', family="Arial Black"), # Wyraźna czcionka
        marker=dict(line=dict(width=1, color='white'))
    )

    # BEZPIECZNY LAYOUT (Naprawiony błąd ValueError)
    fig.update_layout(
        height=min(800, 400 + (len(df['pojazd'].unique()) * 40)), # Dynamiczna wysokość
        margin=dict(l=10, r=10, t=100, b=20),
        showlegend=False,
        barmode='group', # Zapewnia poprawne wyświetlanie wielu zadań
        bargap=0.6,      # JESZCZE SMUKLEJSZE PROSTOKĄTY
        groupgap=0.0
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- EDYTOR ---
st.divider()
st.subheader("📝 Zarządzanie Danymi")

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "start": st.column_config.DateColumn("Start"),
        "koniec": st.column_config.DateColumn("Koniec"),
        "pojazd": st.column_config.TextColumn("🚛 Pojazd"),
        "event": st.column_config.TextColumn("🏷️ Event")
    },
    key="sqm_v6_stable"
)

if st.button("💾 ZAPISZ I AKTUALIZUJ"):
    try:
        save_df = edited_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d').fillna('')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d').fillna('')
        conn.update(data=save_df)
        st.success("Dane zapisane pomyślnie!")
        st.rerun()
    except Exception as e:
        st.error(f"Błąd podczas zapisu: {e}")
