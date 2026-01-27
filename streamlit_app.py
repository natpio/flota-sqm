import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# PRÓBA IMPORTU BIBLIOTEKI ŚWIĄT (Wymaga wpisu w requirements.txt)
try:
    import holidays
    pl_holidays = holidays.Poland(years=[2025, 2026, 2027])
except ImportError:
    pl_holidays = None

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="SQM Logistics Management System",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ZAAWANSOWANA STYLIZACJA CSS ---
st.markdown("""
    <style>
    /* Główna czcionka i tło aplikacji */
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stApp { background-color: #F0F2F6; }

    /* Stylizacja Sidebaru (Ciemny Navy) */
    [data-testid="stSidebar"] {
        background-color: #0A192F !important;
        border-right: 1px solid #172A45;
    }
    [data-testid="stSidebar"] * { color: #CCD6F6 !important; }
    [data-testid="stSidebar"] .stButton button {
        background-color: #64FFDA !important;
        color: #0A192F !important;
        font-weight: bold;
    }

    /* Karty Metryk (KPI) */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #E2E8F0;
    }
    [data-testid="stMetricValue"] { color: #1E293B; font-weight: 700; }

    /* Stylizacja Zakładek (Tabs) */
    .stTabs [data-baseweb="tab-list"] { gap: 15px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #FFFFFF;
        border-radius: 8px 8px 0 0;
        padding: 12px 30px;
        font-weight: 600;
        color: #475569;
        border: 1px solid #E2E8F0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border-color: #2563EB !important;
    }
    
    /* Nagłówek Dashboardu */
    .dashboard-header {
        background: linear-gradient(90deg, #1E293B 0%, #334155 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGIKA DANYCH I SYNCHRONIZACJA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    """Pobiera dane i wymusza poprawne typy, aby uniknąć błędu float/str."""
    df = conn.read(ttl="0")
    # Czyścimy wiersze całkowicie puste
    df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec']).copy()
    
    # Konwersja danych z zabezpieczeniem przed błędami (coerce)
    df['Pojazd'] = df['Pojazd'].astype(str)
    df['Projekt'] = df['Projekt'].astype(str)
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    df['Kierowca'] = df['Kierowca'].fillna("").astype(str)
    df['Status'] = df['Status'].fillna("Zaplanowane").astype(str)
    df['Uwagi'] = df['Uwagi'].fillna("").astype(str)
    
    return df.dropna(subset=['Data_Start', 'Data_Koniec'])

def save_to_sheets(dataframe):
    """Zapisuje zaktualizowany DataFrame do Google Sheets."""
    try:
        conn.update(data=dataframe)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Krytyczny błąd zapisu do bazy: {e}")
        return False

# --- 4. GŁÓWNY SILNIK APLIKACJI ---
try:
    df = get_full_data()

    # --- SIDEBAR: PANEL OPERACYJNY ---
    with st.sidebar:
        st.markdown("## 🚛 OPERACJE SQM")
        st.divider()
        
        # FORMULARZ DODAWANIA NOWEGO WPISU
        with st.expander("🆕 DODAJ NOWY EVENT", expanded=True):
            with st.form("new_event", clear_on_submit=True):
                new_project = st.text_input("Nazwa Eventu")
                # Lista pojazdów pobrana z aktualnej bazy danych
                existing_vehicles = sorted(df['Pojazd'].unique().tolist()) if not df.empty else ["TIR 1", "BUS 1"]
                new_vehicle = st.selectbox("Pojazd / Naczepa", options=existing_vehicles)
                
                new_range = st.date_input("Zakres pracy", value=(datetime.now(), datetime.now() + timedelta(days=3)))
                new_driver = st.text_input("Kierowca")
                new_status = st.selectbox("Status", ["Zaplanowane", "W trasie", "Auto", "Zakończone"])
                new_notes = st.text_area("Uwagi do transportu")
                
                submit_btn = st.form_submit_button("ZATWIERDŹ I WYŚLIJ")

        if submit_btn:
            if len(new_range) == 2 and new_project:
                s_dt, e_dt = pd.to_datetime(new_range[0]), pd.to_datetime(new_range[1])
                
                # WALIDACJA KONFLIKTU (Collision Detection)
                conflict = df[
                    (df['Pojazd'] == new_vehicle) & 
                    (df['Data_Start'] < e_dt) & 
                    (df['Data_Koniec'] > s_dt)
                ]
                
                if not conflict.empty:
                    st.error(f"❌ BLOKADA: Pojazd {new_vehicle} jest już przypisany do: {conflict.iloc[0]['Projekt']}!")
                else:
                    new_entry = pd.DataFrame([{
                        "Pojazd": new_vehicle, "Projekt": new_project, "Data_Start": s_dt,
                        "Data_Koniec": e_dt, "Kierowca": new_driver, "Status": new_status, "Uwagi": new_notes
                    }])
                    df = pd.concat([df, new_entry], ignore_index=True)
                    if save_to_sheets(df):
                        st.success("✅ Dane przesłane do Google Sheets!")
                        st.rerun()
            else:
                st.warning("Uzupełnij nazwę projektu i pełny zakres dat.")

        st.divider()
        if st.button("🔄 SYNCHRONIZUJ Z ARKUSZEM", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- WIDOK GŁÓWNY: DASHBOARD ---
    st.markdown("""
        <div class='dashboard-header'>
            <h1>Centrum Dowodzenia Logistycznego SQM</h1>
            <p>System planowania transportu, załadunków i slotów targowych</p>
        </div>
    """, unsafe_allow_html=True)

    # METRYKI KPI
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flota w systemie", df['Pojazd'].nunique())
    c2.metric("Aktywne Eventy", df['Projekt'].nunique())
    
    # Wyliczanie aut aktualnie pracujących
    today = pd.Timestamp.now().normalize()
    at_work = df[(df['Data_Start'] <= today) & (df['Data_Koniec'] >= today)].shape[0]
    c3.metric("Pojazdy w trasie (Dziś)", at_work)
    
    # Statystyka statusów
    auto_status = df[df['Status'] == 'Auto'].shape[0]
    c4.metric("Status 'Auto'", auto_status)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- ZAKŁADKI GŁÓWNE ---
    tab_gantt, tab_edit, tab_summary = st.tabs(["📅 HARMONOGRAM (GANTT)", "🛠️ PANEL EDYCJI / USUWANIA", "📊 ANALIZA WYKORZYSTANIA"])

    with tab_gantt:
        if not df.empty:
            # Sortowanie danych dla czytelności wykresu
            plot_df = df.sort_values(['Pojazd', 'Data_Start']).copy()
            
            # Tworzenie wykresu Gantta
            fig = px.timeline(
                plot_df,
                x_start="Data_Start",
                x_end="Data_Koniec",
                y="Pojazd",
                color="Projekt",
                text="Projekt",
                hover_data=["Kierowca", "Status", "Uwagi"],
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Prism
            )

            # --- KALENDARZ: MIESIĄCE, DNI, WEEKENDY ---
            start_margin = plot_df['Data_Start'].min() - timedelta(days=7)
            end_margin = plot_df['Data_Koniec'].max() + timedelta(days=14)
            
            # Pętla generująca szare pola dla weekendów i świąt
            current = start_margin
            while current <= end_margin:
                # Sprawdzanie czy weekend lub święto
                is_weekend = current.weekday() >= 5
                is_holiday = pl_holidays and current.date() in pl_holidays
                
                if is_weekend or is_holiday:
                    fig.add_vrect(
                        x0=current.strftime("%Y-%m-%d"), 
                        x1=(current + timedelta(days=1)).strftime("%Y-%m-%d"),
                        fillcolor="#E2E8F0", 
                        opacity=0.4, 
                        line_width=0,
                        layer="below"
                    )
                current += timedelta(days=1)

            # Czerwona linia aktualnego czasu
            fig.add_vline(x=datetime.now(), line_width=3, line_color="#F43F5E", line_dash="solid")

            # USTAWIENIA OSI X (Miesiące u góry, dni tygodnia pod nimi)
            fig.update_xaxes(
                dtick="D1",
                tickformat="%d\n%a", # Numer dnia + skrót dnia tygodnia
                tickfont=dict(size=10, color="#64748B"),
                side="top",
                gridcolor="#F1F5F9",
                range=[start_margin, end_margin]
            )

            fig.update_yaxes(autorange="reversed", title="", gridcolor="#F1F5F9")
            
            fig.update_layout(
                height=700,
                margin=dict(l=0, r=0, t=80, b=0),
                plot_bgcolor="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            fig.update_traces(marker_line_color='white', marker_line_width=2, opacity=0.9, textposition='inside')
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
        else:
            st.info("Baza danych jest pusta. Dodaj pierwszy rekord w panelu bocznym.")

    with tab_edit:
        st.markdown("### Zarządzanie Rejestrem Logistycznym")
        st.caption("Możesz edytować dowolną komórkę. Aby usunąć wiersz: zaznacz go po lewej stronie i naciśnij [Delete].")
        
        # INTERAKTYWNY EDYTOR DANYCH (CRUD)
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Data_Start": st.column_config.DateColumn("Start", format="DD.MM.YYYY", required=True),
                "Data_Koniec": st.column_config.DateColumn("Koniec", format="DD.MM.YYYY", required=True),
                "Status": st.column_config.SelectboxColumn("Status", options=["Zaplanowane", "W trasie", "Auto", "Zakończone"]),
                "Pojazd": st.column_config.TextColumn("🚚 Pojazd", width="medium"),
                "Projekt": st.column_config.TextColumn("📁 Projekt", width="large")
            }
        )
        
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY DO ARKUSZA", type="primary", use_container_width=True):
            if save_to_sheets(edited_df):
                st.success("Zmiany zostały trwale zapisane w Google Sheets!")
                st.rerun()

    with tab_summary:
        st.markdown("### Obłożenie Floty")
        if not df.empty:
            usage = df['Pojazd'].value_counts().reset_index()
            usage.columns = ['Pojazd', 'Liczba zadań']
            fig_bar = px.bar(usage, x='Pojazd', y='Liczba zadań', color='Liczba zadań', 
                             color_continuous_scale='Blues', template='plotly_white')
            st.plotly_chart(fig_bar, use_container_width=True)

except Exception as e:
    st.error(f"Wystąpił nieoczekiwany błąd systemu: {e}")
    st.info("Wskazówka: Sprawdź czy nazwy kolumn w Google Sheets są identyczne jak w kodzie (Pojazd, Projekt, Data_Start, Data_Koniec, Kierowca, Status, Uwagi).")
