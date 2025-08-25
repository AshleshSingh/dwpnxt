import streamlit as st, pathlib
st.set_page_config(page_title="DWPNxt", page_icon="🧭", layout="wide")
st.markdown("<style>" + pathlib.Path("assets/theme.css").read_text() + "</style>", unsafe_allow_html=True)

st.markdown("""
<div style="display:flex;gap:18px;align-items:center;">
  <div style="font-size:42px;line-height:1;font-weight:800;">DWPNxt</div>
  <div class="badge">Near-Zero-Touch Experience</div>
</div>
<p class="hint">Upload once, analyze across pages. Python intelligence by default; optional LLM when a key is present.</p>
""", unsafe_allow_html=True)

st.divider()
st.subheader("Start here")
c1,c2,c3,c4 = st.columns(4)
with c1: st.page_link("pages/1_📥_Upload_&_Settings.py", label="📥 Upload & Settings", use_container_width=True)
with c2: st.page_link("pages/2_📊_Drivers_&_Visualization.py", label="📊 Drivers & Visualization", use_container_width=True)
with c3: st.page_link("pages/3_📈_Trends_&_Insights.py", label="📈 Trends & Insights", use_container_width=True)
with c4: st.page_link("pages/4_💰_Cost_&_ROI.py", label="💰 Cost & ROI", use_container_width=True)

st.divider()
st.subheader("What’s inside")
st.markdown("""
- **Python-first labeling** (rules → clustering → taxonomy & synonyms).  
- **Optional LLM (Gemini/OpenAI)** if you paste a key.  
- **Cache across pages** so analysis doesn’t re-run until you upload a new file.  
- **Processed Excel export** with pivots and charts for drill-downs.
""")
