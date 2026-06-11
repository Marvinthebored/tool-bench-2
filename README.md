# Tool Bench 2

A pipeline benchmark measuring tool-call throughput and basic accuracy across
six stages of structured data processing. Every fully operational agent should
score 6/6. Failures indicate harness or configuration issues.

## Quick start

### 1. Start a run

From this directory:
```bash
./benchctl start <name>
```
Naming convention: `<agent>-<model>`, e.g. `ocmarvin-gpt55`, `claudesub-sonnet46`.

This creates a timestamped run directory (e.g. `ocmarvin-gpt55-20260525-0830/`),
copies the task and data into it, and starts the clock. The command prints the path.

### 2. Point the agent at the run directory

The agent's first instruction should be:

> Read `TASK.md` in `<run-dir>` and execute all stages. Do all work inside that directory.

For a Claude Code subagent:
```
Agent({
  description: "<model> TB2 run",
  model: "<model>",
  prompt: "Read <run-dir>/TASK.md and execute all stages. Work only inside <run-dir>/."
})
```

### 3. Assess

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
