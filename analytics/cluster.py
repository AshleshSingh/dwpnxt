import numpy as np, pandas as pd, re
from typing import Tuple, Dict
from sklearn.feature_extraction.text import TfidfVectorizer, HashingVectorizer, TfidfTransformer
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD, IncrementalPCA
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

def _build_vectorizer(use_hashing=False, max_features=30000):
    if use_hashing:
        vec = HashingVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1,2),
            analyzer="word",
            stop_words=list(CUSTOM_STOPWORDS),
            n_features=max_features,
            alternate_sign=False
        )
        tfidf = TfidfTransformer()
        return vec, tfidf
    else:
        vec = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1,2),
            analyzer="word",
            stop_words=list(CUSTOM_STOPWORDS),
            min_df=2,
            max_df=0.85,
            max_features=max_features
        )
        return vec, None

def featurize(texts: pd.Series,
              use_hashing: bool = False,
              max_features: int = 30000,
              svd_batch_size: int | None = None):
    texts = texts.map(_clean_text)
    vec, tfidf = _build_vectorizer(use_hashing=use_hashing, max_features=max_features)
    if use_hashing:
        X = vec.transform(texts.tolist())
        X = tfidf.fit_transform(X)
    else:
        X = vec.fit_transform(texts.tolist())
    n_comp = min(100, max(2, int(X.shape[1]*0.2)))
    if svd_batch_size:
        svd = IncrementalPCA(n_components=n_comp, batch_size=svd_batch_size)
        for start in range(0, X.shape[0], svd_batch_size):
            svd.partial_fit(X[start:start+svd_batch_size].toarray())
        Xs = svd.transform(X.toarray())
    else:
        svd = TruncatedSVD(n_components=n_comp, random_state=42)
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

def run_clustering(texts: pd.Series | None = None,
                   min_cluster_size=25,
                   kmeans_k=12,
                   X=None,
                   Xs=None,
                   vec=None,
                   svd=None,
                   use_hashing: bool = False,
                   max_features: int = 30000,
                   svd_batch_size: int | None = None) -> Tuple[np.ndarray,str,Dict]:
    if X is None or Xs is None or vec is None or svd is None:
        if texts is None:
            raise ValueError("Either texts or precomputed features must be provided")
        X, Xs, vec, svd = featurize(texts,
                                    use_hashing=use_hashing,
                                    max_features=max_features,
                                    svd_batch_size=svd_batch_size)
    labels, algo, model = try_hdbscan(Xs, min_cluster_size=min_cluster_size)
    if labels is None or (labels.astype(int) < 0).all():
        km = KMeans(n_clusters=min(kmeans_k, max(2, int(Xs.shape[0]/min_cluster_size))), random_state=42, n_init="auto")
        labels = km.fit_predict(Xs)
        algo, model = "kmeans", km
    return labels, algo, {"vec":vec, "svd":svd, "model":model, "X":X, "Xs":Xs}

def iterative_other_reduction(df: pd.DataFrame,
                              target_other_pct=0.12,
                              max_rounds=3,
                              min_cluster_size=25,
                              use_hashing: bool = False,
                              max_features: int = 30000,
                              svd_batch_size: int | None = None) -> pd.DataFrame:
    df = df.copy()
    X, Xs, vec, svd = featurize(df["text"],
                                use_hashing=use_hashing,
                                max_features=max_features,
                                svd_batch_size=svd_batch_size)
    for _ in range(max_rounds):
        mask = df["driver"]=="Other"
        if not mask.any(): break
        if mask.mean() <= target_other_pct: break
        sub_X = X[mask.to_numpy()]
        sub_Xs = Xs[mask.to_numpy()]
        labels, algo, ctx = run_clustering(df.loc[mask,"text"],
                                           min_cluster_size=min_cluster_size,
                                           X=sub_X,
                                           Xs=sub_Xs,
                                           vec=vec,
                                           svd=svd)
        # label names → lightweight top-term strings (pre-LLM/Python labeling happens elsewhere)
        sub = pd.Series(labels, index=df.index[mask])
        df.loc[mask, "driver"] = sub.map(lambda x: f"cluster_{x}" if x != -1 else "Other")
    return df
