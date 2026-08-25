"""Negative control for verify_c6.py.

Plants a known defect, requires verify_c6 to go RED, and requires it to go red
on the guard that TARGETS that defect, identified by message text. A bare
non-zero exit is not enough: this milestone has already caught itself with
plants that went red on an unrelated check while the guard they were aimed at
was never exercised at all.

Two safety properties:

  * Every mutation is anchored on a unique full string and HARD-ERRORS if it
    does not land. A plant that silently fails to apply produces a green that
    means nothing.
  * Originals are copied to a temp directory and restored from that copy.
    Never `git checkout --`, which reverts to HEAD and destroys uncommitted
    work.

Exit 0 if every plant is caught by its own guard and the inert plant is
correctly ignored. Reads nothing on D:.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REPORT = os.path.join(ROOT, "docs", "research", "M116-promotion.md")
OUT = r"C:\dev\strehl-out\M116\invariant"
ARMS = os.path.join(OUT, "arms.json")
GAIN = os.path.join(OUT, "gain.json")
TRAP = os.path.join(OUT, "ta-trap.json")
VERIFIER = os.path.join(HERE, "verify_c6.py")

# (id, kind, target, payload, expected-substring-of-the-guard-message)
PLANTS = [
    ("D1", "md", "| `P0-default` (shipped) | **1.114** | 7 of 12 |",
     "| `P0-default` (shipped) | **1.214** | 7 of 12 |", "12.1 P0 median"),
    ("D2", "md", "windows**, median **+4.42%**.",
     "windows**, median **+4.52%**.", "12.5 magnitude"),
    ("D3", "md", "`corr(violations, frame noise) = 0.639`.",
     "`corr(violations, frame noise) = 0.539`.", "12.8 correlation"),
    ("D4", "md", "two windows straddling the middle. Those two windows are `(656, 1552)` and",
     "two windows straddling the middle. Those two windows are `(656, 1553)` and",
     "12.5 median window A"),
    ("D5", "md", "| **M116 campaign 6** | `q`, one frozen build, identical pixels | **1.0455**",
     "| **M116 campaign 6** | `q`, one frozen build, identical pixels | **1.0555**",
     "12.7 mine"),
    ("D6", "md", "median **0.090**, HOLDING in all 12 windows.",
     "median **0.190**, HOLDING in all 12 windows.", "12.3 A0 misregistered median"),
    ("D7", "md", "integer shift **(0, 0)**, phase-correlation peak **1.0000**",
     "integer shift **(0, 0)**, phase-correlation peak **1.0900**", "12.2 NCC in report"),

    ("D8", "arms", ("verdict_against_prereg_bars", "PROMOTE"), None, "12.4 verdict"),
    ("D9", "arms", ("p2_sha256", "0" * 64), None, "12.2 placebo"),
    ("D10", "arms", ("delta_median", -0.05), None, "delta median"),

    ("D11", "gain", ("median_level_ratio_p1_over_p0", 1.04), None, "level ratio percent"),
    ("D12", "gain", ("q_windows_harmed", 7), None, "12.7"),
    ("D13", "gain", ("median_q_ratio_p1_over_p0", 1.2), None, "gain-invariant q"),

    ("D14", "trap", ("violations_max", 0), None, "12.8"),
    ("D15", "trap", ("ratio_readout_passes_trap", False), None,
     "the ratio readout FAILS the trap"),
    ("D16", "trap", ("violation_readout_passes_trap", True), None,
     "the violation readout PASSES the trap"),
    # The property that makes 12.8 a trap: if a scored frame is one of the
    # instrument's own denominator frames, the ratio is bounded by 1.0 by
    # construction and the trap cannot fail.
    ("D17", "trapframe", "armF-f173", None, "bounded by 1.0 by construction"),
]

# A change no check depends on. If this is "caught", the verifier is keying on
# prose rather than on claims, and its greens are worth less than they look.
INERT = ("I1", "md", "plainly visible and it looks worse.",
         "plainly visible and it looks poor.")

PATHS = {"md": REPORT, "arms": ARMS, "gain": GAIN, "trap": TRAP,
         "trapframe": TRAP}


def die(msg):
    print("MUTATION TARGET NOT FOUND: " + msg)
    sys.exit(3)


def apply_md(path, old, new):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    n = text.count(old)
    if n != 1:
        die("%r occurs %d times in %s, need exactly 1"
            % (old[:60], n, os.path.basename(path)))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace(old, new, 1))


def apply_json(path, key, value):
    with open(path) as fh:
        data = json.load(fh)
    if key not in data:
        die("key %r absent from %s" % (key, os.path.basename(path)))
    if data[key] == value:
        die("key %r in %s already equals the planted value %r; the plant is a "
            "no-op and cannot fail" % (key, os.path.basename(path), value))
    data[key] = value
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)


def apply_trapframe(path, frame):
    with open(path) as fh:
        data = json.load(fh)
    if frame not in data["excluded_because_in_denominator_set"]:
        die("%s is not in the instrument's denominator set, so adding it does "
            "not plant the defect" % frame)
    if any(f["frame"] == frame for f in data["frames"]):
        die("%s is already among the scored frames; the plant is a no-op" % frame)
    data["frames"].append(dict(data["frames"][0], frame=frame))
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)


def run():
    p = subprocess.run([sys.executable, VERIFIER], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    for p in (REPORT, ARMS, GAIN, TRAP, VERIFIER):
        if not os.path.exists(p):
            print("GUARD: missing " + p)
            sys.exit(3)

    rc, out = run()
    if rc != 0:
        print("GUARD: verifier is RED before any plant; fix that first")
        print(out)
        sys.exit(3)

    tmp = tempfile.mkdtemp(prefix="m116c6-")
    backups = {}
    for name, path in {"md": REPORT, "arms": ARMS, "gain": GAIN, "trap": TRAP}.items():
        backups[path] = os.path.join(tmp, name + os.path.splitext(path)[1])
        shutil.copy2(path, backups[path])

    caught, missed, false_pos = [], [], []
    try:
        for pid, kind, target, payload, expect in PLANTS:
            path = PATHS[kind]
            if kind == "md":
                apply_md(path, target, payload)
            elif kind == "trapframe":
                apply_trapframe(path, target)
            else:
                apply_json(path, target[0], target[1])

            rc, out = run()
            shutil.copy2(backups[path], path)

            if rc == 0:
                missed.append((pid, expect, "verifier stayed GREEN"))
            elif expect not in out:
                missed.append((pid, expect,
                               "went RED but not on its own guard; the guard "
                               "that should have fired was never exercised"))
            else:
                caught.append((pid, expect))

        pid, kind, target, payload = INERT
        apply_md(REPORT, target, payload)
        rc, out = run()
        shutil.copy2(backups[REPORT], REPORT)
        if rc != 0:
            false_pos.append((pid, out.strip().splitlines()[-1]))
    finally:
        for path, b in backups.items():
            shutil.copy2(b, path)
        shutil.rmtree(tmp, ignore_errors=True)

    rc, out = run()
    if rc != 0:
        print("GUARD: verifier RED after restore -- originals not cleanly restored")
        print(out)
        sys.exit(3)

    for pid, expect in caught:
        print("CAUGHT   %-4s -> %s" % (pid, expect))
    for pid, expect, why in missed:
        print("MISSED   %-4s -> %s  (%s)" % (pid, expect, why))
    for pid, line in false_pos:
        print("FALSEPOS %-4s -> %s" % (pid, line))
    if not false_pos:
        print("IGNORED  I1   inert prose  (inert, correctly ignored)")

    print("")
    print("%d/%d plants caught by their own guard, %d missed, %d false positive(s)"
          % (len(caught), len(PLANTS), len(missed), len(false_pos)))
    sys.exit(0 if not missed and not false_pos else 1)


if __name__ == "__main__":
    main()
