#!/usr/bin/env python3
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS_DIR = ROOT / "timestamps"

sys.path.insert(0, str(ROOT / ".bench"))
from ts_util import make_timestamp

def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

n = sys.argv[1] if len(sys.argv) > 1 else ""
if not n or not n.isdigit() or not (1 <= int(n) <= 5):
    die("Usage: ./benchctl checkpoint <1-5>")

n = int(n)

if not (TS_DIR / "start.json").exists():
    die("Not started. Run ./benchctl start first.")

if (TS_DIR / "end.json").exists():
    die("Already finished.")

cp_file = TS_DIR / f"checkpoint_{n}.json"
if cp_file.exists():
    die(f"Checkpoint {n} already recorded.")

# Check sequential order
for prev in range(1, n):
    if not (TS_DIR / f"checkpoint_{prev}.json").exists():
        die(f"Checkpoint {prev} not yet recorded. Checkpoints must be sequential.")

ts = make_timestamp()
ts["event"] = f"checkpoint_{n}"
ts["stage_completed"] = n

# Read start time for elapsed calculation
start = json.loads((TS_DIR / "start.json").read_text())
elapsed = (ts["epoch_ms"] - start["epoch_ms"]) / 1000

tmp = cp_file.with_suffix(".json.tmp")
tmp.write_text(json.dumps(ts, indent=2) + "\n")
tmp.replace(cp_file)

print(f"Stage {n} complete — {ts['iso']} ({elapsed:.1f}s elapsed)")
