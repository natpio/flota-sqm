import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="FLOTA SQM 2026", layout="wide", page_icon="🚚")

# Słowniki pomocnicze (Polska Lokalizacja)
PL_MONTHS = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 
             7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
PL_WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
POLISH_HOLIDAYS = ["2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06", "2026-05-01", 
                   "2026-05-03", "2026-06-04", "2026-08-15", "2026-11-01", "2026-11-11", 
                   "2026-12-25", "2026-12-26"]

# --- 2. PEŁNA STRUKTURA FLOTY ---
# Musi być identyczna z tym, co wpisujesz w Google Sheets
VEHICLE_STRUCTURE = {
    "OSOBÓWKI": [
        "01 – Caravelle – PO8LC63", "Caravelle PY6872M - nowa", "03 – Dacia Duster (biedak) – WE5A723",
        "04 – Dacia Jogger – WH6802A", "06 – Dacia Duster – WH7087A ex T Białek", "FORD Transit Connect PY54635",
        "FORD Transit Connect PY54636 BCN", "FORD Transit Connect PY54637", "Chrysler Pacifica PY04266 - MBanasiak",
        "05 – Dacia Duster – WH7083A B.Krauze", "02 – Dacia Duster – WE6Y368 (WYPAS) Marcin N",
        "Seat Ateca WZ445HU Dynasiuk", "Seat Ateca WZ446HU- PM"
    ],
    "BUSY": [
        "25 – Jumper – PY22952", "24 – Jumper – PY22954", "BOXER - PO 5VT68", "BOXER - WZ213GF",
        "BOXER - WZ214GF", "BOXER - WZ215GF", "OPEL DW4WK43", "BOXER (WYPAS) DW7WE24",
        "OPEL wysoki DW4WK45", "BOXER DW9WK54 wysoki", "OPEL DW9WK53"
    ],
    "CIĘŻARÓWKI / TIR": [
        "31 -TIR PZ1V388/PZ2K300 STABLEWSKI", "TIR 2 - WZ654FT/PZ2H972 KOGUS",
        "TIR 3- PNT3530A/PZ4U343 DANIELAK", "44 - SOLO PY 73262", "45 - PY1541M + przyczepa"
    ],
    "SPEDYCJA / RENTAL": [
        "SPEDYCJA 1", "SPEDYCJA 2", "SPEDYCJA 3", "SPEDYCJA 4", "SPEDYCJA 5", "AUTO RENTAL"
    ],
    "MIESZKANIA BCN": [
        "MIESZKANIE BCN - TORRASA", "MIESZKANIE BCN - ARGENTINA (PM)"
    ]
}

# Lista wszystkich pojazdów do sortowania osi Y
ALL_VEHICLES_SORTED = []
for group in VEHICLE_STRUCTURE.values():
    ALL_VEHICLES_SORTED.extend(group)

# --- 3. POŁĄCZENIE I POBIERANIE DANYCH ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Pobranie surowych danych
        df = conn.read(worksheet="FLOTA_SQM", ttl="0")
        if df.empty:
            return pd.DataFrame()
        
        # Czyszczenie i konwersja
        df = df.dropna(subset=['Pojazd', 'Data_Start', 'Data_Koniec']).copy()
        
        # Kluczowe: Konwersja dat na format datetime dla Plotly
        df['Data_Start'] = pd.to_datetime(df['Data_Start'], errors='coerce')
        df['Data_Koniec'] = pd.to_datetime(df['Data_Koniec'], errors='coerce')
        
        # Usunięcie wierszy, gdzie daty się nie skonwertowały
        df = df.dropna(subset=['Data_Start', 'Data_Koniec'])
        
        # Konwersja nazw pojazdów na typ kategoryczny, aby wymusić kolejność na osi Y
        df['Pojazd'] = pd.Categorical(df['Pojazd'], categories=ALL_VEHICLES_SORTED, ordered=True)
        
        return df
    except Exception as e:
        st.error(f"Błąd podczas ładowania arkusza: {e}")
        return pd.DataFrame()

df = load_data()

# --- 4. SIDEBAR - DODAWANIE WPISÓW ---
with st.sidebar:
    st.header("⚙️ Nowy Projekt / Event")
    with st.form("add_form", clear_on_submit=True):
        f_pojazd = st.selectbox("Wybierz Pojazd / Zasób", ALL_VEHICLES_SORTED)
        f_projekt = st.text_input("Nazwa Eventu (wyświetlana na pasku)")
        f_kierowca = st.text_input("Kierowca / Najemca")
        
        c1, c2 = st.columns(2)
        f_start = c1.date_input("Wyjazd", value=datetime.now().date())
        f_end = c2.date_input("Powrót", value=(datetime.now() + timedelta(days=2)).date())
        
        if st.form_submit_button("DODAJ DO GRAFIKU"):
            new_row = pd.DataFrame([{
                "Pojazd": f_pojazd, 
                "Projekt": f_projekt, 
                "Kierowca": f_kierowca,
                "Data_Start": f_start.strftime('%Y-%m-%d'), 
                "Data_Koniec": f_end.strftime('%Y-%m-%d')
            }])
            # Pobranie aktualnych danych, doklejenie i wysyłka
            current_data = conn.read(worksheet="FLOTA_SQM", ttl="0")
            updated_data = pd.concat([current_data, new_row], ignore_index=True)
            conn.update(worksheet="FLOTA_SQM", data=updated_data)
            st.success("Zapisano pomyślnie!")
            st.rerun()

