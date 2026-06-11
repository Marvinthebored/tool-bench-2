#!/usr/bin/env python3
"""Tool Bench 2 — automated assessor.
Usage: python3 assess.py <run-dir> [<run-dir> ...]
   or: ../benchctl assess <run-dir>
"""

import json, os, re, sys, time
from pathlib import Path

ASSESSOR_DIR = Path(__file__).resolve().parent
TB2_ROOT = ASSESSOR_DIR.parent


# ── Data loader ──────────────────────────────────────────────────────────

def load_source_data(run):
    records = []
    rec_dir = run / "data" / "records"
    for i in range(1, 21):
        p = rec_dir / f"rec_{i:02d}.txt"
        if not p.exists():
            continue
        fields = {}
        for line in p.read_text().strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()
        records.append({
            "id": fields["id"],
            "category": fields["category"],
            "value": int(fields["value"]),
            "state": fields["state"],
        })

    teams = {}
    for line in (run / "data" / "teams.csv").read_text().strip().splitlines()[1:]:
        rid, team = line.split(",")
        teams[rid.strip()] = team.strip()

    multipliers = {}
    for line in (run / "data" / "multipliers.csv").read_text().strip().splitlines()[1:]:
        cat, mult = line.split(",")
        multipliers[cat.strip()] = int(mult.strip())

    return records, teams, multipliers


def compute_expected(records, teams, multipliers):
    catalog = sorted(records, key=lambda r: r["id"])

    enriched = [{**r, "team": teams[r["id"]]} for r in catalog]

    scores = {r["id"]: r["value"] * multipliers[r["category"]] for r in enriched}

    scoreboard = sorted(scores.items(), key=lambda x: -x[1])

    team_data = {}
    for rid, score in scores.items():
        t = teams[rid]
        if t not in team_data:
            team_data[t] = {"count": 0, "total": 0, "members": []}
        team_data[t]["count"] += 1
        team_data[t]["total"] += score
        team_data[t]["members"].append((rid, score))

    for t in team_data:
        td = team_data[t]
        td["avg"] = td["total"] / td["count"]
        td["best"] = max(td["members"], key=lambda x: x[1])[0]

    team_ranking = sorted(team_data.items(), key=lambda x: -x[1]["total"])

    state_counts = {}
    cat_counts = {}
    for r in records:
        state_counts[r["state"]] = state_counts.get(r["state"], 0) + 1
        cat_counts[r["category"]] = cat_counts.get(r["category"], 0) + 1

    all_scores = [s for _, s in scoreboard]
    mean_score = sum(all_scores) / len(all_scores)

    return {
        "catalog": catalog,
        "enriched": enriched,
        "scores": scores,
        "scoreboard": scoreboard,
        "team_ranking": team_ranking,
        "team_data": team_data,
        "state_counts": state_counts,
        "cat_counts": cat_counts,
        "mean_score": mean_score,
        "highest": scoreboard[0],
        "lowest": scoreboard[-1],
    }


# ── Stage assessors — all take results_dir, not run ─────────────────────

def parse_csv(text):
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return [], []
    header = [c.strip() for c in lines[0].split(",")]
    rows = [[c.strip() for c in line.split(",")] for line in lines[1:]]
    return header, rows


def assess_s1(results_dir, expected):
    path = results_dir / "s1_catalog.csv"
    if not path.exists():
        return False, ["s1_catalog.csv missing"]
    header, rows = parse_csv(path.read_text())
    notes = []
    if header != ["id", "category", "value", "state"]:
        notes.append(f"header: {header}")
    if len(rows) != 20:
        notes.append(f"{len(rows)} rows (expected 20)")
        return False, notes
    for i, (row, exp) in enumerate(zip(rows, expected["catalog"])):
        exp_row = [exp["id"], exp["category"], str(exp["value"]), exp["state"]]
        if row != exp_row:
            notes.append(f"row {i+1}: got {row}, expected {exp_row}")
    return len(notes) == 0, notes


