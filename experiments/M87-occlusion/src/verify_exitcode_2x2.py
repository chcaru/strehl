"""M87 -- reduce the exit-code 2x2 and the causal sleep ladder to the numbers
that go into the report.  Nothing here is transcribed by hand; every figure
quoted in P142 is printed by this script from the JSON the probes wrote.

Inputs (all written by the .ps1 probes, PowerShell 5.1 writes a BOM so the
reads use utf-8-sig):
    data/exitcode-quota-<host>.json   9 arms x 40 reps, 4 hosts
    data/exitcode-race-<host>.json   12 arms x 60 reps, 2 hosts
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE.parent / "data"

QUOTA_HOSTS = ["child-host", "agent-shell", "pwsh7-child", "ps51-dotsource"]
RACE_HOSTS = ["ps51-child", "pwsh7-child"]


def load(name):
    p = DATA / name
    if not p.exists():
        sys.exit("MISSING OPERAND: %s" % p)
    return json.loads(p.read_text(encoding="utf-8-sig"))


def main():
    print("=" * 72)
    print("PART A -- the 2x2: engine x process style")
    print("=" * 72)

    quota = {h: load("exitcode-quota-%s.json" % h) for h in QUOTA_HOSTS}

    style = {
        "child-host": ("5.1", "child -File"),
        "ps51-dotsource": ("5.1", "in-process dot-source"),
        "pwsh7-child": ("7.6.5", "child -File"),
        "agent-shell": ("7.6.5", "in-process (agent shell)"),
    }

    total_obs_a = 0
    print("%-16s %-7s %-26s %-11s %s" % ("host", "engine", "style", "arms OK", "corrupted values"))
    for h in QUOTA_HOSTS:
        rows = quota[h]
        ok = sum(1 for r in rows if r["quota_agrees"])
        obs = sum(r["reps"] for r in rows)
        total_obs_a += obs
        vals = set()
        for r in rows:
            for v in r["values"]:
                if v != 1:
                    vals.add(v)
        eng, sty = style[h]
        print("%-16s %-7s %-26s %-11s %s" % (h, eng, sty, "%d/9" % ok, sorted(vals) or "none"))
    print("observations in part A: %d" % total_obs_a)

    # observation-level agreement with the strict quota model, per engine
    print()
    for eng in ("7.6.5", "5.1"):
        hosts = [h for h in QUOTA_HOSTS if style[h][0] == eng]
        agree = tot = 0
        for h in hosts:
            for r in quota[h]:
                pred_lost = r["quota_pred"]
                tot += r["reps"]
                agree += r["lost"] if pred_lost else (r["reps"] - r["lost"])
        print("engine %-7s strict-quota agreement at OBSERVATION level: %d/%d = %.4f%%"
              % (eng, agree, tot, 100.0 * agree / tot))

    # quota necessity: every arm the model predicts SAFE, in every host
    print()
    safe_lost = safe_tot = 0
    for h in QUOTA_HOSTS:
        for r in quota[h]:
            if not r["quota_pred"]:
                safe_tot += r["reps"]
                safe_lost += r["lost"]
    print("part A non-quota arms (-First 51 over 50, -Last 3): %d lost of %d"
          % (safe_lost, safe_tot))

    print()
    print("PS 5.1 -First 3 loss rate by volume, both styles pooled (80 reps each):")
    for n in (5, 10, 50, 200, 5000):
        lost = tot = 0
        for h in ("child-host", "ps51-dotsource"):
            for r in quota[h]:
                if r["lines"] == n and r["mode"] == "First" and r["k"] == 3:
                    lost += r["lost"]
                    tot += r["reps"]
        if tot:
            print("  %5d lines: %3d/%3d = %6.2f%%" % (n, lost, tot, 100.0 * lost / tot))

    print()
    print("=" * 72)
    print("PART B -- the causal manipulation: make the process still be running")
    print("=" * 72)

    race = {h: load("exitcode-race-%s.json" % h) for h in RACE_HOSTS}
    total_obs_b = sum(sum(r["reps"] for r in race[h]) for h in RACE_HOSTS)

    print("%-13s %-7s %-6s %-8s %-7s %s" % ("host", "engine", "lines", "sleep_s", "lost", "pct"))
    for h in RACE_HOSTS:
        for r in race[h]:
            if r["is_ctl"]:
                continue
            print("%-13s %-7s %-6d %-8s %-7s %.2f%%"
                  % (h, r["psver"], r["lines"], r["sleep_s"],
                     "%d/%d" % (r["lost"], r["reps"]), r["lost_pct"]))
    print("observations in part B: %d" % total_obs_b)

    ctl_lost = ctl_tot = 0
    for h in RACE_HOSTS:
        for r in race[h]:
            if r["is_ctl"]:
                ctl_tot += r["reps"]
                ctl_lost += r["lost"]
    print("part B negative-control arms: %d lost of %d" % (ctl_lost, ctl_tot))

    # registered prediction P1: monotone rise to 100% on 5.1
    p1 = []
    for n in (5, 50):
        seq = [(r["sleep_s"], r["lost_pct"]) for r in race["ps51-child"]
               if not r["is_ctl"] and r["lines"] == n]
        seq.sort()
        rises = all(seq[i][1] <= seq[i + 1][1] for i in range(len(seq) - 1))
        ends100 = seq[-1][1] == 100.0
        p1.append(rises and ends100)
        print("P1 %d lines: %s  monotone=%s  ends at 100%%=%s"
              % (n, " -> ".join("%.2f%%" % v for _, v in seq), rises, ends100))
    print("P1 (5.1 rate rises with sleep to 100%%): %s" % ("PASS" if all(p1) else "FAIL"))

    p2 = all(r["lost_pct"] == 100.0 for r in race["pwsh7-child"] if not r["is_ctl"])
    print("P2 (7.6.5 unaffected by sleep, 100%% throughout): %s" % ("PASS" if p2 else "FAIL"))
    print("P3/P4 (negative controls hold at every sleep): %s"
          % ("PASS" if ctl_lost == 0 else "FAIL"))

    print()
    print("=" * 72)
    print("TOTAL observations across both parts: %d" % (total_obs_a + total_obs_b))
    print("=" * 72)


if __name__ == "__main__":
    main()
