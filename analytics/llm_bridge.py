import os
from typing import List, Tuple, Optional
from analytics.py_label import python_label_for_cluster

# Gemini
def _try_gemini(texts: List[str], model: str) -> Optional[Tuple[str,str]]:
    try:
        from google import genai
        from google.genai import types
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key: return None
        client = genai.Client(api_key=key)
        SYSTEM = ("You label IT support tickets into concise, executive-friendly 'call drivers'. "
                  "Return a short title (3-5 words, Title Case) and a one-line rationale.")
        prompt = "Examples (trimmed):\n---\n" + "\n---\n".join([t[:280] for t in texts[:12]]) + "\n---\nReturn JSON: {\"title\":\"...\",\"rationale\":\"...\"}"
        resp = client.models.generate_content(
            model=model,
            contents=[{"role":"user","parts":[{"text": SYSTEM}]},
                      {"role":"user","parts":[{"text": prompt}]}],
            config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json", max_output_tokens=256),
        )
        import json, re
        data = json.loads((resp.text or "").strip())
        title = data.get("title","").strip() or None
        rationale = data.get("rationale","")
        if title: return (title, rationale)
    except Exception:
        return None
    return None

# OpenAI (optional)
def _try_openai(texts: List[str], model: str) -> Optional[Tuple[str,str]]:
    try:
        import openai, httpx
        if not os.getenv("OPENAI_API_KEY"): return None
        client = openai.OpenAI(http_client=httpx.Client(timeout=60.0))
        SYSTEM = ("You label IT support tickets into concise, executive-friendly 'call drivers'. "
                  "Return a short title (3-5 words, Title Case) and a one-line rationale.")
        prompt = "Examples (trimmed):\n---\n" + "\n---\n".join([t[:280] for t in texts[:12]]) + "\n---\nReturn JSON: {\"title\":\"...\",\"rationale\":\"...\"}"
        resp = client.chat.completions.create(model=model, temperature=0.2, messages=[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}])
        import json, re
        data = json.loads(resp.choices[0].message.content.strip())
        title = data.get("title","").strip() or None
        rationale = data.get("rationale","")
        if title: return (title, rationale)
    except Exception:
        return None
    return None

def best_label_for_cluster(texts: List[str], provider: str = "auto", gemini_model="gemini-2.5-flash", openai_model="gpt-4o-mini") -> Tuple[str,str,str]:
    """
    Returns: (title, rationale, source) where source ∈ {"gemini","openai","python"}
    """
    if provider in ("auto","gemini"):
        r = _try_gemini(texts, gemini_model)
        if r: return (r[0], r[1], "gemini")
    if provider in ("auto","openai"):
        r = _try_openai(texts, openai_model)
        if r: return (r[0], r[1], "openai")
    # fallback
    t, ra = python_label_for_cluster(texts)
    return (t, ra, "python")
