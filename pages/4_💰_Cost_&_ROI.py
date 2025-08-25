import streamlit as st, pandas as pd, plotly.express as px, pathlib
from analytics.report import driver_kpis, roi_table as roi_from_kpis, _plot_cost_value

st.markdown("<style>" + pathlib.Path("assets/theme.css").read_text() + "</style>", unsafe_allow_html=True)
st.title("💰 Cost, ROI & FTE")

refined = st.session_state.get("refined")
if refined is None or refined.empty:
    st.warning("Please complete the **📊 Drivers & Visualization** step first.")
    st.stop()

if "final_driver" not in refined.columns:
    refined = refined.copy()
    refined["final_driver"] = refined.get("driver", "Other")

include_other = bool(st.session_state.get("include_other", False))
df_used = refined if include_other else refined[refined["final_driver"] != "Other"]

# ----- Inputs FIRST -----
c1,c2,c3 = st.columns(3)
cost_per_min = c1.number_input("L1 cost per minute ($)", 0.2, 10.0, float(st.session_state.get("cost_per_min", 1.20)), 0.1)
deflection_pct = c2.slider("Deflection potential (%)", 0, 100, int(st.session_state.get("deflection_pct", 35)), 1)
coverage = c3.selectbox("Coverage Pattern", ["24x7","16x5 (08–24)","12x5 (08–20)","Custom"], index=0)

c4,c5,c6 = st.columns(3)
off_mult = c4.number_input("Off-hours AHT multiplier", 1.0, 3.0, float(st.session_state.get("off_mult", 1.25)), 0.05)
fte_hours_week = c5.number_input("Hours per FTE per week", 20.0, 60.0, float(st.session_state.get("fte_hours_week", 40.0)), 1.0)
fte_weeks_year = c6.number_input("Weeks per year", 40.0, 54.0, float(st.session_state.get("fte_weeks_year", 52.0)), 1.0)

# custom hours if needed
if coverage == "Custom":
    cc1,cc2,cc3 = st.columns(3)
    start_h = cc1.number_input("In-hours start (0-23)", 0, 23, int(st.session_state.get("cov_start", 8)), 1)
    end_h   = cc2.number_input("In-hours end (1-24)", 1, 24, int(st.session_state.get("cov_end", 20)), 1)
    days_wk = cc3.number_input("In-hours days/week", 1, 7, int(st.session_state.get("cov_days", 5)), 1)
else:
    start_h,end_h,days_wk = (0,24,7) if coverage=="24x7" else ((8,24,5) if "16x5" in coverage else (8,20,5))

# persist
st.session_state["cost_per_min"] = float(cost_per_min)
st.session_state["deflection_pct"] = int(deflection_pct)
st.session_state["off_mult"] = float(off_mult)
if coverage == "Custom":
    st.session_state["cov_start"], st.session_state["cov_end"], st.session_state["cov_days"] = int(start_h), int(end_h), int(days_wk)

def is_in_hours(ts):
    if pd.isna(ts): return True
    dow = ts.weekday()
    in_day = dow < days_wk
    hr = ts.hour
    in_hour = start_h <= hr < end_h
    return in_day and in_hour

def effective_aht_min(df):
    base = df.get("aht_min")
    if base is None or base.isna().all():
        # derive if possible
        if "resolved_dt" in df.columns and "opened_dt" in df.columns:
            base = (pd.to_datetime(df["resolved_dt"], errors="coerce") - pd.to_datetime(df["opened_dt"], errors="coerce")).dt.total_seconds()/60.0
        else:
            base = pd.Series([8.0]*len(df), index=df.index)  # fallback
    base = pd.to_numeric(base, errors="coerce").fillna(8.0).clip(lower=1, upper=480)
    if coverage == "24x7":
        return base
    opened = pd.to_datetime(df.get("opened_dt"), errors="coerce")
    in_hours_mask = opened.apply(is_in_hours)
    eff = base.copy()
    eff[~in_hours_mask] = eff[~in_hours_mask] * float(off_mult)
    return eff

# make KPI df with one 'driver' column and adjusted AHT
df_kpi = df_used.copy()
if "driver" in df_kpi.columns: df_kpi = df_kpi.drop(columns=["driver"])
df_kpi = df_kpi.rename(columns={"final_driver":"driver"})
df_kpi["driver"] = df_kpi["driver"].astype(str).fillna("Other")
df_kpi["aht_min"] = effective_aht_min(df_kpi)

# KPIs, ROI, FTE
kpis = driver_kpis(df_kpi)
deflection = float(deflection_pct)/100.0
roi = roi_from_kpis(kpis, cost_per_min=cost_per_min, deflection=deflection)

# FTE math based on ROI $ (invert $/min)
minutes_saved_annual = roi["Annualized_Savings_$"] / float(cost_per_min)
fte_minutes_year = float(fte_hours_week) * float(fte_weeks_year) * 60.0
roi["Annualized_Saved_Minutes"] = minutes_saved_annual
roi["FTE_Saved"] = minutes_saved_annual / fte_minutes_year

st.subheader("ROI (Annualized) & FTE")
st.dataframe(roi, use_container_width=True)

fig_val = _plot_cost_value(roi)
st.plotly_chart(fig_val, use_container_width=True)

st.download_button(
    "Download ROI (CSV)",
    roi.to_csv(index=False).encode(),
    "dwpnxt_roi.csv",
    "text/csv"
)
