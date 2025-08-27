import os, yaml, re
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

@dataclass
class TaxEntry:
    name: str
    # mapping of synonym -> weight
    synonyms: Dict[str, float]

def save_taxonomy(data: Dict[str, Any], path: str = "config/taxonomy.yaml") -> None:
    """Persist the given taxonomy dictionary to disk."""
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def load_taxonomy(path: str = "config/taxonomy.yaml") -> Dict[str, Any]:
    """Return the raw taxonomy YAML dictionary.

    On any failure or malformed file, a default ``{"taxonomy": []}`` is
    returned so the app can continue running.
    """
    try:
        with open(path) as f:
            doc = yaml.safe_load(f) or {}
        if not isinstance(doc, dict):
            return {"taxonomy": []}
        tax = doc.get("taxonomy")
        if not isinstance(tax, list):
            return {"taxonomy": []}
        return {"taxonomy": tax}
    except (FileNotFoundError, yaml.YAMLError):
        return {"taxonomy": []}


def load_taxonomy_entries(path: str = "config/taxonomy.yaml") -> List[TaxEntry]:
    """Load taxonomy YAML and convert to ``TaxEntry`` objects."""
    doc = load_taxonomy(path)
    out: List[TaxEntry] = []
    for item in doc.get("taxonomy", []):
        try:
            name = item["name"]
            syns_raw = item.get("synonyms", [])
            syns: Dict[str, float] = {}
            for s in syns_raw:
                if isinstance(s, dict):
                    for k, v in s.items():
                        try:
                            syns[str(k).lower()] = float(v)
                        except Exception:
                            continue
                else:
                    syns[str(s).lower()] = 1.0
            out.append(TaxEntry(name=name, synonyms=syns))
        except Exception:
            continue
    return out

# Strong phrase patterns to resolve conflicts
NETWORK_AP_PATTERNS = [r"access point", r"\bap\b", r"wlc", r"wireless controller", r"ssid", r"wlan", r"thin ap", r"gigabitethernet"]
ACCESS_PROV_PATTERNS = [r"add to group", r"request access", r"enablement", r"entitlement", r"grant access", r"provision"]

def match_taxonomy(text: str, entries: List[TaxEntry]) -> Tuple[str, float]:
    t = (text or "").lower()
    phrase_hits = {e.name:0.0 for e in entries}
    token_hits  = {e.name:0.0 for e in entries}
    for e in entries:
        for syn, wt in e.synonyms.items():
            if " " in syn:
                if syn in t:
                    phrase_hits[e.name] += 3 * wt
            else:
                if re.search(r"\b"+re.escape(syn)+r"\b", t):
                    token_hits[e.name] += 1 * wt

    def has_any(pats): 
        return any(re.search(p, t) for p in pats)

    scores = {name: phrase_hits[name] + token_hits[name] for name in phrase_hits}

    # Bias rules
    if has_any(NETWORK_AP_PATTERNS):
        for name in list(scores.keys()):
            if "Network Hardware" in name or "Interface" in name:
                scores[name] += 5
            if "Access Provisioning" in name:
                scores[name] -= 2
    if has_any(ACCESS_PROV_PATTERNS):
        for name in list(scores.keys()):
            if "Access Provisioning" in name:
                scores[name] += 4

    best = max(scores.items(), key=lambda kv: kv[1]) if scores else ("Other",0.0)
    return (best[0], float(best[1]))

# ---------- Backwards compatibility shim ----------
def map_text_to_taxonomy(text, entries):
    """Compatibility alias – forwards to match_taxonomy()."""
    return match_taxonomy(text, entries)
