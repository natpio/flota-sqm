import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import holidays

# 1. KONFIGURACJA
st.set_page_config(page_title="SQM Logistics Planner", layout="wide")

# Stylizacja dla lepszej czytelności (kontrastowy Dashboard)
st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; }
    .main-header { font-size: 24px; font-weight: bold; color: #1E293B; margin-bottom: 20px; }
    div[data-testid="stExpander"] { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. POŁĄCZENIE I FUNKCJE DANYCH
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    df = conn.read(ttl="0")
    df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
    df['Data_Start'] = pd.to_datetime(df['Data_Start'])
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'])
    return df

def save_data(df):
    conn.update(data=df)
    st.cache_data.clear()

# 3. LOGIKA APLIKACJI
try:
    df = get_data()
    pl_holidays = holidays.Poland()

    # --- PANEL BOCZNY: DODAWANIE / EDYCJA ---
    with st.sidebar:
        st.header("🚛 Zarządzanie Eventem")
        with st.form("event_form", clear_on_submit=True):
            event_name = st.text_input("Nazwa Eventu")
            vehicle = st.selectbox("Pojazd", options=sorted(df['Pojazd'].unique()) if not df.empty else ["TIR 1", "Bus 1"])
            d_range = st.date_input("Zakres dat", value=(datetime.now(), datetime.now() + timedelta(days=3)))
            driver = st.text_input("Kierowca")
            submit = st.form_submit_button("Dodaj do harmonogramu")

        if submit and len(d_range) == 2:
            new_start, new_end = pd.to_datetime(d_range[0]), pd.to_datetime(d_range[1])
            
            # WYKRYWANIE KONFLIKTÓW
            conflict = df[(df['Pojazd'] == vehicle) & 
                          (df['Data_Start'] < new_end) & 
                          (df['Data_Koniec'] > new_start)]
            
            if not conflict.empty:
                st.error(f"⚠️ KOLIZJA! Pojazd {vehicle} jest już zajęty przez: {conflict['Projekt'].values[0]}")
            else:
                new_row = pd.DataFrame([{
                    "Pojazd": vehicle, "Projekt": event_name, 
                    "Data_Start": new_start, "Data_Koniec": new_end, 
                    "Kierowca": driver, "Status": "Zaplanowane"
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success("Dodano pomyślnie!")
                st.rerun()

    # --- GŁÓWNY WIDOK ---
    st.markdown("<div class='main-header'>Harmonogram Operacyjny SQM</div>", unsafe_allow_html=True)

    # 4. WYKRES GANTTA Z KALENDARZEM (Miesiące, Dni, Weekendy)
    if not df.empty:
        fig = px.timeline(
            df, x_start="Data_Start", x_end="Data_Koniec", y="Pojazd", 
            color="Projekt", text="Projekt", hover_data=["Kierowca"]
        )

        # Ustawienia Osi Czasu (Dni tygodnia, Weekendy)
        start_view = df['Data_Start'].min() - timedelta(days=2)
        end_view = df['Data_Koniec'].max() + timedelta(days=5)
        
        # Wyróżnienie weekendów i świąt (szare tło jak w Twoim Excelu)
        current_date = start_view
        while current_date <= end_view:
            if current_date.weekday() >= 5 or current_date in pl_holidays:
                fig.add_vrect(
                    x0=current_date, x1=current_date + timedelta(days=1),
                    fillcolor="gray", opacity=0.2, line_width=0
                )
            current_date += timedelta(days=1)

        fig.update_yaxes(autorange="reversed", title="")
        fig.update_xaxes(
            dtick="D1", 
            tickformat="%d\n%a", # Dzień i skrót dnia tygodnia (np. 20 Mon)
            tickfont=dict(size=10),
            range=[start_view, end_view],
            side="top" # Etykiety dat u góry
        )

        fig.update_layout(
            height=500, margin=dict(l=10, r=10, t=50, b=10),
            showlegend=False, plot_bgcolor="white"
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- EDYCJA I USUWANIE (Tabela interaktywna) ---
    st.markdown("### 🛠️ Edycja i Usuwanie")
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Data_Start": st.column_config.DateColumn("Start"),
            "Data_Koniec": st.column_config.DateColumn("Koniec")
        }
    )

    if st.button("Zapisz zmiany w tabeli"):
        save_data(edited_df)
        st.success("Baza danych zaktualizowana.")
        st.rerun()

except Exception as e:
    st.error(f"Błąd: {e}")
