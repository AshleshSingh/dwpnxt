import streamlit as st, pandas as pd, plotly.express as px, pathlib
from analytics.tcd import load_rules, derive_drivers
from analytics.cluster import iterative_other_reduction
from analytics.llm_bridge import best_label_for_cluster
from analytics.taxonomy import load_taxonomy_entries, map_text_to_taxonomy, match_taxonomy

st.markdown("<style>" + pathlib.Path("assets/theme.css").read_text() + "</style>", unsafe_allow_html=True)
st.title("📊 Drivers & Visualization")

df = st.session_state.get("df")
if df is None or df.empty:
    st.warning("Please upload data on the **Upload & Settings** page first.")
    st.stop()

include_other = bool(st.session_state.get("include_other", False))
min_cluster_size = int(st.session_state.get("min_cluster_size", 25))
target_other = float(st.session_state.get("target_other_pct", 12))/100.0
provider = st.session_state.get("llm_provider","auto")

# 1) Rules pass
with st.expander("Rule-based Drivers (first pass)", expanded=True):
    rules = load_rules()
    tcd_df, freq_rules = derive_drivers(df, rules)
    tcd_df["text"] = (tcd_df["short_description"].astype(str).fillna("") + " " + tcd_df["description"].astype(str).fillna(""))
    left_pct = 100.0 * (tcd_df["driver"].eq("Other").mean())
    if not include_other: freq_rules = freq_rules[freq_rules["driver"]!="Other"]
    st.write(f"Coverage after rules: **{100-left_pct:.1f}%**  |  Remaining 'Other': **{left_pct:.1f}%**")
    st.dataframe(freq_rules, use_container_width=True)

# 2) Clustering + iterative reduction + Python/LLM rename (cluster names)
with st.expander("Clustering on 'Other' + Intelligent Labeling (Python-first, LLM optional)", expanded=True):
    refined = iterative_other_reduction(tcd_df, target_other_pct=target_other, max_rounds=3, min_cluster_size=min_cluster_size)

    # Rename all discovered cluster_* or "Other" buckets via bridge (Python → LLM when keys present)
    renamed = {}
    for drv, grp in refined.groupby("driver"):
        if drv.startswith("cluster_") or drv == "Other":
            title, rationale, source = best_label_for_cluster(grp["text"].astype(str).tolist(),
                                                              provider=provider,
                                                              gemini_model="gemini-2.5-flash",
                                                              openai_model="gpt-4o-mini")
            refined.loc[refined["driver"]==drv, "driver"] = title
            renamed[drv] = (title, source)

    if renamed:
        st.success(f"Renamed {len(renamed)} clusters (source: Python/LLM auto).")

    cov_after = 100.0*(~refined["driver"].eq("Other")).mean()
    st.write(f"Coverage after clustering+iterations: **{cov_after:.1f}%** (target Other ≤ {int(target_other*100)}%)")

# 3) Taxonomy mapping + reconciliation
with st.expander("Map to DWPNxt Taxonomy & Reconcile", expanded=True):
    entries = load_taxonomy_entries()
    # taxonomy score per row
    titles, scores = [], []
    for txt in refined["text"].astype(str).tolist():
        t, sc = map_text_to_taxonomy(txt, entries)
        titles.append(t); scores.append(sc)
    refined["taxonomy_match"] = titles
    refined["taxonomy_score"] = scores

    # choose final driver mode: Clusters, Taxonomy, or Merged (taxonomy wins if score>=2)
    mode = st.radio("Final driver mode", ["Merged (recommended)","Clusters only","Taxonomy only"], index=0)
    if mode == "Clusters only":
        refined["final_driver"] = refined["driver"]
    elif mode == "Taxonomy only":
        refined["final_driver"] = refined["taxonomy_match"].fillna("Other")
    else:
        # merged
        refined["final_driver"] = refined.apply(lambda r: r["taxonomy_match"] if (pd.notna(r["taxonomy_match"]) and r["taxonomy_score"]>=2) else r["driver"], axis=1)
    # --- Taxonomy conflict fix & fill 'Other' ---
    tx = refined["text"].astype(str).apply(lambda t: match_taxonomy(t, entries))
    refined["taxonomy_match"] = tx.apply(lambda r: r[0])
    refined["taxonomy_score"] = tx.apply(lambda r: r[1])

    # Force “access point”-style incidents to Network Hardware / Interface
    mask_ap = refined["text"].str.contains(r"\b(access point|wlc|wireless controller|wlan|ssid|thin ap|gigabitethernet)\b", case=False, na=False)
    refined.loc[mask_ap, "final_driver"] = "Network Hardware / Interface"

    # If driver is Other but taxonomy is confident, adopt taxonomy name
    need_fill = (refined["final_driver"].astype(str).eq("Other")) & (refined["taxonomy_score"] >= 2.0)
    refined.loc[need_fill, "final_driver"] = refined.loc[need_fill, "taxonomy_match"]

    st.session_state["refined"] = refined
    freq_all = refined.groupby("final_driver").size().reset_index(name="Tickets").sort_values("Tickets", ascending=False)
    if not include_other and "Other" in freq_all["final_driver"].values:
        mask = (freq_all["Tickets"] > 0) & (freq_all["final_driver"] != "Other")
        freq_all = freq_all[mask]
    st.subheader("Final Drivers")
    fig_top = px.bar(freq_all.head(15), x="final_driver", y="Tickets", title="Top Call Drivers — Final")
    st.plotly_chart(fig_top, use_container_width=True)
    st.dataframe(freq_all.head(50), use_container_width=True)
    st.session_state["freq_all"] = freq_all
    st.session_state["fig_top"] = fig_top

st.info("Next → open **📈 Trends & Insights** then **💰 Cost & ROI**.")
