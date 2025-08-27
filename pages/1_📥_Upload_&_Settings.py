import os, streamlit as st, pandas as pd, pathlib
from analytics.validator import validate_and_normalize
from analytics.tcd import estimate_aht_minutes
from analytics.prefs import save_prefs, load_prefs
from analytics.mapping import CANONICAL, propose_mapping

st.markdown("<style>" + pathlib.Path("assets/theme.css").read_text() + "</style>", unsafe_allow_html=True)
st.title("📥 Upload & Settings")

prefs = load_prefs()

with st.expander("Upload ServiceNow Excel", expanded=True):
    f = st.file_uploader("Upload .xlsx (sheets with required columns will be detected)", type=["xlsx"])
    st.caption("Minimum required: short_description, description (you can map columns below). Optional: assignment_group, persona, site, opened date, AHT, SLA Breach, Reopen, etc.")

if f:
    xl = pd.ExcelFile(f)
    dfs = []
    used = []
    for name in xl.sheet_names:
        tmp = xl.parse(name)
        test_map = propose_mapping(tmp.columns)
        if test_map.get("short_description") and test_map.get("description"):
            tmp["source"] = name
            dfs.append(tmp)
            used.append(name)
    all_cols = sorted({c for d in dfs for c in d.columns}) if dfs else []
    auto = propose_mapping(all_cols)
    raw = pd.concat(dfs, ignore_index=True, sort=False) if dfs else pd.DataFrame()

    if used:
        st.success(f"Found sheets: {', '.join(used)}")
    else:
        st.error("No valid sheets found")

    with st.expander("Column Mapping (auto-detected → change if needed)", expanded=True):
        col_map = {}
        rcols = st.columns(3)
        for i, canon in enumerate(CANONICAL):
            default = auto.get(canon)
            options = ["— none —"] + all_cols
            chosen = rcols[i % 3].selectbox(f"{canon}", options, index=(options.index(default) if default in options else 0))
            col_map[canon] = None if chosen == "— none —" else chosen

        c1,c2 = st.columns(2)
        if c1.button("Quick Load (use auto-mapping)"):
            df, notes = validate_and_normalize(raw, mapping=auto)
            st.session_state["df"] = df
            st.session_state["aht_guess"] = estimate_aht_minutes(df, default=8.0)
            st.session_state["column_map"] = auto
            # mark analysis dirty so Drivers page recomputes once
            for k in ["refined","freq_all","fig_top"]: st.session_state.pop(k, None)
            st.session_state["dirty"] = True
            st.success(f"Loaded rows: {notes['rows']} | Empty text: {notes['empty_text_pct']}%")
        if c2.button("Apply Mapping & Load Data"):
            df, notes = validate_and_normalize(raw, mapping=col_map)
            st.session_state["df"] = df
            st.session_state["aht_guess"] = estimate_aht_minutes(df, default=8.0)
            st.session_state["column_map"] = col_map
            for k in ["refined","freq_all","fig_top"]: st.session_state.pop(k, None)
            st.session_state["dirty"] = True
            st.success(f"Loaded rows: {notes['rows']} | Empty text: {notes['empty_text_pct']}%")

with st.expander("Intelligence & Keys", expanded=True):
    c1,c2,c3 = st.columns(3)
    prefs["llm_provider"] = c1.selectbox("LLM Provider", ["auto","gemini","openai","off"], index=["auto","gemini","openai","off"].index(prefs.get("llm_provider","auto")))
    gem = c2.text_input("GEMINI_API_KEY (optional)", type="password")
    oa  = c3.text_input("OPENAI_API_KEY (optional)", type="password")
    if st.button("Apply Keys (for this session)"):
        if gem: os.environ["GEMINI_API_KEY"] = gem; os.environ["GOOGLE_API_KEY"] = gem
        if oa:  os.environ["OPENAI_API_KEY"] = oa
        st.success("Keys applied to this session. Not saved unless you choose Save with keys.")

with st.expander("Clustering & Coverage", expanded=True):
    c1,c2,c3 = st.columns(3)
    prefs["min_cluster_size"] = c1.number_input("Min cluster size (HDBSCAN)", 10, 200, int(prefs.get("min_cluster_size",25)), 5)
    prefs["target_other_pct"] = c2.slider("Target 'Other' max %", 0, 50, int(prefs.get("target_other_pct",12)), 1)
    prefs["include_other"] = c3.checkbox("Include 'Other' in outputs", value=bool(prefs.get("include_other",False)))

with st.expander("Vectorization", expanded=False):
    c1,c2,c3 = st.columns(3)
    prefs["vectorizer"] = c1.selectbox("Vectorizer", ["tfidf","hashing"], index=["tfidf","hashing"].index(prefs.get("vectorizer","tfidf")))
    prefs["max_features"] = c2.number_input("Max features", 1000, 200000, int(prefs.get("max_features",30000)), 1000)
    prefs["svd_batch_size"] = c3.number_input("SVD batch size (0=all)", 0, 10000, int(prefs.get("svd_batch_size",0)), 100)

with st.expander("Save / Load Settings", expanded=False):
    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 Save Settings (no keys)"):
            path = save_prefs(prefs=prefs, include_keys=False)
            st.success(f"Saved to {path}")
    with c2:
        if st.button("🔐 Save Settings (include keys)"):
            prefs["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY","")
            prefs["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY","")
            path = save_prefs(prefs=prefs, include_keys=True)
            st.warning(f"Saved with keys to {path} (be cautious with git).")

for k in ["llm_provider","min_cluster_size","target_other_pct","include_other","vectorizer","max_features","svd_batch_size"]:
    st.session_state[k] = prefs.get(k)

st.info("Next → open **📊 Drivers & Visualization**")
