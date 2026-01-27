import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# Konfiguracja strony
st.set_page_config(page_title="SQM Logistics Planner", layout="wide")

# Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Odczyt danych z arkusza FLOTA_SQM
        data = conn.read(ttl="0s")
        
        if data is None or data.empty:
            st.warning("Arkusz jest pusty lub nie można go odczytać.")
            return pd.DataFrame()

        # Normalizacja nazw kolumn (usuwamy spacje i zmieniamy na małe litery dla pewności)
        # To sprawi, że "EVENT", "Event" i "event" będą traktowane tak samo
        data.columns = [c.strip().lower() for c in data.columns]
        
        # Wymagane mapowanie dla Twojego arkusza ze zdjęcia:
        # Twoje kolumny: pojazd, event, start, koniec, typ, kierowca, notatka
        
        # Konwersja dat
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        
        # Usuwamy wiersze, które nie mają kluczowych danych (np. pusty pojazd lub data)
        return data.dropna(subset=['pojazd', 'start', 'koniec'])
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        return pd.DataFrame()

df = load_data()

st.title("🚚 SQM Multimedia Solutions - Logistyka Floty")

# --- WIDOK HARMONOGRAMU ---
st.subheader("Interaktywny Harmonogram")

if not df.empty:
    try:
        # Używamy małych liter w nazwach kolumn zgodnie z tym, co zrobił load_data()
        fig = px.timeline(
            df, 
            x_start="start", 
            x_end="koniec", 
            y="pojazd", 
            color="typ" if "typ" in df.columns else None,
            hover_name="event",
            text="event",
            custom_data=["kierowca", "notatka"] if "kierowca" in df.columns else None
        )
        
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Pojazd",
            height=600,
            xaxis=dict(tickformat="%d-%m", dtick="D1")
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Błąd generowania wykresu: {e}")
        st.info("Upewnij się, że kolumny Start i Koniec zawierają poprawne daty (RRRR-MM-DD).")
else:
    st.info("Brak danych do wyświetlenia na wykresie. Sprawdź czy daty w arkuszu są poprawne.")

st.divider()

# --- EDYCJA DANYCH ---
st.subheader("Panel Edycji (Live Sync)")

# Przygotowanie ramki do edycji (jeśli arkusz był pusty)
if df.empty:
    display_df = pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "typ", "kierowca", "notatka"])
else:
    display_df = df

edited_df = st.data_editor(
    display_df,
    num_rows="dynamic",
    use_container_width=True,
    key="sqm_editor"
)

if st.button("💾 ZAPISZ I SYNCHRONIZUJ"):
    try:
        # Przygotowanie do zapisu (powrót do nazw z Twojego zdjęcia dla Google Sheets)
        save_df = edited_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "TYP", "Kierowca", "Notatka"]
        
        # Konwersja dat na tekst przed wysyłką
        save_df['Start'] = save_df['Start'].astype(str)
        save_df['Koniec'] = save_df['Koniec'].astype(str)
        
        conn.update(data=save_df)
        st.success("Dane zostały zapisane pomyślnie w Arkuszu Google!")
        st.rerun()
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")
