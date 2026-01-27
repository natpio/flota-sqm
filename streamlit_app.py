import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURACJA ŚRODOWISKA I UI
# ==========================================
st.set_page_config(
    page_title="LOGISTYKA SQM - PANEL OPERACYJNY",
    layout="wide",
    page_icon="🚚"
)

# Stylizacja interfejsu dla logistyka (wysoki kontrast, ciemny sidebar)
st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        min-width: 420px !important;
    }
    .stSelectbox label, .stTextInput label, .stDateInput label, .stTextArea label {
        color: #f8fafc !important;
        font-weight: bold !important;
        font-size: 1rem !important;
    }
    .status-badge {
        padding: 5px 10px;
        border-radius: 4px;
        font-weight: bold;
        color: white;
    }
    .conflict-alert {
        background-color: #fef2f2;
        border: 2px solid #ef4444;
        padding: 15px;
        border-radius: 8px;
        color: #991b1b;
        font-weight: bold;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. KOMPLETNA STRUKTURA FLOTY SQM
# ==========================================
VEHICLE_STRUCTURE = {
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
    "SPEDYCJA / RENTAL": ["SPEDYCJA 1", "SPEDYCJA 2", "SPEDYCJA 3", "SPEDYCJA 4", "AUTO RENTAL"],
    "MIESZKANIA BCN": ["MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"]
}

ALL_VEHICLES = [v for sub in VEHICLE_STRUCTURE.values() for v in sub]

# Stałe czasu i języka
PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

# ==========================================
# 3. LOGIKA STATUSU I DANYCH
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def calculate_auto_status(row):
    """Wylicza status transportu na podstawie daty dzisiejszej."""
    today = datetime.now().date()
    # Konwersja do date() jeśli to Timestamp
    start = row['Data_Start'].date() if hasattr(row['Data_Start'], 'date') else row['Data_Start']
    end = row['Data_Koniec'].date() if hasattr(row['Data_Koniec'], 'date') else row['Data_Koniec']
    
    if today < start:
        return "📅 PLANOWANY"
    elif start <= today <= end:
        return "🚚 W TRASIE"
    else:
        return "✅ ZAKOŃCZONY"

def get_data_fixed():
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty:
            return pd.DataFrame(columns=["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Uwagi", "Status"])
        
        # Czyszczenie nagłówków
        df.columns = [str(c).strip() for c in df.columns]
        
        # Naprawa typów danych (rozwiązanie błędu FLOAT/TEXT)
        for col in ["Uwagi", "Kierowca", "Projekt", "Pojazd"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace(['nan', 'None', 'NAT'], '')
        
        # Konwersja dat
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        
        # Filtrowanie pustych kluczowych pól
        df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
        
        # APLIKACJA AUTOMATYCZNEGO STATUSU
        df['Status'] = df.apply(calculate_auto_status, axis=1)
        
        return df
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        return pd.DataFrame()

df_main = get_data_fixed()

# ==========================================
# 4. SIDEBAR - DODAWANIE WPISU
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: white;'>➕ NOWY TRANSPORT</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    with st.form("sidebar_form", clear_on_submit=True):
        f_veh = st.selectbox("Wybierz Pojazd", ALL_VEHICLES)
        f_proj = st.text_input("Nazwa Projektu / Targów")
        f_driver = st.text_input("Kierowca / Załadunek")
        
        c1, c2 = st.columns(2)
        f_start = c1.date_input("Wyjazd", value=datetime.now())
        f_end = c2.date_input("Powrót", value=datetime.now() + timedelta(days=2))
        
        f_notes = st.text_area("Uwagi (sloty, naczepa, rozładunek)")
        
        # Walidacja kolizji przed zapisem
        s_dt = pd.to_datetime(f_start)
        e_dt = pd.to_datetime(f_end)
        collision = df_main[(df_main['Pojazd'] == f_veh) & (df_main['Data_Start'] <= e_dt) & (df_main['Data_Koniec'] >= s_dt)]
        
        if not collision.empty:
            st.error(f"🚨 KOLIZJA: {collision.iloc[0]['Projekt']}")
            
        submit = st.form_submit_button("DODAJ DO GRAFIKU", use_container_width=True)
        
        if submit:
            if not f_proj:
                st.warning("Podaj nazwę projektu!")
            elif not collision.empty:
                st.error("Nie można zapisać - auto zajęte.")
            else:
                new_row = pd.DataFrame([{
                    "Pojazd": f_veh, "Projekt": f_proj, "Kierowca": f_driver,
                    "Data_Start": f_start.strftime('%Y-%m-%d'),
                    "Data_Koniec": f_end.strftime('%Y-%m-%d'),
                    "Uwagi": f_notes
                }])
                raw_db = conn.read(worksheet="FLOTA_SQM", ttl="0")
                updated_db = pd.concat([raw_db, new_row], ignore_index=True)
                conn.update(worksheet="FLOTA_SQM", data=updated_db)
                st.success("Dodano pomyślnie!")
                st.rerun()

# ==========================================
# 5. GRAFIK GANTTA ZE STATUSAMI
# ==========================================
st.title("🚚 HARMONOGRAM TRANSPORTOWY SQM")

# Sprawdzenie błędów w bazie
if not df_main.empty:
    all_errs = []
    for v in df_main['Pojazd'].unique():
        v_df = df_main[df_main['Pojazd'] == v].sort_values('Data_Start')
        for i in range(len(v_df)-1):
            if v_df.iloc[i]['Data_Koniec'] >= v_df.iloc[i+1]['Data_Start']:
                all_errs.append(f"**{v}**: {v_df.iloc[i]['Projekt']} / {v_df.iloc[i+1]['Projekt']}")
    if all_errs:
        with st.expander("⚠️ WYKRYTO KONFLIKTY DAT"):
            for e in all_errs:
                st.markdown(f'<div class="conflict-alert">{e}</div>', unsafe_allow_html=True)

# Suwak zakresu
view_range = st.select_slider(
    "Zakres podglądu grafiku:",
    options=[d.date() for d in pd.date_range("2026-01-01", "2026-12-31")],
    value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=20))
)

