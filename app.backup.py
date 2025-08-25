import streamlit as st, os, pathlib
st.set_page_config(page_title="DWPNxt", page_icon="🧭", layout="wide")
st.markdown("<style>" + pathlib.Path("assets/theme.css").read_text() + "</style>", unsafe_allow_html=True)

st.title("DWPNxt — Digital Workplace Next")
st.write("A modern, executive-ready Top Call Driver (TCD) analytics app with offline intelligence and optional LLM labeling.")
st.markdown("""
<div class="card">
  <span class="badge">Start here</span>
  <h3>Pages</h3>
  <ul>
    <li><b>📥 Upload & Settings</b> — Upload Excel, set clustering & keys, preferences.</li>
    <li><b>📊 Drivers & Visualization</b> — Discover drivers (rules → clustering), label via Python or LLM.</li>
    <li><b>💰 Cost & ROI</b> — Cost-to-Value, savings, exports (CSV/PDF).</li>
  </ul>
</div>
""", unsafe_allow_html=True)
st.info("Use the left sidebar to switch pages.")
