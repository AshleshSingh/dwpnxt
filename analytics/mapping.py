import re
from typing import Dict, List, Optional
import pandas as pd

# Canonical columns we support; first two are required.
CANONICAL = [
    "short_description", "description",
    "assignment_group", "u_persona", "u_site",
    "opened_dt", "resolved_dt",
    "u_aht_minutes", "sla_breached", "reopen_count",
    "category", "subcategory", "priority", "source"
]

ALIASES: Dict[str, List[str]] = {
    "short_description": ["short_description","short description","short desc","title","summary","subject"],
    "description":       ["description","desc","details","work notes","additional comments","problem description"],
    "assignment_group":  ["assignment_group","assignment group","group","resolver group"],
    "u_persona":         ["u_persona","persona","user persona","role"],
    "u_site":            ["u_site","site","location","office","region"],
    "opened_dt":         ["opened_at","opened","created_on","created at","sys_created_on","request opened","logged at","start time"],
    "resolved_dt":       ["resolved_at","resolved","closed_at","closed at","close time","resolved on","resolution time"],
    "u_aht_minutes":     ["u_aht_minutes","aht","avg_handle_time","handle minutes","time spent"],
    "sla_breached":      ["sla_breached","breached","sla breach","sla violated","violation"],
    "reopen_count":      ["reopen_count","reopens","reopened","times reopened"],
    "category":          ["category"],
    "subcategory":       ["subcategory","sub category"],
    "priority":          ["priority","p1","p2","p3","p4"],
    "source":            ["source","channel","contact type","opened by"]
}

def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower())

def propose_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    cols = [c for c in columns if isinstance(c, str)]
    low = {_normalize(c): c for c in cols}
    mapping: Dict[str, Optional[str]] = {k: None for k in CANONICAL}

    # pass 1: exact match to canonical
    for canon in CANONICAL:
        if canon in low:
            mapping[canon] = low[canon]

    # pass 2: alias exact match
    for canon in CANONICAL:
        if mapping[canon]: continue
        for alias in ALIASES.get(canon, []):
            a = _normalize(alias)
            if a in low:
                mapping[canon] = low[a]; break

    # pass 3: partial match
    for canon in CANONICAL:
        if mapping[canon]: continue
        for c in cols:
            l = _normalize(c)
            if any(_normalize(a) in l for a in ALIASES.get(canon, [])):
                mapping[canon] = c
                break

    return mapping

def apply_mapping(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    inv = {v: k for k, v in mapping.items() if v and v in df.columns}
    if inv:
        df = df.rename(columns=inv)
    return df
