import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony - SQM Logistics Intelligence
st.set_page_config(
    page_title="SQM Control Tower",
    page_icon="🚛",
    layout="wide"
)

# 2. Stylizacja Enterprise Light
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 15px;
    }
    .stButton>button {
        background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
    }
    /* Stylizacja siatki edytora */
    [data-testid="stDataEditor"] {
        border: 1px solid #dee2e6 !important;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Bezpieczne ładowanie i czyszczenie danych
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_securely():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        
        # Standaryzacja nazw kolumn
        data.columns = [c.strip().lower() for c in data.columns]
        
        # Konwersja dat z zabezpieczeniem (coerce zamienia błędy na NaT)
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        
        # CZYSZCZENIE: st.data_editor nie znosi NaN w kolumnach tekstowych przy określonym column_config
        text_cols = ['pojazd', 'event', 'kierowca', 'notatka']
        for col in text_cols:
            if col in data.columns:
                data[col] = data[col].astype(str).replace(['nan', 'None', '<NA>'], '')
            else:
                data[col] = ""
        
        # Filtrujemy wiersze, które mają chociaż nazwę pojazdu
        return data[data['pojazd'] != ""].reset_index(drop=True)
    except Exception as e:
        st.error(f"Krytyczny błąd bazy danych: {e}")
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = load_data_securely()

# --- PANEL KIEROWNICZY ---
st.title("🛰️ SQM Fleet Control Tower")

if not df.empty:
    m1, m2, m3, m4 = st.columns(4)
    now = datetime.now()
    
    active_now = df[(df['start'] <= now) & (df['koniec'] >= now)].shape[0]
    total_fleet = df['pojazd'].nunique()
    
    m1.metric("Pojazdy w akcji", active_now)
    m2.metric("Wielkość floty", total_fleet)
    m3.metric("Zlecenia (Total)", len(df))
    m4.metric("Dziś", now.strftime("%d.%m.%Y"))

# --- HARMONOGRAM Z LINIA DZISIEJSZĄ I KRATKĄ ---
if not df.empty:
    # Zakres wykresu
    view_start = df['start'].min() - timedelta(days=2)
    view_end = df['koniec'].max() + timedelta(days=10)
    
    fig = px.timeline(
        df.sort_values('pojazd'), 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="pojazd",
        text="event",
        hover_name="event",
        custom_data=["kierowca", "notatka"],
        template="plotly_white"
    )

    # KONFIGURACJA KRATKI (Grid)
    fig.update_xaxes(
        side="top",
        dtick="D1",
        gridcolor="#ccd1d9", # Wyraźna kratka pionowa
        gridwidth=1,
        showgrid=True,
        tickformat="%d\n%a", 
        tickfont=dict(size=11, family="Arial Black", color="#2c3e50"),
        title=""
    )

    fig.update_yaxes(
        autorange="reversed", 
        gridcolor="#f1f3f5", # Linie poziome
        title="",
        tickfont=dict(size=12, color="#2c3e50")
    )

    # LINIA DNIA DZISIEJSZEGO (Nowoczesny wskaźnik)
    fig.add_vline(
        x=now.timestamp() * 1000, 
        line_width=3, 
        line_dash="dash", 
        line_color="#ff4b4b",
        annotation_text="DZISIAJ", 
        annotation_position="top left"
    )

    # PODKREŚLENIE WEEKENDÓW
    curr = view_start
    while curr <= view_end:
        if curr.weekday() >= 5:
            fig.add_vrect(
                x0=curr.strftime("%Y-%m-%d"),
                x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                fillcolor="#f1f3f5",
                opacity=1.0,
                layer="below",
                line_width=0,
            )
        curr += timedelta(days=1)

    fig.update_traces(
        textposition='inside',
        marker=dict(line=dict(width=2, color='white'), opacity=0.85)
    )

    fig.update_layout(
        height=550,
        margin=dict(l=10, r=10, t=100, b=10),
        showlegend=False,
        font=dict(family="Inter, sans-serif")
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- OPERACJE NA DANYCH ---
st.subheader("🛠️ Panel Operatorski")

# Tworzymy czysty DataFrame do edycji (bez ryzyka NaN)
editor_input = df.copy()

edited_df = st.data_editor(
    editor_input,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "pojazd": st.column_config.TextColumn("🚛 Pojazd", width="medium"),
        "event": st.column_config.TextColumn("🏷️ Nazwa Eventu", width="large"),
        "start": st.column_config.DateColumn("📅 Start"),
        "koniec": st.column_config.DateColumn("🏁 Koniec"),
        "kierowca": st.column_config.TextColumn("👤 Kierowca"),
        "notatka": st.column_config.TextColumn("📝 Notatki")
    },
    key="sqm_final_secure_grid"
)

if st.button("💾 SYNCHRONIZUJ I ZAPISZ"):
    try:
        save_df = edited_df.copy()
        # Mapowanie powrotne na nazwy arkusza
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        
        # Konwersja dat na format czytelny dla Google Sheets
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d').fillna('')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(data=save_df)
        st.toast("Zsynchronizowano z chmurą SQM", icon="✅")
        st.rerun()
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")
