# DWPNxt (MVP)

Browser-based Streamlit app to analyze ServiceNow Excel exports, identify Top Call Drivers, and estimate automation ROI.

## Quickstart
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment Notes
To prevent `pandas` C-extension import errors, install a pre-built wheel and ensure the project does not contain a `pandas/` directory that could shadow the package:
```bash
pip install --force-reinstall --no-build-isolation pandas==2.2.2
```
