import re
import pandas as pd
import yaml
from collections import Counter

def load_rules(path="analytics/rules.yaml"):
    with open(path, "r") as f:
      return yaml.safe_load(f)["rules"]

def normalize_text(s):
    if pd.isna(s): return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def derive_drivers(df, rules):
    # make a working text column
    df = df.copy()
    text = (df.get("short_description", "") + " " + df.get("description", "")).fillna("").map(normalize_text)

    # keyword bucket hits
    driver_hits = []
    for i, t in enumerate(text):
        matched = None
        for rule in rules:
            if any(k in t for k in rule["keywords"]):
                matched = rule["name"]; break
        driver_hits.append(matched or "Other")
    df["driver"] = driver_hits

    # frequency table
    freq = df.groupby("driver").size().reset_index(name="tickets")
    freq = freq.sort_values("tickets", ascending=False)
    return df, freq

def estimate_aht_minutes(srs_df, default=8.0):
    col = "u_aht_minutes"
    if col in srs_df.columns and srs_df[col].notna().any():
        v = srs_df[col].dropna()
        return float(v.median())
    return float(default)

def roi_table(freq_df, aht_minutes=8.0, cost_per_min=1.0, deflection_pct=0.35):
    rows = []
    for _, r in freq_df.iterrows():
        driver = r["driver"]
        tickets = int(r["tickets"])
        baseline_cost = tickets * aht_minutes * cost_per_min
        benefit = baseline_cost * deflection_pct
        rows.append({
            "Driver": driver,
            "Tickets": tickets,
            "AHT_min": aht_minutes,
            "Cost_per_min": cost_per_min,
            "Deflection_%": round(deflection_pct*100,1),
            "Annualized_Savings_$": round(benefit, 2)
        })
    out = pd.DataFrame(rows).sort_values("Annualized_Savings_$", ascending=False)
    return out