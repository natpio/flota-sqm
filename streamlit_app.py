import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Konfiguracja strony - SQM Premium Level
st.set_page_config(
    page_title="SQM Logistics | Fleet Control Center",
    page_icon="🚛",
    layout="wide"
)

# 2. Zaawansowany CSS dla wyglądu "SaaS"
st.markdown("""
    <style>
    /* Tło i główny font */
    .main { background-color: #f0f2f5; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    
    /* Stylizacja kontenerów metryk */
    div[data-testid="stMetric"] {
        background-color: white;
        border-radius: 12px;
        padding: 20px 25px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #e1e4e8;
    }
    
    /* Tytuły sekcji */
    h1, h2, h3 { color: #1a1f36; font-weight: 700; }
    
    /* Wygląd edytora danych */
    .stDataEditor {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    
    /* Przyciski akcji */
    .stButton>button {
        background: linear-gradient(135deg, #0061ff 0%, #60efff 100%);
        color: white;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,97,255,0.3); }
    </style>
    """, unsafe_allow_html=True)

# 3. Połączenie z danymi
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
    except:
        return pd.DataFrame()

df = load_data()

# --- NAGŁÓWEK ---
st.markdown("# 🛰️ Fleet Control Center")
st.markdown("### SQM Multimedia Solutions | Logistyka i Transport")

# --- DASHBOARD METRYK ---
if not df.empty:
    col1, col2, col3, col4 = st.columns(4)
    today = datetime.now()
    active = df[(df['start'] <= today) & (df['koniec'] >= today)].shape[0]
    
    col1.metric("Aktywne jednostki", df['pojazd'].nunique())
    col2.metric("Transporty w trasie", active)
    col3.metric("Zaplanowane (30 dni)", len(df[df['start'] > today - timedelta(days=30)]))
    col4.metric("Status operacyjny", "Prawidłowy", delta="SYNC OK")

st.markdown("<br>", unsafe_allow_html=True)

# --- VISUALIZATION: HIGH-CONTRAST GRID ---
if not df.empty:
    # Przygotowanie osi czasu
    min_date = df['start'].min() - timedelta(days=2)
    max_date = df['koniec'].max() + timedelta(days=10)
    
    # Sortowanie pojazdów dla porządku
    plot_df = df.sort_values('pojazd')
    
    fig = px.timeline(
        plot_df, 
        x_start="start", 
        x_end="koniec", 
        y="pojazd", 
        color="pojazd",
        text="event",
        hover_name="event",
        custom_data=["kierowca", "notatka"],
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Bold # Mocne, profesjonalne kolory
    )

    # KONFIGURACJA KRATKI (Grid 2.0)
    fig.update_xaxes(
        side="top",
        dtick="D1",
        gridcolor="#cfd4da", # Wyraźna szara linia siatki
        gridwidth=1,
        showgrid=True,
        tickformat="%d\n%a", # Numer i nazwa dnia
        tickfont=dict(size=12, color="#1a1f36", family="Arial Black"),
        title="",
        range=[min_date, max_date]
    )

    fig.update_yaxes(
        autorange="reversed", 
        gridcolor="#e9ecef", # Poziome linie separujące pojazdy
        title="",
        tickfont=dict(size=12, color="#4f566b", family="Arial")
    )

    # WYRÓŻNIENIE WEEKENDÓW (Subtelne pasy tła)
    curr = min_date
    while curr <= max_date:
        if curr.weekday() >= 5: # Sobota, Niedziela
            fig.add_vrect(
                x0=curr.strftime("%Y-%m-%d"),
                x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d"),
                fillcolor="#f8f9fa",
                opacity=1.0,
                layer="below",
                line_width=0,
            )
            # Dodatkowa linia graniczna dla weekendu
            fig.add_vline(x=curr.strftime("%Y-%m-%d"), line_width=1, line_color="#dee2e6")
        curr += timedelta(days=1)

    # STYLIZACJA PASKÓW (Eventów)
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        marker=dict(
            line=dict(width=2, color='white'), # Biała ramka wokół eventu dla kontrastu
            opacity=0.9
        ),
        hovertemplate="<b>%{hovertext}</b><br>Kierowca: %{customdata[0]}<br>Notatka: %{customdata[1]}<extra></extra>"
    )

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        height=600,
        margin=dict(l=10, r=10, t=100, b=20),
        showlegend=False,
        font=dict(family="Segoe UI", size=13)
    )

    # Wyświetlenie wykresu w kontenerze z cieniem
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- DATA MANAGEMENT PANEL ---
st.markdown("## 📊 Zarządzanie Operacyjne")
t1, t2 = st.tabs(["📝 Harmonogram Floty", "⚡ Wykrywanie Kolizji"])

with t1:
    st.markdown("Dodawaj i edytuj transporty bezpośrednio w tabeli:")
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "pojazd": st.column_config.TextColumn("🚛 Pojazd", required=True),
            "event": st.column_config.TextColumn("🏷️ Event", required=True),
            "start": st.column_config.DateColumn("📅 Data Startu"),
            "koniec": st.column_config.DateColumn("🏁 Data Końca"),
            "kierowca": st.column_config.TextColumn("👤 Kierowca"),
            "notatka": st.column_config.TextColumn("💬 Uwagi")
        },
        key="sqm_premium_grid"
    )

    if st.button("ZAPISZ I AKTUALIZUJ ARKUSZ"):
        save_df = edited_df.copy()
        save_df.columns = ["Pojazd", "EVENT", "Start", "Koniec", "Kierowca", "Notatka"]
        save_df['Start'] = pd.to_datetime(save_df['Start']).dt.strftime('%Y-%m-%d')
        save_df['Koniec'] = pd.to_datetime(save_df['Koniec']).dt.strftime('%Y-%m-%d')
        conn.update(data=save_df)
        st.toast("Dane zsynchronizowane pomyślnie!", icon="🚀")
        st.rerun()

with t2:
    if not edited_df.empty:
        # Logika sprawdzania konfliktów
        c_df = edited_df.sort_values(['pojazd', 'start'])
        conflicts = []
        for v in c_df['pojazd'].unique():
            if not v: continue
            v_data = c_df[c_df['pojazd'] == v]
            for i in range(len(v_data)-1):
                if v_data.iloc[i]['koniec'] > v_data.iloc[i+1]['start']:
                    conflicts.append(f"🔴 **{v}**: Nakładające się zlecenia: '{v_data.iloc[i]['event']}' oraz '{v_data.iloc[i+1]['event']}'")
        
        if conflicts:
            for c in conflicts: st.error(c)
        else:
            st.success("Brak wykrytych kolizji dla floty SQM.")
