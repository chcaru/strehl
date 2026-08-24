"""M87 -- controls for verify_s33.  Does the checker actually re-derive?

A checker that passes proves nothing on its own: it may be matching the
document against itself, or asserting that a figure is merely PRESENT, which
cannot see a value that is wrong in one place and right in another (`P105`).
Each arm below plants a specific defect and states the expected verdict BEFORE
the run.

  N1  mutate ONE of the five instances of r = 0.8833 in the prose.
      Instance-blindness: a presence check stays green here.       RED
  N2  mutate the OPERAND V(0.00) in 96-gate-final.json, prose untouched.
      Proves the ratio is recomputed from data, not read from the text. RED
  N3  mutate the B18 RMS ratio operand in 98-delta-form.json.        RED
  N4  mutate the B17 sweep minimum in 97-gate-attrib.json.           RED
  N5  mutate the B16 Pearson operand in 97-gate-attrib.json.         RED
  N6  mutate the float32 error in 95-control-diag.json.              RED
  N7  flip the B15 verdict operand to GATE-DEPENDENT.                RED
  N8  delete the phrase "NOT an admission artifact" from P128.       RED
  N9  turn the C-POS calibration flag false in 96-gate-final.json.   RED
  N10 mutate a figure in section 30, which section 33 does not own.
      EXPECTED GREEN -- specificity.  Without an arm that is supposed to
      pass, "every arm red" is equally consistent with a checker that fails
      on any edit whatsoever, and the whole set would prove nothing.

NOT TESTED, DELIBERATELY.  verify_s33 re-parses the n_eff ladder from the
orchestrator's `neff-ladder.txt`, and mutating that would be the natural arm
for it.  I am not doing it: that file is another agent's artifact in a shared
scratch directory and seven agents are live in this tree, so a file that is
briefly wrong on disk could be read by someone else mid-arm.  The re-parse is
therefore checked only by the assertion in verify_s33 itself, and this gap is
recorded rather than hidden.

Restores are from a byte copy in %TEMP%, never `git checkout --`, which
reverts to HEAD and would destroy uncommitted work.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
VERIFY = pathlib.Path(__file__).resolve().parent / "verify_s33.py"
TMP = pathlib.Path(tempfile.gettempdir())


def run():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(VERIFY)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def mutate_text(path, anchor, new):
    s = path.read_bytes().decode("utf-8")
    if anchor not in s:
        raise SystemExit(f"MUTATION TARGET NOT FOUND in {path.name}:\n  {anchor}")
    if s.count(anchor) != 1:
        raise SystemExit(f"ANCHOR NOT UNIQUE ({s.count(anchor)}x): {anchor}")
    path.write_bytes(s.replace(anchor, new, 1).encode("utf-8"))


def mutate_json(path, keys, value):
    d = json.loads(path.read_text(encoding="utf-8"))
    n = d
    for k in keys[:-1]:
        n = n[k]
    if keys[-1] not in n:
        raise SystemExit(f"MUTATION TARGET NOT FOUND: {path.name} {keys}")
    n[keys[-1]] = value
    path.write_text(json.dumps(d, indent=1, default=float), encoding="utf-8")


ARMS = [
    ("N1", DOC, "text",
     "| **0.00** | 51 864.0 | 3716 | 31 208 | **0.11906** | **0.8833** | 25 px |",
     "| **0.00** | 51 864.0 | 3716 | 31 208 | **0.11906** | **0.8834** | 25 px |",
     "RED", "one of five instances of r"),
    ("N2", DATA / "96-gate-final.json", "json", ["arms", "0.00", "V"], 0.10,
     "RED", "the V(0.00) operand"),
    ("N3", DATA / "98-delta-form.json", "json", ["B18", "rms_const"], 200.0,
     "RED", "the B18 RMS operand"),
    ("N4", DATA / "97-gate-attrib.json", "json", ["bars", "B17", "min"], 0.60,
     "RED", "the B17 sweep minimum"),
    ("N5", DATA / "97-gate-attrib.json", "json", ["bars", "B16", "pearson"],
     0.95, "RED", "the B16 Pearson operand"),
    ("N6", DATA / "95-control-diag.json", "json",
     ["C_AFFINE", "float32", "max_dV"], 1e-13, "RED", "the float32 error"),
    ("N7", DATA / "96-gate-final.json", "json", ["bars", "B15", "verdict"],
     "GATE-DEPENDENT", "RED", "the B15 verdict"),
    ("N8", DOC, "text", "veil is NOT an admission artifact: it survives a",
     "veil is an admission artifact: it survives a", "RED",
     "P128's headline claim"),
    ("N9", DATA / "96-gate-final.json", "json", ["controls", "C_POS",
                                                  "calibrated"], False,
     "RED", "the C-POS calibration flag"),
    ("N10", DOC, "text",
     "## 30. The sidecar alert: the risk was real, the contamination was not",
     "## 30. The sidecar alert: the risk was fake, the contamination was not",
     "GREEN", "a section 33 does not own"),
]


def main():
    code, out = run()
    print(f"baseline: {'GREEN' if code == 0 else 'RED'}  {out.strip()}")
    if code != 0:
        print("baseline is not green; controls are meaningless.  Stopping.")
        return 1

    disagree = 0
    for tag, path, kind, a, b, expect, what in ARMS:
        bak = TMP / f"m87s33-{tag}-{path.name}"
        shutil.copy2(path, bak)
        try:
            if kind == "text":
                mutate_text(path, a, b)
            else:
                mutate_json(path, a, b)
            c, o = run()
            got = "GREEN" if c == 0 else "RED"
            ok = got == expect
            disagree += 0 if ok else 1
            first = next((l.strip() for l in o.splitlines()
                          if "FAIL" in l), "")
            print(f"  {tag} {expect:>5} -> {got:<5}"
                  f" {'ok' if ok else 'DISAGREES'}   mutated {what}")
            if first:
                print(f"       {first[:120]}")
        finally:
            shutil.copy2(bak, path)
            bak.unlink(missing_ok=True)

    code, out = run()
    print(f"restored: {'GREEN' if code == 0 else 'RED'}  {out.strip()}")
    print(f"\ncontrol_s33: {len(ARMS)} arms, {disagree} disagreements")
    return 1 if (disagree or code != 0) else 0


if __name__ == "__main__":
    sys.exit(main())
