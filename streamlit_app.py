import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURACJA I STYLIZACJA
# ==========================================
st.set_page_config(
    page_title="LOGISTYKA SQM - PANEL OPERACYJNY",
    layout="wide",
    page_icon="🚚"
)

# Stylizacja dla maksymalnej czytelności w logistyce
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        min-width: 400px !important;
    }
    .stSelectbox label, .stTextInput label, .stDateInput label, .stTextArea label {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }
    .conflict-alert {
        background-color: #fef2f2;
        border: 2px solid #ef4444;
        padding: 10px;
        border-radius: 5px;
        color: #b91c1c;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. STRUKTURA FLOTY (ZGODNIE Z PLIKIEM EXCEL)
# ==========================================
VEHICLE_STRUCTURE = {
    "MIESZKANIA BCN": [
        "MIESZKANIE BCN - TORRASA", 
        "MIESZKANIE BCN - ARGENTINA (PM)"
    ],
    "OSOBÓWKI": [
        "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", 
        "03 – Dacia Duster (biedak) – WE5A723", "04 – Dacia Jogger – WH6802A", 
        "06 – Dacia Duster – WH7087A ex T Białek", "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", 
        "Chrysler Pacifica PY04266 - MBanasiak", "05 – Dacia Duster – WH7083A B.Krauze", 
        "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N", "Seat Ateca WZ445HU Dynasiuk", 
        "Seat Ateca WZ446HU- PM"
    ],
    "BUSY": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", 
        "BOXER - WZ213GF", "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", 
        "BOXER (WYPAS) DW7WE24", "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"
    ],
    "CIĘŻARÓWKI / TIR": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "SPEDYCJA": [
        "SPEDYCJA 1", "SPEDYCJA 2", "SPEDYCJA 3", "SPEDYCJA 4", "SPEDYCJA 5", "AUTO RENTAL"
    ]
}

ALL_VEHICLES = [v for sub in VEHICLE_STRUCTURE.values() for v in sub]

# Polskie nazewnictwo dat
PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

# ==========================================
# 3. LOGIKA DANYCH I STATUSÓW
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def calculate_status(row):
    """Automatyczne wyliczanie statusu na podstawie daty."""
    today = datetime.now().date()
    start = row['Data_Start'].date() if hasattr(row['Data_Start'], 'date') else row['Data_Start']
    end = row['Data_Koniec'].date() if hasattr(row['Data_Koniec'], 'date') else row['Data_Koniec']
    
    if today < start:
        return "📅 PLANOWANY"
    elif start <= today <= end:
        return "🚚 W TRASIE"
    else:
        return "✅ ZAKOŃCZONY"

