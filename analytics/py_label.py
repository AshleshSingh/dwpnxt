import re, pandas as pd
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
import yake

# Canonical IT buckets → synonyms
CANON = {
  "Password Reset / Unlock": ["password","unlock","locked","reset","sspr","account lock","forgot"],
  "MFA / SSO / Identity": ["mfa","otp","verify","authenticator","2fa","okta","duo","azure ad","sso","adfs"],
  "Email / Outlook": ["outlook","email","o365","office 365","mailbox","send","receive","calendar","pst"],
  "Conferencing / Teams / Zoom": ["teams","zoom","webex","meeting","audio","video","microphone","camera"],
  "VPN / Network Access": ["vpn","globalprotect","anyconnect","zscaler","proxy","ssl","connect","tunnel"],
  "Network Hardware / Interface": ["switch","router","firewall","cisco","interface","gigabitethernet","uplink","latency","packet loss"],
  "Device / Laptop / Desktop": ["laptop","desktop","pc","boot","battery","keyboard","touchpad","screen","monitor"],
  "Printing / Scanning": ["printer","print","zebra","scan","driver","toner"],
  "Access Provisioning": ["access","add to group","entitlement","license","provision","enable","request access"],
  "Software Install / Update": ["install","installation","update","patch","deployment","intune","sccm","software center"],
  "Storage / OneDrive / SharePoint": ["onedrive","sharepoint","sync","drive","share","permission","library"],
  "Enterprise App — SAP": ["sap","gui","sso sap","saplogon"],
  "Enterprise App — Veeva Vault": ["veeva","vault"],
  "Security / Endpoint": ["defender","antivirus","threat","malware","bitlocker","encryption","policy","compliance"],
  "Telephony / Mobile": ["iphone","ipad","android","mobile","sim","telephony","softphone","ring","call"],
  "Status / Request Updates": ["status","update","where is","eta","progress","check status"],
}

STOPWORDS = set("""
the to for and of in on a an with is are was were be been being from into via by
please need issue help error problem user request ticket desk service still using tried
http https x000d attach attachment screenshot etc link click
""".split())

def _tokens(s: str):
    s = s.lower()
    s = re.sub(r"_x\d{4}_"," ",s)
    s = re.sub(r"[^a-z0-9\s]"," ",s)
    toks = [t for t in s.split() if len(t)>2 and t not in STOPWORDS]
    return toks

def _score_against_canon(tokens):
    cnt = Counter(tokens)
    best_label, best_score = None, 0
    for label, keys in CANON.items():
        score = sum(cnt[k] for k in keys if k in cnt)
        # also partials
        score += sum(v for k,v in cnt.items() if any(k.startswith(p) for p in keys))
        if score > best_score:
            best_label, best_score = label, score
    return best_label, best_score

def _yake_keywords(texts, topk=5):
    kw = yake.KeywordExtractor(lan="en", n=1, top=topk)
    joined = " ".join(texts)[:50000]
    try:
        cand = [w for w,_ in kw.extract_keywords(joined)]
        return [c for c in cand if c not in STOPWORDS][:topk]
    except Exception:
        return []

def python_label_for_cluster(texts):
    texts = [t for t in texts if isinstance(t,str)]
    toks = []
    for t in texts:
        toks.extend(_tokens(t))
    label, score = _score_against_canon(toks)
    if label and score>=2:
        rationale = "Matched IT lexicon by keyword frequency."
        return label, rationale
    # fall back to TF-IDF top terms
    try:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1,2), max_features=1000)
        X = vec.fit_transform(texts)
        sums = X.sum(axis=0).A1
        terms = vec.get_feature_names_out()
        top = [t for _,t in sorted(zip(sums,terms), reverse=True)[:4] if t not in STOPWORDS]
    except Exception:
        top = []
    if not top:
        top = _yake_keywords(texts, topk=4)
    title = " / ".join(top[:4]) if top else "Other"
    return title.title(), "Auto-labeled by keyword salience."
