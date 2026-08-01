import html
import re
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="GMS School Scholarship Test Results 2026",
    page_icon="🏫",
    layout="wide",
)

# Put this Excel file in the same GitHub folder as app.py.
DATA_FILE = Path(__file__).with_name("GMS Result 2026.xlsx")

# Accepted alternatives for each required field.
COLUMN_ALIASES = {
    "roll_no": ["roll_no", "roll no", "roll number", "roll", "serial no", "sr no"],
    "name": ["name", "student name", "candidate name"],
    "father_name": ["father name", "father_name", "father's name", "guardian name"],
    "current_class": ["current class", "current_class", "class", "grade"],
    "marks": ["marks", "obtained marks", "score", "total marks"],
    "status": ["status", "result", "selection status", "remarks"],
}


def clean_text(value) -> str:
    """Convert Excel values into clean display strings."""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    # Excel sometimes reads whole-number IDs as 9.0.
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text


def norm(value) -> str:
    """Normalize text for punctuation/case-insensitive matching."""
    return re.sub(r"[^a-z0-9]+", "", clean_text(value).lower())


def normalize_header(value) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower().replace("_", " "))


def find_column(columns, aliases):
    normalized = {normalize_header(c): c for c in columns}
    for alias in aliases:
        key = normalize_header(alias)
        if key in normalized:
            return normalized[key]
    return None


@st.cache_data(show_spinner=False)
def load_data(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(
            f"'{path.name}' was not found. Add it to the same folder as app.py."
        )

    # sheet_name=0 reads the first worksheet.
    raw = pd.read_excel(path, sheet_name=0, engine="openpyxl")
    raw = raw.loc[:, ~raw.columns.astype(str).str.contains(r"^Unnamed", case=False, regex=True)]
    raw = raw.dropna(how="all")

    mapping = {}
    missing = []
    for standard_name, aliases in COLUMN_ALIASES.items():
        actual = find_column(raw.columns, aliases)
        if actual is None:
            missing.append(standard_name)
        else:
            mapping[actual] = standard_name

    if missing:
        available = ", ".join(map(str, raw.columns))
        raise ValueError(
            "Could not identify these required columns: "
            + ", ".join(missing)
            + f". Columns found in Excel: {available}"
        )

    df = raw.rename(columns=mapping)[list(COLUMN_ALIASES)].copy()

    for column in df.columns:
        df[column] = df[column].map(clean_text)

    df = df[
        (df["roll_no"] != "")
        | (df["name"] != "")
        | (df["father_name"] != "")
    ].copy()

    df["_roll_key"] = df["roll_no"].map(norm)
    df["_name_key"] = df["name"].map(norm)
    df["_father_key"] = df["father_name"].map(norm)
    return df


def status_badge(status: str) -> str:
    s = clean_text(status)
    key = s.lower()
    if "short" in key or "select" in key or "qualif" in key:
        return "✅ Short List"
    if "wait" in key:
        return "⏳ Waiting List"
    if "try" in key or "not select" in key or "fail" in key:
        return "🔁 Try Again"
    return s or "Not specified"


def safe(value) -> str:
    return html.escape(clean_text(value))


def render_card(row: pd.Series) -> None:
    roll_no = safe(row.get("roll_no", ""))
    name = safe(row.get("name", ""))
    father = safe(row.get("father_name", ""))
    current_class = safe(row.get("current_class", ""))
    marks = safe(row.get("marks", ""))
    status = safe(status_badge(row.get("status", "")))

    st.markdown(
        f"""
<div style="
    border: 1px solid rgba(49,51,63,0.20);
    border-radius: 14px;
    padding: 16px 18px;
    margin: 10px 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
">
  <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px;">
    <div>
      <div style="font-size:18px; font-weight:700;">{name}</div>
      <div style="opacity:0.75; margin-top:2px;">Roll No: <b>{roll_no}</b></div>
    </div>
    <div style="font-size:16px; font-weight:700;">{status}</div>
  </div>
  <hr style="margin:12px 0; opacity:0.25;">
  <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px;">
    <div><span style="opacity:0.7;">Father Name:</span><br><b>{father}</b></div>
    <div><span style="opacity:0.7;">Class:</span><br><b>{current_class}</b></div>
    <div><span style="opacity:0.7;">Marks:</span><br><b>{marks}</b></div>
    <div><span style="opacity:0.7;">Status:</span><br><b>{status}</b></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def show_results(results: pd.DataFrame) -> None:
    if results.empty:
        st.warning("No result found. Please check the spelling or roll number.")
        return

    st.success(f"Found {len(results)} result(s).")
    for _, row in results.iterrows():
        render_card(row)


try:
    df = load_data(str(DATA_FILE))
except Exception as error:
    st.error("The result file could not be loaded.")
    st.code(str(error))
    st.info(
        "Make sure the Excel filename is exactly 'GMS Result 2026.xlsx' and that "
        "its first row contains column headings."
    )
    st.stop()

st.markdown(
    """
<div style="text-align:center; padding:8px 0 2px 0;">
  <h1 style="margin-bottom:0;">🏫 GMS School Scholarship Test Results 2026</h1>
  <p style="margin-top:6px; font-size:16px;">
    Enter your <b>Roll No</b>, or search using <b>Student Name + Father Name</b>.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

st.subheader("🔎 Search")
tab1, tab2 = st.tabs(["Search by Roll No", "Search by Name + Father Name"])

with tab1:
    with st.form("roll_search_form"):
        roll_input = st.text_input(
            "Enter Roll No",
            placeholder="Example: GMS - 9",
        ).strip()
        roll_btn = st.form_submit_button("Search Roll No", type="primary")

with tab2:
    with st.form("name_search_form"):
        name_input = st.text_input(
            "Enter Student Name",
            placeholder="Example: Zunaira",
        ).strip()
        father_input = st.text_input(
            "Enter Father Name",
            placeholder="Example: Shad Muhammad",
        ).strip()
        name_btn = st.form_submit_button("Search Name + Father Name", type="primary")

st.divider()

if roll_btn:
    if not roll_input:
        st.warning("Please enter a roll number.")
    else:
        q = norm(roll_input)
        if q.isdigit() and len(q) < 1:
            st.warning("Please enter a valid roll number.")
        else:
            exact = df[df["_roll_key"] == q]

            # Also allow a user to enter only the numeric part, e.g. 9 for GMS-9.
            if exact.empty and q.isdigit():
                exact = df[df["_roll_key"].str.fullmatch(rf"(?:gms)?0*{re.escape(q)}", na=False)]

            show_results(exact)

if name_btn:
    if not name_input or not father_input:
        st.warning("Please enter both Student Name and Father Name.")
    else:
        nq = norm(name_input)
        fq = norm(father_input)

        if len(nq) < 2 or len(fq) < 2:
            st.warning("Please enter at least 2 letters in both fields.")
        else:
            results = df[
                df["_name_key"].str.contains(nq, regex=False, na=False)
                & df["_father_key"].str.contains(fq, regex=False, na=False)
            ]
            show_results(results)

with st.expander("📌 Guide: What do the statuses mean?", expanded=True):
    st.markdown(
        """
- ✅ **Short List**: Selected for the next step. GMS will contact the candidate for an interview.
- ⏳ **Waiting List**: Not selected yet, but selection may be possible if a seat becomes available.
- 🔁 **Try Again**: Not selected in this test. The candidate may prepare and apply again next time.
"""
    )

st.caption("Tip: Roll Number gives the fastest and most accurate result.")
