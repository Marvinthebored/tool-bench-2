#!/usr/bin/env python3
import hashlib, json, os, shutil, sys, time
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent
LOCKED = TEMPLATE / ".bench" / "locked"

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

# Invoked from top-level benchctl OR from within _template
name = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else ""
if not name:
    die("Usage: ./benchctl start <name>\nExample: ./benchctl start ocmarvin-gpt55")

stamp = time.strftime("%Y%m%d-%H%M")
run_name = f"{name}-{stamp}"
run_dir = TEMPLATE.parent / run_name

if run_dir.exists():
    die(f"Directory already exists: {run_dir}")

if not (LOCKED / "TASK.md").exists():
    die("Missing .bench/locked/TASK.md — is _template intact?")

# Create run directory
run_dir.mkdir()
(run_dir / "results" / "s3_scores").mkdir(parents=True)
(run_dir / "timestamps").mkdir()

# Copy .bench scripts (not locked source)
bench_dst = run_dir / ".bench"
bench_dst.mkdir()
(bench_dst / "state").mkdir()
for script in ["checkpoint.py", "finish.py", "extra.py", "status.py", "ts_util.py"]:
    src = TEMPLATE / ".bench" / script
    if src.exists():
        shutil.copy2(src, bench_dst / script)

# Copy run-level benchctl
shutil.copy2(TEMPLATE / "benchctl", run_dir / "benchctl")
os.chmod(run_dir / "benchctl", 0o755)

# Copy and lock source materials
shutil.copy2(LOCKED / "TASK.md", run_dir / "TASK.md")
os.chmod(run_dir / "TASK.md", 0o444)

shutil.copytree(LOCKED / "data", run_dir / "data")
for dirpath, _, filenames in os.walk(run_dir / "data"):
    for f in filenames:
        os.chmod(os.path.join(dirpath, f), 0o444)

# Write start timestamp
sys.path.insert(0, str(bench_dst))
from ts_util import make_timestamp
ts = make_timestamp()
ts["event"] = "start"
ts["cwd"] = str(run_dir)
ts["run_name"] = run_name
ts["tool_bench_version"] = "tb2"

ts_dir = run_dir / "timestamps"
tmp = ts_dir / "start.json.tmp"
tmp.write_text(json.dumps(ts, indent=2) + "\n")
tmp.replace(ts_dir / "start.json")

# Source hashes for integrity
source_hashes = {"TASK.md": sha256(run_dir / "TASK.md")}
for p in sorted((run_dir / "data").rglob("*")):
    if p.is_file():
        source_hashes[str(p.relative_to(run_dir))] = sha256(p)

state = {"started_at": ts["epoch_ms"], "source_hashes": source_hashes}
tmp = bench_dst / "state" / "started.json.tmp"
tmp.write_text(json.dumps(state, indent=2) + "\n")
tmp.replace(bench_dst / "state" / "started.json")

print(f"Started. Run directory: {run_dir}")
print(f"cd {run_dir}")
print(f"Read TASK.md now.")
print(f"Clock started at {ts['iso']}")
