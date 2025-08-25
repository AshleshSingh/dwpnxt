import pandas as pd, streamlit as st, plotly.express as px, os, re
from analytics.validator import validate_and_normalize
from analytics.cluster import iterative_other_reduction
from analytics.report import driver_kpis, roi_table as roi_from_kpis, crosstab, _plot_cost_value, export_pdf
from analytics.tcd import load_rules, derive_drivers, estimate_aht_minutes
from analytics.llm import llm_label_for_cluster

st.set_page_config(page_title="DWPNxt — Comprehensive TCD", layout="wide")
st.title("DWPNxt — Comprehensive Top Call Driver (TCD) & Detailed Report")
st.caption("Upload your ServiceNow Excel (Incidents + ServiceRequests). The app runs rules + clustering + optional LLM labeling and exports an executive PDF.")

# 1) Upload
with st.expander("1) Upload ServiceNow Excel", expanded=True):
    f = st.file_uploader("Upload .xlsx with sheets: 'Incidents', 'ServiceRequests'", type=["xlsx"])
    st.markdown("Minimum useful columns: **short_description**, **description**. Optional: **u_aht_minutes**, **sla_breached**, **reopen_count**, **persona/site/category**.")

if f:
    xl = pd.ExcelFile(f)
    inc = xl.parse("Incidents") if "Incidents" in xl.sheet_names else pd.DataFrame()
    req = xl.parse("ServiceRequests") if "ServiceRequests" in xl.sheet_names else pd.DataFrame()
    df, notes = validate_and_normalize(inc, req)
    st.success(f"Loaded rows: {notes['rows']}  |  Empty text: {notes['empty_text_pct']}%")
    st.session_state["df"] = df
else:
    st.info("Waiting for Excel…")

