import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="FLOTA SQM 2026", layout="wide", page_icon="🚚")

# Custom CSS dla efektu "Excela" i lepszego kontrastu
st.markdown("""
    <style>
    .stApp { background-color: #f1f3f6; }
    .css-1544g2n { background-color: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 FLOTA SQM 2026 | System Zarządzania")

# 2. POŁĄCZENIE Z BAZĄ
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(worksheet="FLOTA_SQM", ttl="0")
    df = df.dropna(how='all').copy()
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    return df.dropna(subset=['Data_Start', 'Data_Koniec'])

df = load_data()

# --- FUNKCJA WYKRYWANIA KOLIZJI ---
def check_collisions(data):
    conflicts = []
    # Sprawdzamy każdy pojazd z osobna
    for pojazd in data['Pojazd'].unique():
        vehicle_df = data[data['Pojazd'] == pojazd].sort_values('Data_Start')
        if len(vehicle_df) > 1:
            for i in range(len(vehicle_df) - 1):
                curr_end = vehicle_df.iloc[i]['Data_Koniec']
                next_start = vehicle_df.iloc[i+1]['Data_Start']
                if curr_end >= next_start:
                    conflicts.append(f"⚠️ Kolizja: {pojazd} ({vehicle_df.iloc[i]['Projekt']} / {vehicle_df.iloc[i+1]['Projekt']})")
    return conflicts

# 3. STATYSTYKI KPI
today = datetime.now()
collisions = check_collisions(df)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Pojazdy w trasie", len(df[(df['Data_Start'] <= today) & (df['Data_Koniec'] >= today)]))
with c2:
    st.metric("Nadchodzące (7 dni)", len(df[(df['Data_Start'] > today) & (df['Data_Start'] <= today + timedelta(days=7))]))
with c3:
    status_color = "normal" if not collisions else "inverse"
    st.metric("Wykryte kolizje", len(collisions), delta=len(collisions), delta_color=status_color)
with c4:
    st.metric("Pojazdy w serwisie", len(df[df['Status'] == "Serwis"]))

if collisions:
    for c in collisions:
        st.error(c)

# 4. SIDEBAR - DODAWANIE
with st.sidebar:
    st.header("➕ Dodaj Transport")
    with st.form("new_transport", clear_on_submit=True):
        pojazd = st.selectbox("Pojazd", [
            "31 - TIR P21V388/P22X300 STABLEWSKI", "TIR 2 - W2654FT/P22H972 KOGUS",
            "TIR 3 - PNT3530A/P24U343 DANIELAK", "44 - SOLO PY 73262",
            "25 - Jumper - PY22952", "24 - Jumper - PY22954", "BOXER - PO 5VT68",
            "OPEL DW4W443", "SPEDYCJA"
        ])
        projekt = st.text_input("Nazwa Projektu / Targi")
        kierowca = st.text_input("Kierowca")
        d_start = st.date_input("Wyjazd", value=today)
        d_end = st.date_input("Powrót", value=today + timedelta(days=3))
        status = st.selectbox("Status", ["Planowanie", "Potwierdzone", "W trasie", "Serwis"])
        
        if st.form_submit_button("DODAJ DO GRAFIKU"):
            new_row = pd.DataFrame([{
                "Pojazd": pojazd, "Projekt": projekt, "Data_Start": d_start.strftime('%Y-%m-%d'),
                "Data_Koniec": d_end.strftime('%Y-%m-%d'), "Kierowca": kierowca, "Status": status
            }])
            current = conn.read(worksheet="FLOTA_SQM", ttl="0")
            conn.update(worksheet="FLOTA_SQM", data=pd.concat([current, new_row], ignore_index=True))
            st.rerun()

# 5. PODRASOWANY WYKRES (WIDOK EXCELOWY)
st.subheader("🗓️ Harmonogram Dzienny Floty")

# Filtr zakresu dla lepszej przejrzystości
view_range = st.date_input("Widok kalendarza:", [today - timedelta(days=5), today + timedelta(days=20)])

if len(view_range) == 2:
    df_viz = df.copy()
    # Pasek musi wizualnie domykać dzień powrotu
    df_viz['Viz_End'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)
    
    fig = px.timeline(
        df_viz, x_start="Data_Start", x_end="Viz_End", y="Pojazd", color="Status",
        text="Projekt", hover_data=["Kierowca"],
        color_discrete_map={
            "Planowanie": "#FAD02E", "Potwierdzone": "#45B6FE", 
            "W trasie": "#37BC61", "Serwis": "#E1341E"
        }
    )

    # Ustawienie "Siatki Excelowej"
    fig.update_xaxes(
        dtick="D1", # Linia co 1 dzień
        tickformat="%d\n%b", 
        gridcolor="#E0E0E0", 
        side="top",
        range=[view_range[0], view_range[1]]
    )
    
    fig.update_yaxes(autorange="reversed", gridcolor="#F0F0F0")
    
    # Linia DZIŚ
    fig.add_vline(x=today.timestamp() * 1000, line_width=2, line_color="red", line_dash="solid")

    fig.update_layout(
        height=600, margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor="white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )

    st.plotly_chart(fig, use_container_width=True)

# 6. EDYCJA I ZAPIS
with st.expander("📝 Edytuj bazę i sloty transportowe"):
    df_edit = df.copy()
    df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
    df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
    
    edited = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 ZAPISZ ZMIANY W GOOGLE SHEETS"):
        conn.update(worksheet="FLOTA_SQM", data=edited)
        st.success("Baza zaktualizowana!")
        st.rerun()
