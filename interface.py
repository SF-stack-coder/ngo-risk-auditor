import streamlit as st
import pandas as pd

st.set_page_config(page_title="Delhi NGO Trust & Risk Auditor", layout="wide")

st.title("🛡️ Delhi NGO Verification & Risk Detection Engine")
st.markdown("Auditing public reviews, operational signals, and NLP sentiment to evaluate donor risk.")

@st.cache_data
def load_data():
    return pd.read_csv("delhi_ngos_assessed.csv")

try:
    df = load_data()
except Exception:
    st.error("Please run your train_model.py first to generate delhi_ngos_assessed.csv!")
    st.stop()

# Sidebar search
st.sidebar.header("Filter & Search")
search_term = st.sidebar.text_input("Search NGO by Name:", "")
selected_tier = st.sidebar.multiselect(
    "Filter by Risk Tier:",
    options=df["risk_tier"].unique(),
    default=df["risk_tier"].unique()
)

filtered_df = df[df["risk_tier"].isin(selected_tier)]
if search_term:
    filtered_df = filtered_df[filtered_df["ngo_name"].astype(str).str.contains(search_term, case=False)]

# Summary metrics
col1, col2, col3 = st.columns(3)
col1.metric("Safe / High Credibility", len(df[df["risk_tier"] == "Safe / High Credibility"]))
col2.metric("Needs Verification", len(df[df["risk_tier"] == "Moderate / Needs Independent Verification"]))
col3.metric("Elevated Risk Flagged", len(df[df["risk_tier"] == "Elevated Risk / Requires Caution"]))

st.divider()

# Results display
for _, row in filtered_df.head(10).iterrows():
    with st.expander(f"📌 {row['ngo_name']} — Score: {round(row['credibility_score'], 1)}/100"):
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Risk Tier:** {row['risk_tier']}")
        c2.write(f"**Average Rating:** {row['avg_review_rating']} ⭐")
        c3.write(f"**Reviews Counted:** {row['authentic_review_count']}")

        st.info(f"**Audit Findings:** {row.get('risk_factors_explanation', 'No red flags identified.')}")
        if pd.notna(row.get("aggregated_reviews")):
            st.caption(f"Review Snippets: {row['aggregated_reviews']}")