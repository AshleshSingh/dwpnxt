import pandas as pd
from typing import Tuple, Dict

REQUIRED_ANY = [["short_description","short description","Short Description"],
                ["description","Description"]]
OPTIONAL_NUMERIC = ["u_aht_minutes","AHT","avg_handle_time","reopen_count"]
OPTIONAL_BOOL = ["sla_breached","SLA breach","SLA Breach"]

def _first_existing(cols, df):
    for c in cols:
        if c in df.columns: return c
    return None

def validate_and_normalize(inc: pd.DataFrame, req: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    notes = {}
    inc = inc.copy() if inc is not None else pd.DataFrame()
    req = req.copy() if req is not None else pd.DataFrame()

    def prep(df, source):
        df = df.copy()
        df["source"] = source
        sd = _first_existing(REQUIRED_ANY[0], df)
        de = _first_existing(REQUIRED_ANY[1], df)
        if sd is None: df["short_description"] = ""; sd = "short_description"
        else: df.rename(columns={sd: "short_description"}, inplace=True)
        if de is None: df["description"] = ""; de = "description"
        else: df.rename(columns={de: "description"}, inplace=True)
        df["short_description"] = df["short_description"].astype(str).fillna("")
        df["description"] = df["description"].astype(str).fillna("")
        # optional fields
        for c in OPTIONAL_NUMERIC:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
        for c in OPTIONAL_BOOL:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip().str.lower().map(
                    {"true":True,"yes":True,"y":True,"1":True,"false":False,"no":False,"n":False,"0":False}
                )
        return df

    incp = prep(inc, "INC"); reqp = prep(req, "REQ")
    df = pd.concat([incp, reqp], ignore_index=True, sort=False)
    df["text"] = (df["short_description"].fillna("") + " " + df["description"].fillna("")).astype(str)

    notes["rows"] = len(df)
    notes["empty_text_pct"] = round(float(df["text"].str.strip().eq("").mean())*100,2)
    df["aht_min"] = pd.to_numeric(
        df[["u_aht_minutes","AHT","avg_handle_time"]].bfill(axis=1).iloc[:,0]
        if any(c in df.columns for c in ["u_aht_minutes","AHT","avg_handle_time"]) else pd.Series([None]*len(df)),
        errors="coerce"
    )
    df["reopen_count_num"] = pd.to_numeric(df.get("reopen_count", None), errors="coerce")
    df["sla_breached_bool"] = df.get("sla_breached", None)
    return df, notes
