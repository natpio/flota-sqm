import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY - MUSI BYĆ NA SAMEJ GÓRZE
st.set_page_config(
    page_title="SQM Fleet Dashboard",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. ZAAWANSOWANA STYLIZACJA CSS (Profesjonalny UI)
st.markdown("""
    <style>
    /* Tło główne */
    .stApp { background-color: #F8FAFC; }
    
    /* Ciemny Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
        color: white !important;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label {
        color: #E2E8F0 !important;
    }
    
    /* Karty metryk (KPI) */
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #E2E8F0;
    }
    
    /* Stylizacja zakładek */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #F1F5F9;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 600;
        color: #475569;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. POŁĄCZENIE Z DANYMI
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Pobieranie danych z arkusza FLOTA_SQM
    df = conn.read(ttl="2s")
    # Usuwamy całkowicie puste wiersze
    df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
    # Konwersja dat
    df['Data_Start'] = pd.to_datetime(df['Data_Start'])
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'])
    return df

try:
    df = load_data()

    # --- PANEL BOCZNY (SIDEBAR) ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; color: white;'>SQM FLOTA</h2>", unsafe_allow_html=True)
        st.divider()
        
        st.markdown("### ⚙️ KONFIGURACJA")
        search = st.text_input("🔍 Szukaj projektu/auta")
        
        # Wybór statusów do wyświetlenia
        status_options = sorted(df['Status'].unique().tolist())
        selected_status = st.multiselect("Statusy:", options=status_options, default=status_options)
        
        st.divider()
        if st.button("🔄 Odśwież system", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        st.caption("v3.1 | System Operacyjny SQM")

    # --- NAGŁÓWEK I KPI ---
    st.markdown("<h1 style='color: #1E293B;'>Pulpit Operacyjny Floty</h1>", unsafe_allow_html=True)
    st.caption(f"Synchronizacja: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

    # Obliczenia do metryk
    today = pd.Timestamp.now().normalize()
    active_now = df[(df['Data_Start'] <= today) & (df['Data_Koniec'] >= today)].shape[0]
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Łączna flota", df['Pojazd'].nunique())
    m2.metric("Projekty w toku", df['Projekt'].nunique())
    m3.metric("W trasie (dziś)", active_now)
    m4.metric("Zaplanowane (7d)", df[df['Data_Start'] > today].shape[0])

    st.markdown("<br>", unsafe_allow_html=True)

    # --- FILTROWANIE ---
    filtered_df = df[
        (df['Projekt'].astype(str).str.contains(search, case=False) | 
         df['Pojazd'].astype(str).str.contains(search, case=False)) &
        (df['Status'].isin(selected_status))
    ]

    # --- GŁÓWNA SEKCJA (TABS) ---
    tab_gantt, tab_table, tab_alerts = st.tabs(["📅 Widok Harmonogramu", "📋 Tabela Szczegółowa", "🚨 Konflikty"])

    with tab_gantt:
        st.markdown("<div style='background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
        if not filtered_df.empty:
            fig = px.timeline(
                filtered_df,
                x_start="Data_Start",
                x_end="Data_Koniec",
                y="Pojazd",
                color="Projekt",
                text="Projekt",
                hover_data=["Kierowca", "Status", "Uwagi"],
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            
            # Linia aktualnego czasu
            fig.add_vline(x=datetime.now(), line_width=2, line_dash="solid", line_color="#EF4444")
            
            fig.update_yaxes(autorange="reversed", title="", gridcolor="#F1F5F9")
            fig.update_xaxes(title="Kalendarz", gridcolor="#F1F5F9")
            
            fig.update_layout(
                height=500,
                margin=dict(l=0, r=0, t=20, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            fig.update_traces(marker_line_color='white', marker_line_width=1, opacity=0.85)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Brak danych do wyświetlenia dla wybranych filtrów.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_table:
        st.dataframe(
            filtered_df.sort_values("Data_Start"),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Data_Start": st.column_config.DateColumn("Początek", format="DD.MM.YYYY"),
                "Data_Koniec": st.column_config.DateColumn("Koniec", format="DD.MM.YYYY"),
                "Pojazd": "🚚 Pojazd",
                "Projekt": "📁 Projekt",
                "Status": st.column_config.SelectboxColumn("Status", options=["Zaplanowane", "W trasie", "Auto", "Zakończone"])
            }
        )

    with tab_alerts:
        # Detekcja konfliktów (ten sam pojazd, nakładające się daty)
        df_conf = filtered_df.sort_values(['Pojazd', 'Data_Start'])
        conflict_rows = []
        for i in range(len(df_conf)-1):
            if df_conf.iloc[i]['Pojazd'] == df_conf.iloc[i+1]['Pojazd']:
                if df_conf.iloc[i]['Data_Koniec'] > df_conf.iloc[i+1]['Data_Start']:
                    conflict_rows.append(df_conf.iloc[i])
                    conflict_rows.append(df_conf.iloc[i+1])
        
        if conflict_rows:
            st.error("🚨 Wykryto kolizje w rezerwacji pojazdów!")
            st.table(pd.DataFrame(conflict_rows).drop_duplicates())
        else:
            st.success("Brak konfliktów. Flota zaplanowana poprawnie.")

except Exception as e:
    st.error(f"Błąd krytyczny: {e}")
    st.info("Upewnij się, że kolumny w arkuszu Google nazywają się: Pojazd, Projekt, Data_Start, Data_Koniec, Kierowca, Status, Uwagi")
