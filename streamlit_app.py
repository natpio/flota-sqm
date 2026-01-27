import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURACJA ŚRODOWISKA
# ==========================================
st.set_page_config(
    page_title="LOGISTYKA SQM - PANEL OPERACYJNY",
    layout="wide",
    page_icon="🚚"
)

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
# 2. STRUKTURA FLOTY SQM
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

PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

# ==========================================
# 3. POŁĄCZENIE I NAPRAWA TYPÓW DANYCH
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_and_fix_data():
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty:
            return pd.DataFrame(columns=["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Uwagi"])
        
        # Czyszczenie nagłówków
        df.columns = [str(c).strip() for c in df.columns]
        
        # KLUCZOWE ROZWIĄZANIE TWOJEGO BŁĘDU:
        # Wymuszamy typ tekstowy dla kolumn, które mogą być puste w GSheets
        for col in ["Uwagi", "Kierowca", "Projekt", "Pojazd"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace(['nan', 'None', 'NAT'], '')
        
        # Konwersja dat
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        
        return df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
    except Exception as e:
        st.error(f"Błąd bazy: {e}")
        return pd.DataFrame()

df_main = load_and_fix_data()

def get_conflicts(df, vehicle, start, end, ignore_idx=None):
    if df.empty: return None
    s_dt, e_dt = pd.to_datetime(start), pd.to_datetime(end)
    temp = df.copy()
    if ignore_idx is not None:
        temp = temp.drop(ignore_idx)
    mask = (temp['Pojazd'] == vehicle) & (temp['Data_Start'] <= e_dt) & (temp['Data_Koniec'] >= s_dt)
    conflicts = temp[mask]
    return conflicts if not conflicts.empty else None

# ==========================================
# 4. SIDEBAR - FORMULARZ
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: white;'>➕ NOWY EVENT</h2>", unsafe_allow_html=True)
    with st.form("new_event_form", clear_on_submit=True):
        f_veh = st.selectbox("Pojazd", ALL_VEHICLES)
        f_proj = st.text_input("Nazwa Eventu")
        f_staff = st.text_input("Kierowca")
        c1, c2 = st.columns(2)
        f_s = c1.date_input("Wyjazd", value=datetime.now())
        f_e = c2.date_input("Powrót", value=datetime.now() + timedelta(days=2))
        f_u = st.text_area("Uwagi (sloty, naczepa)")
        
        conflict = get_conflicts(df_main, f_veh, f_s, f_e)
        if conflict is not None:
            st.error(f"🛑 KOLIZJA: {conflict.iloc[0]['Projekt']}")
            
        if st.form_submit_button("ZAPISZ", use_container_width=True):
            if not f_proj:
                st.warning("Podaj nazwę projektu!")
            elif conflict is not None:
                st.error("Zablokowano: Konflikt terminów")
            else:
                new_data = pd.DataFrame([{
                    "Pojazd": f_veh, "Projekt": f_proj, "Kierowca": f_staff,
                    "Data_Start": f_s.strftime('%Y-%m-%d'),
                    "Data_Koniec": f_e.strftime('%Y-%m-%d'),
                    "Uwagi": f_u
                }])
                old_db = conn.read(worksheet="FLOTA_SQM", ttl="0")
                conn.update(worksheet="FLOTA_SQM", data=pd.concat([old_db, new_data], ignore_index=True))
                st.success("Dodano!")
                st.rerun()

# ==========================================
# 5. HARMONOGRAM (GANTT)
# ==========================================
st.title("🚚 FLOTA SQM 2026")
st.markdown("### 🗓️ Harmonogram Operacyjny")

if not df_main.empty:
    # Wykrywanie konfliktów w całej bazie
    db_errors = []
    for v in df_main['Pojazd'].unique():
        v_df = df_main[df_main['Pojazd'] == v].sort_values('Data_Start')
        for i in range(len(v_df)-1):
            if v_df.iloc[i]['Data_Koniec'] >= v_df.iloc[i+1]['Data_Start']:
                db_errors.append(f"**{v}**: {v_df.iloc[i]['Projekt']} / {v_df.iloc[i+1]['Projekt']}")
    
    if db_errors:
        with st.expander("⚠️ KONFLIKTY W GRAFIKU"):
            for err in db_errors:
                st.markdown(f'<div class="conflict-alert">{err}</div>', unsafe_allow_html=True)

# Suwak zakresu
d_range = [d.date() for d in pd.date_range("2026-01-01", "2026-12-31")]
sel_range = st.select_slider("Przesuń, aby zmienić zakres podglądu:", options=d_range, 
                             value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=21)))

