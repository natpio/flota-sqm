import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Konfiguracja strony
st.set_page_config(page_title="SQM Logistics Planner", layout="wide")

# CSS dla poprawy wyglądu i czytelności
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stMetric { background-color: #fdfdfd; border: 1px solid #ececec; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

# Połączenie
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        data.columns = [c.strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        return data.dropna(subset=['pojazd', 'start', 'koniec'])
    except:
        return pd.DataFrame()

df = load_data()

# --- PANEL STATYSTYK ---
st.title("🚛 SQM Logistics: Fleet Grid Planner")
if not df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Pojazdy w trasie", df['pojazd'].nunique())
    m2.metric("Aktywne zlecenia", len(df))
    m3.metric("Ostatnia synchronizacja", datetime.now().strftime("%H:%M:%S"))

st.divider()

# --- HARMONOGRAM W KRATKĘ ---
if not df.empty:
    # Przygotowanie zakresu dat do rysowania siatki weekendów
    min_date = df['start'].min() - timedelta(days=2)
    max_date = df['koniec'].max() + timedelta(days=7)
    
    # Tworzenie wykresu
    fig = px.timeline(
        df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="pojazd", # Kolorowanie per auto dla czytelności
        text="event",
        hover_name="event",
        custom_data=["kierowca", "notatka"],
        color_discrete_sequence=px.colors.qualitative.Dark24
    )

    # KONFIGURACJA SIATKI I OSI
    fig.update_xaxes(
        side="top",
        dtick="D1", # Linia pomocnicza co 1 dzień
        gridcolor="#e1e1e1", # Kolor pionowych linii siatki
        griddash="solid",
        tickformat="%d\n%a", # Numer dnia i skrót dnia tygodnia
        tickfont=dict(size=10, color="#444"),
        title="",
        # Dodanie miesięcy nad dniami
        ticklabelmode="period",
        minor=dict(dtick="D1", gridcolor="#f0f0f0")
    )

    fig.update_yaxes(
        autorange="reversed", 
        gridcolor="#e1e1e1", # Poziome linie siatki
        title=""
    )

    # ZAZNACZANIE WEEKENDÓW (Pionowe pasy w tle)
    curr = min_date
    while curr <= max_date:
        if curr.weekday() >= 5: # Sobota i Niedziela
            fig.add_vrect(
                x0=curr.strftime("%Y-%m-%d"),
                x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                fillcolor="#f2f2f2", # Jasnoszary pas dla weekendu
                opacity=1,
                layer="below",
                line_width=0,
            )
        curr += timedelta(days=1)

    # WYGLĄD PASKÓW I ETYKIET
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        marker=dict(line=dict(width=1, color='white')),
        hovertemplate="<b>%{hovertext}</b><br>Kierowca: %{customdata[0]}<br>Notatka: %{customdata[1]}<extra></extra>"
    )

    fig.update_layout(
        plot_bgcolor="white", # Tło białe dla kontrastu z siatką
        paper_bgcolor="white",
        height=600,
        showlegend=False,
        margin=dict(l=10, r=10, t=80, b=10),
        font=dict(family="Arial Narrow")
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- PANEL OPERACYJNY ---
st.subheader("📋 Zarządzanie Transportami")
tab_edit, tab_conf = st.tabs(["Edytuj Grafik", "Sprawdź Kolizje"])

with tab_edit:
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "start": st.column_config.DateColumn("Start"),
            "koniec": st.column_config.DateColumn("Koniec"),
            "pojazd": st.column_config.TextColumn("🚛 Pojazd"),
            "event": st.column_config.TextColumn("🏷 Event")
        },
        key="sqm_grid_v1"
    )

    if st.button("💾 ZAPISZ I SYNCHRONIZUJ"):
        save_df = edited_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
        conn.update(data=save_df)
        st.success("Baza zaktualizowana!")
        st.rerun()

with tab_conf:
    if not edited_df.empty:
        c_df = edited_df.sort_values(['pojazd', 'start'])
        conf_list = []
        for v in c_df['pojazd'].unique():
            v_data = c_df[c_df['pojazd'] == v]
            for i in range(len(v_data)-1):
                if v_data.iloc[i]['koniec'] > v_data.iloc[i+1]['start']:
                    conf_list.append(f"❌ {v}: '{v_data.iloc[i]['event']}' nakłada się na '{v_data.iloc[i+1]['event']}'")
        
        if conf_list:
            for c in conf_list: st.error(c)
        else:
            st.success("Brak kolizji czasowych.")
