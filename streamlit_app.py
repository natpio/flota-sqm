import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="FLOTA SQM 2026", layout="wide", page_icon="🚚")

# Słownik polskich miesięcy
PL_MONTHS = {
    1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 
    5: "MAJ", 6: "CZERWIEC", 7: "LIPIEC", 8: "SIERPIEŃ", 
    9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"
}

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    /* Stylizacja dat na osi X */
    [data-testid="stPlotlyChart"] .xtick text { 
        font-family: 'Arial Black', sans-serif !important;
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 FLOTA SQM 2026")

# 2. POŁĄCZENIE Z BAZĄ
conn = st.connection("gsheets", type=GSheetsConnection)

def get_auto_status(start, end):
    today = datetime.now().date()
    s = start.date() if hasattr(start, 'date') else start
    e = end.date() if hasattr(end, 'date') else end
    if today < s: return "Oczekuje"
    elif s <= today <= e: return "W trakcie"
    else: return "Wróciło"

def load_data():
    df = conn.read(worksheet="FLOTA_SQM", ttl="0")
    df = df.dropna(how='all').copy()
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    df = df.dropna(subset=['Data_Start', 'Data_Koniec'])
    df['Status'] = df.apply(lambda x: get_auto_status(x['Data_Start'], x['Data_Koniec']), axis=1)
    return df

df = load_data()

# 3. SIDEBAR
with st.sidebar:
    st.header("⚙️ Nowy Event")
    with st.form("add_form", clear_on_submit=True):
        pojazd = st.selectbox("Pojazd", [
            "31 - TIR P21V388/P22X300 STABLEWSKI", "TIR 2 - W2654FT/P22H972 KOGUS",
            "TIR 3 - PNT3530A/P24U343 DANIELAK", "44 - SOLO PY 73262",
            "25 - Jumper - PY22952", "24 - Jumper - PY22954", "BOXER - PO 5VT68",
            "OPEL DW4W443", "SPEDYCJA"
        ])
        event_name = st.text_input("Nazwa Eventu")
        kierowca = st.text_input("Kierowca")
        d_start = st.date_input("Wyjazd", value=datetime.now())
        d_end = st.date_input("Powrót", value=datetime.now() + timedelta(days=2))
        
        if st.form_submit_button("ZAPISZ"):
            new_row = pd.DataFrame([{"Pojazd": pojazd, "Projekt": event_name, "Kierowca": kierowca,
                                     "Data_Start": d_start.strftime('%Y-%m-%d'), 
                                     "Data_Koniec": d_end.strftime('%Y-%m-%d')}])
            current = conn.read(worksheet="FLOTA_SQM", ttl="0")
            conn.update(worksheet="FLOTA_SQM", data=pd.concat([current, new_row], ignore_index=True))
            st.rerun()

# 4. GRAFIK GANTTA - CZYTELNA OŚ CZASU
st.subheader("🗓️ Harmonogram Dzienny")

if not df.empty:
    df_viz = df.copy()
    df_viz['Viz_End'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)

    fig = px.timeline(
        df_viz, x_start="Data_Start", x_end="Viz_End", y="Pojazd", 
        color="Projekt", text="Projekt",
        hover_data={"Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m", "Status": True, "Projekt": False, "Viz_End": False}
    )

    # --- GENEROWANIE POLSKIEJ OSI CZASU ---
    # Zakres osi: od najwcześniejszej daty do najpóźniejszej w danych
    min_date = df['Data_Start'].min() - timedelta(days=2)
    max_date = df['Data_Koniec'].max() + timedelta(days=14)
    all_days = pd.date_range(start=min_date, end=max_date)

    tick_vals = []
    tick_text = []
    current_month = -1

    for d in all_days:
        tick_vals.append(d)
        # Jeśli zmienia się miesiąc, dodaj jego nazwę pod numerem dnia
        if d.month != current_month:
            tick_text.append(f"<b>{d.day}</b><br><span style='color:#E63946'>{PL_MONTHS[d.month]}</span>")
            current_month = d.month
        else:
            # W pozostałe dni tylko numer dnia
            tick_text.append(f"<b>{d.day}</b>")

    fig.update_xaxes(
        tickmode='array',
        tickvals=tick_vals,
        ticktext=tick_text,
        gridcolor="#E8E8E8",
        side="top",
        range=[datetime.now() - timedelta(days=2), datetime.now() + timedelta(days=21)] # Zoom na 3 tygodnie
    )

    fig.update_yaxes(autorange="reversed", gridcolor="#F5F5F5", title="")
    
    # Pionowa linia DZISIAJ
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=3, line_color="red")

    fig.update_layout(
        height=600,
        margin=dict(l=10, r=10, t=100, b=10),
        showlegend=False,
        plot_bgcolor="white"
    )

    st.plotly_chart(fig, use_container_width=True)

# 5. TABELA EDYCJI
st.markdown("---")
with st.expander("📝 Lista Eventów i Edycja danych"):
    df_edit = df.copy()
    df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
    df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
    df_edit = df_edit.rename(columns={"Projekt": "Event"})
    
    edited = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
    if st.button("💾 ZAPISZ ZMIANY W BAZIE"):
        conn.update(worksheet="FLOTA_SQM", data=edited.rename(columns={"Event": "Projekt"}))
        st.success("Baza zaktualizowana!")
        st.rerun()
