import pandas as pd
import streamlit as st
import plotly.express as px
from analytics.tcd import load_rules, derive_drivers, estimate_aht_minutes, roi_table

st.set_page_config(page_title="DWPNxt MVP", layout="wide")
st.title("DWPNxt — Top Call Driver & Automation ROI (MVP)")
st.caption("Upload ServiceNow Excel (Incidents + ServiceRequests). Tune costs, see Top Drivers and ROI.")

with st.expander("1) Upload ServiceNow Excel", expanded=True):
    file = st.file_uploader("Choose .xlsx with sheets: Incidents, ServiceRequests", type=["xlsx"])
    st.markdown("**Expected columns (minimum):** `short_description`, `description`, `u_aht_minutes` (optional)")

if file:
    try:
        xl = pd.ExcelFile(file)
        inc = xl.parse("Incidents") if "Incidents" in xl.sheet_names else pd.DataFrame()
        req = xl.parse("ServiceRequests") if "ServiceRequests" in xl.sheet_names else pd.DataFrame()
        if not inc.empty: inc["source"] = "INC"
        if not req.empty: req["source"] = "REQ"
        df = pd.concat([inc, req], ignore_index=True, sort=False)
        st.success(f"Loaded rows — Incidents: {len(inc)} | Requests: {len(req)} | Total: {len(df)}")
        st.session_state["tickets"] = df
    except Exception as e:
        st.error(f"Excel read error: {e}")

if "tickets" in st.session_state and not st.session_state["tickets"].empty:
    df = st.session_state["tickets"]

    with st.expander("2) Cost Inputs", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        aht_guess = estimate_aht_minutes(df)
        aht = c1.number_input("Median AHT (min) if missing", 1.0, 60.0, aht_guess, 0.5)
        cost_min = c2.number_input("L1 cost per minute ($)", 0.2, 10.0, 1.20, 0.1)
        defl = c3.slider("Deflection potential (%)", 0, 100, 35, 1) / 100.0
        include_other = c4.checkbox("Include 'Other' bucket", False)

    with st.expander("3) Analyze Top Call Drivers", expanded=True):
        rules = load_rules()
        tcd_df, freq = derive_drivers(df, rules)
        if not include_other:
            freq = freq[freq["driver"] != "Other"]

        st.subheader("Top Drivers by Volume")
        fig = px.bar(freq.head(15), x="driver", y="tickets", title="Top Call Drivers")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("ROI Projection (What-if)")
        roi = roi_table(freq, aht_minutes=aht, cost_per_min=cost_min, deflection_pct=defl)
        st.dataframe(roi, use_container_width=True)
        st.download_button("Download ROI (CSV)", roi.to_csv(index=False).encode(), "dwpnxt_roi.csv", "text/csv")
else:
    st.info("Upload your Excel to begin.")