if "df" in st.session_state:
    df = st.session_state["df"]

    # 2) Parameters
    with st.expander("2) Parameters (Costs, Clustering, Coverage)", expanded=True):
        c1,c2,c3,c4 = st.columns(4)
        aht_default = estimate_aht_minutes(df, default=8.0)
        cost_per_min = c1.number_input("L1 cost per minute ($)", 0.2, 10.0, 1.20, 0.1)
        deflection = c2.slider("Deflection potential (%)", 0, 100, 35, 1)/100.0
        min_cluster_size = int(c3.number_input("Min cluster size (HDBSCAN)", 10, 200, 25, 5))
        target_other = c4.slider("Target 'Other' coverage (max %)", 0, 50, 12, 1) / 100.0
        include_other = st.checkbox("Include 'Other' in outputs", value=False)

    # 3) Rule-based first pass
    with st.expander("3) Rule-based Drivers (first pass)", expanded=True):
        rules = load_rules()
        tcd_df, freq_rules = derive_drivers(df, rules)
        tcd_df["text"] = (tcd_df["short_description"].astype(str).fillna("") + " " + tcd_df["description"].astype(str).fillna(""))
        if not include_other: freq_rules = freq_rules[freq_rules["driver"]!="Other"]
        left_pct = 100.0* (tcd_df["driver"].eq("Other").mean())
        st.write(f"Coverage after rules: **{100-left_pct:.1f}%**  |  Remaining 'Other': **{left_pct:.1f}%**")
        st.dataframe(freq_rules)

    # 4) Clustering + ITERATIVE reduction + LLM labeling
    with st.expander("4) Clustering on 'Other' + LLM Labeling", expanded=True):
        refined = iterative_other_reduction(tcd_df, target_other_pct=target_other, max_rounds=3, min_cluster_size=min_cluster_size)

        st.markdown("**Optional:** LLM labeling to rename messy cluster names")
        use_llm = st.checkbox("Use LLM labeling for discovered clusters", value=True)
        llm_model = st.text_input("LLM model (OpenAI)", value="gpt-4o-mini")

        if use_llm:
            if not os.getenv("OPENAI_API_KEY"):
                st.error("OPENAI_API_KEY not set in environment. Set it and rerun.")
            else:
                # collect sample texts per current driver
                renamed = {}
                for drv, grp in refined.groupby("driver"):
                    if drv in {"Other", "Password Reset / Unlock", "Status Checks", "Access Provisioning (Standard)"}:
                        continue  # keep rule-based good names
                    # rename if label looks generic or contains mostly stopwords/slashes
                    if any(tok in drv.lower() for tok in [" to "," the "," and "," / ","_","cluster","other"]) or len(drv.split()) <= 2:
                        try:
                            title, rationale = llm_label_for_cluster(grp["text"].astype(str).tolist(), model=llm_model)
                            if title and title.lower() not in {"unlabeled","other"}:
                                renamed[drv] = (title, rationale)
                        except Exception as e:
                            st.warning(f"LLM rename failed for '{drv}': {e}")

                if renamed:
                    for old, (new_title, _) in renamed.items():
                        refined.loc[refined["driver"]==old, "driver"] = new_title
                    st.success(f"Renamed {len(renamed)} clusters with LLM.")
                else:
                    st.info("No clusters required renaming by heuristic or LLM disabled.")

        cov_after = 100.0*(~refined["driver"].eq("Other")).mean()
        st.write(f"Coverage after clustering+iterations: **{cov_after:.1f}%** (target Other ≤ {int(target_other*100)}%)")
        freq_all = refined.groupby("driver").size().reset_index(name="Tickets").sort_values("Tickets", ascending=False)
        if not include_other:
            freq_all = freq_all[freq_all["driver"]!="Other"]
        st.dataframe(freq_all.head(25))

        fig_top = px.bar(freq_all.head(15), x="driver", y="Tickets", title="Top Call Drivers — Final (LLM-labeled)" )
        st.plotly_chart(fig_top, use_container_width=True)

        # persist for later sections
        st.session_state["refined"] = refined
        st.session_state["fig_top"] = fig_top

    # 5) KPIs, ROI, Cross-Tabs
    with st.expander("5) KPIs, ROI & Cross-Tabs", expanded=True):
        refined = st.session_state.get("refined", tcd_df)
        kpis = driver_kpis(refined if include_other else refined[refined["driver"]!="Other"])
        roi = roi_from_kpis(kpis, cost_per_min=cost_per_min, deflection=deflection)
        st.subheader("ROI Table")
        st.dataframe(roi, use_container_width=True)

        fig_value = _plot_cost_value(roi)
        st.plotly_chart(fig_value, use_container_width=True)

        # Optional crosstabs if columns exist
        tabs = st.multiselect("Crosstab by… (if present)", ["assignment_group","priority","category","subcategory","u_persona","u_site","source"], default=["source"])
        for by in tabs:
            if by in refined.columns:
                ct = crosstab(refined, by)
                if not ct.empty:
                    st.write(f"### Driver × {by}")
                    st.dataframe(ct)

        st.download_button("Download ROI (CSV)", roi.to_csv(index=False).encode(), "dwpnxt_roi.csv", "text/csv")

    # 6) Executive PDF export
    with st.expander("6) Generate Detailed Executive PDF", expanded=True):
        refined = st.session_state.get("refined", tcd_df)
        fig_top = st.session_state.get("fig_top", None)
        if st.button("Build PDF"):
            if fig_top is None:
                st.error("Please run the clustering section first to generate charts.")
            else:
                summary = {
                    "Total tickets": len(refined),
                    "Coverage (drivers assigned)": f"{100.0*(~refined['driver'].eq('Other')).mean():.1f}%",
                    "Deflection potential": f"{int(deflection*100)}%",
                    "Cost/min": f"${cost_per_min:.2f}"
                }
                fig_value = _plot_cost_value(driver_kpis(refined if include_other else refined[refined['driver']!='Other']).pipe(lambda k: roi_from_kpis(k, cost_per_min, deflection)))
                pdf_bytes = export_pdf(summary, fig_top, fig_value, roi)
                st.download_button("Download Detailed PDF", data=pdf_bytes, file_name="dwpnxt_detailed_report.pdf", mime="application/pdf")
