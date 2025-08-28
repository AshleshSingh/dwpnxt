import streamlit as st, pandas as pd, plotly.express as px, pathlib
st.markdown("<style>" + pathlib.Path("assets/theme.css").read_text() + "</style>", unsafe_allow_html=True)
st.title("📈 Trends & Insights")

refined = st.session_state.get("refined")
if refined is None or refined.empty:
    st.warning("Please complete Drivers step first.")
    st.stop()

df = refined.copy()
if "opened_dt" in df.columns:
    df["_month"] = pd.to_datetime(df["opened_dt"], errors="coerce").dt.to_period("M").astype(str)
else:
    df["_month"] = "Unknown"

# Monthly volume by driver
st.subheader("Monthly Volume by Final Driver")
vol = df.groupby(["_month","final_driver"]).size().reset_index(name="tickets")
fig = px.line(vol, x="_month", y="tickets", color="final_driver", markers=True)
st.plotly_chart(fig, use_container_width=True)

# Pareto (80/20)
st.subheader("Pareto — Are few drivers causing most volume?")
tot = df.groupby("final_driver").size().reset_index(name="tickets").sort_values("tickets", ascending=False)
tot["cum_pct"] = (tot["tickets"].cumsum() / tot["tickets"].sum())*100
figp = px.bar(tot, x="final_driver", y="tickets", title="Pareto by Final Driver")
st.plotly_chart(figp, use_container_width=True)
st.caption(f"Top { (tot['cum_pct']<=80).sum() } drivers contribute ~80% of all tickets.")

# SLA & Reopen
st.subheader("Quality KPIs (SLA Breach %, Reopen %)")
sla = df.groupby("final_driver")["sla_breached_bool"].mean() * 100
reo = df["reopen_count_num"].fillna(0).gt(0).groupby(df["final_driver"]).mean() * 100
kpi = (
    pd.DataFrame({"SLA_Breach_%": sla.round(1), "Reopen_Rate_%": reo.round(1)})
    .fillna(0)
    .infer_objects(copy=False)
    .sort_values("SLA_Breach_%", ascending=False)
)
st.dataframe(kpi, use_container_width=True)
