import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="GMS School Scholarship Test Results 2026",
    page_icon="🏫",
    layout="wide",
)

FILE_NAME = "all_result.xlsx"


def norm(s: str) -> str:
    s = "" if s is None else str(s)
    return re.sub(r"[^a-z0-9]+", "", s.lower())


@st.cache_data
def load_data() -> pd.DataFrame:
    # Your header starts at row 2 in Excel, so header=1
    #df = pd.read_excel(FILE_NAME, header=1)
    df = pd.read_csv("all_result.csv")

    # Remove "Unnamed" columns (extra blank column)
    df = df.loc[:, ~df.columns.astype(str).str.contains(r"^Unnamed", case=False, regex=True)]

    # Clean column names
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Remove fully empty rows
    df = df.dropna(how="all")

    # Keep only required columns
    keep = ["roll_no", "name", "father name", "current class", "marks", "status"]
    df = df[keep].copy()

    # Add normalized search keys
    df["_roll_key"] = df["roll_no"].astype(str).map(norm)
    df["_name_key"] = df["name"].astype(str).map(norm)

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
    # Simple, clean result card (looks good on mobile too)
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
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
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
  <h1 style="margin-bottom: 0;">GMS School Scholarship Test Results 2026</h1>
  <p style="margin-top: 6px; font-size: 16px;">
    Search your result using <b>Roll No</b> or <b>Name</b>
  </p>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("📌 Guide: What do the statuses mean?", expanded=True):
    st.markdown(
        """
- ✅ **Short List**: You are selected for the next step. GMS will contact you for the interview soon.
- ⏳ **Waiting List**: You are not selected yet, but you may be selected if seats become available.
- 🔁 **Try Again**: You are not selected this time. Please prepare and apply again next year.
"""
    )

c1, c2 = st.columns([3, 1], vertical_alignment="bottom")

with c1:
    query = st.text_input(
        "🔎 Search by Roll No or Name",
        placeholder="Example: GMS - 9  or  Zunaira",
    ).strip()

with c2:
    show_all_matches = st.toggle(
        "Show all matches",
        value=True,
        help="If OFF, only the first best match will be shown (looks cleaner).",
    )

st.divider()

if query:
    q = norm(query)

    results = df[df["_roll_key"].str.contains(q, na=False) | df["_name_key"].str.contains(q, na=False)]

    if results.empty:
        st.warning("No result found. Please check spelling / roll number.")
    else:
        st.success(f"Found {len(results)} result(s).")

        # Sort: exact roll first, then exact name, then others
        results = results.copy()
        results["_score"] = (
            (results["_roll_key"] == q).astype(int) * 3
            + (results["_name_key"] == q).astype(int) * 2
        )
        results = results.sort_values(by="_score", ascending=False).drop(columns=["_score"])

        if not show_all_matches:
            results = results.head(1)

        # Render cards
        for _, row in results.iterrows():
            render_card(row)

else:
    st.info("Type your Roll No or Name above to view the result.")

