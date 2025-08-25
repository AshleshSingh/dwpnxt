from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def export_scqa_deck(summary: dict, top_ops: list[dict], roadmap: list[str]) -> bytes:
    from io import BytesIO
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W,H = A4

    # Slide 1: Title
    c.setFont("Helvetica-Bold", 22); c.drawString(40, H-80, "DWPNxt — Automation Strategy (SCQA)")
    c.setFont("Helvetica", 12)
    y = H-120
    for k,v in summary.items():
        c.drawString(40, y, f"{k}: {v}"); y -= 16
    c.showPage()

    # Slide 2: SCQA
    c.setFont("Helvetica-Bold", 18); c.drawString(40, H-60, "SCQA")
    c.setFont("Helvetica-Bold", 12); c.drawString(40, H-90, "Situation"); c.setFont("Helvetica", 11)
    c.drawString(40, H-110, "High support volume concentrated in a few call drivers with measurable AHT and breach risk.")
    c.setFont("Helvetica-Bold", 12); c.drawString(40, H-140, "Complication"); c.setFont("Helvetica", 11)
    c.drawString(40, H-160, "Drivers span identity, email, VPN, apps, + long tail; limited automation coverage today.")
    c.setFont("Helvetica-Bold", 12); c.drawString(40, H-190, "Question"); c.setFont("Helvetica", 11)
    c.drawString(40, H-210, "Where should we automate first for fastest ROI & risk reduction?")
    c.setFont("Helvetica-Bold", 12); c.drawString(40, H-240, "Answer"); c.setFont("Helvetica", 11)
    c.drawString(40, H-260, "Prioritize the top drivers with highest savings & SLA/reopen pain; deploy owned tools first.")
    c.showPage()

    # Slide 3: Top Opportunities
    c.setFont("Helvetica-Bold", 18); c.drawString(40, H-60, "Top Opportunities")
    y = H-90; c.setFont("Helvetica", 11)
    for r in top_ops[:12]:
        line = f"- {r['Driver'][:44]}  | Tickets={int(r['Tickets'])}  | AHT={r['AHT_min']:.1f}m  | Savings=${r['Annualized_Savings_$']:.0f}"
        c.drawString(40, y, line); y -= 16
        if y < 60: c.showPage(); y = H-60
    c.showPage()

    # Slide 4: 30-60-90
    c.setFont("Helvetica-Bold", 18); c.drawString(40, H-60, "30-60-90 Roadmap")
    y = H-90; c.setFont("Helvetica", 11)
    for step in roadmap:
        c.drawString(40, y, f"- {step}"); y -= 16
        if y < 60: c.showPage(); y = H-60

    c.save()
    return buf.getvalue()
