import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURACJA STRONY I STYLE CSS
# ==========================================
st.set_page_config(
    page_title="SYSTEM LOGISTYKI FLOTY SQM",
    layout="wide",
    page_icon="🚚"
)

# Rozbudowane style dla interfejsu transportowego
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    
    /* Stylizacja nagłówków grup w tabeli i na wykresie */
    .group-header {
        background-color: #1d3557;
        color: white;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        margin-top: 20px;
    }
    
    /* Customizacja osi X - dni tygodnia */
    [data-testid="stPlotlyChart"] .xtick text { 
        font-family: 'Verdana', sans-serif !important;
        font-size: 10px !important;
        font-weight: bold !important;
    }
    
    /* Styl dla formularza bocznego */
    section[data-testid="stSidebar"] {
        background-color: #f1f4f9;
        width: 400px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. STAŁE, DATY I POLSKA LOKALIZACJA
# ==========================================
PL_MONTHS = {
    1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 
    5: "MAJ", 6: "CZERWIEC", 7: "LIPIEC", 8: "SIERPIEŃ", 
    9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"
}

PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]

# Święta państwowe 2026 (Logistyka musi je widzieć)
POLISH_HOLIDAYS = {
    "2026-01-01": "Nowy Rok",
    "2026-01-06": "Trzech Króli",
    "2026-04-05": "Wielkanoc",
    "2026-04-06": "Poniedziałek Wielkanocny",
    "2026-05-01": "Święto Pracy",
    "2026-05-03": "Święto Konstytucji",
    "2026-05-24": "Zesłanie Ducha Św.",
    "2026-06-04": "Boże Ciało",
    "2026-08-15": "Wniebowzięcie / Wojska Polskiego",
    "2026-11-01": "Wszystkich Świętych",
    "2026-11-11": "Święto Niepodległości",
    "2026-12-25": "Boże Narodzenie",
    "2026-12-26": "Drugi Dzień Świąt"
}

