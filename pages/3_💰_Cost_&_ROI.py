import streamlit as st, pandas as pd, plotly.express as px, pathlib
from analytics.report import driver_kpis, roi_table as roi_from_kpis, _plot_cost_value, export_pdf
from analytics.tcd import estimate_aht_minutes

st.markdown("<style>" + pathlib.Path("assets/theme.css").read_text() + "</style>", unsafe_allow_html=True)
st.title("💰 Cost & ROI")

refined = st.session_state.get("refined")
if refined is None or refined.empty:
    st.warning("Please complete the **Drivers & Visualization** step first.")
    st.stop()

include_other = st.session_state.get("include_other", False)
df_used = refined if include_other else refined[refined["driver"]!="Other"]

c1,c2 = st.columns(2)
with c1:
    cost_per_min = st.number_input("L1 cost per minute ($)", 0.2, 10.0, 1.20, 0.1)
with c2:
    deflection = st.slider("Deflection potential (%)", 0, 100, 35, 1)/100.0

kpis = driver_kpis(df_used)
roi = roi_from_kpis(kpis, cost_per_min=cost_per_min, deflection=deflection)

st.subheader("ROI (Annualized)")
st.dataframe(roi, use_container_width=True)
fig_val = _plot_cost_value(roi); st.plotly_chart(fig_val, use_container_width=True)

st.download_button("Download ROI (CSV)", roi.to_csv(index=False).encode(), "dwpnxt_roi.csv", "text/csv")

fig_top = st.session_state.get("fig_top", None)
if st.button("Export Detailed Executive PDF"):
    if fig_top is None:
        st.error("Please ensure Drivers page generated the chart.")
    else:
        summary = {
            "Total tickets": len(refined),
            "Coverage (drivers assigned)": f"{100.0*(~refined['driver'].eq('Other')).mean():.1f}%",
            "Deflection potential": f"{int(deflection*100)}%",
            "Cost/min": f"${cost_per_min:.2f}"
        }
        pdf_bytes = export_pdf(summary, fig_top, fig_val, roi)
        st.download_button("Download Detailed PDF", data=pdf_bytes, file_name="dwpnxt_detailed_report.pdf", mime="application/pdf")