def get_data():
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty:
            return pd.DataFrame(columns=["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Uwagi", "Status"])
        
        # Standaryzacja kolumn
        df.columns = [str(c).strip() for c in df.columns]
        
        # Naprawa błędu typów (FLOAT vs TEXT) z Twojego screena
        for col in ["Uwagi", "Kierowca", "Projekt", "Pojazd"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace(['nan', 'None', 'NaN', 'NAT'], '')
        
        # Konwersja dat
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        
        # Usuwanie rekordów bez dat lub pojazdu
        df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
        
        # Wyliczanie statusu
        df['Status'] = df.apply(calculate_status, axis=1)
        return df
    except Exception as e:
        st.error(f"Błąd bazy danych: {e}")
        return pd.DataFrame()

df_main = get_data()

# ==========================================
# 4. SIDEBAR - DODAWANIE (LOGISTYKA)
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: white;'>➕ NOWY TRANSPORT</h2>", unsafe_allow_html=True)
    with st.form("new_entry", clear_on_submit=True):
        f_veh = st.selectbox("Pojazd / Zasób", ALL_VEHICLES)
        f_proj = st.text_input("Projekt (np. Euroshop, ITB)")
        f_staff = st.text_input("Kierowca / Załadunek")
        
        c1, c2 = st.columns(2)
        f_s = c1.date_input("Data Start")
        f_e = c2.date_input("Data Koniec", value=datetime.now() + timedelta(days=3))
        
        f_u = st.text_area("Uwagi (sloty, naczepa)")
        
        # Szybka kontrola kolizji
        s_dt, e_dt = pd.to_datetime(f_s), pd.to_datetime(f_e)
        conflict = df_main[(df_main['Pojazd'] == f_veh) & (df_main['Data_Start'] <= e_dt) & (df_main['Data_Koniec'] >= s_dt)]
        
        if not conflict.empty:
            st.error(f"🚨 KONFLIKT: {conflict.iloc[0]['Projekt']}")
            
        if st.form_submit_button("ZAPISZ W ARKUSZU", use_container_width=True):
            if not f_proj:
                st.warning("Podaj nazwę projektu.")
            elif not conflict.empty:
                st.error("Zablokowano zapis - auto zajęte.")
            else:
                new_row = pd.DataFrame([{
                    "Pojazd": f_veh, "Projekt": f_proj, "Kierowca": f_staff,
                    "Data_Start": f_s.strftime('%Y-%m-%d'),
                    "Data_Koniec": f_e.strftime('%Y-%m-%d'),
                    "Uwagi": f_notes if 'f_notes' in locals() else f_u
                }])
                current_db = conn.read(worksheet="FLOTA_SQM", ttl="0")
                conn.update(worksheet="FLOTA_SQM", data=pd.concat([current_db, new_row], ignore_index=True))
                st.rerun()

# ==========================================
# 5. WIZUALIZACJA (WIDOK EXCELOWY)
# ==========================================
st.title("🚚 HARMONOGRAM FLOTY SQM MULTIMEDIA")

# Zakres podglądu
d_opts = [d.date() for d in pd.date_range("2026-01-01", "2026-12-31")]
sel_range = st.select_slider(
    "Widok czasowy:",
    options=d_opts,
    value=(datetime.now().date() - timedelta(days=3), datetime.now().date() + timedelta(days=21))
)

if not df_main.empty:
    df_v = df_main.copy()
    df_v['Plot_End'] = df_v['Data_Koniec'] + pd.Timedelta(days=1)
    
    # Sortowanie dokładnie jak w Twoim Excelu
    df_v['Pojazd'] = pd.Categorical(df_v['Pojazd'], categories=ALL_VEHICLES, ordered=True)
    df_v = df_v.sort_values('Pojazd')

    fig = px.timeline(
        df_v, x_start="Data_Start", x_end="Plot_End", y="Pojazd", color="Status", text="Projekt",
        color_discrete_map={
            "📅 PLANOWANY": "#94a3b8",  # Szary
            "🚚 W TRASIE": "#ef4444",   # Czerwony
            "✅ ZAKOŃCZONY": "#22c55e"   # Zielony
        },
        hover_data={"Kierowca": True, "Uwagi": True, "Status": True},
        template="plotly_white"
    )

    fig.update_traces(
        textposition='inside', insidetextanchor='middle',
        textfont=dict(size=14, family="Arial Black", color="white")
    )

    # Skalowanie osi X (polskie miesiące/dni)
    t_days = pd.date_range(sel_range[0], sel_range[1])
    tx, tt, lm = [], [], -1
    for d in t_days:
        tx.append(d)
        is_we, is_ho = d.weekday() >= 5, d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        clr = "#ef4444" if is_ho else ("#94a3b8" if is_we else "#1e293b")
        lbl = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
        if d.month != lm:
            lbl = f"<span style='color:#2563eb'><b>{PL_MONTHS[d.month]}</b></span><br>{lbl}"
            lm = d.month
        tt.append(f"<span style='color:{clr}'>{lbl}</span>")
        if is_we or is_ho:
            fig.add_vrect(x0=d, x1=d+timedelta(days=1), fillcolor="rgba(0,0,0,0.05)", layer="below", line_width=0)

    # Separatory grup (Mieszkania/Osobówki/Busy itd.)
    y_sep = 0
    for g, items in VEHICLE_STRUCTURE.items():
        y_sep += len(items)
        fig.add_hline(y=y_sep - 0.5, line_width=1.5, line_color="#cbd5e1")

    fig.update_xaxes(tickmode='array', tickvals=tx, ticktext=tt, side="top", range=[sel_range[0], sel_range[1]])
    fig.update_yaxes(autorange="reversed", title="")
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_color="red", line_dash="dash")
    fig.update_layout(height=1300, margin=dict(l=10, r=10, t=110, b=10))

    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. PANEL EDYCJI (NAPRAWA BŁĘDÓW)
# ==========================================
st.markdown("---")
st.subheader("⚙️ MODUŁ EDYCJI I ZARZĄDZANIA BAZĄ")

if not df_main.empty:
    df_ed = df_main.copy()
    # Konwersja na czyste daty dla edytora
    df_ed['Data_Start'] = df_ed['Data_Start'].dt.date
    df_ed['Data_Koniec'] = df_ed['Data_Koniec'].dt.date
    
    # Naprawa ColumnDataKind.FLOAT (rzutowanie wszystkiego na string)
    for c in ["Uwagi", "Kierowca", "Projekt"]:
        df_ed[c] = df_ed[c].astype(str)

    try:
        edited = st.data_editor(
            df_ed,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Status": st.column_config.TextColumn("Status (Auto)", disabled=True),
                "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_VEHICLES, required=True),
                "Data_Start": st.column_config.DateColumn("Start", format="YYYY-MM-DD"),
                "Data_Koniec": st.column_config.DateColumn("Koniec", format="YYYY-MM-DD")
            }
        )
        
        if st.button("💾 ZAPISZ ZMIANY W GOOGLE SHEETS", use_container_width=True):
            save_df = edited.drop(columns=['Status']) # Nie zapisujemy wirtualnej kolumny
            save_df['Data_Start'] = save_df['Data_Start'].apply(lambda x: x.strftime('%Y-%m-%d'))
            save_df['Data_Koniec'] = save_df['Data_Koniec'].apply(lambda x: x.strftime('%Y-%m-%d'))
            conn.update(worksheet="FLOTA_SQM", data=save_df)
            st.success("Zapisano!")
            st.rerun()
    except Exception as e:
        st.error(f"Błąd edytora: {e}")
else:
    st.info("Baza jest pusta.")
