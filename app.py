import html
import re
from pathlib import Path

import pandas as pd
import streamlit as st


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="GMS School Scholarship Test Results 2026",
    page_icon="🏫",
    layout="wide",
)

DATA_FILE = Path(__file__).with_name("GMS Result 2026.xlsx")


# ---------------------------------------------------------
# Accepted Excel column headings
# ---------------------------------------------------------
COLUMN_ALIASES = {
    "roll_no": [
        "roll no",
        "roll_no",
        "roll number",
        "roll",
        "serial no",
        "sr no",
    ],
    "name": [
        "name",
        "student name",
        "candidate name",
    ],
    "father_name": [
        "father name",
        "father_name",
        "father's name",
        "guardian name",
    ],
    "gender": [
        "gender",
        "sex",
    ],
    "marks": [
        "marks",
        "obtained marks",
        "score",
        "total marks",
    ],
    "status": [
        "status",
        "result",
        "selection status",
        "remarks",
    ],
}


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
def clean_text(value) -> str:
    """Convert Excel values into clean strings."""
    if pd.isna(value):
        return ""

    text = str(value).strip()

    # Excel may convert roll numbers such as 554 into 554.0
    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]

    return text


def normalize_search(value) -> str:
    """Normalize text for searching."""
    return re.sub(
        r"[^a-z0-9]+",
        "",
        clean_text(value).lower(),
    )


def normalize_header(value) -> str:
    """Normalize Excel column names."""
    text = str(value).strip().lower().replace("_", " ")
    return re.sub(r"\s+", " ", text)


def find_column(columns, aliases):
    """Find a matching Excel column using alternative headings."""
    normalized_columns = {
        normalize_header(column): column
        for column in columns
    }

    for alias in aliases:
        normalized_alias = normalize_header(alias)

        if normalized_alias in normalized_columns:
            return normalized_columns[normalized_alias]

    return None


def infer_gender_from_sheet(sheet_name: str) -> str:
    """Infer gender from worksheet name."""
    sheet_key = normalize_header(sheet_name)

    if "female" in sheet_key:
        return "Female"

    if "male" in sheet_key and "female" not in sheet_key:
        return "Male"

    return ""


def is_absent_sheet(sheet_name: str) -> bool:
    """Check whether the worksheet is the absent-students sheet."""
    return "absent" in normalize_header(sheet_name)


# ---------------------------------------------------------
# Load all Excel sheets
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data(file_path: str) -> pd.DataFrame:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"'{path.name}' was not found. "
            "Upload it to the same GitHub folder as app.py."
        )

    workbook = pd.read_excel(
        path,
        sheet_name=None,
        engine="openpyxl",
    )

    all_frames = []
    skipped_sheets = []

    for sheet_name, raw in workbook.items():
        raw = raw.dropna(how="all")

        raw = raw.loc[
            :,
            ~raw.columns.astype(str).str.contains(
                r"^Unnamed",
                case=False,
                regex=True,
            ),
        ]

        if raw.empty:
            continue

        column_mapping = {}

        for standard_name, aliases in COLUMN_ALIASES.items():
            actual_column = find_column(
                raw.columns,
                aliases,
            )

            if actual_column is not None:
                column_mapping[actual_column] = standard_name

        found_columns = set(column_mapping.values())

        required_columns = {
            "roll_no",
            "name",
            "father_name",
        }

        if not required_columns.issubset(found_columns):
            skipped_sheets.append(sheet_name)
            continue

        frame = raw.rename(columns=column_mapping).copy()

        for optional_column in [
            "gender",
            "marks",
            "status",
        ]:
            if optional_column not in frame.columns:
                frame[optional_column] = ""

        # Clean values
        for column in [
            "roll_no",
            "name",
            "father_name",
            "gender",
            "marks",
            "status",
        ]:
            frame[column] = frame[column].map(clean_text)

        # Infer gender from worksheet name when needed
        inferred_gender = infer_gender_from_sheet(sheet_name)

        frame.loc[
            frame["gender"] == "",
            "gender",
        ] = inferred_gender

        # Force absent status for absent worksheet
        if is_absent_sheet(sheet_name):
            frame["status"] = "Absent"
            frame["marks"] = ""

        frame["source_sheet"] = sheet_name

        frame = frame[
            [
                "roll_no",
                "name",
                "father_name",
                "gender",
                "marks",
                "status",
                "source_sheet",
            ]
        ].copy()

        # Remove empty records
        frame = frame[
            (frame["roll_no"] != "")
            | (frame["name"] != "")
            | (frame["father_name"] != "")
        ]

        all_frames.append(frame)

    if not all_frames:
        sheet_names = ", ".join(workbook.keys())

        raise ValueError(
            "No usable result sheets were found. "
            "Each result sheet must contain Name, Father Name and Roll No. "
            f"Sheets found: {sheet_names}"
        )

    df = pd.concat(
        all_frames,
        ignore_index=True,
    )

    df = df.drop_duplicates(
        subset=[
            "roll_no",
            "name",
            "father_name",
            "status",
        ],
        keep="first",
    ).reset_index(drop=True)

    df["_roll_key"] = df["roll_no"].map(normalize_search)
    df["_name_key"] = df["name"].map(normalize_search)
    df["_father_key"] = df["father_name"].map(normalize_search)

    df.attrs["skipped_sheets"] = skipped_sheets

    return df


