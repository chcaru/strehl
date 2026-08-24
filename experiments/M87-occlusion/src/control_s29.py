# -*- coding: utf-8 -*-
"""Negative controls for `verify_s29.py`.

A green verifier is a claim about the instrument, not about the report. Each
control plants one defect, runs the verifier, and requires it to go RED; the
no-op control requires GREEN. Every mutation is anchored on a string whose
occurrence count is asserted first, so a control that fails to land hard-errors
instead of silently passing.

Two controls mutate the JSON operands with the prose untouched: those prove the
verifier re-derives rather than pattern-matches. One control mutates exactly
**one of three** copies of a figure: that is the instance-blindness of `P105`
and `P112`, and it is the specific hole the exact-count design closes.
"""
import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "experiments" / "M87-occlusion" / "src"
REPORT = ROOT / "docs" / "research" / "M87-occlusion.md"
JSON81 = ROOT / "experiments" / "M87-occlusion" / "data" / "81-contour-support.json"
TMP = pathlib.Path(os.environ["TEMP"])
M = "\u2212"


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sub(path: pathlib.Path, old: str, new: str, expect: int, which=None) -> None:
    """Replace `old`; hard-error unless it occurs exactly `expect` times.

    `which=-1` replaces only the last occurrence, which is how the 1-of-N
    instance control is planted.
    """
    assert "\n" not in old, "anchor must be single-line"
    t = path.read_text(encoding="utf-8")
    got = t.count(old)
    if got != expect:
        raise SystemExit(f"MUTATION TARGET NOT FOUND: {old!r} occurs {got}x, "
                         f"expected {expect}x in {path.name}")
    if which == -1:
        i = t.rfind(old)
        t = t[:i] + new + t[i + len(old):]
    else:
        t = t.replace(old, new)
    path.write_text(t, encoding="utf-8")


def jset(path: pathlib.Path, keys: tuple, value) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    node = d
    for k in keys[:-1]:
        node = node[k]
    assert keys[-1] in node, f"MUTATION TARGET NOT FOUND: {keys}"
    old = node[keys[-1]]
    assert old != value, f"mutation is a no-op for {keys}"
    node[keys[-1]] = value
    path.write_text(json.dumps(d, indent=1), encoding="utf-8")


# (name, expectation, description, mutate)
CONTROLS = [
    ("N0-NOOP", "GREEN", "no mutation: the instrument must be quiet",
     lambda: None),
    ("N1-ALL", "RED", "all 3 copies of the boundary share are wrong",
     lambda: sub(REPORT, "29.9951%", "29.9952%", 3)),
    ("N2-ONE-OF-3", "RED", "exactly ONE of 3 copies of the boundary share is "
     "wrong (a presence check would pass this)",
     lambda: sub(REPORT, "29.9951%", "29.9952%", 3, which=-1)),
    ("N3-JSON-FIXED", "RED", "JSON operand T4.thin.fixed moved; prose untouched",
     lambda: jset(JSON81, ("T4", "thin", "fixed"), 0.0357)),
    ("N4-JSON-SD", "RED", "JSON operand T4.null_sd moved, so z must stop "
     "re-deriving; prose untouched",
     lambda: jset(JSON81, ("T4", "null_sd"), 3.4)),
    ("N5-SIGN-BACK", "RED", "one repaired site regressed to the wrong sign",
     lambda: sub(REPORT, f"{M}3.74% with a global depth,", "+3.7% with a "
                 "global depth,", 1)),
    ("N6-ROW-CELL", "RED", "one cell of one T4 table row is wrong",
     lambda: sub(REPORT, f"| **{M}11.01%** | {M}0.00484 |",
                 f"| **{M}11.01%** | {M}0.00481 |", 1)),
    ("N7-VERDICT", "RED", "the registered T1 verdict word is changed",
     lambda: sub(REPORT, "**3.00 px \u2014 MIXED.**",
                 "**3.00 px \u2014 THIN.**", 1)),
    ("N8-ATTENUATION", "RED", "the derived alpha attenuation ratio is wrong",
     lambda: sub(REPORT, "attenuate alpha by **2.1\u00d7**",
                 "attenuate alpha by **2.4\u00d7**", 1)),
]


def main() -> int:
    backups = {}
    for p in (REPORT, JSON81):
        b = TMP / f"m87-s29-{p.name}.bak"
        shutil.copy2(p, b)
        backups[p] = (b, sha(p))
    print(f"backed up {len(backups)} files to {TMP}\n")

    results = []
    try:
        for name, expect, desc, mutate in CONTROLS:
            mutate()
            r = subprocess.run([sys.executable, str(SRC / "verify_s29.py")],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace", cwd=str(ROOT))
            got = "GREEN" if r.returncode == 0 else "RED"
            ok = got == expect
            results.append((name, expect, got, ok))
            mark = "ok  " if ok else "BAD "
            print(f"{mark} {name:<14} expected {expect:<5} got {got:<5}  {desc}")
            if not ok:
                tail = [l for l in r.stdout.splitlines()
                        if "FAIL" in l or "passed;" in l][-4:]
                for l in tail:
                    print(f"       {l}")
            for p, (b, _) in backups.items():
                shutil.copy2(b, p)
    finally:
        for p, (b, h) in backups.items():
            shutil.copy2(b, p)
            assert sha(p) == h, f"RESTORE FAILED for {p}"
        print(f"\nrestored {len(backups)} files; SHA-256 verified identical")

    bad = [r for r in results if not r[3]]
    print(f"\n{len(results) - len(bad)}/{len(results)} controls behaved as "
          f"registered")
    for n, e, g, _ in bad:
        print(f"  - {n}: expected {e}, got {g}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
