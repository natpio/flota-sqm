import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# Konfiguracja strony
st.set_page_config(
    page_title="SQM FLOTA - Panel Logistyczny",
    page_icon="🚛",
    layout="wide"
)

# Nagłówek SQM
st.title("🚛 System Zarządzania Flotą SQM")
st.markdown(f"**Stan na dzień:** {datetime.now().strftime('%d.%m.%Y')}")
st.divider()

# Inicjalizacja połączenia z Twoim arkuszem FLOTA_SQM
conn = st.connection("gsheets", type=GSheetsConnection)

def check_conflicts(df):
    """Funkcja wykrywająca nakładające się terminy dla tego samego pojazdu."""
    conflicts = []
    # Sortujemy po pojeździe i dacie startu
    df_sorted = df.sort_values(['Pojazd', 'Data_Start'])
    
    for i in range(len(df_sorted) - 1):
        current_row = df_sorted.iloc[i]
        next_row = df_sorted.iloc[i+1]
        
        # Jeśli ten sam pojazd i daty się zazębiają
        if current_row['Pojazd'] == next_row['Pojazd']:
            if current_row['Data_Koniec'] > next_row['Data_Start']:
                conflicts.append(current_row['Pojazd'])
    return list(set(conflicts))

try:
    # Pobieranie danych z arkusza FLOTA_SQM
    # ttl="0" pozwala na pobieranie świeżych danych przy każdym odświeżeniu
    df = conn.read(ttl="0")
    
    # Czyszczenie danych (usunięcie pustych wierszy pod tabelą)
    df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
    
    # Konwersja dat na format datetime
    df['Data_Start'] = pd.to_datetime(df['Data_Start'])
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'])

    # Wykrywanie konfliktów
    conflicting_vehicles = check_conflicts(df)

    # --- PANEL BOCZNY (SIDEBAR) ---
    st.sidebar.header("Filtry i Ustawienia")
    
    # Wybór widoku
    view_mode = st.sidebar.radio("Widok:", ["Harmonogram (Gantt)", "Lista zadań", "Konflikty"])
    
    # Filtrowanie pojazdów
    selected_vehicles = st.sidebar.multiselect(
        "Filtruj pojazdy:",
        options=sorted(df['Pojazd'].unique()),
        default=df['Pojazd'].unique()
    )

    # Filtrowanie projektów
    selected_projects = st.sidebar.multiselect(
        "Filtruj projekty:",
        options=sorted(df['Projekt'].unique()),
        default=df['Projekt'].unique()
    )

    # Zastosowanie filtrów
    filtered_df = df[
        (df['Pojazd'].isin(selected_vehicles)) & 
        (df['Projekt'].isin(selected_projects))
    ]

    # --- GŁÓWNA SEKCJA WIZUALIZACJI ---

    if view_mode == "Harmonogram (Gantt)":
        if not filtered_df.empty:
            # Tworzenie wykresu Gantta
            fig = px.timeline(
                filtered_df,
                x_start="Data_Start",
                x_end="Data_Koniec",
                y="Pojazd",
                color="Projekt",
                hover_data=["Kierowca", "Status", "Uwagi"],
                title="Obłożenie Floty",
                text="Projekt",
                template="plotly_white"
            )

            # Odwrócenie osi Y, aby pojazdy były w kolejności alfabetycznej od góry
            fig.update_yaxes(autorange="reversed")
            
            # Formatowanie osi czasu
            fig.update_xaxes(
                dtick="D1", 
                tickformat="%d.%m",
                gridcolor='rgba(0,0,0,0.1)'
            )

            fig.update_layout(
                height=600,
                xaxis_title="Kalendarz",
                yaxis_title="Jednostka transportowa",
                font=dict(size=12)
            )
            
            # Stylizacja pasków
            fig.update_traces(textposition='inside', insidetextanchor='middle')

            st.plotly_chart(fig, use_container_width=True)
            
            # Alert o konfliktach pod wykresem
            if conflicting_vehicles:
                st.error(f"⚠️ WYKRYTO KOLIZJE TERMINÓW dla: {', '.join(conflicting_vehicles)}")
        else:
            st.warning("Brak danych do wyświetlenia dla wybranych filtrów.")

    elif view_mode == "Lista zadań":
        st.subheader("Aktualna lista zleceń logistycznych")
        # Wyświetlamy tabelę z ładnym formatowaniem
        st.dataframe(
            filtered_df.sort_values(by="Data_Start"),
            use_container_width=True,
            column_config={
                "Data_Start": st.column_config.DateColumn("Początek", format="DD.MM.YYYY"),
                "Data_Koniec": st.column_config.DateColumn("Koniec", format="DD.MM.YYYY"),
                "Pojazd": st.column_config.TextColumn("Pojazd/Naczepa"),
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Zaplanowane", "W trasie", "Zakończone", "Auto"]
                )
            },
            hide_index=True
        )

    elif view_mode == "Konflikty":
        st.subheader("⚠️ Raport kolizji w harmonogramie")
        if conflicting_vehicles:
            conflict_data = df[df['Pojazd'].isin(conflicting_vehicles)].sort_values(['Pojazd', 'Data_Start'])
            st.write("Poniższe pojazdy mają nałożone na siebie terminy:")
            st.table(conflict_data[['Pojazd', 'Projekt', 'Data_Start', 'Data_Koniec', 'Kierowca']])
        else:
            st.success("Brak konfliktów w harmonogramie. Wszystkie sloty są wolne.")

except Exception as e:
    st.error(f"Problem z odczytem arkusza: {e}")
    st.info("Sprawdź, czy nazwy kolumn w Google Sheets są identyczne jak w kodzie: Pojazd, Projekt, Data_Start, Data_Koniec, Kierowca, Status, Uwagi")

# Stopka
st.divider()
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Odśwież dane"):
        st.rerun()
with col2:
    st.caption("Aplikacja logistyczna SQM Multimedia Solutions | v1.1")
