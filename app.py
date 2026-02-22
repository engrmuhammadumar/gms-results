import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Student Result Portal", page_icon="📄", layout="wide")

FILE_NAME = "all_result.xlsx"   # keep this file in the same folder as app.py

def normalize(text: str) -> str:
    """Lowercase and remove spaces/symbols so searches like 'GMS9' match 'GMS - 9'."""
    text = "" if text is None else str(text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())

@st.cache_data
def load_data():
    # Your excel header is on row 2 (index 1), so header=1
    df = pd.read_excel(FILE_NAME, header=1)

    # Drop the extra empty column like "Unnamed: 0"
    df = df.loc[:, ~df.columns.astype(str).str.contains(r"^Unnamed", case=False, regex=True)]

    # Clean column names
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Ensure required columns exist (based on your sheet)
    # roll_no, name, father name, current class, marks, status
    for col in ["roll_no", "name", "father name", "current class", "marks", "status"]:
        if col not in df.columns:
            st.error(f"Missing column: {col}. Found columns: {list(df.columns)}")
            st.stop()

    # Drop fully empty rows
    df = df.dropna(how="all")

    # Create normalized search keys
    df["_roll_key"] = df["roll_no"].astype(str).map(normalize)
    df["_name_key"] = df["name"].astype(str).map(normalize)

    return df

df = load_data()

st.title("📄 Student Result Portal")

query = st.text_input("Search by Roll No or Name (e.g., GMS - 9 / Taqwa Ashfaq)").strip()

if query:
    q = normalize(query)

    results = df[(df["_roll_key"].str.contains(q, na=False)) | (df["_name_key"].str.contains(q, na=False))]

    # Show only required columns
    show_cols = ["roll_no", "name", "father name", "current class", "marks", "status"]
    results = results[show_cols]

    if results.empty:
        st.warning("No result found. Please check spelling / roll number format.")
    else:
        st.success(f"Found {len(results)} result(s).")
        st.dataframe(results, use_container_width=True)
else:
    st.info("Type a student Name or Roll No to view the result.")