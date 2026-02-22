import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="GMS School Scholarship Test Results 2026",
    layout="wide",
)

DATA_FILE = "all_result.csv"


def norm(s: str) -> str:
    s = "" if s is None else str(s)
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def looks_like_roll(q: str) -> bool:
    """
    Decide if input is intended as roll no.
    Examples: 'GMS-9', 'gms 9', 'GMS - 500', '9' (we will treat numbers as roll only if length >=2)
    """
    qn = norm(q)
    if qn.startswith("gms"):
        return True
    # if purely digits, only treat as roll if 2+ digits (prevents "5" matching too much)
    if qn.isdigit() and len(qn) >= 2:
        return True
    return False


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE)

    # Remove Unnamed columns (if any)
    df = df.loc[:, ~df.columns.astype(str).str.contains(r"^Unnamed", case=False, regex=True)]

    # Clean column names
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Remove empty rows
    df = df.dropna(how="all")

    # Keep only required columns
    keep = ["roll_no", "name", "father name", "current class", "marks", "status"]
    df = df[keep].copy()

    # Normalized keys for fast matching
    df["_roll_key"] = df["roll_no"].astype(str).map(norm)
    df["_name_key"] = df["name"].astype(str).map(norm)
    df["_father_key"] = df["father name"].astype(str).map(norm)

    return df


def status_badge(status: str) -> str:
    s = (status or "").strip().lower()
    if "short" in s:
        return "✅ Short List"
    if "wait" in s:
        return "⏳ Waiting List"
    if "try" in s:
        return "🔁 Try Again"
    return status


def render_card(row: pd.Series) -> None:
    roll_no = row.get("roll_no", "")
    name = row.get("name", "")
    father = row.get("father name", "")
    cls = row.get("current class", "")
    marks = row.get("marks", "")
    status = status_badge(row.get("status", ""))

    st.markdown(
        f"""
<div style="
    border:1px solid rgba(49,51,63,0.2);
    border-radius:14px;
    padding:16px 18px;
    margin:10px 0;
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

  <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
    <div><span style="opacity:0.7;">Father Name:</span><br><b>{father}</b></div>
    <div><span style="opacity:0.7;">Class:</span><br><b>{cls}</b></div>
    <div><span style="opacity:0.7;">Marks:</span><br><b>{marks}</b></div>
    <div><span style="opacity:0.7;">Status:</span><br><b>{status}</b></div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


# ---------- App ----------
df = load_data()

st.markdown(
    """
<div style="text-align:center; padding: 8px 0 2px 0;">
  <h1 style="margin-bottom: 0;">🏫 GMS School Scholarship Test Results 2026</h1>
  <p style="margin-top: 6px; font-size: 16px;">
    Enter <b>Roll No</b> (recommended) — or use <b>Name + Father Name</b> if you don’t know the roll number.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

# ---- SEARCH FIRST (Above guide) ----
st.subheader("🔎 Search")

tab1, tab2 = st.tabs(["Search by Roll No", "Search by Name + Father Name"])

with tab1:
    roll_input = st.text_input("Enter Roll No (example: GMS - 9)", placeholder="GMS - 9").strip()
    roll_btn = st.button("Search Roll No", type="primary")

with tab2:
    name_input = st.text_input("Enter Student Name", placeholder="Example: Zunaira").strip()
    father_input = st.text_input("Enter Father Name", placeholder="Example: Shad Muhammad").strip()
    name_btn = st.button("Search Name + Father Name", type="primary")

st.divider()

# ---- RESULTS ----
def show_results(results: pd.DataFrame):
    if results.empty:
        st.warning("No result found. Please check spelling / roll number.")
        return
    # Usually a roll no should show 1 record, but show all if duplicates exist
    st.success(f"Found {len(results)} result(s).")
    for _, row in results.iterrows():
        render_card(row)

# Roll search logic (primary)
if roll_btn and roll_input:
    q = norm(roll_input)

    # Prevent too-short search like "5" causing many matches
    if q.isdigit() and len(q) < 2:
        st.warning("Please enter at least 2 digits for roll number (example: GMS - 50).")
    else:
        # Prefer exact match first
        exact = df[df["_roll_key"] == q]

        if not exact.empty:
            show_results(exact)
        else:
            # Starts-with match is safer than contains (prevents '5' matching everything)
            starts = df[df["_roll_key"].str.startswith(q, na=False)]
            show_results(starts)

# Name + Father search logic (both required)
if name_btn:
    if not name_input or not father_input:
        st.warning("Please enter BOTH Name and Father Name.")
    else:
        nq = norm(name_input)
        fq = norm(father_input)

        # Require both to match (contains is okay here, but both together makes it safe)
        results = df[
            df["_name_key"].str.contains(nq, na=False)
            & df["_father_key"].str.contains(fq, na=False)
        ]
        show_results(results)

# ---- GUIDE BELOW SEARCH ----
with st.expander("📌 Guide: What do the statuses mean?", expanded=True):
    st.markdown(
        """
- ✅ **Short List**: You are selected for the next step. GMS will contact you for the interview soon.
- ⏳ **Waiting List**: You are not selected yet, but you may be selected if seats become available.
- 🔁 **Try Again**: You are not selected this time. Please prepare and apply again in the next test.
"""
    )

st.caption("Tip: For fastest and most accurate search, use Roll Number.")
