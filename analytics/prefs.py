import os, yaml
DEFAULT_PREFS = {
  "llm_provider": "auto",   # auto, gemini, openai, off
  "min_cluster_size": 25,
  "target_other_pct": 12,
  "include_other": False,
  "cost_per_min": 1.20,
  "deflection_pct": 35,
}
def save_prefs(path="config/user_prefs.yaml", prefs=None, include_keys=False):
  prefs = prefs or {}
  data = {**DEFAULT_PREFS, **prefs}
  if not include_keys:
    data.pop("GEMINI_API_KEY", None)
    data.pop("OPENAI_API_KEY", None)
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "w") as f: yaml.safe_dump(data, f, sort_keys=False)
  return path
def load_prefs(path="config/user_prefs.yaml"):
  if not os.path.exists(path): return DEFAULT_PREFS.copy()
  with open(path) as f: data = yaml.safe_load(f) or {}
  return {**DEFAULT_PREFS, **data}
