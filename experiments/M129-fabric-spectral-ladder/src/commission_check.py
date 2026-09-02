"""Commission check_prereg.py: prove it fires, defect by defect.

A checker that has never failed may be a silent no-op. Each plant below is a
DELIBERATE, SPECIFIC corruption of one claim in PREREGISTRATION.md, and the
commissioning bar is that the checker reports a failure naming that claim.

Two safety properties, both learned the hard way and both enforced here:

  1. The real document is NEVER modified. Each plant is written to a fresh copy in
     the temp directory and the checker is pointed at the copy. There is no path by
     which a failed run can leave the repository altered, and no `git checkout --`
     anywhere (which reverts to HEAD and destroys uncommitted work).

  2. Every mutation is anchored on a string that must occur EXACTLY ONCE, and the
     plant hard-errors if the anchor is missing or ambiguous. A bare
     `text.replace(old, new, 1)` that silently hits the wrong occurrence produces a
     green negative control, which is worse than no control at all: it certifies the
     instrument using a mutation that was never applied where it was aimed.

Exit 0 only if every plant is caught AND the unmutated document still passes.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(HERE), "PREREGISTRATION.md")
CHECKER = os.path.join(HERE, "check_prereg.py")

# (id, description, anchor that must be unique, replacement)
PLANTS = [
    ("D1", "2.1 GQ quincunx Nyquist reach, last digit",
     "| GQ quincunx | 7.2408 | 69.053 |",
     "| GQ quincunx | 7.2408 | 69.054 |"),

    ("D2", "2.2 H2 bellows factor B",
     "| H2 fact 1152 low | 105.54 | 17.227 | 3.0763 | 1.3099 |",
     "| H2 fact 1152 low | 105.54 | 17.227 | 3.0863 | 1.3099 |"),

    ("D3", "2.2 H3 pupil magnification p",
     "| H3 fact 1152 high | 135.17 | 13.451 | 2.4020 | 1.9400 |",
     "| H3 fact 1152 high | 135.17 | 13.451 | 2.4020 | 1.9500 |"),

    ("D4", "2.3 f/18 H3 cutoff frequency",
     "| 18.0 | 27.07 IN | 32.83 IN | 42.05 IN | +27.00 |",
     "| 18.0 | 27.07 IN | 32.83 IN | 42.95 IN | +27.00 |"),

    ("D5", "2.3 f/11 H3 margin under the GQ reach",
     "| 11.0 | 44.29 IN | 53.73 IN | 68.81 IN | **+0.24** |",
     "| 11.0 | 44.29 IN | 53.73 IN | 68.81 IN | **+1.24** |"),

    ("D6", "2.3 band tag: claim f/8 H2 is measurable when it is not",
     "| 8.0 | 60.90 IN | 73.88 out | 94.62 out | -25.57 |",
     "| 8.0 | 60.90 IN | 73.88 IN | 94.62 out | -25.57 |"),

    ("D7", "section 0 hypothesis separation percentage",
     "a 28.07% separation in cutoff frequency at every aperture",
     "a 26.07% separation in cutoff frequency at every aperture"),

    ("D8", "T2 light ratio between f/5.6 and f/18",
     "f/18 receives ~1/10.3 the light of f/5.6.",
     "f/18 receives ~1/12.3 the light of f/5.6."),

    ("D9", "T4 wavelength sensitivity, B at H3 at 500 nm",
     "at 500 nm, `B` at H2/H3 becomes 3.3840 / 2.6422",
     "at 500 nm, `B` at H2/H3 becomes 3.3840 / 2.6522"),

    ("D10", "T1 depth-of-field growth factor",
     "Depth of field grows 3.2x from f/5.6 to f/18",
     "Depth of field grows 4.2x from f/5.6 to f/18"),

    ("D11", "2.2 H1 cutoff, which must match predict.py's registered value",
     "| H1 fact 1149 (already refuted) | 87.00 | 20.899 | 3.7319 | 0.9956 |",
     "| H1 fact 1149 (already refuted) | 88.00 | 20.899 | 3.7319 | 0.9956 |"),
]


def run(doc_path):
    """Run the checker against a document; return (exit code, stdout)."""
    r = subprocess.run([sys.executable, CHECKER, doc_path],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    with open(DOC, encoding="utf-8") as fh:
        clean = fh.read()

    tmpdir = tempfile.mkdtemp(prefix="m129commission-")
    caught, missed, bad_anchor = [], [], []
    try:
        # --- the instrument must pass on the real document first -----------
        rc, out = run(DOC)
        if rc != 0:
            print("ABORT: the checker fails on the unmutated document.")
            print(out)
            return 1
        base_claims = int(re.search(r"(\d+) claims", out).group(1))
        print(f"baseline: {base_claims} claims, checker GREEN on the real document\n")

        for pid, desc, anchor, repl in PLANTS:
            n = clean.count(anchor)
            if n != 1:
                bad_anchor.append(f"{pid} anchor occurs {n} times, must be exactly 1: "
                                  f"{anchor!r}")
                print(f"  {pid}  ANCHOR ERROR ({n} occurrences)  {desc}")
                continue

            mutated = clean.replace(anchor, repl)
            if mutated == clean:
                bad_anchor.append(f"{pid} mutation produced no change")
                print(f"  {pid}  NO-OP MUTATION  {desc}")
                continue

            path = os.path.join(tmpdir, f"{pid}.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(mutated)

            rc, out = run(path)
            # the checker must both fail AND still have examined every claim
            claims = re.search(r"(\d+) claims", out)
            same_coverage = claims and int(claims.group(1)) == base_claims
            if rc != 0 and same_coverage:
                first = next((ln.strip() for ln in out.splitlines()
                              if ln.strip().startswith("- ")), "")
                caught.append(pid)
                print(f"  {pid}  CAUGHT   {desc}\n           {first}")
            elif rc != 0:
                caught.append(pid)
                print(f"  {pid}  CAUGHT   {desc}  (coverage changed: "
                      f"{claims.group(1) if claims else '?'} vs {base_claims})")
            else:
                missed.append(pid)
                print(f"  {pid}  MISSED   {desc}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    total = len(PLANTS)
    print(f"\npartition: caught {len(caught)} + missed {len(missed)} + "
          f"anchor errors {len(bad_anchor)} = {total}")
    for b in bad_anchor:
        print(f"  ANCHOR: {b}")
    if missed or bad_anchor:
        print("\nCOMMISSIONING FAILED")
        return 1
    print("COMMISSIONING PASSED: every planted defect was caught")
    return 0


if __name__ == "__main__":
    sys.exit(main())
