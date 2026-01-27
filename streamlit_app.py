import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony
st.set_page_config(
    page_title="SQM Logistics | Fleet Manager",
    page_icon="🚚",
    layout="wide"
)

# 2. Stylizacja Clean Light Mode
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #212529; }
    
    /* Karty statystyk w stylu SaaS */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    [data-testid="stMetricValue"] { color: #007bff !important; font-weight: 600; }
    
    /* Przyciski */
    .stButton>button {
        background-color: #007bff;
        color: white;
        border-radius: 6px;
        padding: 0.5rem 2rem;
        border: none;
        font-weight: 500;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# 3. Dane
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        if data is None or data.empty:
            return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])
        data.columns = [c.strip().lower() for c in data.columns]
        data['start'] = pd.to_datetime(data['start'], errors='coerce')
        data['koniec'] = pd.to_datetime(data['koniec'], errors='coerce')
        for col in ['pojazd', 'event', 'kierowca', 'notatka']:
            if col in data.columns:
                data[col] = data[col].astype(str).replace(['nan', 'None'], '')
        return data
    except:
        return pd.DataFrame(columns=["pojazd", "event", "start", "koniec", "kierowca", "notatka"])

df = load_data()

# --- DASHBOARD HEADER ---
st.title("System Zarządzania Flotą SQM")
st.markdown("---")

# Statystyki
m1, m2, m3, m4 = st.columns(4)
today = datetime.now()
m1.metric("Aktywne pojazdy", df['pojazd'].nunique() if not df.empty else 0)
m2.metric("Zaplanowane eventy", len(df))
m3.metric("Transporty dziś", df[(df['start'] <= today) & (df['koniec'] >= today)].shape[0] if not df.empty else 0)
m4.metric("Status bazy", "Synchronizacja OK")

# --- GANTT CHART SECTION ---
if not df.empty and df['start'].notnull().any():
    st.subheader("Harmonogram Operacyjny")
    
    plot_df = df.dropna(subset=['start', 'koniec', 'pojazd']).sort_values('pojazd')
    
    # Obliczanie zakresu dat dla weekendów
    min_date = plot_df['start'].min() - timedelta(days=2)
    max_date = plot_df['koniec'].max() + timedelta(days=5)
    
    fig = px.timeline(
        plot_df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="pojazd",
        text="event",
        hover_name="event",
        custom_data=["kierowca", "notatka"],
        color_discrete_sequence=px.colors.qualitative.Set3 # Pastelowe kolory na jasnym tle
    )

    # Ustawienia osi X zgodnie z życzeniem (Miesiąc, Dzień, Dzień tygodnia)
    fig.update_xaxes(
        side="top",
        dtick="D1", # Jednostka co 1 dzień
        tickformat="%d\n%a", # Dzień i skrót tygodnia (np. 27 Tue)
        hoverformat="%Y-%m-%d",
        gridcolor="#f0f0f0",
        tickangle=0,
        title="",
    )
    
    # Dodanie nazw miesięcy jako dodatkowa warstwa (Plotly nie pozwala na 3 poziomy natywnie w px,
    # dlatego używamy formatowania ticków i grupujemy daty)
    fig.update_layout(
        xaxis=dict(
            tickformat="%d\n%a", 
            labelalias={datetime(2026, 1, 1).strftime("%d\n%a"): "Jan"}, # Uproszczenie dla czytelności
        )
    )

    # Zaznaczanie weekendów (pionowe pasy)
    current_d = min_date
    while current_d <= max_date:
        if current_d.weekday() >= 5: # 5=Sobota, 6=Niedziela
            fig.add_vrect(
                x0=current_d.strftime("%Y-%m-%d 00:00"),
                x1=(current_d + timedelta(days=1)).strftime("%Y-%m-%d 00:00"),
                fillcolor="#f2f2f2",
                opacity=0.5,
                layer="below",
                line_width=0,
            )
        current_d += timedelta(days=1)

    fig.update_yaxes(autorange="reversed", title="", gridcolor="#f0f0f0")
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=500,
        showlegend=False,
        margin=dict(l=10, r=10, t=100, b=10),
        font=dict(color="#495057", size=11)
    )
    
    fig.update_traces(
        textposition='inside',
        marker=dict(line=dict(width=1, color='white')),
        hovertemplate="<b>%{hovertext}</b><br>Kierowca: %{customdata[0]}<br>Notatki: %{customdata[1]}<extra></extra>"
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- MANAGEMENT PANEL ---
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Baza danych i Planowanie")

tab1, tab2 = st.tabs(["📝 Edycja wpisów", "📋 Lista konfliktów"])

with tab1:
    editor_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "pojazd": st.column_config.TextColumn("Pojazd", width="medium"),
            "event": st.column_config.TextColumn("Nazwa eventu", width="large"),
            "start": st.column_config.DateColumn("Start"),
            "koniec": st.column_config.DateColumn("Koniec"),
            "kierowca": st.column_config.TextColumn("Kierowca"),
            "notatka": st.column_config.TextColumn("Notatka")
        },
        key="sqm_light_v1"
    )

    if st.button("Zapisz zmiany w arkuszu"):
        save_df = editor_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d').fillna('')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d').fillna('')
        conn.update(data=save_df)
        st.toast("Dane zostały pomyślnie zapisane.", icon="☁️")
        st.rerun()

with tab2:
    if not editor_df.empty:
        c_df = editor_df.sort_values(['pojazd', 'start'])
        conflicts = []
        for v in c_df['pojazd'].unique():
            if not v: continue
            v_data = c_df[c_df['pojazd'] == v]
            for i in range(len(v_data)-1):
                if v_data.iloc[i]['koniec'] > v_data.iloc[i+1]['start']:
                    conflicts.append(f"Kolizja: **{v}** zajęty przez '{v_data.iloc[i]['event']}' oraz '{v_data.iloc[i+1]['event']}'")
        
        if conflicts:
            for c in conflicts: st.warning(c)
        else:
            st.success("Wszystkie pojazdy mają poprawnie zaplanowany czas.")
