import numpy as np, pandas as pd, re
from typing import Tuple, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from collections import Counter
from sklearn.feature_extraction import text

CUSTOM_STOPWORDS = set(text.ENGLISH_STOP_WORDS) | {
    "please","issue","help","error","need","user","problem","thanks","thank",
    "unable","required","received","message","login","logon","link","click",
    "etc","still","using","tried","request","report","ticket","service","desk",
    "x000d","http","https","attachment","attachments","screenshot","screenshots"
}

def _clean_text(s):
    s = str(s).lower()
    s = re.sub(r"_x\d{4}_", " ", s)   # remove excel artifacts like _x000D_
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _build_vectorizer():
    return TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1,2),
        analyzer="word",
        stop_words=list(CUSTOM_STOPWORDS),
        min_df=2,
        max_df=0.85,
        max_features=30000
    )

def featurize(texts: pd.Series):
    texts = texts.map(_clean_text)
    vec = _build_vectorizer()
    X = vec.fit_transform(texts.tolist())
    svd = TruncatedSVD(n_components=min(100, max(2, int(X.shape[1]*0.2))), random_state=42)
    Xs = svd.fit_transform(X)
    return X, Xs, vec, svd

def try_hdbscan(Xs, min_cluster_size=25, min_samples=None):
    try:
        import hdbscan
        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size,
                                    min_samples=min_samples, prediction_data=True)
        labels = clusterer.fit_predict(Xs)
        return labels, "hdbscan", clusterer
    except Exception:
        return None, "none", None

def run_clustering(texts: pd.Series,
                   min_cluster_size=25,
                   kmeans_k=12) -> Tuple[np.ndarray,str,Dict]:
    X, Xs, vec, svd = featurize(texts)
    labels, algo, model = try_hdbscan(Xs, min_cluster_size=min_cluster_size)
    if labels is None or (labels.astype(int) < 0).all():
        km = KMeans(n_clusters=min(kmeans_k, max(2, int(len(texts)/min_cluster_size))), random_state=42, n_init="auto")
        labels = km.fit_predict(Xs)
        algo, model = "kmeans", km
    return labels, algo, {"vec":vec, "svd":svd, "model":model, "X":X, "Xs":Xs}

def iterative_other_reduction(df: pd.DataFrame,
                              target_other_pct=0.12,
                              max_rounds=3,
                              min_cluster_size=25) -> pd.DataFrame:
    df = df.copy()
    for _ in range(max_rounds):
        mask = df["driver"]=="Other"
        if not mask.any(): break
        if mask.mean() <= target_other_pct: break
        labels, algo, ctx = run_clustering(df.loc[mask,"text"], min_cluster_size=min_cluster_size)
        # label names → lightweight top-term strings (pre-LLM/Python labeling happens elsewhere)
        sub = pd.Series(labels, index=df.index[mask])
        df.loc[mask, "driver"] = sub.map(lambda x: f"cluster_{x}" if x != -1 else "Other")
    return df
