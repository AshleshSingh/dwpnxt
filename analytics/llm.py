import os, re, random, json
from typing import List, Tuple
from openai import OpenAI
import httpx

# Single, reusable client. httpx will honor environment proxies automatically.
_http_client = httpx.Client(timeout=60.0)
_client_singleton = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), http_client=_http_client)

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
    msgs = [
        {"role":"system","content":SYSTEM},
        {"role":"user","content":USER_TEMPLATE.format(examples="\n---\n".join(_pick_examples(texts)))}
    ]
    resp = _client_singleton.chat.completions.create(model=model, messages=msgs, temperature=0.2)
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