def assess_s2(results_dir, expected):
    path = results_dir / "s2_enriched.csv"
    if not path.exists():
        return False, ["s2_enriched.csv missing"]
    header, rows = parse_csv(path.read_text())
    notes = []
    if header != ["id", "category", "value", "state", "team"]:
        notes.append(f"header: {header}")
    if len(rows) != 20:
        notes.append(f"{len(rows)} rows (expected 20)")
        return False, notes
    for i, (row, exp) in enumerate(zip(rows, expected["enriched"])):
        exp_row = [exp["id"], exp["category"], str(exp["value"]), exp["state"], exp["team"]]
        if row != exp_row:
            notes.append(f"row {i+1}: got {row}, expected {exp_row}")
    return len(notes) == 0, notes


def assess_s3(results_dir, expected):
    score_dir = results_dir / "s3_scores"
    notes = []
    if not score_dir.exists():
        return False, ["s3_scores/ directory missing"]
    for rid, exp_score in expected["scores"].items():
        f = score_dir / f"{rid}.txt"
        if not f.exists():
            notes.append(f"{rid}.txt missing")
            continue
        content = f.read_text().strip()
        try:
            actual = int(content)
        except ValueError:
            notes.append(f"{rid}.txt: '{content}' not an integer")
            continue
        if actual != exp_score:
            notes.append(f"{rid}: got {actual}, expected {exp_score}")
    return len(notes) == 0, notes


def assess_s4(results_dir, expected):
    path = results_dir / "s4_scoreboard.csv"
    if not path.exists():
        return False, ["s4_scoreboard.csv missing"]
    header, rows = parse_csv(path.read_text())
    notes = []
    if header != ["id", "score"]:
        notes.append(f"header: {header}")
    if len(rows) != 20:
        notes.append(f"{len(rows)} rows (expected 20)")
        return False, notes
    for i, (row, (exp_id, exp_score)) in enumerate(zip(rows, expected["scoreboard"])):
        exp_row = [exp_id, str(exp_score)]
        if row != exp_row:
            notes.append(f"row {i+1}: got {row}, expected {exp_row}")
    return len(notes) == 0, notes


