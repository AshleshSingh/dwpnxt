import os, yaml, re
from typing import Dict, List

BASE_DIR = "config/views"

def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "default"

def save_view(name: str, data: Dict) -> str:
    os.makedirs(BASE_DIR, exist_ok=True)
    slug = _slugify(name)
    path = os.path.join(BASE_DIR, f"{slug}.yaml")
    with open(path, "w") as f:
        yaml.safe_dump({"name": name, "view": data}, f, sort_keys=False)
    return path

def list_views() -> List[str]:
    if not os.path.exists(BASE_DIR): return []
    return sorted([f[:-5] for f in os.listdir(BASE_DIR) if f.endswith(".yaml")])

def load_view(name_or_slug: str) -> Dict:
    slug = _slugify(name_or_slug)
    path = os.path.join(BASE_DIR, f"{slug}.yaml")
    with open(path) as f:
        doc = yaml.safe_load(f) or {}
    return doc.get("view", {})
