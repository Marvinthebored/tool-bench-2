# Tool Bench 2

A pipeline benchmark measuring tool-call throughput and basic accuracy across
six stages of structured data processing. Every fully operational agent should
score 6/6. Failures indicate harness or configuration issues.

## Quick start

### 1. Run the benchmark

Open `PROMPT.md`, substitute the real path to this directory, and copy/paste the
one-liner to the candidate agent. That's it.

The agent reads `TASK.md`, runs `./benchctl start <name>` itself to create its own
timestamped run directory, and executes all six stages inside it. No setup on your
part beyond fixing the path in the prompt.

### 2. Assess

Once the agent has finished, score its run:
```bash
./benchctl assess <run-dir>
```

This scores the run, writes `<run-dir>/RESULTS.md`, and updates the leaderboard
in `RESULTS.md` (this directory).

Assess multiple runs at once:
```bash
./benchctl assess run1/ run2/ run3/
```

## What it measures

| Stage | Name | Min tool calls | Tests |
|-------|------|---------------|-------|
| S1 | Catalog | 21 | Read 20 files, write sorted CSV |
| S2 | Enrich | 3 | Join two CSVs |
| S3 | Score | 22 | Compute per-record, write 20 files |
| S4 | Rank | 21 | Read 20 files, write sorted CSV |
| S5 | Team Summary | 3 | Aggregate + markdown table |
| S6 | Report | 4 | Summarize from prior outputs |

**~74 minimum tool calls.** Per-stage timing from `./benchctl checkpoint` calls.

## Scoring

Binary pass/fail per stage. 6 stages = 6 points max.
Assessment is fully automated — no manual review needed.

Leaderboard sorted by total time (fastest first).

## Timing

- Total: `finish.epoch_ms - start.epoch_ms`
- Per-stage: from checkpoint timestamps
- All timestamps in ISO 8601 with timezone in the JSON files
