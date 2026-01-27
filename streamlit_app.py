import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY
st.set_page_config(
    page_title="SQM Logistics Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CUSTOM CSS - Profesjonalny look
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    [data-testid="stMetricValue"] { font-size: 28px; font-weight: 700; color: #1E3A8A; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px 5px 0px 0px; gap: 1px; }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. POŁĄCZENIE I DANE
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # Pobieramy dane z arkusza FLOTA_SQM
    df = conn.read(ttl="5s")
    # Usuwamy puste wiersze na podstawie kluczowych kolumn
    df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
    # Konwersja na datetime
    df['Data_Start'] = pd.to_datetime(df['Data_Start'])
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'])
    return df

try:
    df = get_data()

    # --- PANEL BOCZNY ---
    with st.sidebar:
        st.image("https://sqm.pl/wp-content/uploads/2018/10/logo_sqm_header.png", width=180)
        st.markdown("### 🛠️ Parametry widoku")
        
        # POPRAWKA BŁĘDU: Użycie timedelta zamiast + int
        min_date = df['Data_Start'].min().date()
        max_date = (df['Data_Koniec'].max() + timedelta(days=14)).date()
        
        date_range = st.date_input(
            "Zakres filtrowania",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date + timedelta(days=365)
        )
        
        search_query = st.text_input("🔍 Szukaj (Projekt / Kierowca / Pojazd)")
        
        st.divider()
        st.info("System monitoruje kolizje w czasie rzeczywistym.")

    # --- HEADER ---
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("Centrum Operacyjne Floty")
        st.markdown(f"**Aktualizacja:** {datetime.now().strftime('%H:%M:%S')}")
    with c2:
        if st.button("🔄 Przeładuj dane", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- FILTROWANIE ---
    # Logika wyszukiwarki
    mask = (
        df['Projekt'].astype(str).str.contains(search_query, case=False) | 
        df['Kierowca'].astype(str).str.contains(search_query, case=False) |
        df['Pojazd'].astype(str).str.contains(search_query, case=False)
    )
    
    # Logika zakresu dat (sprawdzenie czy wybrano obie daty)
    if len(date_range) == 2:
        mask = mask & (df['Data_Start'].dt.date >= date_range[0]) & (df['Data_Koniec'].dt.date <= date_range[1])
    
    filtered_df = df[mask]

    # --- METRYKI ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Łączna flota", df['Pojazd'].nunique())
    m2.metric("Projekty w toku", df['Projekt'].nunique())
    
    today = pd.Timestamp.now().normalize()
    active_now = df[(df['Data_Start'] <= today) & (df['Data_Koniec'] >= today)].shape[0]
    m3.metric("W trasie (dziś)", active_now)
    
    # Sprawdzanie konfliktów (ten sam pojazd, nakładające się daty)
    conflicts = filtered_df[filtered_df.duplicated(subset=['Pojazd'], keep=False)]
    m4.metric("Alerty kolizji", "0" if conflicts.empty else len(conflicts), delta_color="inverse")

    # --- WIDOK GŁÓWNY ---
    tab_gantt, tab_list, tab_conflicts = st.tabs(["📅 Harmonogram Gantt", "📑 Tabela Operacyjna", "⚠️ Konflikty"])

    with tab_gantt:
        if not filtered_df.empty:
            fig = px.timeline(
                filtered_df,
                x_start="Data_Start",
                x_end="Data_Koniec",
                y="Pojazd",
                color="Projekt",
                text="Projekt",
                hover_data=["Kierowca", "Status"],
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            
            # Linia aktualnego czasu
            fig.add_vline(x=datetime.now(), line_width=2, line_dash="dash", line_color="#FF4B4B")
            
            fig.update_yaxes(autorange="reversed", gridcolor="#f0f0f0")
            fig.update_xaxes(gridcolor="#f0f0f0", title="Oś czasu")
            
            fig.update_layout(
                height=600,
                margin=dict(l=10, r=10, t=10, b=10),
                plot_bgcolor="white",
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            fig.update_traces(marker_line_color='white', marker_line_width=2, opacity=0.9)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Brak danych dla wybranych filtrów.")

    with tab_list:
        st.dataframe(
            filtered_df.sort_values(by="Data_Start"),
            column_config={
                "Data_Start": st.column_config.DateColumn("Start", format="DD.MM.YYYY"),
                "Data_Koniec": st.column_config.DateColumn("Koniec", format="DD.MM.YYYY"),
                "Status": st.column_config.SelectboxColumn("Status", options=["Zaplanowane", "W trasie", "Auto", "Zakończone"]),
                "Uwagi": st.column_config.TextColumn("Komentarz", width="large")
            },
            use_container_width=True,
            hide_index=True
        )

    with tab_conflicts:
        # Bardziej zaawansowana logika konfliktów
        df_sorted = filtered_df.sort_values(['Pojazd', 'Data_Start'])
        conflict_list = []
        for i in range(len(df_sorted)-1):
            if df_sorted.iloc[i]['Pojazd'] == df_sorted.iloc[i+1]['Pojazd']:
                if df_sorted.iloc[i]['Data_Koniec'] > df_sorted.iloc[i+1]['Data_Start']:
                    conflict_list.append(df_sorted.iloc[i])
                    conflict_list.append(df_sorted.iloc[i+1])
        
        if conflict_list:
            st.error("Wykryto nakładające się terminy dla tych samych jednostek!")
            st.table(pd.DataFrame(conflict_list).drop_duplicates())
        else:
            st.success("Brak konfliktów czasowych w wybranym zakresie.")

except Exception as e:
    st.error(f"Wystąpił błąd podczas przetwarzania danych: {e}")
    st.info("Upewnij się, że kolumny w arkuszu nazywają się dokładnie: Pojazd, Projekt, Data_Start, Data_Koniec, Kierowca, Status, Uwagi")
