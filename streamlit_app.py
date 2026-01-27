import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY
st.set_page_config(
    page_title="SQM Dashboard",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. ZAAWANSOWANY CSS DLA EFEKTU DASHBOARDU
st.markdown("""
    <style>
    .stApp { background-color: #F4F7F9; }
    [data-testid="stSidebar"] { background-color: #1E293B !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        border: 1px solid #E2E8F0;
        font-weight: 600;
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
    # Pobranie surowych danych
    df = conn.read(ttl="2s")
    
    # CZYSZCZENIE: Usunięcie wierszy, gdzie kluczowe pola są puste (NaN to typ float, co powoduje błąd)
    df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
    
    # KONWERSJA: Wymuszenie typów, aby uniknąć błędu '<' między float a str
    df['Pojazd'] = df['Pojazd'].astype(str)
    df['Projekt'] = df['Projekt'].astype(str)
    df['Kierowca'] = df['Kierowca'].fillna("Brak").astype(str)
    df['Status'] = df['Status'].fillna("Nieokreślony").astype(str)
    
    # DATY: Konwersja na format czasowy
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    
    # Usunięcie wierszy z błędnymi datami
    df = df.dropna(subset=['Data_Start', 'Data_Koniec'])
    
    return df

try:
    df = load_data()

    # --- PANEL BOCZNY ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>SQM LOGISTICS</h2>", unsafe_allow_html=True)
        st.divider()
        search = st.text_input("🔍 Szukaj projektu/auta")
        
        # Bezpieczne pobranie unikalnych statusów do filtra
        unique_statuses = sorted(df['Status'].unique())
        status_filter = st.multiselect("Status:", options=unique_statuses, default=unique_statuses)
        
        st.divider()
        if st.button("🔄 Odśwież system", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- NAGŁÓWEK I KPI ---
    st.markdown("<h1 style='color: #1E293B;'>Pulpit Logistics Dashboard</h1>", unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    today = pd.Timestamp.now().normalize()
    active_today = df[(df['Data_Start'] <= today) & (df['Data_Koniec'] >= today)].shape[0]
    
    m1.metric("Łączna flota", df['Pojazd'].nunique())
    m2.metric("Aktywne projekty", df['Projekt'].nunique())
    m3.metric("W trasie (dziś)", active_today)
    m4.metric("Zaplanowane", df[df['Data_Start'] > today].shape[0])

    # --- FILTROWANIE ---
    filtered_df = df[
        (df['Projekt'].str.contains(search, case=False) | df['Pojazd'].str.contains(search, case=False)) &
        (df['Status'].isin(status_filter))
    ]

    # --- SEKCJA GŁÓWNA ---
    tab1, tab2, tab3 = st.tabs(["📊 Harmonogram Gantt", "📑 Tabela Operacyjna", "⚠️ Konflikty"])

    with tab1:
        if not filtered_df.empty:
            # Sortowanie przed wykresem, aby uniknąć błędów renderowania
            plot_df = filtered_df.sort_values('Pojazd')
            
            fig = px.timeline(
                plot_df,
                x_start="Data_Start",
                x_end="Data_Koniec",
                y="Pojazd",
                color="Projekt",
                text="Projekt",
                hover_data=["Kierowca", "Status"],
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            
            # Linia "TERAZ" - poprawka: dodanie timedelta(0) dla pewności typu
            now_line = datetime.now()
            fig.add_vline(x=now_line, line_width=3, line_dash="solid", line_color="#EF4444")
            
            fig.update_yaxes(autorange="reversed", title="")
            fig.update_xaxes(title="Oś czasu")
            fig.update_layout(height=600, margin=dict(l=0, r=0, t=20, b=0))
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Brak danych do wyświetlenia.")

    with tab2:
        # Tabela z wymuszonym sortowaniem po dacie
        st.dataframe(
            filtered_df.sort_values("Data_Start"),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Data_Start": st.column_config.DateColumn("Start", format="DD.MM.YYYY"),
                "Data_Koniec": st.column_config.DateColumn("Koniec", format="DD.MM.YYYY"),
            }
        )

    with tab3:
        # Detekcja konfliktów
        df_conf = filtered_df.sort_values(['Pojazd', 'Data_Start'])
        conflicts = []
        for i in range(len(df_conf)-1):
            curr_row = df_conf.iloc[i]
            next_row = df_conf.iloc[i+1]
            if curr_row['Pojazd'] == next_row['Pojazd']:
                if curr_row['Data_Koniec'] > next_row['Data_Start']:
                    conflicts.append(curr_row)
                    conflicts.append(next_row)
        
        if conflicts:
            st.error("🚨 Wykryto nakładające się rezerwacje!")
            st.table(pd.DataFrame(conflicts).drop_duplicates())
        else:
            st.success("Brak konfliktów czasowych.")

except Exception as e:
    st.error(f"Wystąpił błąd: {e}")
    st.info("Upewnij się, że w arkuszu Google nie ma 'śmieciowych' danych w pustych wierszach.")