# --- 5. GŁÓWNY PANEL - WYKRES GANTTA ---
st.title("🚚 GRAFIK FLOTY SQM 2026")

# Suwak zakresu dat
slider_options = [d.date() for d in pd.date_range(start="2026-01-01", end="2026-12-31", freq='D')]
selected_range = st.select_slider(
    "Ustaw zakres podglądu miesięcy (suwak do końca roku):", 
    options=slider_options, 
    value=(datetime.now().date() - timedelta(days=2), datetime.now().date() + timedelta(days=21))
)
start_view, end_view = selected_range

if not df.empty:
    # Przygotowanie danych do wizualizacji
    df_plot = df.copy()
    
    # Plotly Timeline pokazuje czas DO - musimy dodać 1 dzień, żeby pasek wypełnił ostatni dzień pracy
    df_plot['Data_Koniec_Viz'] = df_plot['Data_Koniec'] + pd.Timedelta(days=1)
    
    # Sortowanie danych
    df_plot = df_plot.sort_values('Pojazd')

    # Tworzenie wykresu
    fig = px.timeline(
        df_plot, 
        x_start="Data_Start", 
        x_end="Data_Koniec_Viz", 
        y="Pojazd", 
        color="Projekt",
        text="Projekt", # To wyświetla tekst na pasku
        hover_data={"Data_Start": "|%d.%m", "Data_Koniec": "|%d.%m", "Kierowca": True, "Data_Koniec_Viz": False},
        template="plotly_white"
    )

    # WIELKOŚĆ I WYRAŹNOŚĆ NAPISÓW NA PASKACH
    fig.update_traces(
        textposition='inside', 
        insidetextanchor='middle',
        textfont=dict(size=14, family="Arial Black", color="white"),
        marker=dict(line=dict(width=1, color="white")) # Obramowanie paska
    )

    # KONFIGURACJA OSI X (DATY I WEEKENDY)
    current_days = pd.date_range(start=start_view, end=end_view)
    tick_vals, tick_text, last_m = [], [], -1

    for d in current_days:
        tick_vals.append(d)
        is_we = d.weekday() >= 5
        is_hol = d.strftime('%Y-%m-%d') in POLISH_HOLIDAYS
        
        color = "black"
        if is_hol: color = "red"
        elif is_we: color = "#999999"

        label = f"<b>{d.day}</b><br>{PL_WEEKDAYS[d.weekday()]}"
        if d.month != last_m:
            label = f"<span style='color:blue'><b>{PL_MONTHS[d.month]}</b></span><br>{label}"
            last_m = d.month
            
        tick_text.append(f"<span style='color:{color}'>{label}</span>")
        
        # Zaznaczanie weekendów i świąt w tle
        if is_we or is_hol:
            fig.add_vrect(x0=d, x1=d + timedelta(days=1), fillcolor="rgba(200,200,200,0.2)", layer="below", line_width=0)

    # LINIE ODDZIELAJĄCE TYPY POJAZDÓW
    current_y_pos = 0
    for group_name, vehicles in VEHICLE_STRUCTURE.items():
        current_y_pos += len(vehicles)
        fig.add_hline(y=current_y_pos - 0.5, line_width=2, line_color="#cccccc")

    # Ustawienia osi i layoutu
    fig.update_xaxes(
        tickmode='array', 
        tickvals=tick_vals, 
        ticktext=tick_text, 
        side="top", 
        range=[pd.to_datetime(start_view), pd.to_datetime(end_view)]
    )
    
    fig.update_yaxes(
        autorange="reversed", # Najważniejsze, by kolejność była zgodna z ALL_VEHICLES_SORTED
        title="",
        showgrid=True,
        gridcolor="#f0f0f0"
    )

    # Linia DZISIAJ
    fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=3, line_color="red", line_dash="dash")

    fig.update_layout(
        height=1200, # Odpowiednia wysokość dla dużej liczby aut
        margin=dict(l=10, r=10, t=120, b=10),
        showlegend=False,
        plot_bgcolor="white"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Brak danych do wyświetlenia. Dodaj pierwszy event w panelu bocznym.")

# --- 6. TABELA EDYCJI ---
st.markdown("---")
with st.expander("📝 Lista i szybka edycja danych"):
    if not df.empty:
        # Przygotowanie kopii do edycji
        df_edit = df.copy()
        df_edit['Data_Start'] = df_edit['Data_Start'].dt.date
        df_edit['Data_Koniec'] = df_edit['Data_Koniec'].dt.date
        
        edited = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
        if st.button("ZAPISZ ZMIANY W ARKUSZU"):
            conn.update(worksheet="FLOTA_SQM", data=edited)
            st.success("Dane zsynchronizowane z Google Sheets!")
            st.rerun()
