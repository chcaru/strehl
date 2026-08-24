"""Registered negative controls for verify_s31.py.

A green verifier is a claim about the instrument, not about the work. These
arms plant defects the verifier must catch, and one defect it must NOT catch.

Design rules this file obeys, each of them paid for earlier in the milestone:

* Every anchor is a UNIQUE, SINGLE line of text. A multi-line anchor never
  matches a CRLF file, so the mutation silently does nothing and the arm
  reports green for the wrong reason (P114).
* A missing anchor is a hard error -- `MUTATION TARGET NOT FOUND` -- never a
  silent `replace(x, y, 1)` no-op.
* N1 mutates ONE of three instances of a repeated figure. A checker that only
  asks whether a string is present anywhere is instance-blind and would pass
  a number that is wrong in one place and right in another (P105).
* N3-N7 mutate a JSON OPERAND and leave the prose untouched. If the verifier
  were string-matching its own document these arms would stay green; going
  red proves it re-derives.
* N9 is expected GREEN. Without it, a control set in which every arm goes red
  is equally consistent with a verifier that fails on any edit at all.
* The document is backed up to %TEMP% and restored from that copy. Never
  `git checkout --`: it reverts to HEAD and destroys uncommitted work.
* The exit code is read from `subprocess.run(...).returncode` in Python. A
  PowerShell pipeline truncated by `Select-Object -First N` reports 0 for a
  process that exited 1 (rule 46).
"""
import os
import pathlib
import shutil
import subprocess
import sys

SRC = pathlib.Path(__file__).resolve().parent
ROOT = SRC.parents[2]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
DATA = SRC.parent / "data"
VERIFY = SRC / "verify_s31.py"
TMP = pathlib.Path(os.environ["TEMP"]) / "M87-s31-controls"

# name, target file, unique single-line anchor, replacement, expected colour
ARMS = [
    ("N1  one of three 211x instances", DOC,
     "Slope **\u22120.5228**, intercept 283.3 DN at `n_eff` = 1, across a 211\u00d7 range of",
     "Slope **\u22120.5228**, intercept 283.3 DN at `n_eff` = 1, across a 212\u00d7 range of",
     "RED"),
    ("N2  veil amplitude in prose", DOC,
     "Amplitude **+4133 DN** over the \u2212742.5 DN baseline: 35.7 codes of the",
     "Amplitude **+4103 DN** over the \u2212742.5 DN baseline: 35.7 codes of the",
     "RED"),
    ("N3  JSON operand: veil amplitude", DATA / "90-veil.json",
     '"amp_dn": 4133.30078125', '"amp_dn": 3900.30078125', "RED"),
    ("N4  JSON operand: tips inside mask", DATA / "92-erasure.json",
     '"tips_in_mask": 0', '"tips_in_mask": 7', "RED"),
    ("N5  JSON operand: C-INT not exactly 1", DATA / "92-erasure.json",
     '"C_INT": 1.0', '"C_INT": 0.98', "RED"),
    ("N6  JSON operand: derived ratio decoupled", DATA / "89-rescore.json",
     '"B10_ratio": 0.6735206805460128', '"B10_ratio": 0.6835206805460128',
     "RED"),
    ("N7  JSON operand: recorded render hash", DATA / "87-election.json",
     '"sha_render": "e400a63aa9f6ab1f1957940d7bd9d4965d67e01f6f0e1a0a7abc30d8e7f17112"',
     '"sha_render": "d400a63aa9f6ab1f1957940d7bd9d4965d67e01f6f0e1a0a7abc30d8e7f17112"',
     "RED"),
    ("N8  extra unescaped pipe in P118 row", DOC,
     "13.1\u00d7 smaller and the wrong sign. | MEASURED |",
     "13.1\u00d7 smaller and the wrong sign. | MEA|SURED |", "RED"),
    ("N9  prose reworded, no figure touched", DOC,
     "No, and the two-layer reading survives, but the population is not the one my",
     "No, and the two-layer account survives, but the population is not the one my",
     "GREEN"),
]


def run_verifier():
    r = subprocess.run([sys.executable, str(VERIFY)], capture_output=True,
                       cwd=str(ROOT), env={**os.environ,
                                           "PYTHONIOENCODING": "utf-8"})
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    return r.returncode, out


def main():
    code, out = run_verifier()
    if code != 0:
        print("BASELINE IS NOT GREEN -- controls are meaningless")
        print(out)
        return 1
    print(f"baseline GREEN: {out.strip().splitlines()[0]}\n")

    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    targets = {p for _, p, _, _, _ in ARMS}
    backups = {}
    for p in targets:
        b = TMP / p.name
        shutil.copy2(p, b)
        backups[p] = b

    results, bad = [], 0
    try:
        for name, path, old, new, want in ARMS:
            src = backups[path].read_bytes().decode("utf-8")
            n = src.count(old)
            if n != 1:
                raise SystemExit(
                    f"MUTATION TARGET NOT FOUND: arm {name!r} anchor occurs "
                    f"{n} times in {path.name}, need exactly 1")
            path.write_bytes(src.replace(old, new).encode("utf-8"))
            rc, o = run_verifier()
            got = "GREEN" if rc == 0 else "RED"
            first = next((l for l in o.splitlines() if "FAIL" in l or
                          "Error" in l or "Traceback" in l), "")
            shutil.copy2(backups[path], path)
            ok = got == want
            bad += 0 if ok else 1
            results.append((name, want, got, ok, first.strip()[:78]))
    finally:
        for p, b in backups.items():
            shutil.copy2(b, p)

    rc, out = run_verifier()
    restored = "GREEN" if rc == 0 else "RED"
    print(f"{'arm':<38} {'want':<6} {'got':<6} ok  first failure")
    for name, want, got, ok, first in results:
        print(f"{name:<38} {want:<6} {got:<6} "
              f"{'yes' if ok else 'NO ':<3} {first}")
    print(f"\nrestored baseline: {restored}")
    if restored != "GREEN":
        print("RESTORE FAILED -- the document is not as it was")
        bad += 1
    print(f"{len(results)} arms, {bad} disagreements")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
