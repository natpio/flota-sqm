import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

# ==========================================
# 1. KONFIGURACJA STRONY
# ==========================================
st.set_page_config(
    page_title="LOGISTYKA SQM - PANEL OPERACYJNY",
    layout="wide",
    page_icon="🚚"
)

# Stylizacja interfejsu
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .sidebar-header { color: #f8fafc; font-size: 1.3rem; font-weight: bold; margin-bottom: 15px; }
    .conflict-box {
        background-color: #fee2e2; border: 2px solid #ef4444;
        padding: 15px; border-radius: 8px; color: #b91c1c; margin-bottom: 20px;
    }
    [data-testid="stSidebar"] { background-color: #0f172a !important; }
    .stDateInput label, .stSelectbox label, .stTextInput label { color: #f8fafc !important; }
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

# Stałe dat
PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

# ==========================================
# 3. FUNKCJE DANYCH
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty:
            return pd.DataFrame(columns=["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Uwagi"])
        
        # Czyszczenie nagłówków
        df.columns = [str(c).strip() for c in df.columns]
        
        # Konwersja dat z zabezpieczeniem
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        
        # Usunięcie wierszy całkowicie pustych
        df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
        return df
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        return pd.DataFrame()

df_main = load_data()

def check_conflicts(df, vehicle, start, end, ignore_idx=None):
    if df.empty: return None
    s_dt = pd.to_datetime(start)
    e_dt = pd.to_datetime(end)
    
    temp_df = df.copy()
    if ignore_idx is not None:
        temp_df = temp_df.drop(ignore_idx)
        
    mask = (temp_df['Pojazd'] == vehicle) & (temp_df['Data_Start'] <= e_dt) & (temp_df['Data_Koniec'] >= s_dt)
    conflicts = temp_df[mask]
    return conflicts if not conflicts.empty else None

# ==========================================
# 4. SIDEBAR - DODAWANIE WPISU
# ==========================================
with st.sidebar:
    st.markdown('<p class="sidebar-header">🚚 NOWY TRANSPORT</p>', unsafe_allow_html=True)
    
    with st.form("new_transport_form"):
        f_veh = st.selectbox("Pojazd", ALL_VEHICLES)
        f_proj = st.text_input("Projekt / Event")
        f_driver = st.text_input("Kierowca / Załadunek")
        
        c1, c2 = st.columns(2)
        f_start = c1.date_input("Wyjazd", value=datetime.now())
        f_end = c2.date_input("Powrót", value=datetime.now() + timedelta(days=2))
        
        f_notes = st.text_area("Uwagi (sloty, naczepa, rozładunek)")
        
        # Walidacja kolizji
        conflict_data = check_conflicts(df_main, f_veh, f_start, f_end)
        if conflict_data is not None:
            st.error(f"🛑 KOLIZJA: {conflict_data.iloc[0]['Projekt']}")
            can_submit = False
        else:
            can_submit = True
            
        submit = st.form_submit_button("DODAJ DO GRAFIKU", use_container_width=True)
        
        if submit and can_submit:
            if not f_proj:
                st.warning("Podaj nazwę projektu!")
            else:
                new_row = pd.DataFrame([{
                    "Pojazd": f_veh, "Projekt": f_proj, "Kierowca": f_driver,
                    "Data_Start": f_start.strftime('%Y-%m-%d'),
                    "Data_Koniec": f_end.strftime('%Y-%m-%d'),
                    "Uwagi": f_notes
                }])
                old_df = conn.read(worksheet="FLOTA_SQM", ttl="0")
                updated_df = pd.concat([old_df, new_row], ignore_index=True)
                conn.update(worksheet="FLOTA_SQM", data=updated_df)
                st.success("Dodano pomyślnie!")
                st.rerun()

# ==========================================
# 5. GRAFIK GANTTA
# ==========================================
st.title("📊 GRAFIK TRANSPORTOWY SQM MULTIMEDIA")

# Sekcja alertów o istniejących błędach
if not df_main.empty:
    all_errors = []
    for v in df_main['Pojazd'].unique():
        v_df = df_main[df_main['Pojazd'] == v].sort_values('Data_Start')
        for i in range(len(v_df)-1):
            if v_df.iloc[i]['Data_Koniec'] >= v_df.iloc[i+1]['Data_Start']:
                all_errors.append(f"**{v}**: {v_df.iloc[i]['Projekt']} / {v_df.iloc[i+1]['Projekt']}")
    
    if all_errors:
        with st.expander("⚠️ WYKRYTO KONFLIKTY DAT (KLIKNIJ)"):
            for e in all_errors:
                st.markdown(f'<div class="conflict-box">{e}</div>', unsafe_allow_html=True)

# Suwak czasu
slider_opts = [d.date() for d in pd.date_range("2026-01-01", "2026-12-31")]
view_range = st.select_slider(
    "Zakres podglądu:", options=slider_opts,
    value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=20))
)

if not df_main.empty:
    df_p = df_main.copy()
    df_p['Viz_End'] = df_p['Data_Koniec'] + pd.Timedelta(days=1)
    df_p['Pojazd'] = pd.Categorical(df_p['Pojazd'], categories=ALL_VEHICLES, ordered=True)
    df_p = df_p.sort_values('Pojazd')

    fig = px.timeline(
        df_p, x_start="Data_Start", x_end="Viz_End", y="Pojazd", color="Projekt", text="Projekt",
        hover_data={"Kierowca": True, "Uwagi": True, "Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m", "Viz_End": False},
        template="plotly_white"
    )

    fig.update_traces(
        textposition='inside', insidetextanchor='middle',
        textfont=dict(size=13, family="Arial Black", color="white"),
        marker=dict(line=dict(width=1, color="white"))
    )

    # Oś X
    v_days = pd.date_range(view_range[0], view_range[1])
    t_v, t_t, last_m = [], [], -1
    for d in v_days:
        t_v.append(d)
        is_we, is_ho = d.weekday() >= 5, d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        clr = "#ef4444" if is_ho else ("#94a3b8" if is_we else "#1e293b")
        lbl = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
        if d.month != last_m:
            lbl = f"<span style='color:#0284c7'><b>{PL_MONTHS[d.month]}</b></span><br>{lbl}"
            last_m = d.month
        t_t.append(f"<span style='color:{clr}'>{lbl}</span>")
        if is_we or is_ho:
            fig.add_vrect(x0=d, x1=d+timedelta(days=1), fillcolor="rgba(200,200,200,0.1)", layer="below", line_width=0)

    # Separatory grup
    y_sep = 0
    for g, items in VEHICLE_STRUCTURE.items():
        y_sep += len(items)
        fig.add_hline(y=y_sep - 0.5, line_width=2, line_color="#e2e8f0")

    fig.update_xaxes(tickmode='array', tickvals=t_v, ticktext=t_t, side="top", range=[view_range[0], view_range[1]])
    fig.update_yaxes(autorange="reversed", title="")
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_color="red", line_dash="dot")
    fig.update_layout(height=1200, margin=dict(l=10, r=10, t=110, b=10), showlegend=False)

    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. PANEL EDYCJI (ROZWIĄZANIE BŁĘDU)
