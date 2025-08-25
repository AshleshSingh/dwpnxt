import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib, io, zipfile

from analytics.xlsx_export import build_processed_workbook
from analytics.report import driver_kpis, roi_table as roi_from_kpis
from analytics.views_store import save_view, list_views, load_view

# Theme
st.markdown("<style>" + pathlib.Path("assets/theme.css").read_text() + "</style>", unsafe_allow_html=True)
st.title("🔎 Assignment Group Drill-down")

refined = st.session_state.get("refined")
if refined is None or refined.empty:
    st.warning("Please complete **📊 Drivers & Visualization** first.")
    st.stop()

df = refined.copy()

# Month column
if "opened_dt" in df.columns:
    dt = pd.to_datetime(df["opened_dt"], errors="coerce")
    df["_month"] = dt.dt.to_period("M").astype(str).fillna("Unknown")
else:
    df["_month"] = "Unknown"

df["Final Driver"] = df.get("final_driver", df.get("driver", "Other")).astype(str)

ag_col = "assignment_group" if "assignment_group" in df.columns else None
persona_col = "u_persona" if "u_persona" in df.columns else None
site_col    = "u_site" if "u_site" in df.columns else None

# Saved Views
with st.expander("Saved Views", expanded=False):
    colA, colB, colC = st.columns(3)
    with colA:
        preset_name = st.text_input("View name", key="view_name")
        if st.button("Save current selection"):
            st.session_state.setdefault("dd_drivers", [])
            st.session_state.setdefault("dd_months", [])
            st.session_state.setdefault("dd_ags", [])
            st.session_state.setdefault("dd_personas", [])
            st.session_state.setdefault("dd_sites", [])
            view = {
                "drivers":  st.session_state["dd_drivers"],
                "months":   st.session_state["dd_months"],
                "ags":      st.session_state["dd_ags"],
                "personas": st.session_state["dd_personas"],
                "sites":    st.session_state["dd_sites"],
            }
            st.success(f"Saved view → {save_view(preset_name or 'default', view)}")
    with colB:
        options = list_views()
        chosen = st.selectbox("Load view", options if options else ["(none)"], index=0)
        if options and st.button("Apply view"):
            v = load_view(chosen)
            st.session_state["dd_drivers"]  = v.get("drivers", [])
            st.session_state["dd_months"]   = v.get("months", [])
            st.session_state["dd_ags"]      = v.get("ags", [])
            st.session_state["dd_personas"] = v.get("personas", [])
            st.session_state["dd_sites"]    = v.get("sites", [])
            st.rerun()
    with colC:
        if st.button("Clear selection"):
            for k in ["dd_drivers","dd_months","dd_ags","dd_personas","dd_sites"]:
                st.session_state.pop(k, None)
            st.rerun()

drivers = sorted(df["Final Driver"].dropna().unique().tolist())
months  = sorted(df["_month"].dropna().unique().tolist(), key=lambda s: (s=="Unknown", s))
ag_opts = sorted(df[ag_col].dropna().unique().tolist()) if ag_col else []
per_opts= sorted(df[persona_col].dropna().unique().tolist()) if persona_col else []
site_opts=sorted(df[site_col].dropna().unique().tolist()) if site_col else []

fcols = st.columns(5)
sel_driver  = fcols[0].multiselect("Driver", drivers, default=st.session_state.get("dd_drivers", drivers[: min(8, len(drivers))]), key="dd_drivers")
sel_month   = fcols[1].multiselect("Month", months, default=st.session_state.get("dd_months", months), key="dd_months")
sel_ag      = fcols[2].multiselect("Assignment Group", ag_opts, default=st.session_state.get("dd_ags", []), key="dd_ags")
sel_persona = fcols[3].multiselect("Persona", per_opts, default=st.session_state.get("dd_personas", []), key="dd_personas")
sel_site    = fcols[4].multiselect("Site", site_opts, default=st.session_state.get("dd_sites", []), key="dd_sites")

mask = pd.Series(True, index=df.index)
if sel_driver:  mask &= df["Final Driver"].isin(sel_driver)
if sel_month:   mask &= df["_month"].isin(sel_month)
if ag_col and sel_ag:           mask &= df[ag_col].isin(sel_ag)
if persona_col and sel_persona: mask &= df[persona_col].isin(sel_persona)
if site_col and sel_site:       mask &= df[site_col].isin(sel_site)

fdf = df.loc[mask].copy()

# Metrics
c1,c2,c3 = st.columns(3)
c1.metric("Tickets (filtered)", f"{len(fdf):,}")
sla = fdf["sla_breached_bool"].mean()*100 if "sla_breached_bool" in fdf.columns else 0.0
c2.metric("SLA Breach %", f"{sla:.1f}%")
reo = fdf["reopen_count_num"].fillna(0).gt(0).mean()*100 if "reopen_count_num" in fdf.columns else 0.0
c3.metric("Reopen Rate %", f"{reo:.1f}%")

# Charts / tables
if ag_col:
    g = fdf.groupby([ag_col, "Final Driver"]).size().reset_index(name="Tickets").sort_values("Tickets", ascending=False)
    st.subheader("Tickets by Assignment Group × Driver")
    fig = px.bar(g, x=ag_col, y="Tickets", color="Final Driver", title="Volume by Assignment Group", barmode="stack")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(g, use_container_width=True)
else:
    st.info("No `assignment_group` column detected. Showing Driver × Month.")
    g = fdf.groupby(["Final Driver","_month"]).size().reset_index(name="Tickets")
    fig = px.bar(g, x="_month", y="Tickets", color="Final Driver", title="Volume by Month", barmode="stack")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(g, use_container_width=True)

st.subheader("Filtered Incidents (detail)")
st.dataframe(fdf, use_container_width=True)

# Exports (filtered slice)
colA, colB, colC = st.columns(3)
with colA:
    st.download_button(
        "Download Filtered CSV",
        fdf.to_csv(index=False).encode(),
        "DWPNxt_Filtered.csv",
        "text/csv",
        use_container_width=True
    )
with colB:
    xbytes = build_processed_workbook(fdf)
    st.download_button(
        "Download Filtered Excel (summary)",
        xbytes,
        "DWPNxt_Filtered.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ROI for filtered slice (reuse session settings)
cost_per_min = float(st.session_state.get("cost_per_min", 1.20))
deflection   = float(st.session_state.get("deflection_pct", 35)) / 100.0
df_kpi = fdf.copy()
if "driver" in df_kpi.columns: df_kpi = df_kpi.drop(columns=["driver"])
df_kpi = df_kpi.rename(columns={"Final Driver":"driver"})
kpis = driver_kpis(df_kpi)
roi  = roi_from_kpis(kpis, cost_per_min=cost_per_min, deflection=deflection)

with colC:
    st.download_button(
        "Download Filtered ROI (CSV)",
        roi.to_csv(index=False).encode(),
        "DWPNxt_Filtered_ROI.csv",
        "text/csv",
        use_container_width=True
    )

st.divider()
st.subheader("📦 Export Outputs (ZIP only)")

# Outputs-only ZIP
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
    z.writestr("outputs/DWPNxt_Filtered.csv", fdf.to_csv(index=False))
    z.writestr("outputs/DWPNxt_Filtered.xlsx", xbytes)
    z.writestr("outputs/DWPNxt_Filtered_ROI.csv", roi.to_csv(index=False))
st.download_button("Download Outputs ZIP", data=buf.getvalue(), file_name="DWPNxt_Outputs.zip", mime="application/zip", use_container_width=True)
