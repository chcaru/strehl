"""Negative controls for verify_s30.py.

A verifier that returns GREEN is a claim about the INSTRUMENT, not about the
report.  Each control below plants a specific, known defect and requires the
verifier to go RED.  A control that silently fails to plant its defect would
turn itself green, so every mutation is anchored on a SINGLE-LINE string whose
occurrence count is asserted, and a miss is a hard error, never a pass.

N1 is the instance-blindness control: it corrupts exactly ONE of two copies of
a figure.  A verifier that checks presence rather than an exact count passes
that, which is the blind spot recorded in facts P112/P113.

N4 exercises the C0 control-character guard, which is the only check in this
toolchain that looks for the defect fact P116 records.

Exit codes are read via subprocess.run().returncode INSIDE PYTHON, never
through a shell pipeline: a truncating `Select-Object -First N` leaves
$LASTEXITCODE unmodified, so a shell-side gate can inherit an unrelated
command's status (fact P115).

Both mutated files are backed up to %TEMP% and restored with a SHA-256
identity check.
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
SRC = HERE / "src"
DOC = pathlib.Path("docs/research/M87-occlusion.md")
JSN = HERE / "data" / "83-arm-a-retake.json"
TMP = pathlib.Path(os.environ["TEMP"])

TARGETS = [DOC, JSN]


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def backup():
    saved = {}
    for p in TARGETS:
        b = TMP / f"{p.name}.s30ctl.bak"
        shutil.copy2(p, b)
        assert sha(b) == sha(p), p
        saved[p] = (b, sha(p))
    print(f"backed up {len(saved)} files to {TMP}")
    return saved


def restore(saved):
    for p, (b, h) in saved.items():
        shutil.copy2(b, p)
        assert sha(p) == h, f"restore mismatch: {p}"
    print(f"restored {len(saved)} files; SHA-256 verified identical")


def sub(old, new, count, which=None):
    """Replace in the report. `which` = index of the single occurrence to
    corrupt (for instance-blindness controls); None = all of them."""
    assert "\n" not in old and "\r" not in old, "anchor must be single-line"
    t = DOC.read_bytes().decode("utf-8")
    got = t.count(old)
    if got != count:
        raise SystemExit(f"MUTATION TARGET NOT FOUND: {got} != {count} of {old!r}")
    if which is None:
        t = t.replace(old, new)
    else:
        i = -1
        for _ in range(which + 1):
            i = t.index(old, i + 1)
        t = t[:i] + new + t[i + len(old):]
    DOC.write_bytes(t.encode("utf-8"))


def jset(path, value):
    d = json.loads(JSN.read_text(encoding="utf-8"))
    node = d
    for k in path[:-1]:
        node = node[k]
    assert path[-1] in node, path
    node[path[-1]] = value
    JSN.write_text(json.dumps(d, indent=1, default=float), encoding="utf-8")


def plant_ctrl():
    """Plant a U+000B exactly as a PowerShell here-string would."""
    t = DOC.read_bytes().decode("utf-8")
    old = "**Verdict CONFIRM**"
    assert t.count(old) == 1
    t = t.replace(old, "**\x0berdict CONFIRM**")
    DOC.write_bytes(t.encode("utf-8"))


CONTROLS = [
    ("N0-NOOP", "GREEN", lambda: None,
     "no mutation: the instrument must be quiet"),
    ("N1-HASH-1-OF-2", "RED",
     lambda: sub("`e5d6182fff887119e8fc5a12`", "`e5d6182fff887119e8fc5a13`", 2, 0),
     "exactly ONE of two copies of the A/A2 hash is wrong (presence would pass)"),
    ("N2-JSON-ISO", "RED", lambda: jset(["retake", "ISO_A2"], 0.061),
     "JSON operand ISO_A2 moved; prose untouched, so 8.086 must stop re-deriving"),
    ("N3-JSON-VERDICT", "RED", lambda: jset(["retake", "verdict"], "CORRECT"),
     "JSON verdict disagrees with the word in the prose"),
    ("N4-CTRLCHAR", "RED", plant_ctrl,
     "a U+000B planted exactly as a here-string would write it"),
    ("N5-MOVED", "RED", lambda: sub("**1.49 points**", "**1.59 points**", 1),
     "the re-derived shift from the original -6.6% is wrong"),
    ("N6-N-U", "RED", lambda: sub("(n = 6600, `d*` = 16)", "(n = 6060, `d*` = 16)", 1),
     "a profile count that must match 35-registration.json"),
    ("N7-S36", "RED", lambda: sub("total **\u22126.595%**", "total **\u22126.795%**", 1),
     "the script-36 decomposition no longer re-derives from its JSON"),
]


def run_verifier():
    r = subprocess.run([sys.executable, str(SRC / "verify_s30.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return "GREEN" if r.returncode == 0 else "RED"


def main():
    saved = backup()
    results = []
    try:
        for name, expect, mutate, why in CONTROLS:
            restore(saved) if name != "N0-NOOP" else None
            try:
                mutate()
            except SystemExit as e:
                print(f"FAIL {name}: {e}")
                results.append((name, expect, "NOT-PLANTED", why))
                continue
            got = run_verifier()
            ok = "ok  " if got == expect else "FAIL"
            print(f"{ok} {name:16s} expected {expect:5s} got {got:5s}  {why}")
            results.append((name, expect, got, why))
    finally:
        restore(saved)

    good = sum(1 for _, e, g, _ in results if e == g)
    print(f"\n{good}/{len(results)} controls behaved as registered")
    return 0 if good == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