if not df_main.empty:
    df_v = df_main.copy()
    df_v['Plot_End'] = df_v['Data_Koniec'] + pd.Timedelta(days=1)
    df_v['Pojazd'] = pd.Categorical(df_v['Pojazd'], categories=ALL_VEHICLES, ordered=True)
    df_v = df_v.sort_values('Pojazd')

    fig = px.timeline(
        df_v, x_start="Data_Start", x_end="Plot_End", y="Pojazd", color="Projekt", text="Projekt",
        hover_data={"Kierowca": True, "Uwagi": True, "Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m"},
        template="plotly_white"
    )

    fig.update_traces(textposition='inside', insidetextanchor='middle', 
                      textfont=dict(size=14, family="Arial Black", color="white"))

    # Oś X
    v_days = pd.date_range(sel_range[0], sel_range[1])
    tx, tt, lm = [], [], -1
    for d in v_days:
        tx.append(d)
        is_we, is_ho = d.weekday() >= 5, d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        c = "#ef4444" if is_ho else ("#94a3b8" if is_we else "#1e293b")
        lbl = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
        if d.month != lm:
            lbl = f"<span style='color:#2563eb'><b>{PL_MONTHS[d.month]}</b></span><br>{lbl}"
            lm = d.month
        tt.append(f"<span style='color:{c}'>{lbl}</span>")
        if is_we or is_ho:
            fig.add_vrect(x0=d, x1=d+timedelta(days=1), fillcolor="rgba(0,0,0,0.05)", layer="below", line_width=0)

    # Linie oddzielające grupy
    y_pos = 0
    for g, items in VEHICLE_STRUCTURE.items():
        y_pos += len(items)
        fig.add_hline(y=y_pos - 0.5, line_width=1.5, line_color="#cbd5e1")

    fig.update_xaxes(tickmode='array', tickvals=tx, ticktext=tt, side="top", range=[sel_range[0], sel_range[1]])
    fig.update_yaxes(autorange="reversed", title="")
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_color="red", line_dash="dash")
    fig.update_layout(height=1250, margin=dict(l=10, r=10, t=110, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. EDYCJA I ZARZĄDZANIE (FIX)
# ==========================================
st.markdown("---")
st.subheader("⚙️ MODUŁ EDYCJI I ZARZĄDZANIA BAZĄ")

with st.expander("Otwórz Panel Edycji Masowej (Excel Mode)"):
    if not df_main.empty:
        # Przygotowanie danych do edycji
        df_edit = df_main.copy()
        df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
        df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
        
        # FINALNA NAPRAWA BŁĘDU ColumnDataKind.FLOAT:
        # Zapewniamy, że kolumny tekstowe są faktycznie tekstowe
        for c in ["Uwagi", "Kierowca", "Projekt", "Pojazd"]:
            df_edit[c] = df_edit[c].astype(str)

        try:
            res = st.data_editor(
                df_edit,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_VEHICLES, required=True),
                    "Projekt": st.column_config.TextColumn("Projekt", required=True),
                    "Kierowca": st.column_config.TextColumn("Kierowca"),
                    "Data_Start": st.column_config.DateColumn("Wyjazd", required=True),
                    "Data_Koniec": st.column_config.DateColumn("Powrót", required=True),
                    "Uwagi": st.column_config.TextColumn("Uwagi")
                }
            )
            
            if st.button("💾 SYNCHRONIZUJ Z CHMURĄ"):
                # Konwersja na format zapisu
                final = res.copy()
                final['Data_Start'] = final['Data_Start'].apply(lambda x: x.strftime('%Y-%m-%d'))
                final['Data_Koniec'] = final['Data_Koniec'].apply(lambda x: x.strftime('%Y-%m-%d'))
                
                conn.update(worksheet="FLOTA_SQM", data=final)
                st.success("Zaktualizowano Google Sheets!")
                st.rerun()
                
        except Exception as e:
            st.error(f"Wystąpił błąd podczas edycji danych: {e}")
    else:
        st.info("Brak danych.")
