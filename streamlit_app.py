import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Konfiguracja strony
st.set_page_config(page_title="SQM Logistics | Fleet Manager", layout="wide", initial_sidebar_state="expanded")

# Stylizacja CSS
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        
        # Normalizacja nazw kolumn
        data.columns = [c.strip().lower() for c in data.columns]
        
        # KLUCZOWA POPRAWKA: Konwersja dat z obsługą błędów (coerce zamieni złe formaty na NaT/None)
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        
        # Upewniamy się, że kolumny tekstowe są faktycznie tekstami (usuwamy None)
        text_cols = ['pojazd', 'event', 'kierowca', 'notatka']
        for col in text_cols:
            if col in data.columns:
                data[col] = data[col].astype(str).replace('nan', '').replace('None', '')
            else:
                data[col] = ""
                
        return data
    except Exception as e:
        st.error(f"Błąd bazy: {e}")
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = load_data()

# --- SIDEBAR ---
st.sidebar.title("Nawigacja")
if not df.empty:
    # Usuwamy puste wpisy z listy pojazdów do filtra
    unique_vehs = sorted([v for v in df['pojazd'].unique() if v])
    selected_vehicles = st.sidebar.multiselect("Filtruj pojazdy", unique_vehs, default=unique_vehs)
    display_df = df[df['pojazd'].isin(selected_vehicles)]
else:
    display_df = df

st.sidebar.divider()
st.sidebar.info("SQM Flota v4.1")

# --- NAGŁÓWEK I METRYKI ---
st.title("🚚 Planowanie Logistyki SQM")

m1, m2, m3, m4 = st.columns(4)
today = datetime.now()
active_tasks = display_df[(display_df['start'] <= today) & (display_df['koniec'] >= today)].shape[0] if not display_df.empty else 0
total_fleet = display_df['pojazd'].nunique() if not display_df.empty else 0

m1.metric("Aktywne Transporty", active_tasks)
m2.metric("Pojazdy w filtrze", total_fleet)
m3.metric("Zaplanowane Eventy", display_df.shape[0])
m4.metric("Dzisiejsza Data", today.strftime("%d.%m.%Y"))

st.divider()

# --- HARMONOGRAM ---
if not display_df.empty and display_df['start'].notnull().any():
    st.subheader("Oś Czasu Wydarzeń")
    # Filtrujemy tylko wiersze z poprawnymi datami do wykresu
    plot_df = display_df.dropna(subset=['start', 'koniec', 'pojazd'])
    plot_df = plot_df[plot_df['pojazd'] != ""]
    
    if not plot_df.empty:
        fig = px.timeline(
            plot_df, 
            x_start="start", 
            x_end="koniec", 
            y="pojazd", 
            color="event",
            hover_name="event",
            text="event",
            custom_data=["kierowca", "notatka"],
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_yaxes(autorange="reversed", title="")
        fig.update_xaxes(dtick="D1", tickformat="%d\n%b", side="top")
        fig.update_layout(height=500, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Brak danych z poprawnymi datami do wyświetlenia wykresu.")

# --- PANEL EDYCJI ---
st.subheader("📝 Zarządzanie Danymi")

# Tworzymy czystą kopię do edytora, aby uniknąć problemów z typami
editor_df = df.copy()

edited_df = st.data_editor(
    editor_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "start": st.column_config.DateColumn("Start", format="YYYY-MM-DD"),
        "koniec": st.column_config.DateColumn("Koniec", format="YYYY-MM-DD"),
        "pojazd": st.column_config.TextColumn("Pojazd"),
        "event": st.column_config.TextColumn("EVENT"),
        "kierowca": st.column_config.TextColumn("Kierowca"),
        "notatka": st.column_config.TextColumn("Notatka")
    },
    key="sqm_v4_1_editor"
)

if st.button("💾 ZAPISZ ZMIANY", type="primary"):
    save_df = edited_df.copy()
    # Przywracamy nazwy kolumn arkusza
    save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
    # Konwersja na tekst, żeby Google Sheets nie miało problemów z formatem JSON
    save_df['Start'] = save_df['Start'].dt.strftime('%Y-%m-%d').fillna('')
    save_df['Koniec'] = save_df['Koniec'].dt.strftime('%Y-%m-%d').fillna('')
    
    conn.update(data=save_df)
    st.toast("Zsynchronizowano!", icon="✅")
    st.rerun()
