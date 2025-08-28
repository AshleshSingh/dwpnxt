import os, yaml, re
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Pattern

@dataclass
class TaxEntry:
    name: str
    # mapping of synonym -> weight
    synonyms: Dict[str, float]


@dataclass
class CompiledTaxEntry:
    """Taxonomy entry with precompiled regex patterns and weights."""
    name: str
    phrase_patterns: List[Tuple[Pattern, float]]
    token_patterns: List[Tuple[Pattern, float]]

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


def compile_taxonomy_entries(entries: List[TaxEntry]) -> List[CompiledTaxEntry]:
    """Precompile regex patterns for each taxonomy entry."""
    compiled: List[CompiledTaxEntry] = []
    for e in entries:
        phrase_pats: List[Tuple[Pattern, float]] = []
        token_pats: List[Tuple[Pattern, float]] = []
        for syn, wt in e.synonyms.items():
            if " " in syn:
                phrase_pats.append((re.compile(re.escape(syn)), wt))
            else:
                base = 0.25 if syn in GENERIC_WEAK else 1.0
                token_pats.append((re.compile(r"\b" + re.escape(syn) + r"\b"), wt * base))
        compiled.append(
            CompiledTaxEntry(
                name=e.name,
                phrase_patterns=phrase_pats,
                token_patterns=token_pats,
            )
        )
    return compiled

# Strong phrase patterns to resolve conflicts
NETWORK_AP_PATTERNS = [
    r"access point",
    r"\bap\b",
    r"wlc",
    r"wireless controller",
    r"ssid",
    r"wlan",
    r"thin ap",
    r"gigabitethernet",
]
ACCESS_PROV_PATTERNS = [
    r"add to group",
    r"request access",
    r"enablement",
    r"entitlement",
    r"grant access",
    r"provision",
]
NETWORK_AP_REGEXES = [re.compile(p) for p in NETWORK_AP_PATTERNS]
ACCESS_PROV_REGEXES = [re.compile(p) for p in ACCESS_PROV_PATTERNS]
GENERIC_WEAK = {"access"}  # downweight generic token



def match_taxonomy(text: str, entries: List[CompiledTaxEntry]) -> Tuple[str, float]:
    t = (text or "").lower()

    phrase_hits = {e.name: 0.0 for e in entries}
    token_hits = {e.name: 0.0 for e in entries}
    for e in entries:
        for pat, wt in e.phrase_patterns:
            if pat.search(t):
                phrase_hits[e.name] += 3 * wt
        for pat, wt in e.token_patterns:
            if pat.search(t):
                token_hits[e.name] += 1 * wt

    network_ap_hit = any(p.search(t) for p in NETWORK_AP_REGEXES)
    access_prov_hit = any(p.search(t) for p in ACCESS_PROV_REGEXES)

    scores = {name: phrase_hits[name] + token_hits[name] for name in phrase_hits}

    # Bias rules
    if network_ap_hit:
        for name in list(scores.keys()):
            if "Network Hardware" in name or "Interface" in name:
                scores[name] += 5
            if "Access Provisioning" in name:
                scores[name] -= 2
    if access_prov_hit:
        for name in list(scores.keys()):
            if "Access Provisioning" in name:
                scores[name] += 4

    best = max(scores.items(), key=lambda kv: kv[1]) if scores else ("Other",0.0)
    return (best[0], float(best[1]))

# ---------- Backwards compatibility shim ----------
def map_text_to_taxonomy(text: str, entries: List[CompiledTaxEntry]):
    """Compatibility alias – forwards to match_taxonomy()."""
    return match_taxonomy(text, entries)
