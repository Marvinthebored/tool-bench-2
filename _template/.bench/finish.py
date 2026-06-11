#!/usr/bin/env python3
import hashlib, json, os, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS_DIR = ROOT / "timestamps"
RESULTS = ROOT / "results"
STATE = ROOT / ".bench" / "state"

sys.path.insert(0, str(ROOT / ".bench"))
from ts_util import make_timestamp

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def make_readonly(path):
    if path.is_file():
        os.chmod(path, 0o444)
    elif path.is_dir():
        for child in path.iterdir():
            make_readonly(child)
        os.chmod(path, 0o555)

def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

if not (TS_DIR / "start.json").exists():
    die("Not started.")

if (TS_DIR / "end.json").exists():
    die("Already finished. If you want to submit corrections, run ./benchctl extra")

# Hash and snapshot results as they stand at finish time
output_hashes = {}
output_mtimes = {}
for p in sorted(RESULTS.rglob("*")):
    if p.is_file() and p.name != ".gitkeep":
        rel = str(p.relative_to(ROOT))
        output_hashes[rel] = sha256(p)
        output_mtimes[rel] = int(p.stat().st_mtime * 1000)

start = json.loads((TS_DIR / "start.json").read_text())
ts = make_timestamp()
elapsed = (ts["epoch_ms"] - start["epoch_ms"]) / 1000

ts["event"] = "finish"
ts["cwd"] = str(ROOT)
ts["tool_bench_version"] = "tb2"
ts["output_hashes"] = output_hashes
ts["output_mtimes"] = output_mtimes

tmp = TS_DIR / "end.json.tmp"
tmp.write_text(json.dumps(ts, indent=2) + "\n")
tmp.replace(TS_DIR / "end.json")

# Copy results into a snapshot so the assessor can score the primary submission
# even if the bot later corrects files before running extra.
snapshot_dir = STATE / "snapshot"
if snapshot_dir.exists():
    shutil.rmtree(snapshot_dir)
shutil.copytree(RESULTS, snapshot_dir)

STATE.mkdir(parents=True, exist_ok=True)
finished = {"finished_at": ts["epoch_ms"], "output_hashes": output_hashes}
tmp = STATE / "finished.json.tmp"
tmp.write_text(json.dumps(finished, indent=2) + "\n")
tmp.replace(STATE / "finished.json")

# Lock data only — results/ stays writable for corrections, timestamps/ stays
# writable so extra can record its timestamp. Both are locked by extra.
for target in [ROOT / "TASK.md", ROOT / "data"]:
    if target.exists():
        make_readonly(target)

print(f"Primary time recorded — {ts['iso']} ({elapsed:.1f}s)")
print()
print("results/ is still writable. You may correct any mistakes, then run:")
print("  ./benchctl extra")
print("to record your final submission and lock everything.")
print("If your results are correct, you are done — no need to run extra.")