# ---------------------------------------------------------
# Status formatting
# ---------------------------------------------------------
def format_status(status: str) -> str:
    text = clean_text(status)
    key = text.lower()

    if "absent" in key:
        return "❌ Absent"

    if (
        "short" in key
        or "select" in key
        or "qualif" in key
        or "pass" in key
    ):
        return "✅ Passed and Shortlisted for Interview"

    if "wait" in key:
        return "⏳ Waiting List"

    if (
        "try" in key
        or "not select" in key
        or "fail" in key
    ):
        return "🔁 Try Again"

    return text or "Not specified"


def safe_html(value) -> str:
    """Escape values before placing them in HTML."""
    return html.escape(clean_text(value))


# ---------------------------------------------------------
# Result card
# ---------------------------------------------------------
def render_card(row: pd.Series) -> None:
    roll_no = safe_html(row.get("roll_no", ""))
    name = safe_html(row.get("name", ""))
    father_name = safe_html(row.get("father_name", ""))
    gender = safe_html(row.get("gender", "")) or "—"
    marks = safe_html(row.get("marks", "")) or "—"
    status = safe_html(
        format_status(row.get("status", ""))
    )

    st.markdown(
        f"""
<div style="border:1px solid rgba(49,51,63,0.20); border-radius:14px; padding:18px; margin:12px 0; box-shadow:0 2px 10px rgba(0,0,0,0.06);">
    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
        <div>
            <div style="font-size:20px; font-weight:700;">
                {name}
            </div>
            <div style="opacity:0.75; margin-top:4px;">
                Roll No: <b>{roll_no}</b>
            </div>
        </div>
        <div style="font-size:16px; font-weight:700;">
            {status}
        </div>
    </div>

    <hr style="margin:14px 0; opacity:0.25;">

    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:14px;">
        <div>
            <span style="opacity:0.7;">Father Name:</span><br>
            <b>{father_name}</b>
        </div>

        <div>
            <span style="opacity:0.7;">Gender:</span><br>
            <b>{gender}</b>
        </div>

        <div>
            <span style="opacity:0.7;">Marks:</span><br>
            <b>{marks}</b>
        </div>

        <div>
            <span style="opacity:0.7;">Status:</span><br>
            <b>{status}</b>
        </div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def show_results(results: pd.DataFrame) -> None:
    if results.empty:
        st.warning(
            "No result found. Please check the spelling or roll number."
        )
        return

    st.success(f"Found {len(results)} result(s).")

    for _, row in results.iterrows():
        render_card(row)


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------
try:
    df = load_data(str(DATA_FILE))

except Exception as error:
    st.error("The result file could not be loaded.")
    st.code(str(error))

    st.info(
        "Keep 'GMS Result 2026.xlsx' in the same folder as app.py. "
        "The Male, Female and Absent Students sheets must contain "
        "Name, Father Name and Roll No."
    )

    st.stop()


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.title("🏫 GMS School Scholarship Test Results 2026")

st.markdown(
    """
Enter your **Roll No**, or search using  
**Student Name + Father Name**.
"""
)


# ---------------------------------------------------------
# Search section
# ---------------------------------------------------------
st.subheader("🔎 Search")

tab_roll, tab_name = st.tabs(
    [
        "Search by Roll No",
        "Search by Name + Father Name",
    ]
)


# ---------------------------------------------------------
# Roll-number search form
# ---------------------------------------------------------
with tab_roll:
    with st.form("roll_search_form"):
        roll_input = st.text_input(
            "Enter Roll No",
            placeholder="Example: 554",
        ).strip()

        roll_button = st.form_submit_button(
            "Search Roll No",
            type="primary",
            use_container_width=True,
        )


# ---------------------------------------------------------
# Name search form
# ---------------------------------------------------------
with tab_name:
    with st.form("name_search_form"):
        name_input = st.text_input(
            "Enter Student Name",
            placeholder="Example: Muhammad Irfan Siddiqi",
        ).strip()

        father_input = st.text_input(
            "Enter Father Name",
            placeholder="Example: Bakht Zada",
        ).strip()

        name_button = st.form_submit_button(
            "Search Name + Father Name",
            type="primary",
            use_container_width=True,
        )


st.divider()


# ---------------------------------------------------------
# Roll-number search logic
# ---------------------------------------------------------
if roll_button:
    if not roll_input:
        st.warning("Please enter a roll number.")

    else:
        query = normalize_search(roll_input)

        results = df[
            df["_roll_key"] == query
        ]

        # Support inputs such as GMS-554 when Excel contains 554
        if results.empty:
            numeric_query = re.sub(
                r"^gms",
                "",
                query,
            )

            if numeric_query.isdigit():
                numeric_query = (
                    numeric_query.lstrip("0") or "0"
                )

                normalized_rolls = (
                    df["_roll_key"]
                    .str.replace(
                        r"^gms",
                        "",
                        regex=True,
                    )
                    .str.lstrip("0")
                    .replace("", "0")
                )

                results = df[
                    normalized_rolls == numeric_query
                ]

        show_results(results)


# ---------------------------------------------------------
# Name and father-name search logic
# ---------------------------------------------------------
if name_button:
    if not name_input or not father_input:
        st.warning(
            "Please enter both Student Name and Father Name."
        )

    else:
        name_query = normalize_search(name_input)
        father_query = normalize_search(father_input)

        if (
            len(name_query) < 2
            or len(father_query) < 2
        ):
            st.warning(
                "Please enter at least 2 letters in both fields."
            )

        else:
            results = df[
                df["_name_key"].str.contains(
                    name_query,
                    regex=False,
                    na=False,
                )
                & df["_father_key"].str.contains(
                    father_query,
                    regex=False,
                    na=False,
                )
            ]

            show_results(results)


# ---------------------------------------------------------
# Status guide
# ---------------------------------------------------------
with st.expander(
    "📌 Guide: What do the statuses mean?",
    expanded=True,
):
    st.markdown(
        """
- ✅ **Passed and Shortlisted for Interview**: The candidate passed the test and was shortlisted for the interview.
- ⏳ **Waiting List**: The candidate may be considered if a seat becomes available.
- 🔁 **Try Again**: The candidate was not selected this time.
- ❌ **Absent**: The candidate did not attend the test, so marks appear as **—**.
"""
    )


st.caption(
    "Tip: Searching with the roll number gives the fastest and most accurate result."
)
