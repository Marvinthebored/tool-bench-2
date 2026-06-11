# Tool Bench 2

You are being benchmarked. This file is your entry point.

## Setup

1. Choose a short run name that identifies you: `<agent>-<model>`, e.g. `claudesub-sonnet46` or `ocmarvin-gpt55`.

2. From **this directory** (the one containing this file), run:
   ```
   ./benchctl start <your-chosen-name>
   ```
   This script creates your run directory, copies all data, and starts the clock. It prints the path.
   **Do not create the run directory manually** — the script sets up required structure that manual creation will miss.

3. `cd` into that directory and read `TASK.md` there.

4. Complete all stages as instructed in that `TASK.md`.

## Rules

- Do not read files in `.bench/` or any parent directory.
- All work must be done inside the run directory created in step 2.
- Do not read or write files outside that run directory once you have started.
