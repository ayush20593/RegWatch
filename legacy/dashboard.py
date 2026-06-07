from pathlib import Path
import json

import pandas as pd
import streamlit as st


DATA_FILE = Path("compliance_updates.json")
LEGACY_DATA_FILE = Path("sebi_updates.json")

REQUIRED_COLUMNS = {
    "id": "",
    "regulator": "Unknown",
    "source_type": "Other",
    "document_type": "Other",
    "category": "Other",
    "title": "",
    "date": "",
    "summary": "",
    "applicability": "Needs compliance review",
    "risk_level": "Low",
    "page_url": "",
    "pdf_url": "",
    "detected_at": "",
}


def load_data() -> list[dict]:
    for path in (DATA_FILE, LEGACY_DATA_FILE):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            st.error(f"{path.name} is not valid JSON.")
            st.stop()
    return []


def prepare_dataframe(data: list[dict]) -> pd.DataFrame:
    if not data:
        return pd.DataFrame(columns=list(REQUIRED_COLUMNS))

    df = pd.DataFrame(data)
    for column, default in REQUIRED_COLUMNS.items():
        if column not in df.columns:
            df[column] = default

    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)
    df["detected_at"] = pd.to_datetime(
        df["detected_at"], errors="coerce", utc=True
    ).dt.tz_localize(None)
    display_sort_date = df["date"].fillna(df["detected_at"])
    df["sort_date"] = display_sort_date.astype("int64").where(display_sort_date.notna(), -1)
    return df.sort_values("sort_date", ascending=False, na_position="last")


def multiselect_filter(label: str, values: pd.Series) -> list[str]:
    options = sorted([value for value in values.dropna().unique() if value])
    return st.sidebar.multiselect(label, options=options, default=options)


st.set_page_config(page_title="Compliance Monitor", layout="wide")
st.title("Compliance Monitor")

with st.sidebar:
    st.header("Actions")
    refresh_limit = st.number_input(
        "Updates per source",
        min_value=1,
        max_value=25,
        value=8,
        step=1,
    )
    if st.button("Fetch latest updates", use_container_width=True):
        with st.spinner("Fetching regulator updates..."):
            from app import run

            run(
                limit_per_source=int(refresh_limit),
                send_notifications=False,
                reset_data=True,
            )
        st.rerun()

data = load_data()
df = prepare_dataframe(data)

if df.empty:
    st.info("No updates found yet. Run `python3 app.py --no-email` to fetch the first batch.")
    st.stop()

st.sidebar.header("Filters")
regulators = multiselect_filter("Regulator", df["regulator"])
document_types = multiselect_filter("Document type", df["document_type"])
risk_levels = multiselect_filter("Risk level", df["risk_level"])
search = st.sidebar.text_input("Search title or summary")

filtered = df[
    df["regulator"].isin(regulators)
    & df["document_type"].isin(document_types)
    & df["risk_level"].isin(risk_levels)
]

if search:
    search_text = search.lower()
    filtered = filtered[
        filtered["title"].str.lower().str.contains(search_text, na=False)
        | filtered["summary"].str.lower().str.contains(search_text, na=False)
    ]

st.subheader("Overview")
metric_cols = st.columns(4)
metric_cols[0].metric("Total updates", len(filtered))
metric_cols[1].metric("Regulators", filtered["regulator"].nunique())
metric_cols[2].metric("High risk", int((filtered["risk_level"] == "High").sum()))
metric_cols[3].metric("With PDFs", int(filtered["pdf_url"].astype(bool).sum()))

chart_cols = st.columns(2)
with chart_cols[0]:
    st.subheader("By regulator")
    st.bar_chart(filtered["regulator"].value_counts())

with chart_cols[1]:
    st.subheader("By document type")
    st.bar_chart(filtered["document_type"].value_counts())

st.subheader("Updates")

for _, row in filtered.iterrows():
    title = row["title"] or "Untitled update"
    date_str = row["date"].strftime("%d %b %Y") if pd.notna(row["date"]) else "Date not available"
    detected_str = (
        row["detected_at"].strftime("%d %b %Y %H:%M")
        if pd.notna(row["detected_at"])
        else "Not available"
    )

    with st.container(border=True):
        header_cols = st.columns([4, 1])
        with header_cols[0]:
            st.markdown(f"### {title}")
            st.caption(
                f"{row['regulator']} | {row['document_type']} | {date_str} | "
                f"Detected: {detected_str}"
            )
        with header_cols[1]:
            st.metric("Risk", row["risk_level"])

        st.write(row["summary"] or "No summary available.")
        st.caption(row["applicability"] or "Needs compliance review")

        button_cols = st.columns(2)
        if row["pdf_url"]:
            button_cols[0].link_button("Open document", row["pdf_url"])
        if row["page_url"] and row["page_url"] != row["pdf_url"]:
            button_cols[1].link_button("Open source page", row["page_url"])