def assess_s5(results_dir, expected):
    path = results_dir / "s5_teams.md"
    if not path.exists():
        return False, ["s5_teams.md missing"]
    content = path.read_text()
    notes = []

    table_rows = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("|") and not re.match(r"^\|[-\s|]+\|$", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            table_rows.append(cells)

    if len(table_rows) < 2:
        return False, ["no table found"]

    data_rows = table_rows[1:]
    if len(data_rows) != 5:
        notes.append(f"{len(data_rows)} team rows (expected 5)")
        return False, notes

    for i, (row, (team_name, td)) in enumerate(zip(data_rows, expected["team_ranking"])):
        exp = [team_name, str(td["count"]), str(td["total"]), f"{td['avg']:.2f}", td["best"]]
        if row != exp:
            notes.append(f"row {i+1}: got {row}, expected {exp}")
    return len(notes) == 0, notes


def assess_s6(results_dir, expected):
    path = results_dir / "s6_report.md"
    if not path.exists():
        return False, ["s6_report.md missing"]
    content = path.read_text()
    notes = []

    checks = {
        "records":       (r"Records:\s*(\d+)",                         str(len(expected["catalog"]))),
        "active":        (r"Active:\s*(\d+)",                          str(expected["state_counts"].get("active", 0))),
        "inactive":      (r"Inactive:\s*(\d+)",                        str(expected["state_counts"].get("inactive", 0))),
        "pending":       (r"Pending:\s*(\d+)",                         str(expected["state_counts"].get("pending", 0))),
        "cat_a":         (r"A=(\d+)",                                  str(expected["cat_counts"].get("A", 0))),
        "cat_b":         (r"B=(\d+)",                                  str(expected["cat_counts"].get("B", 0))),
        "cat_c":         (r"C=(\d+)",                                  str(expected["cat_counts"].get("C", 0))),
        "highest_id":    (r"Highest score:\s*(REC-\d+)",               expected["highest"][0]),
        "highest_score": (r"Highest score:\s*REC-\d+\s*\((\d+)\)",    str(expected["highest"][1])),
        "lowest_id":     (r"Lowest score:\s*(REC-\d+)",                expected["lowest"][0]),
        "lowest_score":  (r"Lowest score:\s*REC-\d+\s*\((\d+)\)",     str(expected["lowest"][1])),
        "mean":          (r"Mean score:\s*([\d.]+)",                   f"{expected['mean_score']:.1f}"),
        "top_team":      (r"Top team:\s*(\w+)",                        expected["team_ranking"][0][0]),
        "top_total":     (r"Top team:\s*\w+\s*\(total=(\d+)\)",       str(expected["team_ranking"][0][1]["total"])),
        "bottom_team":   (r"Bottom team:\s*(\w+)",                     expected["team_ranking"][-1][0]),
        "bottom_total":  (r"Bottom team:\s*\w+\s*\(total=(\d+)\)",    str(expected["team_ranking"][-1][1]["total"])),
    }

    for label, (pattern, exp_val) in checks.items():
        m = re.search(pattern, content, re.IGNORECASE)
        if not m:
            notes.append(f"{label}: not found")
        elif m.group(1) != exp_val:
            notes.append(f"{label}: got '{m.group(1)}', expected '{exp_val}'")

    return len(notes) == 0, notes


def assess_stages(results_dir, expected):
    fns = [
        ("S1", assess_s1), ("S2", assess_s2), ("S3", assess_s3),
        ("S4", assess_s4), ("S5", assess_s5), ("S6", assess_s6),
    ]
    stages = {}
    for label, fn in fns:
        passed, notes = fn(results_dir, expected)
        stages[label] = {"pass": passed, "notes": notes}
    return stages


# ── Timing ───────────────────────────────────────────────────────────────

def load_timing(run):
    ts_dir = run / "timestamps"
    timing = {"primary": None, "extra_period": None, "total": None,
               "stages": {}, "has_extra": False, "warnings": []}

    start_f = ts_dir / "start.json"
    end_f   = ts_dir / "end.json"
    extra_f = ts_dir / "extra.json"

    if not start_f.exists():
        timing["warnings"].append("start.json missing")
        return timing

    start = json.loads(start_f.read_text())
    start_ms = start["epoch_ms"]
    timing["start_iso"] = start.get("iso", "")

    if not end_f.exists():
        timing["warnings"].append("end.json missing — run not finished")
        return timing

    end = json.loads(end_f.read_text())
    end_ms = end["epoch_ms"]
    timing["primary"] = (end_ms - start_ms) / 1000
    timing["end_iso"] = end.get("iso", "")

    if extra_f.exists():
        extra = json.loads(extra_f.read_text())
        extra_ms = extra["epoch_ms"]
        timing["extra_period"] = (extra_ms - end_ms) / 1000
        timing["total"] = (extra_ms - start_ms) / 1000
        timing["has_extra"] = True
        timing["extra_iso"] = extra.get("iso", "")
    else:
        timing["total"] = timing["primary"]

    # Per-stage from checkpoints
    prev_ms = start_ms
    for i in range(1, 6):
        cp_f = ts_dir / f"checkpoint_{i}.json"
        if cp_f.exists():
            cp = json.loads(cp_f.read_text())
            timing["stages"][f"S{i}"] = (cp["epoch_ms"] - prev_ms) / 1000
            prev_ms = cp["epoch_ms"]
        else:
            timing["warnings"].append(f"checkpoint_{i} missing")
            break

    if "S5" in timing["stages"]:
        timing["stages"]["S6"] = (end_ms - prev_ms) / 1000

    return timing


# ── Run assessment ───────────────────────────────────────────────────────

def assess_run(run_dir):
    run = Path(run_dir).resolve()
    name = run.name

    records, teams, multipliers = load_source_data(run)
    expected = compute_expected(records, teams, multipliers)

    timing = load_timing(run)

    # Primary: score against finish-time snapshot if it exists, else current results
    snapshot     = run / ".bench" / "state" / "snapshot"
    extra_snap   = run / ".bench" / "state" / "extra_snapshot"
    results_dir  = run / "results"

    primary_results = snapshot if snapshot.exists() else results_dir
    primary_stages  = assess_stages(primary_results, expected)
    primary_score   = sum(1 for s in primary_stages.values() if s["pass"])

    # Final: score against extra snapshot if it exists
    has_extra = extra_snap.exists()
    if has_extra:
        final_stages = assess_stages(extra_snap, expected)
        final_score  = sum(1 for s in final_stages.values() if s["pass"])
    else:
        final_stages = primary_stages
        final_score  = primary_score

    return {
        "name":           name,
        "primary_stages": primary_stages,
        "primary_score":  primary_score,
        "final_stages":   final_stages,
        "final_score":    final_score,
        "has_extra":      has_extra,
        "timing":         timing,
    }


# ── Output helpers ───────────────────────────────────────────────────────

STAGE_NAMES = {
    "S1": "Catalog", "S2": "Enrich", "S3": "Score",
    "S4": "Rank",    "S5": "Summary", "S6": "Report",
}


def print_report(r):
    print(f"\n{'=' * 60}")
    print(f"  {r['name']}")
    print(f"{'=' * 60}")

    t = r["timing"]
    if t["primary"] is not None:
        if t["has_extra"]:
            print(f"  Primary: {t['primary']:.1f}s | Extra: {t['extra_period']:.1f}s | Total: {t['total']:.1f}s")
        else:
            print(f"  Total: {t['primary']:.1f}s")
    if t.get("stages"):
        for label, dur in t["stages"].items():
            print(f"    {label}: {dur:.1f}s")
    for w in t.get("warnings", []):
        print(f"  ⚠ {w}")

    print()

    show_extra = r["has_extra"] and r["final_score"] != r["primary_score"]

    for label in ["S1", "S2", "S3", "S4", "S5", "S6"]:
        ps = r["primary_stages"][label]
        fs = r["final_stages"][label]
        p_mark = "PASS" if ps["pass"] else "FAIL"
        st = t["stages"].get(label)
        time_str = f"{st:.1f}s" if st is not None else ""

        if show_extra and ps["pass"] != fs["pass"]:
            f_mark = "PASS" if fs["pass"] else "FAIL"
            extra_tag = f" → {f_mark} (extra)"
        else:
            extra_tag = ""

        notes_str = f"  ← {'; '.join(ps['notes'][:3])}" if ps["notes"] and not ps["pass"] else ""
        print(f"  {label} {STAGE_NAMES[label]:<10} {p_mark:<5} {time_str:>7}{extra_tag}{notes_str}")

    print(f"\n  Primary score: {r['primary_score']}/6", end="")
    if r["has_extra"]:
        print(f"  |  Final score: {r['final_score']}/6 (after extra time)")
    else:
        print()


def write_run_results(run_dir, report):
    run = Path(run_dir).resolve()
    t = report["timing"]
    lines = [f"# Results: {report['name']}", "",
             f"Assessed: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}", ""]

    primary_str = f"{t['primary']:.1f}s" if t["primary"] is not None else "n/a"
    total_str   = f"{t['total']:.1f}s"   if t["total"]   is not None else "n/a"

    lines += ["| Stage | Primary | Final | Time | Notes |",
              "|-------|---------|-------|------|-------|"]

    for label in ["S1", "S2", "S3", "S4", "S5", "S6"]:
        ps = report["primary_stages"][label]
        fs = report["final_stages"][label]
        p_res = "PASS" if ps["pass"] else "FAIL"
        f_res = "PASS" if fs["pass"] else "FAIL"
        st  = t["stages"].get(label)
        ts  = f"{st:.1f}s" if st is not None else "—"
        notes = "; ".join(ps["notes"][:2]) if ps["notes"] and not ps["pass"] else ""
        lines.append(f"| {label} {STAGE_NAMES[label]} | {p_res} | {f_res} | {ts} | {notes} |")

    lines += [""]

    if report["has_extra"]:
        lines.append(f"**Primary: {report['primary_score']}/6 in {primary_str} | "
                     f"Final: {report['final_score']}/6 in {total_str} "
                     f"(+{t['extra_period']:.1f}s extra)**")
    else:
        lines.append(f"**Score: {report['primary_score']}/6 — {primary_str}**")

    if t.get("warnings"):
        lines += ["", "Warnings:"] + [f"- {w}" for w in t["warnings"]]

    lines.append("")
    result_path = run / "RESULTS.md"
    try:
        result_path.write_text("\n".join(lines))
    except PermissionError:
        os.chmod(run, 0o755)
        result_path.write_text("\n".join(lines))
    print(f"  Wrote {result_path}")


def update_leaderboard(reports):
    lb_path = TB2_ROOT / "RESULTS.md"

    header = ("# Tool Bench 2 — Results\n\n"
              f"Last updated: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n\n")

    existing = {}
    if lb_path.exists():
        for line in lb_path.read_text().splitlines():
            if line.startswith("| ") and not line.startswith("| Run") and "---" not in line:
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 2:
                    existing[cells[0]] = line

    for r in reports:
        t = r["timing"]
        primary_str = f"{t['primary']:.1f}s" if t["primary"] is not None else "n/a"
        total_str   = f"{t['total']:.1f}s"   if t["total"]   is not None else "n/a"
        extra_str   = f"+{t['extra_period']:.0f}s" if t["has_extra"] else ""

        stage_strs = []
        for label in ["S1", "S2", "S3", "S4", "S5", "S6"]:
            ps = r["primary_stages"][label]
            fs = r["final_stages"][label]
            st = t["stages"].get(label)
            time_s = f"{st:.1f}" if st is not None else "—"
            # Show primary mark; if extra fixed it, show ↑
            if ps["pass"]:
                mark = "✓"
            elif fs["pass"]:
                mark = "↑"   # fixed in extra time
            else:
                mark = "✗"
            stage_strs.append(f"{mark} {time_s}")

        score_col = f"{r['primary_score']}/6"
        if r["has_extra"] and r["final_score"] != r["primary_score"]:
            score_col += f"→{r['final_score']}/6"

        line = (f"| {r['name']} | {score_col} | {primary_str} | {extra_str} | {total_str} | "
                f"{' | '.join(stage_strs)} |")
        existing[r["name"]] = line

    def sort_key(item):
        cells = [c.strip() for c in item[1].strip("|").split("|")]
        try:
            return (0, float(cells[4].replace("s", "")))
        except (ValueError, IndexError):
            return (1, 0)

    sorted_entries = sorted(existing.items(), key=sort_key)

    table  = "| Run | Score | Primary | Extra | Total | S1 | S2 | S3 | S4 | S5 | S6 |\n"
    table += "|-----|-------|---------|-------|-------|----|----|----|----|----|----|\n"
    for _, line in sorted_entries:
        table += line + "\n"

    lb_path.write_text(header + table)
    print(f"  Updated {lb_path}")


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <run-dir> [<run-dir> ...]")
        sys.exit(1)

    reports = []
    for d in sys.argv[1:]:
        r = assess_run(d)
        reports.append(r)
        print_report(r)
        write_run_results(d, r)

    update_leaderboard(reports)

    if len(reports) > 1:
        print(f"\n{'=' * 60}")
        print(f"  COMPARISON")
        print(f"{'=' * 60}")
        print(f"  {'Run':<35} {'Primary':>8} {'Final':>6} {'Time':>8}")
        print(f"  {'-'*60}")
        for r in sorted(reports, key=lambda x: x["timing"].get("primary") or 9999):
            t = r["timing"]
            pt = f"{t['primary']:.1f}s" if t["primary"] else "—"
            tt = f"{t['total']:.1f}s"   if t["total"]   else "—"
            print(f"  {r['name']:<35} {r['primary_score']:>5}/6 {r['final_score']:>3}/6 {pt if not t['has_extra'] else tt:>8}")


if __name__ == "__main__":
    main()
