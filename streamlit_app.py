import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="SQM Logistics Planner", layout="wide")

# Inicjalizacja połączenia z Google Sheets
# Upewnij się, że w secrets masz odpowiednie poświadczenia
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Odczytujemy dane z arkusza
        data = conn.read(ttl="0s")
        # Jeśli arkusz jest pusty, tworzymy strukturę z Twoimi nagłówkami
        if data.empty:
            return pd.DataFrame(columns=["Pojazd", "Event", "Start", "Koniec", "Typ", "Kierowca", "Notatka"])
        
        # Konwersja dat na format datetime dla obliczeń i wykresu
        data['Start'] = pd.to_datetime(data['Start'])
        data['Koniec'] = pd.to_datetime(data['Koniec'])
        return data
    except Exception as e:
        st.error(f"Błąd podczas ładowania danych: {e}")
        return pd.DataFrame(columns=["Pojazd", "Event", "Start", "Koniec", "Typ", "Kierowca", "Notatka"])

# Załadowanie aktualnych danych
df = load_data()

st.title("🚚 SQM Multimedia Solutions - Logistyka Eventowa")

# --- WIDOK HARMONOGRAMU (GANTT) ---
st.subheader("Harmonogram Floty")

if not df.empty:
    # Tworzenie interaktywnego wykresu Gantta
    fig = px.timeline(
        df, 
        x_start="Start", 
        x_end="Koniec", 
        y="Pojazd", 
        color="Typ",
        hover_name="Event",
        text="Event",
        custom_data=["Kierowca", "Notatka"]
    )
    
    # Konfiguracja wyglądu
    fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=sorted(df['Pojazd'].unique()))
    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Samochód",
        height=600,
        xaxis=dict(
            tickformat="%d-%m",
            dtick="D1",
            gridcolor="LightGrey"
        ),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    # Dodanie informacji o kierowcy do dymka po najechaniu
    fig.update_traces(
        hovertemplate="<b>Event: %{hovertext}</b><br>Kierowca: %{customdata[0]}<br>Start: %{x|%Y-%m-%d}<br>Koniec: %{x|%Y-%m-%d}<br>Notatka: %{customdata[1]}"
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Brak danych do wyświetlenia. Dodaj pierwszy event poniżej.")

# --- PANEL ZARZĄDZANIA I EDYCJI ---
st.divider()
col_table, col_actions = st.columns([3, 1])

with col_table:
    st.subheader("Tabela Planowania")
    # Edytor danych zastępujący Excela
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True, 
        key="main_table_editor",
        column_config={
            "Start": st.column_config.DateColumn("Start", format="YYYY-MM-DD", required=True),
            "Koniec": st.column_config.DateColumn("Koniec", format="YYYY-MM-DD", required=True),
            "Typ": st.column_config.SelectboxColumn("Typ", options=["Targi", "Transport", "Serwis", "Magazyn", "Stałe"]),
            "Pojazd": st.column_config.TextColumn("Pojazd", help="Wpisz nazwę lub numer rejestracyjny")
        }
    )

with col_actions:
    st.subheader("Zarządzanie")
    if st.button("💾 ZAPISZ ZMIANY", use_container_width=True, type="primary"):
        # Konwersja dat z powrotem na stringi przed zapisem do arkusza
        final_df = edited_df.copy()
        final_df['Start'] = final_df['Start'].dt.strftime('%Y-%m-%d')
        final_df['Koniec'] = final_df['Koniec'].dt.strftime('%Y-%m-%d')
        
        conn.update(data=final_df)
        st.success("Dane zapisane w Google Sheets!")
        st.rerun()

    if st.button("🔄 ODŚWIEŻ", use_container_width=True):
        st.rerun()

    # --- KONTROLA KOLIZJI ---
    st.subheader("Status floty")
    
    def check_conflicts(dataframe):
        conflicts = []
        # Ignorujemy puste wiersze
        valid_df = dataframe.dropna(subset=['Pojazd', 'Start', 'Koniec']).sort_values(['Pojazd', 'Start'])
        
        for vehicle in valid_df['Pojazd'].unique():
            v_df = valid_df[valid_df['Pojazd'] == vehicle]
            for i in range(len(v_df) - 1):
                current_event = v_df.iloc[i]
                next_event = v_df.iloc[i+1]
                
                # Sprawdzenie czy daty się nakładają
                if current_event['Koniec'] > next_event['Start']:
                    conflicts.append({
                        "Pojazd": vehicle,
                        "E1": current_event['Event'],
                        "E2": next_event['Event']
                    })
        return conflicts

    conflicts = check_conflicts(edited_df)
    if conflicts:
        for c in conflicts:
            st.error(f"⚠️ **KOLIZJA:** {c['Pojazd']}\n\n {c['E1']} nakłada się na {c['E2']}")
    else:
        st.success("✅ Brak kolizji w terminach.")

# --- EKSPORT ---
st.sidebar.subheader("Eksport danych")
csv = edited_df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    "Pobierz jako CSV",
    csv,
    "plan_floty_sqm.csv",
    "text/csv",
    key='download-csv'
)
