# -*- coding: utf-8 -*-
"""Negative controls on verify_s28.py.

A checker that returns 0 is a claim about the instrument, not about the
document. Each control plants a known defect anchored on a full unique
string, hard-errors if the anchor does not land the expected number of
times, runs the verifier, and restores the file from a temp copy
(never `git checkout --`), confirming the restore by hash.
"""
import hashlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "research" / "M87-occlusion.md"
VERIFY = ROOT / "experiments" / "M87-occlusion" / "src" / "verify_s28.py"

CONTROLS = [
    # name, find, replace, occurrences to change (None = all), expect
    ("N1 every instance of a T4 figure is wrong",
     "65.16", "65.61", None, "RED"),
    ("N2 a single instance of the same figure is wrong",
     "65.16", "65.61", 1, "GREEN"),
    ("N3 the drift rho is wrong everywhere",
     "\u22120.9289", "\u22120.9298", None, "RED"),
    ("N4 a control's slope is wrong everywhere",
     "+0.9802", "+0.9820", None, "RED"),
    ("N5 a re-derived share is wrong everywhere",
     "16.24%", "16.42%", None, "RED"),
]

# Controls that mutate the OPERAND rather than the prose. These test that the
# verifier re-derives from the JSON instead of pattern-matching the document
# against itself: the prose is untouched and must still go red.
JSON_CONTROLS = [
    ("N6 the observed-step operand is wrong in the JSON",
     "80-sign-repaired.json", "63.5", "61.5", "RED"),
    ("N7 a control is marked failing in the JSON",
     "80-sign-repaired.json", '"controls_ok": true', '"controls_ok": false',
     "RED"),
]


def run():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(VERIFY)], capture_output=True,
                       env=env, cwd=str(ROOT))
    out = p.stdout.decode("utf-8", "replace")
    return p.returncode, out


def main():
    orig = REPORT.read_bytes()
    h0 = hashlib.sha256(orig).hexdigest()
    backup = pathlib.Path(tempfile.gettempdir()) / "M87-s28-backup.md"
    backup.write_bytes(orig)
    print(f"backed up {REPORT.name} ({len(orig)} bytes, sha256 {h0[:16]}) to "
          f"{backup}")

    rc, out = run()
    print(f"\nbaseline: rc={rc}  {out.strip().splitlines()[-1]}")
    if rc != 0:
        print("BASELINE IS NOT GREEN -- controls are meaningless; aborting")
        return 1

    text = orig.decode("utf-8")
    results = []
    for name, find, repl, count, expect in CONTROLS:
        n = text.count(find)
        if n == 0:
            raise SystemExit(f"MUTATION TARGET NOT FOUND: {find!r} for {name}")
        if count is not None and n < count + 1:
            raise SystemExit(
                f"MUTATION TARGET APPEARS ONLY {n}x: {find!r} for {name} needs "
                f"at least {count + 1} so that one instance survives")
        mutated = text.replace(find, repl, count) if count else text.replace(find, repl)
        if mutated == text:
            raise SystemExit(f"MUTATION DID NOT LAND for {name}")
        REPORT.write_text(mutated, encoding="utf-8")
        rc, out = run()
        got = "GREEN" if rc == 0 else "RED"
        ok = got == expect
        tail = [l for l in out.strip().splitlines() if l.strip().startswith("-")]
        results.append((name, n, count or n, got, expect, ok, tail[:2]))
        REPORT.write_bytes(orig)
        if hashlib.sha256(REPORT.read_bytes()).hexdigest() != h0:
            raise SystemExit("RESTORE FAILED -- the report is not byte-identical")

    for name, fname, find, repl, expect in JSON_CONTROLS:
        jp = ROOT / "experiments" / "M87-occlusion" / "data" / fname
        jorig = jp.read_bytes()
        jh = hashlib.sha256(jorig).hexdigest()
        jt = jorig.decode("utf-8")
        n = jt.count(find)
        if n == 0:
            raise SystemExit(f"MUTATION TARGET NOT FOUND in {fname}: {find!r} "
                             f"for {name}")
        jp.write_text(jt.replace(find, repl), encoding="utf-8")
        rc, out = run()
        got = "GREEN" if rc == 0 else "RED"
        tail = [l for l in out.strip().splitlines() if l.strip().startswith("-")]
        results.append((name + " (operand, prose untouched)", n, n, got, expect,
                        got == expect, tail[:2]))
        jp.write_bytes(jorig)
        if hashlib.sha256(jp.read_bytes()).hexdigest() != jh:
            raise SystemExit(f"RESTORE FAILED for {fname}")

    print("\n--- controls ---")
    for name, n, k, got, expect, ok, tail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        print(f"          {k} of {n} instance(s) mutated -> {got} "
              f"(expected {expect})")
        for t in tail:
            print(f"          {t.strip()}")

    final = hashlib.sha256(REPORT.read_bytes()).hexdigest()
    print(f"\nreport restored: sha256 {final[:16]} "
          f"({'identical' if final == h0 else 'DIFFERENT'})")
    rc, out = run()
    print(f"verifier on the restored file: rc={rc}  "
          f"{out.strip().splitlines()[-1]}")
    bad = [r for r in results if not r[5]]
    if bad or rc != 0 or final != h0:
        print(f"\n{len(bad)} control(s) behaved unexpectedly")
        return 1
    print("\nall controls behaved as registered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
