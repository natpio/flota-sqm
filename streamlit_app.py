import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

# ==========================================
# 1. KONFIGURACJA ŚRODOWISKA (UI/UX)
# ==========================================
st.set_page_config(
    page_title="LOGISTYKA SQM - PANEL OPERACYJNY",
    layout="wide",
    page_icon="🚚"
)

# Profesjonalna stylizacja interfejsu logistycznego
st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    /* Stylizacja Sidebaru dla lepszej widoczności w halach targowych */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        min-width: 420px !important;
    }
    .stSelectbox label, .stTextInput label, .stDateInput label, .stTextArea label {
        color: #f8fafc !important;
        font-weight: bold !important;
        font-size: 1rem !important;
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
    /* Powiększenie czcionek na wykresie Gantta */
    .plot-container {
        border-radius: 12px;
        overflow: hidden;
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

# Stałe kalendarzowe (Polska 2026)
PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

# ==========================================
# 3. OBSŁUGA BAZY DANYCH (GSHEETS)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_latest_data():
    try:
        # Odczyt bez cache, aby widzieć zmiany natychmiast
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty:
            return pd.DataFrame(columns=["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Uwagi"])
        
        # Standaryzacja kolumn (usuwanie spacji)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Konwersja dat z zabezpieczeniem przed błędami wprowadzania
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        
        # Usuwamy tylko wiersze, które nie mają kluczowych danych
        df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
        return df
    except Exception as e:
        st.error(f"Błąd krytyczny połączenia: {e}")
        return pd.DataFrame()

df_main = get_latest_data()

# Funkcja weryfikacji dostępności pojazdu
def check_for_conflicts(df, vehicle, start, end, current_idx=None):
    if df.empty: return None
    s_dt = pd.to_datetime(start)
    e_dt = pd.to_datetime(end)
    
    # Kopiujemy dane i opcjonalnie wykluczamy obecnie edytowany wiersz
    temp_df = df.copy()
    if current_idx is not None:
        temp_df = temp_df.drop(current_idx)
        
    mask = (temp_df['Pojazd'] == vehicle) & (temp_df['Data_Start'] <= e_dt) & (temp_df['Data_Koniec'] >= s_dt)
    conflicts = temp_df[mask]
    return conflicts if not conflicts.empty else None

# ==========================================
# 4. PANEL BOCZNY - DODAWANIE TRANSPORTU
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: white;'>🛠️ OPERACJE TRANSPORTOWE</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    with st.form("new_entry_form", clear_on_submit=True):
        v_sel = st.selectbox("Wybierz Pojazd / Naczepę", ALL_VEHICLES)
        p_name = st.text_input("Nazwa Projektu / Eventu")
        k_info = st.text_input("Kierowca / Dane załadunkowe")
        
        col_a, col_b = st.columns(2)
        d_start = col_a.date_input("Data Wyjazdu", value=datetime.now())
        d_end = col_b.date_input("Data Powrotu", value=datetime.now() + timedelta(days=2))
        
        u_notes = st.text_area("Szczegóły (sloty, naczepa, uwagi logistyczne)")
        
        # Wstępna walidacja konfliktu
        conflict_found = check_for_conflicts(df_main, v_sel, d_start, d_end)
        if conflict_found is not None:
            st.error(f"🚨 KONFLIKT: {conflict_found.iloc[0]['Projekt']}")
            
        submit_data = st.form_submit_button("ZAPISZ W HARMONOGRAMIE", use_container_width=True)
        
        if submit_data:
            if not p_name:
                st.warning("Musisz podać nazwę projektu!")
            elif conflict_found is not None:
                st.error("Nie można zapisać - popraw daty lub zmień pojazd.")
            else:
                # Przygotowanie wiersza do zapisu
                new_row = pd.DataFrame([{
                    "Pojazd": v_sel, "Projekt": p_name, "Kierowca": k_info,
                    "Data_Start": d_start.strftime('%Y-%m-%d'),
                    "Data_Koniec": d_end.strftime('%Y-%m-%d'),
                    "Uwagi": u_notes
                }])
                
                # Pobranie aktualnego stanu i update
                current_db = conn.read(worksheet="FLOTA_SQM", ttl="0")
                updated_db = pd.concat([current_db, new_row], ignore_index=True)
                conn.update(worksheet="FLOTA_SQM", data=updated_db)
                st.success("Zapisano pomyślnie!")
                st.rerun()

# ==========================================
# 5. WIZUALIZACJA - GRAFIK OPERACYJNY GANTTA
# ==========================================
st.title("🚚 HARMONOGRAM LOGISTYCZNY SQM MULTIMEDIA")

# Wyświetlanie istniejących konfliktów w bazie danych
if not df_main.empty:
    all_conflicts = []
    for veh in df_main['Pojazd'].unique():
        v_subset = df_main[df_main['Pojazd'] == veh].sort_values('Data_Start')
        for i in range(len(v_subset)-1):
            if v_subset.iloc[i]['Data_Koniec'] >= v_subset.iloc[i+1]['Data_Start']:
                all_conflicts.append(f"<b>{veh}</b>: {v_subset.iloc[i]['Projekt']} i {v_subset.iloc[i+1]['Projekt']}")
    
    if all_conflicts:
        with st.expander("⚠️ WYKRYTO KONFLIKTY DAT W BAZIE"):
            for c in all_conflicts:
                st.markdown(f'<div class="conflict-alert">{c}</div>', unsafe_allow_html=True)

# Suwak zakresu czasu (Widok)
date_options = [d.date() for d in pd.date_range("2026-01-01", "2026-12-31")]
selected_range = st.select_slider(
    "Ustaw zakres podglądu:",
    options=date_options,
    value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=21))
)

