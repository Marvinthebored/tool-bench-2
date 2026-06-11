#!/usr/bin/env python3
import json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS_DIR = ROOT / "timestamps"

start_file = TS_DIR / "start.json"
end_file = TS_DIR / "end.json"

if not start_file.exists():
    print("Status: NOT STARTED")
    raise SystemExit(0)

start = json.loads(start_file.read_text())

if end_file.exists():
    end = json.loads(end_file.read_text())
    elapsed = (end["epoch_ms"] - start["epoch_ms"]) / 1000
    print(f"Status: FINISHED")
    print(f"Started:  {start['iso']}")
    print(f"Finished: {end['iso']}")
    print(f"Elapsed:  {elapsed:.1f}s")
else:
    now_ms = time.time_ns() // 1_000_000
    elapsed = (now_ms - start["epoch_ms"]) / 1000
    print(f"Status: IN PROGRESS")
    print(f"Started:  {start['iso']}")
    print(f"Elapsed:  {elapsed:.1f}s so far")

# Show checkpoints
for i in range(1, 6):
    cp = TS_DIR / f"checkpoint_{i}.json"
    if cp.exists():
        data = json.loads(cp.read_text())
        stage_elapsed = (data["epoch_ms"] - start["epoch_ms"]) / 1000
        print(f"  Stage {i}: {data['iso']} ({stage_elapsed:.1f}s)")
