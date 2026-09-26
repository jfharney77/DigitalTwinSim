"""Native answer for one POST, for e2e/static_engine.check.mjs to compare the
in-browser engine against. Usage: native_answer.py <Component> <path> <body-json>"""
import json, os, sys
from pathlib import Path
repo = Path(__file__).resolve().parents[2]
comp, path, body = sys.argv[1:4]
py = repo / comp / "backend" / ".venv" / "bin" / "python"
if py.exists() and not os.environ.get("NATIVE_NO_REEXEC"):
    os.environ["NATIVE_NO_REEXEC"] = "1"; os.execv(str(py), [str(py), *sys.argv])
sys.path[:0] = [str(repo / comp / "backend"), str(repo)]
os.chdir(repo / comp / "backend")
from twinkit.static_dispatch import dispatch
from app.main import app
status, payload = dispatch(app, "POST", path, {}, json.loads(body))
print(json.dumps({"status": status, "body": payload}))
