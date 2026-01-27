import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Konfiguracja strony - szeroki układ ułatwia przeglądanie harmonogramu
st.set_page_config(page_title="SQM FLOTA - Panel Logistyczny", layout="wide")

st.title("🚚 Zarządzanie Flotą i Transportem SQM")
st.markdown("---")

# Inicjalizacja połączenia z Google Sheets (Arkusz: FLOTA_SQM)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Odczytujemy dane. TTL=0 wymusza odświeżenie przy każdym przeładowaniu
    return conn.read(worksheet="FLOTA_SQM", ttl="0")

try:
    df = load_data()
except Exception as e:
    st.error(f"Nie udało się połączyć z arkuszem 'FLOTA_SQM'. Sprawdź nazwę arkusza i uprawnienia.")
    st.stop()

# --- PANEL BOCZNY: OPERACJE ---
with st.sidebar:
    st.header("⚙️ Zarządzanie Transportem")
    
    with st.expander("➕ Dodaj nowy transport", expanded=False):
        with st.form("add_form"):
            pojazd = st.selectbox("Wybierz pojazd", [
                "TIR 31 - P21V388/P22X300 STABLEWSKI",
                "TIR 2 - W2654FT/P22H972 KOGUS",
                "TIR 3 - PNT3530A/P24U343 DANIELAK",
                "44 - SOLO PY 73262",
                "45 - PY1541M + przyczepa",
                "Jumper - PY22952",
                "Jumper - PY22954",
                "Boxer - PO 5VT68",
                "Boxer - WZ211GF",
                "Boxer - WZ214GF",
                "Boxer - WZ215GF",
                "OPEL DW4W443",
                "SPEDYCJA"
            ])
            projekt = st.text_input("Nazwa wydarzenia / Projektu", placeholder="np. MWC Barcelona")
            kierowca = st.text_input("Kierowca / Dane kontaktowe")
            
            col1, col2 = st.columns(2)
            d_start = col1.date_input("Data wyjazdu/załadunku")
            d_end = col2.date_input("Data powrotu/rozładunku")
            
            status = st.selectbox("Status początkowy", ["Planowanie", "Potwierdzone", "W trasie", "Serwis"])
            
            submit = st.form_submit_button("DODAJ DO GRAFIKU")
            
            if submit:
                if d_start > d_end:
                    st.error("BŁĄD: Data zakończenia jest wcześniejsza niż rozpoczęcia.")
                else:
                    new_entry = pd.DataFrame([{
                        "Pojazd": pojazd,
                        "Projekt": projekt,
                        "Data_Start": d_start.strftime('%Y-%m-%d'),
                        "Data_Koniec": d_end.strftime('%Y-%m-%d'),
                        "Kierowca": kierowca,
                        "Status": status
                    }])
                    updated_df = pd.concat([df, new_entry], ignore_index=True)
                    conn.update(worksheet="FLOTA_SQM", data=updated_df)
                    st.success("Zapisano pomyślnie!")
                    st.rerun()

    st.markdown("---")
    st.info("Aplikacja synchronizuje dane w czasie rzeczywistym z arkuszem Google: **FLOTA_SQM**.")

# --- WIZUALIZACJA HARMONOGRAMU (Zastępuje widok Excela) ---

st.subheader("🗓️ Oś Czasu i Obłożenie Slotów")

if not df.empty:
    # Konwersja dat dla Plotly
    df['Data_Start'] = pd.to_datetime(df['Data_Start'])
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'])

    # Filtry widoku
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        date_range = st.date_input(
            "Zakres podglądu",
            value=(datetime.now().date() - timedelta(days=7), datetime.now().date() + timedelta(days=30))
        )
    
    # Tworzenie wykresu Gantta
    fig = px.timeline(
        df, 
        x_start="Data_Start", 
        x_end="Data_Koniec", 
        y="Pojazd", 
        color="Status",
        hover_name="Projekt",
        hover_data=["Kierowca", "Data_Start", "Data_Koniec"],
        text="Projekt",
        opacity=0.8,
        template="plotly_white",
        color_discrete_map={
            "Planowanie": "#FFA500",
            "Potwierdzone": "#2E8B57",
            "W trasie": "#1E90FF",
            "Serwis": "#FF4500"
        }
    )

    # Ustawienie zakresu osi X zgodnie z wyborem użytkownika
    if len(date_range) == 2:
        fig.update_xaxes(range=[date_range[0], date_range[1]])

    fig.update_yaxes(autorange="reversed")  # Zachowanie kolejności pojazdów z góry na dół
    fig.update_layout(
        height=700,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Dni miesiąca",
        yaxis_title=None,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- EDYCJA DANYCH W TABELI ---
    st.markdown("---")
    st.subheader("📝 Edycja szczegółowa (Sloty, Kierowcy, Ładunki)")
    
    # Edytowalna tabela z walidacją typów
    edited_df = st.data_editor(
        df,
        column_config={
            "Pojazd": st.column_config.TextColumn("Pojazd", width="medium", disabled=False),
            "Projekt": st.column_config.TextColumn("Projekt/Targi", width="large"),
            "Data_Start": st.column_config.DateColumn("Wyjazd"),
            "Data_Koniec": st.column_config.DateColumn("Powrót"),
            "Status": st.column_config.SelectboxColumn(
                "Status", 
                options=["Planowanie", "Potwierdzone", "W trasie", "Serwis", "Zakończone"]
            )
        },
        num_rows="dynamic",
        use_container_width=True,
        key="main_editor"
    )

    if st.button("💾 ZAPISZ ZMIANY W BAZIE"):
        try:
            conn.update(worksheet="FLOTA_SQM", data=edited_df)
            st.success("Baza FLOTA_SQM została zaktualizowana!")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd podczas zapisu: {e}")

else:
    st.warning("Baza danych jest obecnie pusta.")

# --- OCENA SYTUACJI LOGISTYCZNEJ ---
st.markdown("---")
st.subheader("⚖️ Ocena logistyczna")
col_stat1, col_stat2, col_stat3 = st.columns(3)

with col_stat1:
    conflict_count = df.duplicated(subset=['Pojazd', 'Data_Start']).sum()
    if conflict_count > 0:
        st.error(f"Wykryto kolizje terminów: {conflict_count}")
    else:
        st.success("Brak nakładających się terminów dla tych samych aut.")

with col_stat2:
    active_trucks = df[df['Status'] == "W trasie"]['Pojazd'].nunique()
    st.metric("Pojazdy aktualnie w trasie", active_trucks)

with col_stat3:
    upcoming_events = df[df['Data_Start'] > datetime.now()].shape[0]
    st.metric("Nadchodzące transporty", upcoming_events)
