import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# Konfiguracja strony
st.set_page_config(
    page_title="SQM Multimedia Solutions - Logistyka",
    page_icon="🚛",
    layout="wide"
)

# Stylizacja CSS dla lepszej czytelności (kontrast jak w Twoim Excelu)
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# Inicjalizacja połączenia
# Kod automatycznie pobierze dane z sekcji [connections.gsheets] w Twoich Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Odczytujemy dane - upewnij się, że arkusz ma nagłówki: Task, Start, End, Resource, Status
        data = conn.read(ttl="10s") # krótki cache dla pracy w czasie rzeczywistym
        # Usuwamy całkowicie puste wiersze
        data = data.dropna(subset=['Task', 'Start', 'End'])
        
        # Konwersja dat z obsługą błędów
        data['Start'] = pd.to_datetime(data['Start'])
        data['End'] = pd.to_datetime(data['End'])
        return data
    except Exception as e:
        st.error(f"Błąd podczas ładowania danych z Google Sheets: {e}")
        return pd.DataFrame()

# Pobieranie danych
df = load_data()

if not df.empty:
    # --- BOCZNY PANEL (SIDEBAR) ---
    st.sidebar.image("https://sqm.pl/wp-content/uploads/2018/10/logo_sqm_header.png", width=150) # Przykładowy placeholder logo
    st.sidebar.header("Zarządzanie Flotą i Slotami")
    
    # Filtrowanie daty
    min_date = df['Start'].min().date()
    max_date = df['End'].max().date()
    
    st.sidebar.subheader("Zakres czasu")
    date_range = st.sidebar.date_input(
        "Wybierz zakres:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Filtrowanie zasobów (Pojazdy/Naczepy)
    all_tasks = sorted(df['Task'].unique())
    selected_tasks = st.sidebar.multiselect(
        "Wybierz zasoby (np. naczepy/sloty):",
        options=all_tasks,
        default=all_tasks
    )

    # Filtrowanie po projektach
    all_resources = sorted(df['Resource'].unique())
    selected_resources = st.sidebar.multiselect(
        "Wybierz projekty/eventy:",
        options=all_resources,
        default=all_resources
    )

    # Aplikowanie filtrów
    mask = (df['Task'].isin(selected_tasks)) & \
           (df['Resource'].isin(selected_resources))
    
    # Dodatkowe filtrowanie daty (jeśli wybrano zakres)
    if len(date_range) == 2:
        mask = mask & (df['Start'].dt.date >= date_range[0]) & (df['End'].dt.date <= date_range[1])
    
    filtered_df = df[mask]

    # --- WIDOK GŁÓWNY ---
    st.title("Harmonogram Logistyczny SQM")
    
    # Metryki na górze
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Liczba operacji", len(filtered_df))
    m2.metric("Aktywne pojazdy", filtered_df['Task'].nunique())
    m3.metric("Projekty w toku", filtered_df['Resource'].nunique())
    m4.info("Dane pobrane z Google Cloud")

    # --- WYKRES GANTTA (Plotly) ---
    if not filtered_df.empty:
        fig = px.timeline(
            filtered_df,
            x_start="Start",
            x_end="End",
            y="Task",
            color="Resource",
            text="Resource",
            hover_data=["Status", "Start", "End"],
            opacity=0.8,
            template="plotly_white"
        )

        # Ustawienia estetyczne wykresu
        fig.update_yaxes(autorange="reversed", title="Zasób / Jednostka transportowa")
        fig.update_xaxes(
            title="Oś czasu",
            dtick="D1", # Tick co jeden dzień
            tickformat="%d.%m\n%H:%M",
            gridcolor='LightGrey'
        )
        
        fig.update_layout(
            height=700,
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # Dodanie etykiet tekstowych wewnątrz pasków
        fig.update_traces(textposition='inside', insidetextanchor='middle')

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Brak danych dla wybranych filtrów.")

    # --- SZCZEGÓŁOWA TABELA ---
    st.subheader("📋 Szczegóły transportów")
    st.dataframe(
        filtered_df.sort_values(by="Start"),
        use_container_width=True,
        column_config={
            "Start": st.column_config.DatetimeColumn("Początek", format="DD.MM.YYYY HH:mm"),
            "End": st.column_config.DatetimeColumn("Koniec", format="DD.MM.YYYY HH:mm"),
            "Task": "Zasób",
            "Resource": "Projekt/Klient"
        }
    )

else:
    st.info("Oczekiwanie na dane z arkusza Google... Upewnij się, że dodałeś adres Service Account do udostępniania.")

# Stopka z informacją o wersji
st.markdown("---")
st.caption(f"Wersja Systemu 1.0 | Ostatnia synchronizacja: {datetime.now().strftime('%H:%M:%S')}")
