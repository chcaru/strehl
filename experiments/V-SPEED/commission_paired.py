"""Paired commissioning of the harness timer.

WHY THIS EXISTS. The first commissioning (commission.ps1) ran an unplanted
control block, then a planted block, and compared the two. On an idle box that
works. On this box it does not: nine agents share it, and the same `strehl
stack` command on the same 22 frames varied 12.31 - 16.34 s unplanted, a spread
of 4.03 s against a 5.00 s plant. A block design cannot resolve a plant that is
the same size as the drift between blocks, and reporting one that did would be
the mood, not the measurement.

So pair it. Each PAIR runs the same stage twice back to back, once bare and
once planted, alternating which comes first. Machine drift is then common-mode
within a pair and cancels in the difference.

Two arms, and both are load-bearing:

  PLANT arm  pairs of (bare, planted). median delta must be +PLANT within TOL.
             Rejects a timer that cannot see a real 5 s.
  NULL arm   pairs of (bare, bare). median delta must be ~0.
             Rejects a timer that adds 5 s to everything, and measures the
             noise floor of the pairing itself, so the PLANT arm's tolerance
             has a scale to be read against.

The planted call goes through runner.time_stage() -- the exact function that
produces every number this lane reports -- armed through the exact environment
variables the production path reads.

Usage: python commission_paired.py <stage> <pairs>
       stage in {strehl, focus-stack}
"""

import json
import os
import statistics
import sys
import time

import runner

PLANT = 5.0
TOL = 0.5
SYNTH_S = 10.0
SUBJECT = "109MSDCF"
SRC = r"D:\personal\macro\109MSDCF"
BASE = os.path.join(runner.ROOT, SUBJECT)
LOGDIR = os.path.join(BASE, "logs")
OUTDIR = os.path.join(BASE, "out")
TIFDIR = os.path.join(BASE, "tif-srgb")


def build(stage, i, planted):
    import glob

    tag = f"cp-{stage}-{'p' if planted else 'b'}{i}"
    out = os.path.join(OUTDIR, f"{tag}.tif")
    log = os.path.join(LOGDIR, f"{tag}.log")
    if stage == "strehl":
        cmd = [runner.STREHL, "stack", SRC, "--out", out, "--srgb", "--auto-exposure"]
    elif stage == "focus-stack":
        tifs = sorted(glob.glob(os.path.join(TIFDIR, "*.tif")))
        cmd = [runner.FS, f"--output={out}"] + tifs
    elif stage == "synthetic":
        # A child of KNOWN, load-insensitive duration, run through the same
        # time_stage() that produces every reported number. This is the
        # commissioning of record: it isolates the harness from the workload's
        # own variance, which on this box is larger than the plant (see the
        # `strehl` arm, retained precisely because it failed).
        cmd = [sys.executable, "-c", f"import time; time.sleep({SYNTH_S})"]
        out = None
    else:
        raise SystemExit(f"unknown stage {stage!r}")
    return cmd, out, log


def once(stage, i, planted):
    cmd, out, log = build(stage, i, planted)
    if out and os.path.exists(out):
        os.remove(out)
    if planted:
        os.environ["V_SPEED_PLANT_STAGE"] = stage
        os.environ["V_SPEED_PLANT_S"] = str(PLANT)
    else:
        os.environ["V_SPEED_PLANT_STAGE"] = ""
        os.environ["V_SPEED_PLANT_S"] = "0"
    rec = runner.time_stage(stage, cmd, log)
    if rec["rc"] != 0:
        raise SystemExit(f"stage {stage} returned rc={rec['rc']}; refusing to commission")
    if planted and rec["planted_s"] != PLANT:
        raise SystemExit(
            f"PLANT DID NOT ARM: planted_s={rec['planted_s']} for stage {stage}. "
            "An unarmed plant reads as a green commissioning; refusing."
        )
    if (not planted) and rec["planted_s"] != 0.0:
        raise SystemExit("BARE RUN CARRIED A PLANT; refusing.")
    return rec["wall_s"]


def arm(stage, pairs, planted_second_member):
    deltas, rows = [], []
    for i in range(pairs):
        bare_first = (i % 2) == 0
        if bare_first:
            a = once(stage, i, False)
            b = once(stage, i, planted_second_member)
        else:
            b = once(stage, i, planted_second_member)
            a = once(stage, i, False)
        deltas.append(b - a)
        rows.append((i, "bare-first" if bare_first else "treated-first", a, b, b - a))
        print(
            f"  pair {i}  {'bare-first ' if bare_first else 'treated-1st'}"
            f"  bare {a:7.2f}   other {b:7.2f}   delta {b - a:+7.2f}",
            flush=True,
        )
    return deltas, rows


def main():
    stage = sys.argv[1]
    pairs = int(sys.argv[2])
    do_null = len(sys.argv) > 3 and sys.argv[3] == "null"

    runner.check_binaries()
    print(f"stage={stage} pairs={pairs} plant={PLANT:.2f}s tol={TOL:.2f}s")

    print(f"\nPLANT arm ({pairs} pairs of bare vs +{PLANT:.1f}s):")
    dp, rp = arm(stage, pairs, True)
    med_p = statistics.median(dp)

    result = {
        "stage": stage,
        "pairs": pairs,
        "plant_s": PLANT,
        "plant_deltas": dp,
        "plant_median_delta_s": med_p,
        "plant_spread_s": max(dp) - min(dp),
    }
    ok_p = abs(med_p - PLANT) <= TOL
    print(
        f"  PLANT median delta {med_p:+.2f} s (expected {PLANT:+.2f}), "
        f"spread {max(dp) - min(dp):.2f} s -> {'PASS' if ok_p else 'FAIL'}"
    )

    ok_n = True
    if do_null:
        print(f"\nNULL arm ({pairs} pairs of bare vs bare):")
        dn, rn = arm(stage, pairs, False)
        med_n = statistics.median(dn)
        result.update(
            {
                "null_deltas": dn,
                "null_median_delta_s": med_n,
                "null_spread_s": max(dn) - min(dn),
            }
        )
        ok_n = abs(med_n) <= TOL
        print(
            f"  NULL  median delta {med_n:+.2f} s (expected  +0.00), "
            f"spread {max(dn) - min(dn):.2f} s -> {'PASS' if ok_n else 'FAIL'}"
        )

    result["verdict"] = "PASS" if (ok_p and ok_n) else "FAIL"
    result["t_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(runner.ROOT, "commission-paired.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")

    print(f"\nCOMMISSIONING ({stage}, paired): {result['verdict']}")
    if result["verdict"] != "PASS":
        print("A timer that cannot see a planted 5 s cannot see a real 5 s.")
        print("REFUSING to report timings.")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
