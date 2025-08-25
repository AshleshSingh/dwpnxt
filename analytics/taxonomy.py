import yaml, re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class TaxEntry:
    name: str
    synonyms: List[str]


def load_taxonomy(path: str = "config/taxonomy.yaml") -> Dict:
    """Load taxonomy definitions as a dictionary.

    Returns an empty dict when the file is missing or malformed so the app can
    continue running without crashing.
    """
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}


def save_taxonomy(data: Dict, path: str = "config/taxonomy.yaml") -> None:
    """Persist taxonomy definitions back to YAML."""
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def load_taxonomy_entries(path: str = "config/taxonomy.yaml") -> List[TaxEntry]:
    """Return taxonomy as a list of TaxEntry objects for matching."""
    doc = load_taxonomy(path)
    out: List[TaxEntry] = []
    for item in doc.get("taxonomy", []):
        out.append(
            TaxEntry(
                name=item["name"],
                synonyms=[str(s).lower() for s in item.get("synonyms", [])],
            )
        )
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
