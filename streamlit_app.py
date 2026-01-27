import streamlit as st
import pandas as pd
import plotly.express as px
from st_gsheets_connection import GSheetsConnection
from datetime import date

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Flota SQM – Planowanie",
    layout="wide",
)

SHEET_NAME = "FLOTA_SQM"

STATUS_COLORS = {
    "BCN": "#d81b60",
    "Magazyn": "#fbc02d",
    "Serwis": "#616161",
    "Event": "#1e88e5",
    "Transport": "#43a047",
}

# --------------------------------------------------
# DATA
# --------------------------------------------------
@st.cache_data(ttl=5)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet=SHEET_NAME)

    df["Data_Start"] = pd.to_datetime(df["Data_Start"])
    df["Data_Koniec"] = pd.to_datetime(df["Data_Koniec"])
    df["ID"] = df.index

    return df


def save_data(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet=SHEET_NAME, data=df.drop(columns=["ID"]))


df = load_data()

# --------------------------------------------------
# SIDEBAR – FILTRY
# --------------------------------------------------
st.sidebar.header("🔍 Filtry")

pojazd_f = st.sidebar.multiselect(
    "Pojazd",
    sorted(df["Pojazd"].dropna().unique()),
)

projekt_f = st.sidebar.multiselect(
    "Projekt",
    sorted(df["Projekt"].dropna().unique()),
)

kierowca_f = st.sidebar.multiselect(
    "Kierowca",
    sorted(df["Kierowca"].dropna().unique()),
)

status_f = st.sidebar.multiselect(
    "Status",
    sorted(df["Status"].dropna().unique()),
)

data_od, data_do = st.sidebar.date_input(
    "Zakres dat",
    value=(df["Data_Start"].min().date(), df["Data_Koniec"].max().date()),
)

# --------------------------------------------------
# FILTER LOGIC
# --------------------------------------------------
filtered = df.copy()

if pojazd_f:
    filtered = filtered[filtered["Pojazd"].isin(pojazd_f)]
if projekt_f:
    filtered = filtered[filtered["Projekt"].isin(projekt_f)]
if kierowca_f:
    filtered = filtered[filtered["Kierowca"].isin(kierowca_f)]
if status_f:
    filtered = filtered[filtered["Status"].isin(status_f)]

filtered = filtered[
    (filtered["Data_Start"].dt.date >= data_od)
    & (filtered["Data_Koniec"].dt.date <= data_do)
]

# --------------------------------------------------
# MAIN – GANTT
# --------------------------------------------------
st.title("🚚 Flota SQM – Planowanie")

fig = px.timeline(
    filtered,
    x_start="Data_Start",
    x_end="Data_Koniec",
    y="Pojazd",
    color="Status",
    color_discrete_map=STATUS_COLORS,
    hover_data=["Projekt", "Kierowca", "Uwagi"],
)

fig.update_yaxes(autorange="reversed")
fig.update_layout(
    height=750,
    legend_title_text="Status",
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# TABELA
# --------------------------------------------------
st.subheader("📋 Wpisy")

selected = st.dataframe(
    filtered[
        [
            "ID",
            "Pojazd",
            "Projekt",
            "Kierowca",
            "Status",
            "Data_Start",
            "Data_Koniec",
            "Uwagi",
        ]
    ],
    use_container_width=True,
)

# --------------------------------------------------
# ADD / EDIT
# --------------------------------------------------
st.divider()
st.subheader("➕ / ✏️ Dodaj lub edytuj wpis")

edit_id = st.selectbox(
    "Edytuj istniejący wpis (opcjonalnie)",
    options=[None] + df["ID"].tolist(),
)

if edit_id is not None:
    row = df[df["ID"] == edit_id].iloc[0]
else:
    row = {}

with st.form("entry_form"):
    c1, c2, c3 = st.columns(3)

    pojazd = c1.text_input("Pojazd", row.get("Pojazd", ""))
    projekt = c2.text_input("Projekt", row.get("Projekt", ""))
    kierowca = c3.text_input("Kierowca",_
