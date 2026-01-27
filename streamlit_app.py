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
            return pd.DataFrame(columns=["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"])

        # Ujednolicenie nazw kolumn na małe litery
        data.columns = [c.strip().lower() for c in data.columns]
        
        # Usuwamy kolumnę typ, jeśli jakimś cudem jeszcze tam jest w danych wejściowych
        if 'typ' in data.columns:
            data = data.drop(columns=['typ'])
        
        # Konwersja dat na format czytelny dla wykresu
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        
        # Filtrujemy tylko wiersze z kluczowymi danymi
        return data.dropna(subset=['pojazd', 'start', 'koniec'])
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        return pd.DataFrame()

df = load_data()

st.title("🚚 SQM Multimedia Solutions - Zarządzanie Flotą")

# --- WIZUALIZACJA ---
if not df.empty:
    # Tworzenie wykresu - teraz kolorujemy według 'event', żeby paski się różniły
    fig = px.timeline(
        df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="event",
        hover_name="event",
        text="event",
        custom_data=["kierowca", "notatka"]
    )
    
    # Estetyka wykresu
    fig.update_yaxes(autorange="reversed", title="Samochód")
    fig.update_xaxes(title="Kalendarz", dtick="D1", tickformat="%d-%m")
    fig.update_traces(textposition='inside', insidetextanchor='middle')
    
    fig.update_layout(
        height=600,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False, # Ukrywamy legendę, bo przy 200 eventach byłaby nieczytelna
        hoverlabel=dict(bgcolor="white", font_size=12)
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Dodaj dane w tabeli poniżej, aby wygenerować harmonogram.")

st.divider()

# --- PANEL EDYCJI ---
st.subheader("📋 Panel Edycji i Planowania")

# Konfiguracja kolumn w edytorze (bez TYP)
edited_df = st.data_editor(
    df if not df.empty else pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"]),
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "start": st.column_config.DateColumn("Start", format="YYYY-MM-DD"),
        "koniec": st.column_config.DateColumn("Koniec", format="YYYY-MM-DD"),
        "pojazd": st.column_config.TextColumn("Pojazd"),
        "event": st.column_config.TextColumn("EVENT")
    },
    key="sqm_v4_editor"
)

# Przycisk zapisu
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
        # Przygotowanie do zapisu - nazwy kolumn dokładnie jak w Twoim arkuszu (bez TYP)
        save_df = edited_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        
        # Konwersja dat na tekst
        save_df['Start'] = save_df['Start'].astype(str)
        save_df['Koniec'] = save_df['Koniec'].astype(str)
        
        conn.update(data=save_df)
        st.success("Zapisano!")
        st.rerun()

# --- ANALIZA KOLIZJI ---
with col2:
    def check_conflicts(d):
        if d.empty: return []
        conf = []
        # Sortujemy po pojeździe i czasie startu
        d = d.sort_values(['pojazd', 'start'])
        for v in d['pojazd'].unique():
            v_data = d[d['pojazd'] == v]
            for i in range(len(v_data)-1):
                # Jeśli koniec obecnego zadania jest później niż start następnego
                if v_data.iloc[i]['koniec'] > v_data.iloc[i+1]['start']:
                    conf.append(f"⚠️ {v}: {v_data.iloc[i]['event']} koliduje z {v_data.iloc[i+1]['event']}")
        return conf

    alerts = check_conflicts(edited_df)
    if alerts:
        with st.expander("Wykryto kolizje w grafiku!", expanded=True):
            for a in alerts:
                st.error(a)