if not df_main.empty:
    df_p = df_main.copy()
    # Korekta dla Plotly - paski muszą kończyć się na końcu dnia
    df_p['Viz_End'] = df_p['Data_Koniec'] + pd.Timedelta(days=1)
    
    # Sortowanie zgodne z hierarchią firmy
    df_p['Pojazd'] = pd.Categorical(df_p['Pojazd'], categories=ALL_VEHICLES, ordered=True)
    df_p = df_p.sort_values('Pojazd')

    fig = px.timeline(
        df_p, x_start="Data_Start", x_end="Viz_End", y="Pojazd", color="Projekt", text="Projekt",
        hover_data={"Kierowca": True, "Uwagi": True, "Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m"},
        template="plotly_white"
    )

    fig.update_traces(
        textposition='inside', insidetextanchor='middle',
        textfont=dict(size=14, family="Arial Black", color="white"),
        marker=dict(line=dict(width=1, color="white"))
    )

    # Budowa osi X z polskim nazewnictwem i świętami
    view_days = pd.date_range(selected_range[0], selected_range[1])
    t_vals, t_text, last_m = [], [], -1
    for d in view_days:
        t_vals.append(d)
        is_we, is_ho = d.weekday() >= 5, d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        clr = "#ef4444" if is_ho else ("#94a3b8" if is_we else "#1e293b")
        lbl = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
        
        if d.month != last_m:
            lbl = f"<span style='color:#2563eb'><b>{PL_MONTHS[d.month]}</b></span><br>{lbl}"
            last_m = d.month
            
        t_text.append(f"<span style='color:{clr}'>{lbl}</span>")
        if is_we or is_ho:
            fig.add_vrect(x0=d, x1=d+timedelta(days=1), fillcolor="rgba(0,0,0,0.06)", layer="below", line_width=0)

    # Separatory grup (Osobówki/Busy/Ciężarówki)
    y_mark = 0
    for group, items in VEHICLE_STRUCTURE.items():
        y_mark += len(items)
        fig.add_hline(y=y_mark - 0.5, line_width=1.5, line_color="#cbd5e1")

    fig.update_xaxes(tickmode='array', tickvals=t_vals, ticktext=t_text, side="top", range=[selected_range[0], selected_range[1]])
    fig.update_yaxes(autorange="reversed", title="")
    # Linia czasu "DZISIAJ"
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_color="#ef4444", line_dash="dash")
    
    fig.update_layout(height=1250, margin=dict(l=10, r=10, t=110, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. MASOWA EDYCJA - ROZWIĄZANIE BŁĘDÓW
# ==========================================
st.markdown("---")
st.subheader("⚙️ MODUŁ EDYCJI I ZARZĄDZANIA BAZĄ")

with st.expander("Otwórz Panel Edycji Masowej (Excel Mode)"):
    if not df_main.empty:
        # KLUCZOWE: Konwersja na typy proste przed edytorem, aby uniknąć StreamlitAPIException
        df_for_edit = df_main.copy()
        df_for_edit['Data_Start'] = df_for_edit['Data_Start'].dt.date
        df_for_edit['Data_Koniec'] = df_for_edit['Data_Koniec'].dt.date
        
        try:
            edited_results = st.data_editor(
                df_for_edit,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_VEHICLES, required=True),
                    "Projekt": st.column_config.TextColumn("Projekt", required=True),
                    "Data_Start": st.column_config.DateColumn("Wyjazd", format="YYYY-MM-DD", required=True),
                    "Data_Koniec": st.column_config.DateColumn("Powrót", format="YYYY-MM-DD", required=True),
                    "Uwagi": st.column_config.TextColumn("Szczegóły Logistyczne")
                }
            )
            
            if st.button("💾 ZAPISZ ZMIANY W CHMURZE", use_container_width=True):
                # Konwersja powrotna na stringi dla zapisu w GSheets
                save_ready = edited_results.copy()
                save_ready['Data_Start'] = save_ready['Data_Start'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x)
                save_ready['Data_Koniec'] = save_ready['Data_Koniec'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x)
                
                conn.update(worksheet="FLOTA_SQM", data=save_ready)
                st.success("Baza danych zaktualizowana pomyślnie.")
                st.rerun()
                
        except Exception as editor_err:
            st.error(f"Wystąpił błąd podczas edycji danych: {editor_err}")
            st.info("Najczęstsza przyczyna: Niepoprawny format daty w arkuszu Google. Sprawdź czy wszystkie daty w Excelu są w formacie RRRR-MM-DD.")
    else:
        st.info("Baza danych jest obecnie pusta. Dodaj pierwszy transport w panelu bocznym.")

# KONIEC KODU: 345 LINII.
