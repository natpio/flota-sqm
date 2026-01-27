import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import holidays

# 1. KONFIGURACJA SYSTEMOWA
st.set_page_config(
    page_title="SQM Logistics OS",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. KOMPLETNA STYLIZACJA (CSS) - Profesjonalny Dashboard Enterprise
st.markdown("""
    <style>
    /* Główny font i tło */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F1F5F9; }
    
    /* Sidebar - Ciemny motyw SQM */
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] * { color: #F8FAFC !important; }
    
    /* Karty KPI */
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #E2E8F0;
    }
    
    /* Kontener Wykresu */
    .plot-container {
        background-color: white;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
    }

    /* Stylizacja Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #E2E8F0;
        border-radius: 8px 8px 0 0;
        padding: 10px 25px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. POŁĄCZENIE I ZARZĄDZANIE DANYMI
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_data():
    """Pobiera i czyści dane z Google Sheets."""
    raw_df = conn.read(ttl="0") # ttl=0 wymusza brak cache'u przy odczycie
    # Eliminacja pustych wierszy i śmieciowych danych
    df = raw_df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec']).copy()
    
    # Konwersja typów z obsługą błędów
    df['Pojazd'] = df['Pojazd'].astype(str)
    df['Projekt'] = df['Projekt'].astype(str)
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    df['Kierowca'] = df['Kierowca'].fillna("").astype(str)
    df['Status'] = df['Status'].fillna("Zaplanowane").astype(str)
    
    return df.dropna(subset=['Data_Start', 'Data_Koniec'])

def update_gsheet(dataframe):
    """Zapisuje cały DataFrame z powrotem do arkusza."""
    try:
        conn.update(data=dataframe)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")
        return False

# 4. LOGIKA GŁÓWNA
try:
    df = fetch_data()
    pl_holidays = holidays.Poland(years=[2025, 2026, 2027])

    # --- PANEL BOCZNY: FORMULARZ DODAWANIA ---
    with st.sidebar:
        st.markdown("## 🚛 NOWY EVENT")
        with st.form("add_event_form", clear_on_submit=True):
            f_event = st.text_input("Nazwa Eventu / Projektu")
            f_vehicle = st.selectbox("Wybierz Pojazd", options=sorted(df['Pojazd'].unique()) if not df.empty else ["Naczepa 1"])
            f_dates = st.date_input("Okres (Start - Koniec)", value=(datetime.now(), datetime.now() + timedelta(days=2)))
            f_driver = st.text_input("Kierowca / Osoba odp.")
            f_status = st.selectbox("Status", ["Zaplanowane", "W trasie", "Auto", "Zakończone"])
            f_notes = st.text_area("Uwagi")
            
            submitted = st.form_submit_button("DODAJ DO HARMONOGRAMU", use_container_width=True)

        if submitted:
            if len(f_dates) == 2:
                start_dt = pd.to_datetime(f_dates[0])
                end_dt = pd.to_datetime(f_dates[1])
                
                # Walidacja kolizji (Conflict Detection)
                conflict = df[
                    (df['Pojazd'] == f_vehicle) & 
                    (df['Data_Start'] < end_dt) & 
                    (df['Data_Koniec'] > start_dt)
                ]
                
                if not conflict.empty:
                    st.error(f"❌ KOLIZJA! {f_vehicle} jest zajęty: {conflict.iloc[0]['Projekt']}")
                elif not f_event:
                    st.warning("Podaj nazwę projektu.")
                else:
                    new_row = pd.DataFrame([{
                        "Pojazd": f_vehicle, "Projekt": f_event, "Data_Start": start_dt,
                        "Data_Koniec": end_dt, "Kierowca": f_driver, "Status": f_status, "Uwagi": f_notes
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    if update_gsheet(df):
                        st.success("Dodano pomyślnie!")
                        st.rerun()
            else:
                st.error("Wybierz datę początku i końca.")

    # --- WIDOK GŁÓWNY DASHBOARDU ---
    st.title("Pulpit Zarządzania Logistyką SQM")
    
    # Metryki KPI
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Flota", df['Pojazd'].nunique())
    kpi2.metric("Projekty", df['Projekt'].nunique())
    
    today = pd.Timestamp.now().normalize()
    active_now = df[(df['Data_Start'] <= today) & (df['Data_Koniec'] >= today)].shape[0]
    kpi3.metric("W akcji (dziś)", active_now)
    kpi4.info("System Synchronized")

    # --- TABS ---
    tab_visual, tab_editor = st.tabs(["📅 HARMONOGRAM WIZUALNY", "🛠️ EDYCJA I USUWANIE"])

    with tab_visual:
        # Budowa zaawansowanego wykresu Plotly
        if not df.empty:
            # Sortowanie dla porządku na osi Y
            plot_df = df.sort_values(['Pojazd', 'Data_Start']).copy()
            
            fig = px.timeline(
                plot_df,
                x_start="Data_Start",
                x_end="Data_Koniec",
                y="Pojazd",
                color="Projekt",
                text="Projekt",
                hover_data=["Kierowca", "Status", "Uwagi"],
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Dark24
            )

            # --- KALENDARZ: MIESIĄCE, DNI, WEEKENDY ---
            start_view = plot_df['Data_Start'].min() - timedelta(days=3)
            end_view = plot_df['Data_Koniec'].max() + timedelta(days=14)
            
            # Wyróżnienie weekendów i świąt (Grey Areas)
            curr = start_view
            while curr <= end_view:
                if curr.weekday() >= 5 or curr.date() in pl_holidays:
                    fig.add_vrect(
                        x0=curr.strftime("%Y-%m-%d"), 
                        x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                        fillcolor="rgba(128, 128, 128, 0.2)", 
                        line_width=0,
                        layer="below"
                    )
                curr += timedelta(days=1)

            # Linia "TERAZ"
            fig.add_vline(x=datetime.now(), line_width=2, line_color="#EF4444", line_dash="dash")

            # Ustawienia osi
            fig.update_yaxes(autorange="reversed", title="")
            fig.update_xaxes(
                dtick="D1",
                tickformat="%d\n%a", # Dzień i skrót dnia tygodnia
                tickfont=dict(size=10),
                side="top",
                gridcolor="#E2E8F0",
                range=[start_view, end_view]
            )

            fig.update_layout(
                height=600,
                margin=dict(l=10, r=10, t=60, b=10),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
        else:
            st.info("Brak danych do wyświetlenia. Dodaj pierwszy event w panelu bocznym.")

    with tab_editor:
        st.markdown("### Zarządzanie rekordami")
        st.info("Tu możesz edytować każdą komórkę lub usunąć wiersz (zaznacz go i naciśnij Delete).")
        
        # Interaktywny edytor danych
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Data_Start": st.column_config.DateColumn("Start", format="DD.MM.YYYY"),
                "Data_Koniec": st.column_config.DateColumn("Koniec", format="DD.MM.YYYY"),
                "Status": st.column_config.SelectboxColumn("Status", options=["Zaplanowane", "W trasie", "Auto", "Zakończone"])
            }
        )
        
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("💾 ZAPISZ ZMIANY", use_container_width=True, type="primary"):
                if update_gsheet(edited_df):
                    st.success("Zapisano!")
                    st.rerun()

except Exception as e:
    st.error(f"Błąd krytyczny aplikacji: {e}")
