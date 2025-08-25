import os
import json
from typing import List, Tuple, Optional
from analytics.py_label import python_label_for_cluster


def _build_prompt(texts: List[str]) -> str:
    """Builds the prompt used for LLM labeling."""
    return (
        "Examples (trimmed):\n---\n"
        + "\n---\n".join([t[:280] for t in texts[:12]])
        + "\n---\nReturn JSON: {\"title\":\"...\",\"rationale\":\"...\"}"
    )


def _parse_label_response(raw: str) -> Tuple[str, str]:
    """Parses the JSON response from an LLM label request."""
    data = json.loads((raw or "").strip())
    return data.get("title", "").strip(), data.get("rationale", "")

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
        prompt = _build_prompt(texts)
        resp = client.models.generate_content(
            model=model,
            contents=[{"role":"user","parts":[{"text": SYSTEM}]},
                      {"role":"user","parts":[{"text": prompt}]}],
            config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json", max_output_tokens=256),
        )
        title, rationale = _parse_label_response(resp.text)
        if title:
            return (title, rationale)
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
        prompt = _build_prompt(texts)
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],
        )
        title, rationale = _parse_label_response(resp.choices[0].message.content)
        if title:
            return (title, rationale)
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
