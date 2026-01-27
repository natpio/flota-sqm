import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# Konfiguracja strony pod standardy SQM
st.set_page_config(page_title="SQM Logistics Planner", layout="wide")

# Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Odczyt danych z arkusza FLOTA_SQM
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["Pojazd", "EVENT", "Start", "Koniec", "TYP", "Kierowca", "Notatka"])

        # Ujednolicenie nazw kolumn na małe litery do obróbki w Pythonie
        data.columns = [c.strip().lower() for c in data.columns]
        
        # Konwersja dat na format czytelny dla wykresu
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        
        # Filtrujemy tylko wiersze, które mają minimum danych do wyświetlenia
        return data.dropna(subset=['pojazd', 'start', 'koniec'])
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        return pd.DataFrame()

df = load_data()

st.title("🚚 SQM Multimedia Solutions - Zarządzanie Flotą")

# --- WIZUALIZACJA ---
if not df.empty:
    # Definiujemy kolory dla typów zadań (odpowiedniki kolorów z Twojego Excela)
    color_map = {
        "TARGI": "#1f77b4",      # Niebieski
        "TRANSPORT": "#ff7f0e",  # Pomarańczowy
        "SERWIS": "#d62728",     # Czerwony
        "MAGAZYN": "#bcbd22",    # Żółty
        "BCN": "#e377c2",        # Różowy (Barcelona)
        "STAŁE": "#7f7f7f"       # Szary
    }

    # Tworzenie wykresu
    fig = px.timeline(
        df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="typ",
        hover_name="event",
        text="event",
        custom_data=["kierowca", "notatka"],
        color_discrete_map=color_map
    )
    
    # Estetyka wykresu
    fig.update_yaxes(autorange="reversed", title="Samochód")
    fig.update_xaxes(title="Kalendarz", dtick="D1", tickformat="%d-%m")
    fig.update_traces(textposition='inside', insidetextanchor='middle')
    
    fig.update_layout(
        height=600,
        margin=dict(l=20, r=20, t=40, b=20),
        legend_title_text="Rodzaj zadania",
        hoverlabel=dict(bgcolor="white", font_size=12)
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Dodaj dane w tabeli poniżej, aby wygenerować harmonogram.")

# --- PANEL EDYCJI ---
st.divider()
st.subheader("📋 Panel Edycji i Planowania")

# Konfiguracja kolumn w edytorze
edited_df = st.data_editor(
    df if not df.empty else pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "typ", "kierowca", "notatka"]),
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "start": st.column_config.DateColumn("Start", format="YYYY-MM-DD"),
        "koniec": st.column_config.DateColumn("Koniec", format="YYYY-MM-DD"),
        "typ": st.column_config.SelectboxColumn("TYP", options=["TARGI", "TRANSPORT", "SERWIS", "MAGAZYN", "BCN", "STAŁE"]),
        "pojazd": st.column_config.TextColumn("Pojazd")
    },
    key="sqm_v3_editor"
)

# Przycisk zapisu
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
        # Przygotowanie do zapisu - przywracamy oryginalne nazwy kolumn z Twojego arkusza
        save_df = edited_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "TYP", "Kierowca", "Notatka"]
        
        # Konwersja dat na tekst przed wysyłką do Google
        save_df['Start'] = save_df['Start'].astype(str)
        save_df['Koniec'] = save_df['Koniec'].astype(str)
        
        conn.update(data=save_df)
        st.success("Zsynchronizowano z Google Sheets!")
        st.rerun()

# --- ANALIZA KOLIZJI ---
with col2:
    def check_conflicts(d):
        if d.empty: return []
        conf = []
        d = d.sort_values(['pojazd', 'start'])
        for v in d['pojazd'].unique():
            v_data = d[d['pojazd'] == v]
            for i in range(len(v_data)-1):
                if v_data.iloc[i]['koniec'] > v_data.iloc[i+1]['start']:
                    conf.append(f"⚠️ {v}: {v_data.iloc[i]['event']} nachodzi na {v_data.iloc[i+1]['event']}")
        return conf

    alerts = check_conflicts(edited_df)
    if alerts:
        with st.expander("Wykryto kolizje w grafiku!", expanded=True):
            for a in alerts:
                st.error(a)
