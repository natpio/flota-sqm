import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. KONFIGURACJA STRONY
st.set_page_config(
    page_title="SQM Logistics Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CUSTOM CSS - Profesjonalny look & feel
st.markdown("""
    <style>
    /* Główny tło i czcionka */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Stylizacja metryk */
    [data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: 700;
        color: #1E3A8A;
    }
    
    /* Stylizacja bocznego menu */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Kontener dla wykresów */
    .plot-container {
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        padding: 10px;
        background: white;
    }

    /* Customowe kolory statusów */
    .status-zaplanowane { color: #3b82f6; font-weight: bold; }
    .status-w-trasie { color: #f59e0b; font-weight: bold; }
    .status-zakonczone { color: #10b981; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 3. POŁĄCZENIE I DANE
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    df = conn.read(ttl="5s")
    df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
    df['Data_Start'] = pd.to_datetime(df['Data_Start'])
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'])
    return df

try:
    df = get_data()

    # --- SIDEBAR ---
    with st.sidebar:
        st.image("https://sqm.pl/wp-content/uploads/2018/10/logo_sqm_header.png", width=180)
        st.markdown("### Konfiguracja Widoku")
        
        date_range = st.date_input(
            "Zakres raportowania",
            value=(df['Data_Start'].min(), df['Data_Start'].max() + pd.Timedelta(days=7))
        )
        
        search_query = st.text_input("🔍 Szukaj projektu lub kierowcy")
        
        st.divider()
        st.caption("SQM Fleet Management v2.0")
        st.caption("System operacyjny logistyki")

    # --- HEADER ---
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("Centrum Operacyjne Floty")
        st.markdown(f"_Ostatnia aktualizacja danych: {datetime.now().strftime('%H:%M:%S')}_")
    with c2:
        if st.button("🔄 Odśwież system", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- METRYKI KLUCZOWE ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Łączna flota", df['Pojazd'].nunique())
    m2.metric("Aktywne projekty", df['Projekt'].nunique())
    
    # Wyliczanie pojazdów w trasie na dziś
    today = pd.Timestamp.now().normalize()
    active_now = df[(df['Data_Start'] <= today) & (df['Data_Koniec'] >= today)].shape[0]
    m3.metric("Pojazdy w trasie (dziś)", active_now)
    
    m4.metric("Zaplanowane (7d)", df[df['Data_Start'] > today].shape[0])

    # --- TABS: WIZUALIZACJA I DANE ---
    tab_gantt, tab_table, tab_stats = st.tabs(["📊 Harmonogram Wizualny", "📋 Lista Operacyjna", "📈 Analityka"])

    with tab_gantt:
        # Filtrowanie danych na podstawie wyszukiwania
        mask = df['Projekt'].str.contains(search_query, case=False) | df['Kierowca'].str.contains(search_query, case=False)
        plot_df = df[mask]

        if not plot_df.empty:
            fig = px.timeline(
                plot_df,
                x_start="Data_Start",
                x_end="Data_Koniec",
                y="Pojazd",
                color="Projekt",
                text="Projekt",
                hover_data={"Kierowca": True, "Status": True, "Data_Start": "|%d %b", "Data_Koniec": "|%d %b"},
                color_discrete_sequence=px.colors.qualitative.Bold
            )

            # Dodanie linii "Dzisiaj"
            fig.add_vline(x=datetime.now(), line_width=2, line_dash="dash", line_color="red", 
                         annotation_text="TERAZ", annotation_position="top left")

            fig.update_yaxes(autorange="reversed", gridcolor="#eeeeee")
            fig.update_xaxes(gridcolor="#eeeeee")
            
            fig.update_layout(
                height=550,
                margin=dict(l=10, r=10, t=30, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor="white"
            )
            
            fig.update_traces(marker_line_color='rgb(8,48,107)', marker_line_width=1.5, opacity=0.85)

            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning("Brak wyników dla podanych kryteriów.")

    with tab_table:
        st.subheader("Szczegóły logistyczne")
        # Wykorzystanie AgGrid-like st.dataframe
        st.dataframe(
            df,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Zaplanowane", "W trasie", "Zakończone", "Auto"],
                    required=True,
                ),
                "Data_Start": st.column_config.DateColumn("Start", format="DD/MM/YYYY"),
                "Data_Koniec": st.column_config.DateColumn("Koniec", format="DD/MM/YYYY"),
                "Pojazd": st.column_config.TextColumn("🚚 Pojazd"),
                "Projekt": st.column_config.TextColumn("📁 Projekt"),
            },
            hide_index=True,
            use_container_width=True
        )

    with tab_stats:
        st.subheader("Wykorzystanie Floty")
        usage = df['Pojazd'].value_counts().reset_index()
        usage.columns = ['Pojazd', 'Liczba Projektów']
        fig_bar = px.bar(usage, x='Pojazd', y='Liczba Projektów', color='Liczba Projektów', 
                         color_continuous_scale='Blues', template='plotly_white')
        st.plotly_chart(fig_bar, use_container_width=True)

except Exception as e:
    st.error(f"Krytyczny błąd systemu: {e}")
    st.info("Sprawdź połączenie z Google Cloud Console i uprawnienia arkusza.")
