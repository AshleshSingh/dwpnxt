import re, pandas as pd, yaml

def load_rules(path="analytics/rules.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)["rules"]

def normalize_text(s):
    s = "" if s is None else str(s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _safe_text_series(df: pd.DataFrame, col_name: str) -> pd.Series:
    if col_name in df.columns:
        return df[col_name].astype(str).fillna("")
    return pd.Series([""] * len(df), index=df.index, dtype="string")

def derive_drivers(df, rules):
    df = df.copy()
    cols = {c.lower().strip(): c for c in df.columns}
    sd_col = cols.get("short_description") or cols.get("short description") or "short_description"
    d_col  = cols.get("description") or "description"
    sd = _safe_text_series(df, sd_col)
    desc = _safe_text_series(df, d_col)
    text_joined = (sd + " " + desc).map(normalize_text)
    buckets = []
    for t in text_joined:
        hit = None
        for rule in rules:
            if any(k in t for k in rule["keywords"]):
                hit = rule["name"]; break
        buckets.append(hit or "Other")
    df["driver"] = buckets
    return df, df.groupby("driver").size().reset_index(name="tickets").sort_values("tickets", ascending=False)

def estimate_aht_minutes(df, default=8.0):
    for candidate in ["u_aht_minutes","AHT","avg_handle_time"]:
        if candidate in df.columns:
            vals = pd.to_numeric(df[candidate], errors="coerce").dropna()
            if not vals.empty:
                return float(vals.median())
    return float(default)
