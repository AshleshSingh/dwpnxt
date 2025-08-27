import re, pandas as pd, yaml
from functools import lru_cache

@lru_cache(maxsize=1)
def load_rules(path="analytics/rules.yaml"):
    """Load rule definitions and compile regex patterns with caching."""
    with open(path, "r") as f:
        rules = yaml.safe_load(f)["rules"]

    compiled = []
    for rule in rules:
        words = [re.escape(w) for w in rule["keywords"]]
        pattern = re.compile(r"\b(?:" + "|".join(words) + r")\b", flags=re.IGNORECASE)
        compiled.append({"name": rule["name"], "regex": pattern})
    return compiled

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
    """Derive ticket drivers by applying cached regex patterns."""
    df = df.copy()
    cols = {c.lower().strip(): c for c in df.columns}
    sd_col = cols.get("short_description") or cols.get("short description") or "short_description"
    d_col  = cols.get("description") or "description"
    sd = _safe_text_series(df, sd_col)
    desc = _safe_text_series(df, d_col)
    text_joined = (sd + " " + desc).map(normalize_text)

    df["driver"] = "Other"
    for rule in rules:
        mask = text_joined.str.contains(rule["regex"], na=False)
        df.loc[mask & (df["driver"] == "Other"), "driver"] = rule["name"]

    summary = (
        df.groupby("driver")
        .size()
        .reset_index(name="tickets")
        .sort_values("tickets", ascending=False)
    )
    return df, summary

def estimate_aht_minutes(df, default=8.0):
    for candidate in ["u_aht_minutes","AHT","avg_handle_time"]:
        if candidate in df.columns:
            vals = pd.to_numeric(df[candidate], errors="coerce").dropna()
            if not vals.empty:
                return float(vals.median())
    return float(default)
