import pandas as pd, streamlit as st, plotly.express as px
from analytics.validator import validate_and_normalize
from analytics.cluster import run_clustering, label_clusters, iterative_other_reduction
from analytics.report import driver_kpis, roi_table as roi_from_kpis, crosstab, _plot_top_bar, _plot_cost_value, export_pdf
from analytics.tcd import load_rules, derive_drivers, estimate_aht_minutes

st.set_page_config(page_title="DWPNxt — Comprehensive TCD", layout="wide")

st.title("DWPNxt — Comprehensive Top Call Driver (TCD) & Detailed Report")
st.caption("Upload your ServiceNow Excel (Incidents + ServiceRequests). The app runs rules + clustering and exports an executive PDF.")

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
        if not include_other: freq_rules = freq_rules[freq_rules["driver"]!="Other"]
        left_pct = 100.0* (tcd_df["driver"].eq("Other").mean())
        st.write(f"Coverage after rules: **{100-left_pct:.1f}%**  |  Remaining 'Other': **{left_pct:.1f}%**")
        st.dataframe(freq_rules)

    # 4) Clustering pass on 'Other' + iterative reduction
    with st.expander("4) Clustering on 'Other' (HDBSCAN→KMeans fallback) & Iterative Reduction", expanded=True):
        refined = iterative_other_reduction(tcd_df, target_other_pct=target_other, max_rounds=3, min_cluster_size=min_cluster_size)
        cov_after = 100.0*(~refined["driver"].eq("Other")).mean()
        st.write(f"Coverage after clustering+iterations: **{cov_after:.1f}%** (target Other ≤ {int(target_other*100)}%)")
        freq_all = refined.groupby("driver").size().reset_index(name="Tickets").sort_values("Tickets", ascending=False)
        if not include_other:
            freq_all = freq_all[freq_all["driver"]!="Other"]
        st.dataframe(freq_all.head(25))

        # charts
        fig_top = px.bar(freq_all.head(15), x="driver", y="Tickets", title="Top Call Drivers — Final")
        st.plotly_chart(fig_top, use_container_width=True)

    # 5) KPIs, ROI, Cross-tabs
    with st.expander("5) KPIs, ROI & Cross-Tabs", expanded=True):
        kpis = driver_kpis(refined if include_other else refined[refined["driver"]!="Other"])
        roi = roi_from_kpis(kpis, cost_per_min=cost_per_min, deflection=deflection)
        st.subheader("ROI Table")
        st.dataframe(roi, use_container_width=True)

        # extra chart
        fig_value = _plot_cost_value(roi)
        st.plotly_chart(fig_value, use_container_width=True)

        # Optional crosstabs if columns exist
        tabs = st.multiselect("Crosstab by… (if present)", ["assignment_group","priority","category","subcategory","u_persona","u_site","source"], default=["source"])
        for by in tabs:
            ct = crosstab(refined, by)
            if not ct.empty:
                st.write(f"### Driver × {by}")
                st.dataframe(ct)

        st.download_button("Download ROI (CSV)", roi.to_csv(index=False).encode(), "dwpnxt_roi.csv", "text/csv")

    # 6) Executive PDF export
    with st.expander("6) Generate Detailed Executive PDF", expanded=True):
        if st.button("Build PDF"):
            summary = {
                "Total tickets": len(refined),
                "Coverage (drivers assigned)": f"{100.0*(~refined['driver'].eq('Other')).mean():.1f}%",
                "Deflection potential": f"{int(deflection*100)}%",
                "Cost/min": f"${cost_per_min:.2f}"
            }
            pdf_bytes = export_pdf(summary, fig_top, fig_value, roi)
            st.download_button("Download Detailed PDF", data=pdf_bytes, file_name="dwpnxt_detailed_report.pdf", mime="application/pdf")
