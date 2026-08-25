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
    # N9-N11 cover the three anchored full-coverage checks that replaced a
    # single document-wide count of "**100.00%**".  Section 34 inflated that
    # count from 3 to 5 by quoting an unrelated rate of 100%, and bumping the
    # expectation would have been the repair P140 recorded as wrong.  These
    # arms carry a `want`, so each has to turn the check it aims at red.
    ("N9-COVER-P111", "RED", "the P111 fact-row copy of the full-coverage "
     "figure is altered",
     lambda: sub(REPORT, "It measured **100.00%** and printed PASS.",
                 "It measured **99.00%** and printed PASS.", 1),
     "full coverage @ P111 fact row"),
    ("N10-COVER-TABLE", "RED", "the 29 table cell holding the full-coverage "
     "figure is altered",
     lambda: sub(REPORT, "| **100.00%** | 0.4137 |",
                 "| **99.00%** | 0.4137 |", 1),
     "full coverage @ 29 table"),
    # N11 is the arm the repair exists for.  Un-bolding PASS at the section 29
    # site makes that sentence textually identical to the P111 one, so the
    # document still contains two sentences reading 100.00% and a bare count
    # of the figure would be unchanged.  Only anchors that distinguish the two
    # sites can see it: the P111 anchor must go to 2x and the 29 anchor to 0x.
    ("N11-COVER-COLLAPSE", "RED", "PASS un-bolded at the 29 site, collapsing "
     "it onto the P111 site (a bare count cannot see this)",
     lambda: sub(REPORT, "It measured **100.00%** and printed **PASS**.",
                 "It measured **100.00%** and printed PASS.", 1),
     "full coverage @ 29 prose"),
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
        for entry in CONTROLS:
            name, expect, desc, mutate = entry[:4]
            want = entry[4] if len(entry) > 4 else None
            mutate()
            r = subprocess.run([sys.executable, str(SRC / "verify_s29.py")],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace", cwd=str(ROOT))
            got = "GREEN" if r.returncode == 0 else "RED"
            failed = [l.strip()[2:] for l in (r.stdout or "").splitlines()
                      if l.startswith("  - ")]
            ok = got == expect
            note = ""
            # A RED from an unrelated check is a false pass of the control: it
            # certifies a check that was never exercised.
            if ok and want is not None and not any(want in f for f in failed):
                ok = False
                note = f"  [RED BUT NOT FROM {want!r}]"
            results.append((name, expect, got, ok))
            mark = "ok  " if ok else "BAD "
            print(f"{mark} {name:<19} expected {expect:<5} got {got:<5}  {desc}{note}")
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