# ==========================================
# 3. DEFINICJA PEŁNEJ STRUKTURY FLOTY
# ==========================================
VEHICLE_STRUCTURE = {
    "OSOBÓWKI": [
        "01 – Caravelle – PO8LC63",
        "Caravelle PY6872M - nowa",
        "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A",
        "06 – Dacia Duster – WH7087A ex T Białek",
        "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN",
        "FORD Transit Connect PY54637",
        "Chrysler Pacifica PY04266 - MBanasiak",
        "05 – Dacia Duster – WH7083A B.Krauze",
        "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "Seat Ateca WZ445HU Dynasiuk",
        "Seat Ateca WZ446HU- PM"
    ],
    "BUSY": [
        "25 – Jumper – PY22952",
        "24 – Jumper – PY22954",
        "BOXER - PO 5VT68",
        "BOXER - WZ213GF",
        "BOXER - WZ214GF",
        "BOXER - WZ215GF",
        "OPEL DW4WK43",
        "BOXER (WYPAS) DW7WE24",
        "OPEL wysoki DW4WK45",
        "BOXER DW9WK54 wysoki",
        "OPEL DW9WK53"
    ],
    "CIĘŻARÓWKI / TIR": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI",
        "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK",
        "44 - SOLO PY 73262",
        "45 - PY1541M + przyczepa"
    ],
    "SPEDYCJA / RENTAL": [
        "SPEDYCJA 1", "SPEDYCJA 2", "SPEDYCJA 3", 
        "SPEDYCJA 4", "SPEDYCJA 5", "AUTO RENTAL"
    ],
    "MIESZKANIA BCN": [
        "MIESZKANIE BCN - TORRASA",
        "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}

# Lista płaska do walidacji i selectboxów
SORTED_VEHICLE_LIST = []
for category, vehicles in VEHICLE_STRUCTURE.items():
    SORTED_VEHICLE_LIST.extend(vehicles)

# ==========================================
# 4. OBSŁUGA POŁĄCZENIA I DANYCH
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def calculate_auto_status(start_date, end_date):
    """Przelicza status transportu w oparciu o datę systemową"""
    today = datetime.now().date()
    try:
        s = start_date.date() if isinstance(start_date, datetime) else start_date
        e = end_date.date() if isinstance(end_date, datetime) else end_date
        if today < s:
            return "⏳ Oczekuje"
        elif s <= today <= e:
            return "🚚 W trasie"
        else:
            return "✅ Wróciło"
    except:
        return "Błąd daty"

def fetch_and_clean_data():
    """Pobiera i formatuje dane z Google Sheets"""
    df = conn.read(worksheet="FLOTA_SQM", ttl="0")
    if df.empty:
        return pd.DataFrame()
    
    # Czyszczenie wierszy bez kluczowych danych
    df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec']).copy()
    
    # Konwersja dat z obsługą błędów
    df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
    df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
    df = df.dropna(subset=['Data_Start', 'Data_Koniec'])
    
    # Dodanie statusu dynamicznego
    df['Status'] = df.apply(lambda x: calculate_auto_status(x['Data_Start'], x['Data_Koniec']), axis=1)
    
    # Wymuszenie kolejności pojazdów zgodnej ze strukturą firmy
    df['Pojazd'] = pd.Categorical(df['Pojazd'], categories=SORTED_VEHICLE_LIST, ordered=True)
    return df

# Wczytanie danych
df_raw = fetch_and_clean_data()

# ==========================================
# 5. SIDEBAR - FORMULARZ LOGISTYKA
# ==========================================
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/uploads/2019/02/logo-sqm.png", width=150) # Przykładowe logo
    st.header("📝 NOWY TRANSPORT / SLOT")
    
    with st.form("transport_form", clear_on_submit=True):
        selected_car = st.selectbox("Pojazd / Zasób", SORTED_VEHICLE_LIST)
        project_name = st.text_input("Nazwa Eventu / Projektu")
        driver = st.text_input("Kierowca / Załadunek")
        
        col_d1, col_d2 = st.columns(2)
        date_in = col_d1.date_input("Wyjazd", value=datetime.now().date())
        date_out = col_d2.date_input("Powrót", value=(datetime.now() + timedelta(days=2)).date())
        
        notes = st.text_area("Uwagi logistyczne (np. sloty, nr naczepy)")
        
        submit = st.form_submit_button("DODAJ DO HARMONOGRAMU")
        
        if submit:
            if not project_name:
                st.error("Podaj nazwę projektu!")
            else:
                new_data = pd.DataFrame([{
                    "Pojazd": selected_car,
                    "Projekt": project_name,
                    "Kierowca": driver,
                    "Data_Start": date_in.strftime('%Y-%m-%d'),
                    "Data_Koniec": date_out.strftime('%Y-%m-%d'),
                    "Uwagi": notes
                }])
                
                # Aktualizacja bazy
                current_df = conn.read(worksheet="FLOTA_SQM", ttl="0")
                updated_df = pd.concat([current_df, new_data], ignore_index=True)
                conn.update(worksheet="FLOTA_SQM", data=updated_df)
                st.success("Zapisano pomyślnie!")
                st.rerun()

# ==========================================
# 6. GŁÓWNY PANEL WIZUALIZACJI
# ==========================================
st.title("🚚 GRAFIK OPERACYJNY FLOTY SQM 2026")

# Selektor zakresu (Slider)
slider_dates = [d.date() for d in pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')]
default_start = datetime.now().date() - timedelta(days=2)
default_end = datetime.now().date() + timedelta(days=21)

selected_range = st.select_slider(
    "Ustaw zakres podglądu osi czasu:",
    options=slider_dates,
    value=(default_start, default_end)
)
view_start, view_end = selected_range

if not df_raw.empty:
    # Przygotowanie kopii do wykresu
    df_viz = df_raw.copy()
    
    # Plotly Timeline potrzebuje daty końcowej o 1 dzień większej, aby zamalować cały dzień
    df_viz['Data_Koniec_Viz'] = df_viz['Data_Koniec'] + pd.Timedelta(days=1)
    
    # Tworzenie wykresu Gantta
    fig = px.timeline(
        df_viz,
        x_start="Data_Start",
        x_end="Data_Koniec_Viz",
        y="Pojazd",
        color="Projekt",
        text="Projekt",
        hover_data={
            "Status": True,
            "Kierowca": True,
            "Data_Start": "|%d.%m.%Y",
            "Data_Koniec": "|%d.%m.%Y",
            "Data_Koniec_Viz": False
        },
        template="plotly_white"
    )

    # --- STYLIZACJA WYKRESU (WYRAŹNE NAPISY) ---
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=14, family="Arial Black", color="white"),
        marker=dict(line=dict(width=1, color='white'))
    )

    # --- GENEROWANIE OSI X (DATY, MIESIĄCE, ŚWIĘTA) ---
    timeline_days = pd.date_range(start=view_start, end=view_end)
    t_vals, t_text, last_month = [], [], -1

    for day in timeline_days:
        t_vals.append(day)
        day_iso = day.strftime('%Y-%m-%d')
        is_holiday = day_iso in POLISH_HOLIDAYS
        is_weekend = day.weekday() >= 5 # 5=Sobota, 6=Niedziela
        
        # Kolorystyka etykiety
        font_color = "black"
        if is_holiday: font_color = "#d62828"
        elif is_weekend: font_color = "#6d6d6d"
        
        # Budowa etykiety: Dzień + Skrót dnia
        day_label = f"<b>{day.day}</b><br>{PL_WEEKDAYS[day.weekday()]}"
        
        # Jeśli zmienia się miesiąc, dodaj nagłówek miesiąca
        if day.month != last_month:
            day_label = f"<span style='color:#1d3557'><b>{PL_MONTHS[day.month]}</b></span><br>" + day_label
            last_month = day.month
            
        t_text.append(f"<span style='color:{font_color}'>{day_label}</span>")

        # Podświetlenie tła (Weekendy i Święta)
        if is_weekend or is_holiday:
            fig.add_vrect(
                x0=day, x1=day + timedelta(days=1),
                fillcolor="rgba(200, 200, 200, 0.2)" if is_weekend else "rgba(214, 40, 40, 0.1)",
                layer="below", line_width=0
            )

    # --- LINIE ODDZIELAJĄCE TYPY TRANSPORTU ---
    current_y = 0
    for group_name, vehicles in VEHICLE_STRUCTURE.items():
        current_y += len(vehicles)
        fig.add_hline(y=current_y - 0.5, line_width=2, line_color="#dee2e6")

    # Finalna konfiguracja layoutu
    fig.update_xaxes(
        tickmode='array',
        tickvals=t_vals,
        ticktext=t_text,
        side="top",
        range=[pd.to_datetime(view_start), pd.to_datetime(view_end)],
        gridcolor="#f1f3f5"
    )
    
    fig.update_yaxes(
        autorange="reversed",
        title="",
        showgrid=True,
        gridcolor="#f1f3f5"
    )

    # Linia CZASU RZECZYWISTEGO (DZISIAJ)
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=3, line_color="#e63946", line_dash="dash")

    fig.update_layout(
        height=1200, # Wysoki wykres, by uniknąć ścisku
        margin=dict(l=10, r=10, t=120, b=10),
        showlegend=False,
        plot_bgcolor="white"
    )

    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. PANEL EDYCJI DANYCH (TABELA)
# ==========================================
st.markdown("---")
st.subheader("📋 REJESTR TRANSPORTÓW I EDYCJA")

with st.expander("Kliknij, aby otworzyć edytor bazy danych"):
    if not df_raw.empty:
        # Przygotowanie do edytora (usuwamy kolumny pomocnicze)
        df_editor = df_raw.copy()
        df_editor['Data_Start'] = df_editor['Data_Start'].dt.date
        df_editor['Data_Koniec'] = df_editor['Data_Koniec'].dt.date
        
        # Edytor tabelaryczny
        response = st.data_editor(
            df_editor,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Pojazd": st.column_config.SelectboxColumn("Pojazd", options=SORTED_VEHICLE_LIST),
                "Status": st.column_config.TextColumn("Status", disabled=True),
            }
        )
        
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY"):
            # Przed zapisem usuwamy kolumnę Status, bo jest wyliczana dynamicznie
            df_to_save = response.drop(columns=['Status']) if 'Status' in response else response
            conn.update(worksheet="FLOTA_SQM", data=df_to_save)
            st.success("Baza danych zaktualizowana!")
            st.rerun()
    else:
        st.info("Brak wpisów w bazie danych.")
