import os, streamlit as st, pandas as pd, pathlib
from analytics.validator import validate_and_normalize
from analytics.tcd import estimate_aht_minutes

st.markdown("<style>" + pathlib.Path("assets/theme.css").read_text() + "</style>", unsafe_allow_html=True)
st.title("📥 Upload & Settings")

with st.expander("Upload ServiceNow Excel", expanded=True):
    f = st.file_uploader("Upload .xlsx with sheets: 'Incidents', 'ServiceRequests'", type=["xlsx"])
    st.caption("Minimum useful columns: short_description, description. Optional: u_aht_minutes, sla_breached, reopen_count, persona/site/category.")
    if f:
        xl = pd.ExcelFile(f)
        inc = xl.parse("Incidents") if "Incidents" in xl.sheet_names else pd.DataFrame()
        req = xl.parse("ServiceRequests") if "ServiceRequests" in xl.sheet_names else pd.DataFrame()
        df, notes = validate_and_normalize(inc, req)
        st.success(f"Loaded rows: {notes['rows']}  |  Empty text: {notes['empty_text_pct']}%")
        st.session_state["df"] = df
        st.session_state["aht_guess"] = estimate_aht_minutes(df, default=8.0)

with st.expander("Intelligence Settings", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("GEMINI_API_KEY (optional)", type="password", key="ui_gemini")
    with col2:
        st.text_input("OPENAI_API_KEY (optional)", type="password", key="ui_openai")
    with col3:
        st.selectbox("LLM Provider preference", ["auto","gemini","openai","off"], index=0, key="llm_provider")

    # bind env vars for current session
    if st.button("Apply Keys"):
        if st.session_state.get("ui_gemini"):
            os.environ["GEMINI_API_KEY"] = st.session_state["ui_gemini"]
            os.environ["GOOGLE_API_KEY"] = st.session_state["ui_gemini"]
        if st.session_state.get("ui_openai"):
            os.environ["OPENAI_API_KEY"] = st.session_state["ui_openai"]
        st.success("Keys applied to this session. If you change them, click Apply again.")

with st.expander("Clustering & Coverage", expanded=True):
    c1,c2,c3 = st.columns(3)
    c1.number_input("Min cluster size (HDBSCAN)", min_value=10, max_value=200, value=25, step=5, key="min_cluster_size")
    c2.slider("Target 'Other' max %", 0, 50, 12, 1, key="target_other_pct")
    c3.checkbox("Include 'Other' in outputs", value=False, key="include_other")

st.info("Next → open **📊 Drivers & Visualization** in the sidebar.")
