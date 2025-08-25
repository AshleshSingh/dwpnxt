import pandas as pd
from typing import Tuple, Dict, Optional
import re

REQUIRED_ANY = [["short_description"], ["description"]]
OPTIONAL_NUMERIC = ["u_aht_minutes","AHT","avg_handle_time","reopen_count"]
OPTIONAL_BOOL = ["sla_breached","SLA breach","SLA Breach"]
DATE_HINTS = re.compile(r"(open|create|log|start|request|fulfill|resolve|close)", re.I)

def _first_existing(cands, df):
    for c in cands:
        if c in df.columns: return c
    return None

def _norm_text_cols(df):
    sd = _first_existing(REQUIRED_ANY[0], df) or "short_description"
    de = _first_existing(REQUIRED_ANY[1], df) or "description"
    if sd not in df.columns: df[sd] = ""
    if de not in df.columns: df[de] = ""
    df.rename(columns={sd:"short_description", de:"description"}, inplace=True)
    df["short_description"] = df["short_description"].astype(str).fillna("")
    df["description"] = df["description"].astype(str).fillna("")
    return df

def _parse_dates(df):
    # opened_dt
    if "opened_dt" in df.columns:
        df["opened_dt"] = pd.to_datetime(df["opened_dt"], errors="coerce")
    else:
        date_cols = [c for c in df.columns if DATE_HINTS.search(c)]
        best = None
        for c in date_cols:
            s = pd.to_datetime(df[c], errors="coerce")
            if s.notna().sum() > 0:
                best = s if best is None else s.combine_first(best)
        df["opened_dt"] = best if best is not None else pd.NaT
    # resolved_dt
    if "resolved_dt" in df.columns:
        df["resolved_dt"] = pd.to_datetime(df["resolved_dt"], errors="coerce")
    else:
        cands = [c for c in df.columns if re.search(r"(resolve|close|complete)", c, re.I)]
        best = None
        for c in cands:
            s = pd.to_datetime(df[c], errors="coerce")
            if s.notna().sum() > 0:
                best = s if best is None else s.combine_first(best)
        df["resolved_dt"] = best if best is not None else pd.NaT
    return df

def validate_and_normalize(inc: pd.DataFrame, req: pd.DataFrame, mapping: Optional[Dict]=None) -> Tuple[pd.DataFrame, Dict]:
    notes = {}
    inc = inc.copy() if inc is not None else pd.DataFrame()
    req = req.copy() if req is not None else pd.DataFrame()

    if mapping:
        from analytics.mapping import apply_mapping
        inc = apply_mapping(inc, mapping)
        req = apply_mapping(req, mapping)

    def prep(df, source):
        df = df.copy()
        df["source"] = source
        df = _norm_text_cols(df)
        for c in OPTIONAL_NUMERIC:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
        for c in OPTIONAL_BOOL:
            if c in df.columns:
                df[c] = (df[c].astype(str).str.strip().str.lower()
                         .map({"true":True,"yes":True,"y":True,"1":True,"false":False,"no":False,"n":False,"0":False}))
        df = _parse_dates(df)
        return df

    incp = prep(inc, "INC"); reqp = prep(req, "REQ")
    df = pd.concat([incp, reqp], ignore_index=True, sort=False)

    df["text"] = (df["short_description"].fillna("") + " " + df["description"].fillna("")).astype(str)

    # prefer provided AHT; else derive from dates
    provided = None
    if any(c in df.columns for c in ["u_aht_minutes","AHT","avg_handle_time"]):
        provided = pd.to_numeric(df[["u_aht_minutes","AHT","avg_handle_time"]].bfill(axis=1).iloc[:,0], errors="coerce")
    derived = (df["resolved_dt"] - df["opened_dt"]).dt.total_seconds()/60.0
    df["aht_min"] = provided.fillna(derived) if provided is not None else derived
    df["aht_min"] = df["aht_min"].clip(lower=1, upper=480)

    df["reopen_count_num"] = pd.to_numeric(df.get("reopen_count", None), errors="coerce")
    df["sla_breached_bool"] = df.get("sla_breached", None)

    notes["rows"] = len(df)
    notes["empty_text_pct"] = round(float(df["text"].str.strip().eq("").mean())*100,2)

    return df, notes
