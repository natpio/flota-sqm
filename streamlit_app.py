import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURACJA ŚRODOWISKA
# ==========================================
st.set_page_config(
    page_title="LOGISTYKA SQM",
    layout="wide",
    page_icon="🚚"
)

# Czysty, czytelny styl bez zbędnych bajerów
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
# 2. STRUKTURA FLOTY (ZGODNIE Z TWOIM EXCELEM)
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
    "SPEDYCJA / RENTAL": [
        "SPEDYCJA 1", "SPEDYCJA 2", "SPEDYCJA 3", "SPEDYCJA 4", "AUTO RENTAL"
    ]
}

ALL_VEHICLES = [v for sub in VEHICLE_STRUCTURE.values() for v in sub]

# Tłumaczenia kalendarza
PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

# ==========================================
# 3. POŁĄCZENIE I DANE
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data_v3():
    try:
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty:
            return pd.DataFrame(columns=["Pojazd", "Projekt", "Kierowca", "Data_Start", "Data_Koniec", "Uwagi", "Status"])
        
        # Standaryzacja i rygorystyczna naprawa typów danych
        df.columns = [str(c).strip() for c in df.columns]
        for col in ["Uwagi", "Kierowca", "Projekt", "Pojazd"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace(['nan', 'None', 'NAT', 'NaN'], '')
        
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec'])
        
        # Wyliczanie statusu (logika operacyjna)
        def calc_status(row):
            today = datetime.now().date()
            s = row['Data_Start'].date()
            e = row['Data_Koniec'].date()
            if today < s: return "📅 PLANOWANY"
            if s <= today <= e: return "🚚 W TRASIE"
            return "✅ ZAKOŃCZONY"
            
        df['Status'] = df.apply(calc_status, axis=1)
        return df
    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")
        return pd.DataFrame()

df_main = get_data_v3()

# ==========================================
# 4. SIDEBAR - DODAWANIE
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: white;'>➕ NOWY TRANSPORT</h2>", unsafe_allow_html=True)
    with st.form("add_form", clear_on_submit=True):
        f_v = st.selectbox("Pojazd", ALL_VEHICLES)
        f_p = st.text_input("Projekt")
        f_k = st.text_input("Kierowca")
        f_s = st.date_input("Start")
        f_e = st.date_input("Koniec", value=datetime.now() + timedelta(days=2))
        f_u = st.text_area("Uwagi")
        
        if st.form_submit_button("DODAJ DO ARKUSZA", use_container_width=True):
            if f_p:
                new_data = pd.DataFrame([{
                    "Pojazd": f_v, "Projekt": f_p, "Kierowca": f_k,
                    "Data_Start": f_s.strftime('%Y-%m-%d'),
                    "Data_Koniec": f_e.strftime('%Y-%m-%d'),
                    "Uwagi": f_u
                }])
                old = conn.read(worksheet="FLOTA_SQM", ttl="0")
                conn.update(worksheet="FLOTA_SQM", data=pd.concat([old, new_data], ignore_index=True))
                st.rerun()

# ==========================================
# 5. WIZUALIZACJA GANTT
# ==========================================
st.title("🚚 HARMONOGRAM FLOTY SQM")

# Suwak widoku
sel_range = st.select_slider(
    "Zakres podglądu:",
    options=[d.date() for d in pd.date_range("2026-01-01", "2026-12-31")],
    value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=21))
)

if not df_main.empty:
    df_v = df_main.copy()
    df_v['Plot_End'] = df_v['Data_Koniec'] + pd.Timedelta(days=1)
    df_v['Pojazd'] = pd.Categorical(df_v['Pojazd'], categories=ALL_VEHICLES, ordered=True)
    df_v = df_v.sort_values('Pojazd')

    fig = px.timeline(
        df_v, x_start="Data_Start", x_end="Plot_End", y="Pojazd", color="Status", text="Projekt",
        color_discrete_map={"📅 PLANOWANY": "#94a3b8", "🚚 W TRASIE": "#ef4444", "✅ ZAKOŃCZONY": "#22c55e"},
        template="plotly_white"
    )

    # Stylizacja osi i separatorów (Zgodnie z Twoim Excel)
    fig.update_traces(textposition='inside', insidetextanchor='middle', textfont=dict(size=14, family="Arial Black", color="white"))
    
    t_days = pd.date_range(sel_range[0], sel_range[1])
    tx, tt, lm = [], [], -1
    for d in t_days:
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

    y_pos = 0
    for g, items in VEHICLE_STRUCTURE.items():
        y_pos += len(items)
        fig.add_hline(y=y_pos - 0.5, line_width=1.5, line_color="#cbd5e1")

    fig.update_xaxes(tickmode='array', tickvals=tx, ticktext=tt, side="top", range=[sel_range[0], sel_range[1]])
    fig.update_yaxes(autorange="reversed", title="")
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_color="red", line_dash="dash")
    fig.update_layout(height=1300, margin=dict(l=10, r=10, t=110, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. PANEL EDYCJI (NAPRAWA BŁĘDÓW)
# ==========================================
st.markdown("---")
st.subheader("⚙️ MODUŁ EDYCJI")

if not df_main.empty:
    df_ed = df_main.copy()
    df_ed['Data_Start'] = df_ed['Data_Start'].dt.date
    df_ed['Data_Koniec'] = df_ed['Data_Koniec'].dt.date
    for c in ["Uwagi", "Kierowca", "Projekt"]:
        df_ed[c] = df_ed[c].astype(str)

    edited = st.data_editor(
        df_ed,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Status": st.column_config.TextColumn("Status (Auto)", disabled=True),
            "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=ALL_VEHICLES, required=True),
        }
    )
    
    if st.button("💾 ZAPISZ ZMIANY"):
        save = edited.drop(columns=['Status'])
        save['Data_Start'] = save['Data_Start'].apply(lambda x: x.strftime('%Y-%m-%d'))
        save['Data_Koniec'] = save['Data_Koniec'].apply(lambda x: x.strftime('%Y-%m-%d'))
        conn.update(worksheet="FLOTA_SQM", data=save)
        st.success("Gotowe!")
        st.rerun()
