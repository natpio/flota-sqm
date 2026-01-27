import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Zabezpieczenie przed brakiem biblioteki holidays
try:
    import holidays
    pl_holidays = holidays.Poland(years=[2025, 2026, 2027])
except ImportError:
    pl_holidays = []
    st.warning("Biblioteka 'holidays' nie jest zainstalowana. Weekendy będą widoczne, ale święta państwowe nie zostaną wyróżnione.")

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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #F1F5F9; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] * { color: #F8FAFC !important; }
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #E2E8F0;
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
    raw_df = conn.read(ttl="0")
    df = raw_df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec']).copy()
    df['Pojazd'] = df['Pojazd'].astype(str)
    df['Projekt'] = df['Projekt'].astype(str)
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    df['Kierowca'] = df['Kierowca'].fillna("").astype(str)
    df['Status'] = df['Status'].fillna("Zaplanowane").astype(str)
    return df.dropna(subset=['Data_Start', 'Data_Koniec'])

def update_gsheet(dataframe):
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

    # --- PANEL BOCZNY: FORMULARZ ---
    with st.sidebar:
        st.markdown("## 🚛 NOWY EVENT")
        with st.form("add_event_form", clear_on_submit=True):
            f_event = st.text_input("Nazwa Eventu")
            f_vehicle = st.selectbox("Pojazd", options=sorted(df['Pojazd'].unique()) if not df.empty else ["Auto 1"])
            f_dates = st.date_input("Okres", value=(datetime.now(), datetime.now() + timedelta(days=2)))
            f_driver = st.text_input("Kierowca")
            submitted = st.form_submit_button("DODAJ", use_container_width=True)

        if submitted and len(f_dates) == 2:
            start_dt, end_dt = pd.to_datetime(f_dates[0]), pd.to_datetime(f_dates[1])
            conflict = df[(df['Pojazd'] == f_vehicle) & (df['Data_Start'] < end_dt) & (df['Data_Koniec'] > start_dt)]
            
            if not conflict.empty:
                st.error(f"❌ KOLIZJA! {f_vehicle} zajęty przez: {conflict.iloc[0]['Projekt']}")
            else:
                new_row = pd.DataFrame([{
                    "Pojazd": f_vehicle, "Projekt": f_event, "Data_Start": start_dt,
                    "Data_Koniec": end_dt, "Kierowca": f_driver, "Status": "Zaplanowane"
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                if update_gsheet(df):
                    st.success("Dodano!")
                    st.rerun()

    # --- WIDOK GŁÓWNY ---
    st.title("Pulpit Operacyjny SQM")
    
    tab_visual, tab_editor = st.tabs(["📅 HARMONOGRAM WIZUALNY", "🛠️ EDYCJA I USUWANIE"])

    with tab_visual:
        if not df.empty:
            plot_df = df.sort_values(['Pojazd', 'Data_Start'])
            fig = px.timeline(plot_df, x_start="Data_Start", x_end="Data_Koniec", y="Pojazd", color="Projekt", text="Projekt", template="plotly_white")

            # SZARE WEEKENDY I ŚWIĘTA
            start_v = plot_df['Data_Start'].min() - timedelta(days=5)
            end_v = plot_df['Data_Koniec'].max() + timedelta(days=14)
            curr = start_v
            while curr <= end_v:
                if curr.weekday() >= 5 or (hasattr(pl_holidays, 'get') and curr.date() in pl_holidays):
                    fig.add_vrect(x0=curr.strftime("%Y-%m-%d"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                                 fillcolor="rgba(128, 128, 128, 0.2)", line_width=0, layer="below")
                curr += timedelta(days=1)

            fig.update_yaxes(autorange="reversed")
            fig.update_xaxes(dtick="D1", tickformat="%d\n%a", side="top", range=[start_v, end_v])
            fig.update_layout(height=600, margin=dict(l=10, r=10, t=60, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with tab_editor:
        st.markdown("### Zarządzanie rekordami")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("💾 ZAPISZ ZMIANY", type="primary"):
            if update_gsheet(edited_df):
                st.success("Zapisano!")
                st.rerun()

except Exception as e:
    st.error(f"Błąd aplikacji: {e}")
