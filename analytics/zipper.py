import io, zipfile, os, glob
from typing import Dict, Tuple

def build_zip(file_map: Dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path, data in file_map.items():
            z.writestr(path, data)
    return buf.getvalue()

def pick_project_files() -> list[str]:
    # Include code & config; skip heavy/secret dirs
    globs = [
        "DWPNxt.py",
        "requirements.txt",
        "README.md",
        "assets/theme.css",
        "config/taxonomy.yaml",
        "config/user_prefs.yaml",
        ".streamlit/config.toml",
        "analytics/*.py",
        "analytics/*.yaml",
        "pages/*.py",
    ]
    files = []
    for g in globs:
        files.extend(glob.glob(g))
    # filter out non-existing
    return [f for f in files if os.path.isfile(f)]
