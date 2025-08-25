from io import BytesIO
import pandas as pd
import xlsxwriter

def _make_unique_columns(cols):
    seen = {}
    out = []
    for c in cols:
        s = str(c)
        if s in seen:
            seen[s] += 1
            out.append(f"{s}.{seen[s]}")
        else:
            seen[s] = 0
            out.append(s)
    return out

def _write_df(ws, df, start_row=0, start_col=0):
    # header
    for j, col in enumerate(df.columns, start=start_col):
        ws.write(start_row, j, str(col))
    # rows
    for i, row in enumerate(df.itertuples(index=False), start=start_row+1):
        for j, v in enumerate(row, start=start_col):
            ws.write(i, j, "" if pd.isna(v) else v)

def build_processed_workbook(refined: pd.DataFrame) -> bytes:
    # Copy & normalize
    df = refined.copy()
    # Final Driver column
    if "final_driver" in df.columns and "Final Driver" not in df.columns:
        df["Final Driver"] = df["final_driver"].astype(str)
    if "Final Driver" not in df.columns and "driver" in df.columns:
        df["Final Driver"] = df["driver"].astype(str)
    if "Final Driver" not in df.columns:
        df["Final Driver"] = "Other"

    # Month column
    if "opened_dt" in df.columns:
        dt = pd.to_datetime(df["opened_dt"], errors="coerce")
        df["_month"] = dt.dt.to_period("M").astype(str)
        df["_month"] = df["_month"].fillna("Unknown")
    else:
        df["_month"] = "Unknown"

    # De-dup columns to avoid Excel confusion
    df.columns = _make_unique_columns(df.columns)

    # Summaries (instead of Excel pivots)
    drv = df["Final Driver"]
    by_driver = drv.value_counts(dropna=False).rename_axis("Final Driver").reset_index(name="Tickets")

    # Crosstab Driver x Month
    # Find the actual columns after de-dup (case-insensitive)
    def _find(name):
        for c in df.columns:
            if str(c).lower() == name.lower():
                return c
        for c in df.columns:
            if name.lower() in str(c).lower():
                return c
        return None
    fd_col = _find("Final Driver")
    mo_col = _find("_month")

    ct = pd.crosstab(df[fd_col], df[mo_col]).reset_index()
    ct = ct.rename(columns={fd_col: "Final Driver"})

    # Build workbook
    out = BytesIO()
    wb = xlsxwriter.Workbook(out, {'in_memory': True})

    # Data sheet
    ws_data = wb.add_worksheet("Data")
    _write_df(ws_data, df)

    # Summary sheets (driver counts and driver x month)
    ws_sum_drv = wb.add_worksheet("Summary_Drivers")
    _write_df(ws_sum_drv, by_driver)
    ws_sum_drm = wb.add_worksheet("Summary_Driver_Month")
    _write_df(ws_sum_drm, ct)

    # Chart from Summary_Drivers
    chart = wb.add_chart({'type': 'column'})
    # Use first 30 rows for readability; users can extend in Excel
    chart.add_series({
        'name':       "Tickets",
        'categories': '=Summary_Drivers!A2:A31',
        'values':     '=Summary_Drivers!B2:B31'
    })
    chart.set_title({'name': 'Top Call Drivers'})
    chart.set_x_axis({'name': 'Driver'})
    chart.set_y_axis({'name': 'Tickets'})

    ws_dash = wb.add_worksheet("Summary")
    ws_dash.write(0, 0, "DWPNxt — Top Call Drivers")
    ws_dash.insert_chart('A3', chart, {'x_scale': 1.4, 'y_scale': 1.3})

    wb.close()
    return out.getvalue()
