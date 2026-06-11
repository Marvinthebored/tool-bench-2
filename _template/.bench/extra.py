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

if not (TS_DIR / "end.json").exists():
    die("Run ./benchctl finish first.")

if (TS_DIR / "extra.json").exists():
    die("Extra already recorded. Run is fully closed.")

# Hash and snapshot corrected results
output_hashes = {}
output_mtimes = {}
for p in sorted(RESULTS.rglob("*")):
    if p.is_file() and p.name != ".gitkeep":
        rel = str(p.relative_to(ROOT))
        output_hashes[rel] = sha256(p)
        output_mtimes[rel] = int(p.stat().st_mtime * 1000)

start = json.loads((TS_DIR / "start.json").read_text())
end = json.loads((TS_DIR / "end.json").read_text())
ts = make_timestamp()

primary_elapsed = (end["epoch_ms"] - start["epoch_ms"]) / 1000
extra_elapsed = (ts["epoch_ms"] - end["epoch_ms"]) / 1000
total_elapsed = (ts["epoch_ms"] - start["epoch_ms"]) / 1000

ts["event"] = "extra"
ts["cwd"] = str(ROOT)
ts["tool_bench_version"] = "tb2"
ts["output_hashes"] = output_hashes
ts["output_mtimes"] = output_mtimes
ts["primary_elapsed_s"] = primary_elapsed
ts["extra_elapsed_s"] = extra_elapsed

tmp = TS_DIR / "extra.json.tmp"
tmp.write_text(json.dumps(ts, indent=2) + "\n")
tmp.replace(TS_DIR / "extra.json")

# Copy corrected results into extra_snapshot
extra_snapshot = STATE / "extra_snapshot"
if extra_snapshot.exists():
    shutil.rmtree(extra_snapshot)
shutil.copytree(RESULTS, extra_snapshot)

extra_state = {
    "extra_at": ts["epoch_ms"],
    "primary_elapsed_s": primary_elapsed,
    "extra_elapsed_s": extra_elapsed,
    "output_hashes": output_hashes,
}
tmp = STATE / "extra.json.tmp"
tmp.write_text(json.dumps(extra_state, indent=2) + "\n")
tmp.replace(STATE / "extra.json")

# Now lock everything
for target in [ROOT / "TASK.md", ROOT / "data", RESULTS, TS_DIR]:
    if target.exists():
        make_readonly(target)

print(f"Extra time recorded — {ts['iso']}")
print(f"  Primary: {primary_elapsed:.1f}s | Extra: {extra_elapsed:.1f}s | Total: {total_elapsed:.1f}s")
print("All locked.")
