import yaml, re
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class TaxEntry:
    name: str
    synonyms: List[str]

def load_taxonomy(path: str = "config/taxonomy.yaml") -> List[TaxEntry]:
    with open(path) as f:
        doc = yaml.safe_load(f)
    out = []
    for item in doc.get("taxonomy", []):
        out.append(TaxEntry(name=item["name"], synonyms=[str(s).lower() for s in item.get("synonyms", [])]))
    return out

# Strong phrase patterns to resolve conflicts
NETWORK_AP_PATTERNS = [r"access point", r"\bap\b", r"wlc", r"wireless controller", r"ssid", r"wlan", r"thin ap", r"gigabitethernet"]
ACCESS_PROV_PATTERNS = [r"add to group", r"request access", r"enablement", r"entitlement", r"grant access", r"provision"]
GENERIC_WEAK = {"access"}  # downweight generic token

def match_taxonomy(text: str, entries: List[TaxEntry]) -> Tuple[str, float]:
    t = (text or "").lower()
    phrase_hits = {e.name:0 for e in entries}
    token_hits  = {e.name:0 for e in entries}
    for e in entries:
        for syn in e.synonyms:
            if " " in syn:
                if syn in t:
                    phrase_hits[e.name] += 3
            else:
                if re.search(r"\b"+re.escape(syn)+r"\b", t):
                    token_hits[e.name] += 1 if syn not in GENERIC_WEAK else 0.25

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
