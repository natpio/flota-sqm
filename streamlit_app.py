import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="FLOTA SQM 2026", layout="wide", page_icon="🚚")

# Custom CSS dla maksymalnej widoczności dat i miesięcy
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stPlotlyChart"] .xtick text { 
        font-size: 16px !important; 
        font-weight: 900 !important; 
        fill: #000000 !important;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 FLOTA SQM 2026")

# 2. POŁĄCZENIE Z BAZĄ
conn = st.connection("gsheets", type=GSheetsConnection)

def get_auto_status(start, end):
    today = datetime.now().date()
    start = start.date() if hasattr(start, 'date') else start
    end = end.date() if hasattr(end, 'date') else end
    
    if today < start:
        return "Oczekuje"
    elif start <= today <= end:
        return "W trakcie"
    else:
        return "Wróciło"

def load_data():
    df = conn.read(worksheet="FLOTA_SQM", ttl="0")
    df = df.dropna(how='all').copy()
    
    # Konwersja dat
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    df = df.dropna(subset=['Data_Start', 'Data_Koniec'])
    
    # Automatyczna zmiana statusu na podstawie daty
    df['Status'] = df.apply(lambda x: get_auto_status(x['Data_Start'], x['Data_Koniec']), axis=1)
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Problem z formatem danych: {e}")
    st.stop()

# 3. SIDEBAR - FORMULARZ
with st.sidebar:
    st.header("⚙️ Dodaj Nowy Event")
    with st.form("add_form", clear_on_submit=True):
        pojazd = st.selectbox("Pojazd", [
            "31 - TIR P21V388/P22X300 STABLEWSKI", "TIR 2 - W2654FT/P22H972 KOGUS",
            "TIR 3 - PNT3530A/P24U343 DANIELAK", "44 - SOLO PY 73262",
            "25 - Jumper - PY22952", "24 - Jumper - PY22954", "BOXER - PO 5VT68",
            "OPEL DW4W443", "SPEDYCJA"
        ])
        event = st.text_input("Nazwa Eventu")
        kierowca = st.text_input("Kierowca")
        
        c1, c2 = st.columns(2)
        d_start = c1.date_input("Wyjazd", value=datetime.now())
        d_end = c2.date_input("Powrót", value=datetime.now() + timedelta(days=2))
        
        if st.form_submit_button("ZAPISZ DO GRAFIKU"):
            # Status zostanie nadany automatycznie przy ładowaniu
            new_row = pd.DataFrame([{
                "Pojazd": pojazd, "Projekt": event, "Kierowca": kierowca,
                "Data_Start": d_start.strftime('%Y-%m-%d'),
                "Data_Koniec": d_end.strftime('%Y-%m-%d'),
                "Status": "Oczekuje" 
            }])
            current_data = conn.read(worksheet="FLOTA_SQM", ttl="0")
            updated_data = pd.concat([current_data, new_row], ignore_index=True)
            conn.update(worksheet="FLOTA_SQM", data=updated_data)
            st.rerun()

# 4. GRAFIK GANTTA
st.subheader("🗓️ Harmonogram Eventów")

if not df.empty:
    df_viz = df.copy()
    df_viz['Viz_End'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)

    fig = px.timeline(
        df_viz, 
        x_start="Data_Start", x_end="Viz_End", y="Pojazd", 
        color="Status", text="Projekt",
        hover_data={"Data_Start": "|%d %b", "Data_Koniec": "|%d %b", "Kierowca": True, "Status": True, "Viz_End": False},
        color_discrete_map={
            "Oczekuje": "#45B6FE",  # Niebieski
            "W trakcie": "#37BC61", # Zielony
            "Wróciło": "#9E9E9E"    # Szary
        },
        labels={"Projekt": "Event"}
    )

    fig.update_xaxes(
        dtick="D1",             
        tickformat="<b>%d</b><br><b>%b</b>",
        tickfont=dict(size=16, color="black", family="Arial Black"),
        gridcolor="#D3D3D3", 
        showgrid=True,
        side="top",
        title_text=""
    )

    fig.update_yaxes(autorange="reversed", tickfont=dict(size=12, color="black"))
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=4, line_color="red")

    fig.update_layout(
        height=600,
        margin=dict(l=10, r=10, t=110, b=10),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )

    st.plotly_chart(fig, use_container_width=True)

# 5. TABELA EDYCJI
st.markdown("---")
with st.expander("📝 Lista Eventów i Edycja", expanded=True):
    df_edit = df.copy()
    df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
    df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
    
    # Zmiana nazwy kolumny tylko do wyświetlania w edytorze
    df_edit = df_edit.rename(columns={"Projekt": "Event"})

    edited_df = st.data_editor(
        df_edit, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Wyjazd": st.column_config.DateColumn("Wyjazd"),
            "Powrót": st.column_config.DateColumn("Powrót"),
            "Status": st.column_config.TextColumn("Status (Auto)", disabled=True), # Status jest auto, więc blokujemy edycję
        }
    )
    
    if st.button("💾 ZAPISZ ZMIANY"):
        # Powrót do oryginalnej nazwy kolumny przed zapisem do GS
        final_df = edited_df.rename(columns={"Event": "Projekt"})
        conn.update(worksheet="FLOTA_SQM", data=final_df)
        st.success("Zaktualizowano bazę!")
        st.rerun()