# ==========================================
st.markdown("---")
st.subheader("📝 MASOWA EDYCJA BAZY")

with st.expander("Otwórz edytor (Excel Mode)"):
    if not df_main.empty:
        # KLUCZOWE ROZWIĄZANIE BŁĘDU:
        # Konwertujemy kolumny na konkretne typy przed przekazaniem do data_editor
        df_to_edit = df_main.copy()
        
        # Upewniamy się, że daty są obiektami datetime (nie stringami)
        df_to_edit['Data_Start'] = pd.to_datetime(df_to_edit['Data_Start']).dt.date
        df_to_edit['Data_Koniec'] = pd.to_datetime(df_to_edit['Data_Koniec']).dt.date
        
        # Konfiguracja edytora z jawnym mapowaniem typów
        try:
            edited_df = st.data_editor(
                df_to_edit,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_VEHICLES, required=True),
                    "Projekt": st.column_config.TextColumn("Projekt", required=True),
                    "Kierowca": st.column_config.TextColumn("Kierowca / Załadunek"),
                    "Data_Start": st.column_config.DateColumn("Wyjazd", format="YYYY-MM-DD", required=True),
                    "Data_Koniec": st.column_config.DateColumn("Powrót", format="YYYY-MM-DD", required=True),
                    "Uwagi": st.column_config.TextColumn("Uwagi Logistyczne")
                }
            )
            
            if st.button("💾 ZAPISZ ZMIANY W ARKUSZU"):
                # Konwersja z powrotem na string do zapisu w Google Sheets
                save_df = edited_df.copy()
                save_df['Data_Start'] = save_df['Data_Start'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x)
                save_df['Data_Koniec'] = save_df['Data_Koniec'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x)
                
                conn.update(worksheet="FLOTA_SQM", data=save_df)
                st.success("Zsynchronizowano z Google Sheets!")
                st.rerun()
                
        except Exception as e:
            st.error(f"Błąd edytora: {e}")
            st.info("Spróbuj odświeżyć stronę lub sprawdź czy w arkuszu Google nie ma błędnych dat.")
    else:
        st.info("Brak danych do edycji.")

# Pełna długość kodu: ~335 linii.
