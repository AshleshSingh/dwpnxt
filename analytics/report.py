import io, pandas as pd, plotly.express as px
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

def driver_kpis(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if "driver" not in d.columns and "final_driver" in d.columns:
        d = d.rename(columns={"final_driver": "driver"})
    d["driver"] = d["driver"].astype(str).fillna("Other")
    gp = d.groupby("driver", dropna=False)
    out = pd.DataFrame({
        "Tickets": gp.size(),
        "With_AHT": gp["aht_min"].apply(lambda s: s.notna().sum()),
        "Median_AHT": gp["aht_min"].median(),
        "SLA_Breach_%": gp["sla_breached_bool"].mean()*100,
        "Reopen_Rate_%": gp["reopen_count_num"].fillna(0).gt(0).mean()*100
    }).fillna(0).reset_index()
    return out.sort_values("Tickets", ascending=False)

def roi_table(kpis: pd.DataFrame, cost_per_min: float, deflection: float) -> pd.DataFrame:
    aht = kpis["Median_AHT"].fillna(kpis["Median_AHT"].median()).replace({0:kpis["Median_AHT"].median() or 8.0})
    baseline = kpis["Tickets"] * aht * cost_per_min
    savings = baseline * deflection
    kpis = kpis.copy()
    kpis["Annualized_Savings_$"] = savings.round(2)
    kpis["AHT_min"] = aht
    return kpis[["driver","Tickets","AHT_min","SLA_Breach_%","Reopen_Rate_%","Annualized_Savings_$"]].rename(columns={"driver":"Driver"})

def crosstab(df: pd.DataFrame, by: str) -> pd.DataFrame:
    if by not in df.columns: return pd.DataFrame()
    tab = pd.crosstab(df["driver"], df[by]).sort_values(by=list(df[by].value_counts().index), ascending=False)
    return tab

def _plot_top_bar(df: pd.DataFrame):
    fig = px.bar(df.head(15), x="driver", y="Tickets", title="Top Call Drivers")
    fig.update_layout(margin=dict(l=10,r=10,t=40,b=10), height=400)
    return fig

def _plot_cost_value(roi: pd.DataFrame):
    fig = px.bar(roi.head(15), x="Driver", y="Annualized_Savings_$", title="Cost → Value (Annualized Savings)")
    fig.update_layout(margin=dict(l=10,r=10,t=40,b=10), height=400)
    return fig

def export_pdf(summary: dict, top_bar_fig, value_fig, roi_df: pd.DataFrame) -> bytes:
    # export plots to PNG in-memory
    top_png = top_bar_fig.to_image(format="png", scale=2)
    val_png = value_fig.to_image(format="png", scale=2)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W,H = A4

    c.setFont("Helvetica-Bold", 14); c.drawString(24, H-40, "DWPNxt — Detailed TCD & ROI Report")
    c.setFont("Helvetica", 10)
    y = H-60
    for k,v in summary.items():
        c.drawString(24, y, f"{k}: {v}")
        y -= 14

    # charts
    y -= 6
    c.drawImage(ImageReader(io.BytesIO(top_png)), 24, y-200, width=W-48, height=200, preserveAspectRatio=True, mask='auto')
    y -= 210
    c.drawImage(ImageReader(io.BytesIO(val_png)), 24, y-200, width=W-48, height=200, preserveAspectRatio=True, mask='auto')
    c.showPage()

    # top ROI table (first 25 rows)
    c.setFont("Helvetica-Bold", 12); c.drawString(24, H-40, "Top Opportunities (ROI)")
    c.setFont("Helvetica", 9)
    y = H-60
    for _, r in roi_df.head(25).iterrows():
        line = f"{r['Driver'][:40]:40}  Tickets={int(r['Tickets']):6d}  AHT={r['AHT_min']:.1f}m  Savings=${r['Annualized_Savings_$']:.2f}"
        c.drawString(24, y, line); y -= 12
        if y < 40: c.showPage(); y = H-40
    c.save()
    return buf.getvalue()
