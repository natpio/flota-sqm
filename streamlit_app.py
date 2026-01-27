import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

# ==========================================
# 1. KONFIGURACJA ŚRODOWISKA I CSS
# ==========================================
st.set_page_config(
    page_title="LOGISTYKA SQM - SYSTEM ZARZĄDZANIA",
    layout="wide",
    page_icon="🚚"
)

# Rozbudowany arkusz stylów dla profesjonalnego wyglądu
st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    
    /* Panel boczny - ciemny motyw SQM */
    section[data-testid="stSidebar"] {
        background-color: #0f172a !important;
        min-width: 400px !important;
    }
    
    /* Alerty i karty */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
        border-bottom: 4px solid #3b82f6;
    }
    
    .conflict-alert {
        background-color: #fef2f2;
        border-left: 5px solid #ef4444;
        padding: 15px;
        margin: 10px 0;
        color: #991b1b;
        font-weight: 500;
    }
    
    /* Plotly kontener */
    .plot-wrapper {
        background-color: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    /* Nagłówki */
    h1, h2, h3 { color: #1e293b; font-family: 'Segoe UI', sans-serif; }
    
    /* Dostosowanie czcionek w sidebarze */
    .stSelectbox label, .stTextInput label, .stDateInput label, .stTextArea label {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DEFINICJA ZASOBÓW (FLOTA SQM)
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

# Stałe kalendarzowe
PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

# ==========================================
# 3. SILNIK DANYCH (GOOGLE SHEETS + CLEANING)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def fetch_data():
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty:
            return pd.DataFrame(columns=["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Uwagi"])
        
        # Standaryzacja i czyszczenie
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
        
        # Konwersja dat z obsługą błędnych wpisów
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        df = df.dropna(subset=['Data_Start', 'Data_Koniec'])
        
        return df
    except Exception as e:
        st.error(f"Krytyczny błąd bazy danych: {e}")
        return pd.DataFrame()

df_main = fetch_data()

def validate_overlap(df, veh, start, end, exclude_idx=None):
    if df.empty: return None
    s_dt, e_dt = pd.to_datetime(start), pd.to_datetime(end)
    temp = df.copy()
    if exclude_idx is not None: temp = temp.drop(exclude_idx)
    
    collision = temp[(temp['Pojazd'] == veh) & (temp['Data_Start'] <= e_dt) & (temp['Data_Koniec'] >= s_dt)]
    return collision if not collision.empty else None

# ==========================================
# 4. SIDEBAR - FORMULARZ LOGISTYKA
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: white;'>🚛 ZARZĄDZANIE TRANSPORTEM</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    with st.form("main_logistics_form", clear_on_submit=True):
        f_veh = st.selectbox("Wybierz Pojazd", ALL_VEHICLES)
        f_proj = st.text_input("Nazwa Projektu / Targów")
        f_staff = st.text_input("Kierowca / Team")
        
        c1, c2 = st.columns(2)
        f_start = c1.date_input("Data Wyjazdu")
        f_end = c2.date_input("Data Powrotu", value=datetime.now() + timedelta(days=3))
        
        f_notes = st.text_area("Uwagi logistyczne (sloty, rozładunek, naczepa)")
        
        # Weryfikacja konfliktu przed zapisem
        conflict = validate_overlap(df_main, f_veh, f_start, f_end)
        
        save_btn = st.form_submit_button("ZAPISZ TRANSPORT", use_container_width=True)
        
        if save_btn:
            if not f_proj:
                st.error("BŁĄD: Nazwa projektu jest wymagana!")
            elif conflict is not None:
                st.warning(f"ZABLOKOWANO: Auto zajęte przez projekt: {conflict.iloc[0]['Projekt']}")
            else:
                new_entry = pd.DataFrame([{
                    "Pojazd": f_veh, "Projekt": f_proj, "Kierowca": f_staff,
                    "Data_Start": f_start.strftime('%Y-%m-%d'),
                    "Data_Koniec": f_end.strftime('%Y-%m-%d'),
                    "Uwagi": f_notes
                }])
                raw_gsheet = conn.read(worksheet="FLOTA_SQM", ttl="0")
                updated_gsheet = pd.concat([raw_gsheet, new_entry], ignore_index=True)
                conn.update(worksheet="FLOTA_SQM", data=updated_gsheet)
                st.success("Dodano do harmonogramu!")
                st.rerun()

# ==========================================
# 5. DASHBOARD - STATYSTYKI (NOWOŚĆ)
# ==========================================
st.title("🚚 PANEL LOGISTYKI SQM MULTIMEDIA")

if not df_main.empty:
    m1, m2, m3, m4 = st.columns(4)
    today = datetime.now()
    
    active_today = df_main[(df_main['Data_Start'] <= today) & (df_main['Data_Koniec'] >= today)]
    m1.markdown(f'<div class="metric-card"><h3>W TRASIE</h3><h2>{len(active_today)}</h2></div>', unsafe_allow_html=True)
    
    this_month = df_main[df_main['Data_Start'].dt.month == today.month]
    m2.markdown(f'<div class="metric-card"><h3>EVENTY (MIES)</h3><h2>{len(this_month)}</h2></div>', unsafe_allow_html=True)
    
    heavy_duty = df_main[df_main['Pojazd'].str.contains("TIR|SOLO")]
    m3.markdown(f'<div class="metric-card"><h3>CIĘŻKIE TRASY</h3><h2>{len(heavy_duty)}</h2></div>', unsafe_allow_html=True)
    
    m4.markdown(f'<div class="metric-card"><h3>FLOTA RAZEM</h3><h2>{len(ALL_VEHICLES)}</h2></div>', unsafe_allow_html=True)

# ==========================================
# 6. GRAFIK GANTTA (WIZUALIZACJA)
# ==========================================
st.markdown("### 📅 HARMONOGRAM OPERACYJNY 2026")

# Globalne sprawdzenie błędów w bazie
if not df_main.empty:
    errors = []
    for v in df_main['Pojazd'].unique():
        v_df = df_main[df_main['Pojazd'] == v].sort_values('Data_Start')
        for i in range(len(v_df)-1):
            if v_df.iloc[i]['Data_Koniec'] >= v_df.iloc[i+1]['Data_Start']:
                errors.append(f"Kolizja: **{v}** -> {v_df.iloc[i]['Projekt']} i {v_df.iloc[i+1]['Projekt']}")
    
    if errors:
        with st.expander("⚠️ WYKRYTO KONFLIKTY W BAZIE"):
            for e in errors:
                st.markdown(f'<div class="conflict-alert">{e}</div>', unsafe_allow_html=True)

# Suwak zakresu czasu
days_list = [d.date() for d in pd.date_range("2026-01-01", "2026-12-31")]
v_range = st.select_slider(
    "Zmień zakres widoczności grafiku:", options=days_list,
    value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=20))
)

if not df_main.empty:
    with st.container():
        df_viz = df_main.copy()
        df_viz['Plot_End'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)
        df_viz['Pojazd'] = pd.Categorical(df_viz['Pojazd'], categories=ALL_VEHICLES, ordered=True)
        df_viz = df_viz.sort_values('Pojazd')

        fig = px.timeline(
            df_viz, x_start="Data_Start", x_end="Plot_End", y="Pojazd", color="Projekt", text="Projekt",
            hover_data={"Kierowca": True, "Uwagi": True, "Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m"},
            template="plotly_white", opacity=0.9
        )

        fig.update_traces(
            textposition='inside', insidetextanchor='middle',
            textfont=dict(size=14, family="Arial Black", color="white"),
            marker=dict(line=dict(width=1, color="white"))
        )

        # Konfiguracja Osi X (Polskie nazewnictwo)
        timeline_days = pd.date_range(v_range[0], v_range[1])
        xticks, xlabels, last_month = [], [], -1
        
        for d in timeline_days:
            xticks.append(d)
            is_we = d.weekday() >= 5
            is_ho = d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
            
            c = "#dc2626" if is_ho else ("#94a3b8" if is_we else "#1e293b")
            label = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
            
            if d.month != last_month:
                label = f"<span style='color:#2563eb'><b>{PL_MONTHS[d.month]}</b></span><br>{label}"
                last_month = d.month
            
            xlabels.append(f"<span style='color:{c}'>{label}</span>")
            
            if is_we or is_ho:
                fig.add_vrect(x0=d, x1=d+timedelta(days=1), fillcolor="rgba(200,200,200,0.12)", layer="below", line_width=0)

        # Separatory grup floty
        y_mark = 0
        for group, members in VEHICLE_STRUCTURE.items():
            y_mark += len(members)
            fig.add_hline(y=y_mark - 0.5, line_width=2, line_color="#cbd5e1")

        fig.update_xaxes(tickmode='array', tickvals=xticks, ticktext=xlabels, side="top", range=[v_range[0], v_range[1]])
        fig.update_yaxes(autorange="reversed", title="")
        
        # Dzisiejsza data
        fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=3, line_color="#ef4444", line_dash="dash")
        
        fig.update_layout(height=1250, margin=dict(l=10, r=10, t=110, b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. ZAAWANSOWANY EDYTOR BAZY (DODATKOWE LINIE)
# ==========================================
st.markdown("---")
st.subheader("⚙️ ZARZĄDZANIE REJESTREM")

with st.expander("Otwórz Panel Edycji Masowej (Tryb Arkusza)"):
    if not df_main.empty:
        # Przygotowanie danych do edycji - wymuszenie typów
        df_editor = df_main.copy()
        df_editor['Data_Start'] = df_editor['Data_Start'].dt.date
        df_editor['Data_Koniec'] = df_editor['Data_Koniec'].dt.date
        
        res_df = st.data_editor(
            df_editor,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_VEHICLES, required=True),
                "Projekt": st.column_config.TextColumn("Projekt", required=True),
                "Data_Start": st.column_config.DateColumn("Wyjazd", required=True),
                "Data_Koniec": st.column_config.DateColumn("Powrót", required=True),
                "Uwagi": st.column_config.TextColumn("Szczegóły Logistyczne (Sloty/Naczepy)")
            }
        )
        
        if st.button("💾 SYNCHRONIZUJ Z GOOGLE SHEETS", use_container_width=True):
            # Konwersja do zapisu
            final_save = res_df.copy()
            final_save['Data_Start'] = final_save['Data_Start'].apply(lambda x: x.strftime('%Y-%m-%d'))
            final_save['Data_Koniec'] = final_save['Data_Koniec'].apply(lambda x: x.strftime('%Y-%m-%d'))
            
            conn.update(worksheet="FLOTA_SQM", data=final_save)
            st.success("Dane zostały nadpisane w chmurze.")
            st.rerun()
    else:
        st.info("Brak wpisów do wyświetlenia.")

# ==========================================
# 8. ANALIZA OBŁOŻENIA (DODATKOWE LINIE)
# ==========================================
st.markdown("---")
if not df_main.empty:
    st.subheader("📊 ANALIZA WYKORZYSTANIA FLOTY")
    usage_col1, usage_col2 = st.columns(2)
    
    # Wykres kołowy projektów
    proj_counts = df_main['Projekt'].value_counts().head(10)
    fig_pie = px.pie(values=proj_counts.values, names=proj_counts.index, title="TOP 10 PROJEKTÓW (Liczba kursów)")
    usage_col1.plotly_chart(fig_pie)
    
    # Wykres słupkowy pojazdów
    veh_counts = df_main['Pojazd'].value_counts().head(15)
    fig_bar = px.bar(x=veh_counts.index, y=veh_counts.values, title="NAJCZĘŚCIEJ WYKORZYSTYWANE POJAZDY", labels={'x': 'Pojazd', 'y': 'Ilość wyjazdów'})
    usage_col2.plotly_chart(fig_bar)

# Licznik linii: ~345.