if not df_main.empty:
    df_viz = df_main.copy()
    df_viz['Viz_End'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)
    df_viz['Pojazd'] = pd.Categorical(df_viz['Pojazd'], categories=ALL_VEHICLES, ordered=True)
    df_viz = df_viz.sort_values('Pojazd')

    # Gantt kolorowany po statusie
    fig = px.timeline(
        df_viz, x_start="Data_Start", x_end="Viz_End", y="Pojazd", color="Status", text="Projekt",
        color_discrete_map={
            "📅 PLANOWANY": "#94a3b8",  # Szary
            "🚚 W TRASIE": "#ef4444",   # Czerwony
            "✅ ZAKOŃCZONY": "#22c55e"   # Zielony
        },
        hover_data={"Kierowca": True, "Uwagi": True, "Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m", "Status": True},
        template="plotly_white"
    )

    fig.update_traces(
        textposition='inside', insidetextanchor='middle',
        textfont=dict(size=14, family="Arial Black", color="white"),
        marker=dict(line=dict(width=1, color="white"))
    )

    # Oś X - polskie daty
    timeline_days = pd.date_range(view_range[0], view_range[1])
    xticks, xtitles, last_m = [], [], -1
    for d in timeline_days:
        xticks.append(d)
        is_we, is_ho = d.weekday() >= 5, d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        clr = "#ef4444" if is_ho else ("#94a3b8" if is_we else "#1e293b")
        lbl = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
        if d.month != last_m:
            lbl = f"<span style='color:#2563eb'><b>{PL_MONTHS[d.month]}</b></span><br>{lbl}"
            last_m = d.month
        xtitles.append(f"<span style='color:{clr}'>{lbl}</span>")
        if is_we or is_ho:
            fig.add_vrect(x0=d, x1=d+timedelta(days=1), fillcolor="rgba(200,200,200,0.1)", layer="below", line_width=0)

    # Separatory grup floty
    y_mark = 0
    for group, items in VEHICLE_STRUCTURE.items():
        y_mark += len(items)
        fig.add_hline(y=y_mark - 0.5, line_width=1.5, line_color="#cbd5e1")

    fig.update_xaxes(tickmode='array', tickvals=xticks, ticktext=xtitles, side="top", range=[view_range[0], view_range[1]])
    fig.update_yaxes(autorange="reversed", title="")
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_color="red", line_dash="dash")
    fig.update_layout(height=1250, margin=dict(l=10, r=10, t=110, b=10), showlegend=True)

    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. EDYCJA I ZARZĄDZANIE (STATUSY AUTO)
# ==========================================
st.markdown("---")
st.subheader("⚙️ PANEL EDYCJI I REJESTR TRANSPORTÓW")

with st.expander("Otwórz Panel Edycji Masowej (Status wyliczany automatycznie)"):
    if not df_main.empty:
        # Przygotowanie danych do edytora (rzutowanie na daty dla kompatybilności)
        df_edit = df_main.copy()
        df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
        df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
        
        # Wymuszamy typ tekstowy kolumn tekstowych
        for col in ["Uwagi", "Kierowca", "Projekt"]:
            df_edit[col] = df_edit[col].astype(str)

        # Konfiguracja edytora
        res_df = st.data_editor(
            df_edit,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Status": st.column_config.TextColumn("Status (Auto)", disabled=True, help="Wyliczany na podstawie dat"),
                "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_VEHICLES, required=True),
                "Projekt": st.column_config.TextColumn("Projekt", required=True),
                "Kierowca": st.column_config.TextColumn("Kierowca"),
                "Data_Start": st.column_config.DateColumn("Wyjazd", required=True),
                "Data_Koniec": st.column_config.DateColumn("Powrót", required=True),
                "Uwagi": st.column_config.TextColumn("Uwagi / Sloty")
            }
        )
        
        if st.button("💾 SYNCHRONIZUJ I PRZELICZ STATUSY", use_container_width=True):
            # Przed zapisem usuwamy kolumnę Status (nie zapisujemy jej do Excela, jest wirtualna)
            final_save = res_df.drop(columns=['Status'])
            
            # Formate daty dla Google Sheets
            final_save['Data_Start'] = final_save['Data_Start'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x)
            final_save['Data_Koniec'] = final_save['Data_Koniec'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x)
            
            conn.update(worksheet="FLOTA_SQM", data=final_save)
            st.success("Baza zaktualizowana!")
            st.rerun()
    else:
        st.info("Baza danych jest pusta.")

# LICZNIK LINII: ~350.
