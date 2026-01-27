import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Konfiguracja strony - szeroki układ i ciemny motyw pasujący do SQM
st.set_page_config(page_title="SQM Logistics | Fleet Manager", layout="wide", initial_sidebar_state="expanded")

# Stylizacja CSS dla lepszego wyglądu tabeli i metryk
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stForm"] { border: none; padding: 0; }
    </style>
    """, unsafe_allow_html=True)

# 2. Połączenie z danymi
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"])
        data.columns = [c.strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.dropna(subset=['pojazd', 'start', 'koniec'])
    except Exception as e:
        st.error(f"Błąd bazy: {e}")
        return pd.DataFrame()

df = load_data()

# --- SIDEBAR ---
st.sidebar.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo.png", width=150) # Przykładowe logo
st.sidebar.title("Nawigacja")

if not df.empty:
    all_vehicles = sorted(df['pojazd'].unique())
    selected_vehicles = st.sidebar.multiselect("Filtruj pojazdy", all_vehicles, default=all_vehicles)
    df = df[df['pojazd'].isin(selected_vehicles)]

st.sidebar.divider()
st.sidebar.info("System zarządzania flotą SQM v4.0. Dane synchronizowane z Google Sheets.")

# --- NAGŁÓWEK I METRYKI ---
st.title("🚚 Planowanie Logistyki SQM")

m1, m2, m3, m4 = st.columns(4)
today = datetime.now()
active_tasks = df[(df['start'] <= today) & (df['koniec'] >= today)].shape[0] if not df.empty else 0
total_fleet = df['pojazd'].nunique() if not df.empty else 0

m1.metric("Aktywne Transporty", active_tasks)
m2.metric("Pojazdy w Systemie", total_fleet)
m3.metric("Zaplanowane Eventy", df.shape[0] if not df.empty else 0)
m4.metric("Dzisiejsza Data", today.strftime("%d.%m.%Y"))

st.divider()

# --- HARMONOGRAM (WIZUALIZACJA) ---
if not df.empty:
    st.subheader("Oś Czasu Wydarzeń")
    
    # Podrasowany wykres Plotly
    fig = px.timeline(
        df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="event", # Kolorowanie per event dla rozróżnienia
        hover_name="event",
        text="event",
        custom_data=["kierowca", "notatka"],
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Pastel # Łagodniejsze, profesjonalne kolory
    )
    
    fig.update_yaxes(autorange="reversed", title="")
    fig.update_xaxes(
        title="",
        dtick="D1", 
        tickformat="%d\n%b",
        gridcolor="#f0f0f0",
        side="top"
    )
    
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        marker=dict(line=dict(width=1, color='white'), opacity=0.9),
        hovertemplate="<b>%{hovertext}</b><br>Kierowca: %{customdata[0]}<br>Okres: %{x|%d.%m} - %{x|%d.%m}<br>Notatka: %{customdata[1]}<extra></extra>"
    )
    
    fig.update_layout(
        height=500,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        font=dict(family="Arial", size=12)
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("Brak danych do wyświetlenia. Skorzystaj z panelu poniżej.")

# --- PANEL EDYCJI ---
st.subheader("📝 Zarządzanie Danymi")
with st.expander("Kliknij, aby edytować lub dodać nowe wpisy", expanded=True):
    edited_df = st.data_editor(
        df if not df.empty else pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"]),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "start": st.column_config.DateColumn("📆 Start", format="YYYY-MM-DD", required=True),
            "koniec": st.column_config.DateColumn("🏁 Koniec", format="YYYY-MM-DD", required=True),
            "pojazd": st.column_config.TextColumn("🚛 Pojazd", required=True),
            "event": st.column_config.TextColumn("🏷️ Event", required=True),
            "kierowca": st.column_config.TextColumn("👤 Kierowca"),
            "notatka": st.column_config.TextColumn("💬 Uwagi")
        },
        key="sqm_premium_editor"
    )

    col_btn, col_alert = st.columns([1, 3])
    with col_btn:
        if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
            save_df = edited_df.copy()
            # Mapowanie z powrotem na nazwy z Arkusza Google
            save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
            save_df['Start'] = save_df['Start'].astype(str)
            save_df['Koniec'] = save_df['Koniec'].astype(str)
            conn.update(data=save_df)
            st.toast("Zapisano pomyślnie!", icon="✅")
            st.rerun()

    with col_alert:
        # Szybka kontrola kolizji w tle
        if not edited_df.empty:
            check_df = edited_df.sort_values(['pojazd', 'start'])
            for v in check_df['pojazd'].unique():
                v_data = check_df[check_df['pojazd'] == v]
                for i in range(len(v_data)-1):
                    if v_data.iloc[i]['koniec'] > v_data.iloc[i+1]['start']:
                        st.error(f"KOLIZJA: {v} nakłada się na dwa eventy!")
