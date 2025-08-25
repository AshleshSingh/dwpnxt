import os, re, random, json
from typing import List, Tuple, Optional
from openai import OpenAI
import httpx

# Lazily created OpenAI and httpx clients.
_cached_client: Optional[OpenAI] = None
_cached_httpx: Optional[httpx.Client] = None


def get_client() -> Optional[OpenAI]:
    """Return a cached OpenAI client or ``None`` if the API key is missing."""
    global _cached_client, _cached_httpx
    if _cached_client is not None:
        return _cached_client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    _cached_httpx = httpx.Client(timeout=60.0)
    _cached_client = OpenAI(api_key=api_key, http_client=_cached_httpx)
    return _cached_client


def close_client() -> None:
    """Close the cached httpx client, if any."""
    global _cached_client, _cached_httpx
    if _cached_httpx is not None:
        _cached_httpx.close()
    _cached_client = None
    _cached_httpx = None

def _pick_examples(texts: List[str], k: int = 12) -> List[str]:
    texts = [t for t in texts if isinstance(t, str) and t.strip()]
    random.seed(42); random.shuffle(texts)
    return [t[:280] for t in texts[:k]]

SYSTEM = (
    "You label IT support tickets into concise, executive-friendly 'call drivers'. "
    "Return a short title (3-5 words, Title Case) and one-line rationale. "
    "Avoid stopwords. Prefer terms like VPN, Outlook, Teams, SSPR, MFA, Printer, Access, Network, Laptop, "
    "Software Install, Email, Calendar, Conferencing, Password Reset, Account Unlock, Request Status."
)

USER_TEMPLATE = """You are naming ONE cluster of IT tickets.

Examples (trimmed):
---
{examples}
---

Return JSON with:
- title: 3-5 words, Title Case, no quotes
- rationale: <= 20 words, why this cluster belongs together

Return ONLY JSON, no prose.
"""

def llm_label_for_cluster(texts: List[str], model: str = "gpt-4o-mini") -> Tuple[str,str]:
    client = get_client()
    if client is None:
        return "Unlabeled", ""

    msgs = [
        {"role":"system","content":SYSTEM},
        {"role":"user","content":USER_TEMPLATE.format(examples="\n---\n".join(_pick_examples(texts)))}
    ]
    resp = client.chat.completions.create(model=model, messages=msgs, temperature=0.2)
    content = resp.choices[0].message.content.strip()
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
