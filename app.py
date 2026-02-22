import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="GMS School Scholarship Test Results 2026",
    page_icon="🏫",
    layout="wide",
)

# ---------- Helpers ----------
def norm(s: str) -> str:
    s = "" if s is None else str(s)
    return re.sub(r"[^a-z0-9]+", "", s.lower())

@st.cache_data
def load_data():
    # FAST option: if you convert to CSV, use read_csv (much faster than Excel)
     df = pd.read_csv("all_result.csv")

    # Current: Excel
    #df = pd.read_excel("all_result.xlsx", header=1)

    # remove Unnamed columns
    df = df.loc[:, ~df.columns.astype(str).str.contains(r"^Unnamed", case=False, regex=True)]
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.dropna(how="all")

    # keep only needed columns
    keep = ["roll_no", "name", "father name", "current class", "marks", "status"]
    df = df[keep].copy()

    # normalized keys
    df["_roll_key"] = df["roll_no"].astype(str).map(norm)
    df["_name_key"] = df["name"].astype(str).map(norm)

    return df

df = load_data()

# ---------- UI ----------
st.markdown(
    """
    <div style="text-align:center; padding: 10px 0 4px 0;">
        <h1 style="margin-bottom: 0;">🏫 GMS School Scholarship Test Results 2026</h1>
        <p style="margin-top: 6px; font-size: 16px;">
            Search your result using <b>Roll No</b> or <b>Name</b>
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Info / meanings box
with st.expander("📌 What do these statuses mean? (Read this)", expanded=True):
    st.markdown(
        """
- ✅ **Short List**: You are selected for the next step. The school will contact you / you should follow the next instructions.
- ⏳ **Waiting List**: You are not selected yet, but you may be selected if seats become available.
- 🔁 **Try Again**: You are not selected this time. Please prepare and apply again in the next test.
        """
    )

# Search area (nice layout)
col1, col2 = st.columns([3, 1], vertical_alignment="bottom")

with col1:
    query = st.text_input("🔎 Enter Roll No or Name (example: GMS - 9 / Zunaira)", placeholder="Type Roll No or Name...").strip()

with col2:
    exact_roll_only = st.toggle("🎯 Exact Roll Match", value=False, help="If ON, Roll No must match exactly (recommended).")

st.divider()

if query:
    q = norm(query)

    # Fast path: exact roll match if toggle is ON
    if exact_roll_only:
        results = df[df["_roll_key"] == q]
    else:
        results = df[df["_roll_key"].str.contains(q, na=False) | df["_name_key"].str.contains(q, na=False)]

    if results.empty:
        st.warning("No result found. Please check spelling / roll number.")
    else:
        st.success(f"Found {len(results)} result(s).")
        st.dataframe(
            results[["roll_no", "name", "father name", "current class", "marks", "status"]],
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("Type your Roll No or Name above to view the result.")
