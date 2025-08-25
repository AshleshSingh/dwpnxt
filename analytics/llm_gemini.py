import os, re, random, json
from typing import List, Tuple
from google import genai
from google.genai import types

# Pick up either GEMINI_API_KEY or GOOGLE_API_KEY
_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
_client = genai.Client(api_key=_api_key)

def _pick_examples(texts: List[str], k: int = 12) -> List[str]:
    texts = [t for t in texts if isinstance(t, str) and t.strip()]
    random.seed(42); random.shuffle(texts)
    return [t[:280] for t in texts[:k]]

SYSTEM = (
    "You label IT support tickets into concise, executive-friendly 'call drivers'. "
    "Return a short title (3-5 words, Title Case) and one-line rationale. "
    "Prefer common IT terms: VPN, Outlook, Email, Teams, SSPR, MFA, Printer, Access, Network, "
    "Laptop, Software Install, Device Compliance, Conferencing, Password Reset, Unlock, Status Request."
)

USER_TEMPLATE = """You are naming ONE cluster of IT tickets.

Examples (trimmed):
---
{examples}
---

Return JSON with exactly:
{{
  "title": "<3-5 words, Title Case>",
  "rationale": "<<=20 words>"
}}

Return ONLY JSON, no prose.
"""

def gemini_label_for_cluster(texts: List[str], model: str = "gemini-2.5-flash") -> Tuple[str,str]:
    prompt = USER_TEMPLATE.format(examples="\n---\n".join(_pick_examples(texts)))

    # NOTE: google-genai uses 'config=', not 'generation_config='
    resp = _client.models.generate_content(
        model=model,
        contents=[
            {"role":"user","parts":[{"text": SYSTEM}]},
            {"role":"user","parts":[{"text": prompt}]},
        ],
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            max_output_tokens=256,
        ),
    )

    content = (resp.text or "").strip()
    try:
        data = json.loads(content)
        title = data.get("title","Unlabeled")
        rationale = data.get("rationale","")
    except Exception:
        title = re.sub(r'[^a-zA-Z0-9 /-]+',' ', content).strip()[:48] or "Unlabeled"
        rationale = ""

    # post-clean
    title = re.sub(r'\b(the|a|an|for|to|and|of|in|on)\b', '', title, flags=re.I)
    title = re.sub(r'\s+', ' ', title).strip(" -/")
    if not title: title = "Unlabeled"
    return title, rationale
