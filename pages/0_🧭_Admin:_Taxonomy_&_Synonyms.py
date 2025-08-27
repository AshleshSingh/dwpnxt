import streamlit as st, pathlib, yaml
from analytics.taxonomy import load_taxonomy, save_taxonomy

st.markdown("<style>" + pathlib.Path("assets/theme.css").read_text() + "</style>", unsafe_allow_html=True)
st.title("🧭 Admin: Taxonomy & Synonyms")

tax = load_taxonomy()
st.caption("Edit your DWPNxt taxonomy in place. Download, modify, and upload if you prefer editing offline.")

col1,col2 = st.columns(2)
with col1: st.download_button("Download taxonomy.yaml", data=yaml.safe_dump(tax, sort_keys=False).encode(), file_name="taxonomy.yaml", mime="text/yaml")
with col2:
    up = st.file_uploader("Upload taxonomy.yaml to replace", type=["yaml","yml"])
    if up:
        try:
            data = yaml.safe_load(up.read())
            save_taxonomy(data)
            st.success("Replaced taxonomy.yaml")
        except Exception as e:
            st.error(f"YAML error: {e}")

st.subheader("Inline Editor")
for i, cat in enumerate(tax.get("taxonomy", [])):
    with st.expander(cat["name"], expanded=False):
        new_name = st.text_input("Name", value=cat["name"], key=f"name_{i}")
        existing_syns = []
        for s in cat.get("synonyms", []):
            if isinstance(s, dict):
                k, v = next(iter(s.items()))
                existing_syns.append(f"{k}:{v}")
            else:
                existing_syns.append(str(s))
        syn = st.text_area(
            "Synonyms (comma separated)",
            value=", ".join(existing_syns),
            key=f"syn_{i}",
        )
        cat["name"] = new_name.strip() or cat["name"]
        parsed = []
        for s in syn.split(","):
            s = s.strip()
            if not s:
                continue
            if ":" in s:
                term, wt = s.split(":", 1)
                try:
                    parsed.append({term.strip(): float(wt)})
                except ValueError:
                    parsed.append(term.strip())
            else:
                parsed.append(s)
        cat["synonyms"] = parsed

if st.button("Save changes"):
    save_taxonomy(tax)
    st.success("Saved taxonomy.yaml")
