"""negctl_patch.py — commission verify_patch.py by planting defects.

A green verifier is a claim about an instrument, and the claim is worthless
until the instrument has been shown to go red. This copies the report and the
scorer JSONs into %TEMP%, plants one defect at a time, and requires RED.

Two rules carried from negctl_ca.py, both learned the hard way:

  * every mutation is anchored on a string that must occur EXACTLY ONCE, and a
    miss is a hard error rather than a silent no-op. A bare replace(x, y, 1)
    lands on whichever site comes first, which is usually not the canonical
    one, and reports a false GREEN.
  * one INERT plant, which changes prose that carries no claim, must be
    IGNORED. A verifier that goes red on everything is as useless as one that
    goes red on nothing.

Run:  python experiments/M116-promotion/negctl_patch.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HERE = Path(__file__).resolve().parent
REPORT = HERE.parents[1] / "docs" / "research" / "M116-promotion.md"
SRC_OUT = Path(r"C:\dev\strehl-out\M116\patch")
VERIFY = HERE / "verify_patch.py"

# (name, kind, anchor, replacement, must_be_caught)
# kind: "md" mutates the report, "k"/"f" mutate a scorer JSON by key path.
PLANTS = [
    ("D1  plant value K(M0)", "md",
     "| `M0` gate 0 — **the plant** | `2.911` |",
     "| `M0` gate 0 — **the plant** | `2.912` |", True),
    ("D2  shipped K(A0)", "md",
     "| `A0` shipped gate 4 | `26.660` | `32.78` |",
     "| `A0` shipped gate 4 | `26.680` | `32.78` |", True),
    ("D3  G1 verdict flipped", "md",
     "**`G1` FAILED, with the sign reversed.**",
     "**`G1` PASSED, as predicted.**", True),
    ("D4  H1 ROI-W ratio", "md",
     "| ROI-W `y=256 x=768 384px` | `0.00738` | `0.02029` | **`2.750`** | PASS |",
     "| ROI-W `y=256 x=768 384px` | `0.00738` | `0.02029` | **`2.760`** | PASS |",
     True),
    ("D5  H1 ROI-N ratio", "md",
     "| `0.05908` | `0.05811` | **`0.983`** | **FAIL** |",
     "| `0.05908` | `0.05811` | **`1.983`** | **FAIL** |", True),
    ("D6  blur control ratio", "md",
     "| **ratio, bar `>= 2.0`** | **`3.000`** — PASS |",
     "| **ratio, bar `>= 2.0`** | **`3.500`** — PASS |", True),
    ("D7  detail cost A2", "md",
     "| `A2` soft gate gaussian | `-0.01868` |",
     "| `A2` soft gate gaussian | `-0.01860` |", True),
    ("D8  campaign verdict", "md",
     "**Campaign 5 verdict: NO WORKING INSTRUMENT.",
     "**Campaign 5 verdict: A WORKING INSTRUMENT.", True),
    ("D9  n_eff in flat ROI", "md",
     "| median in the flattest-decile ROI | **`99.00`** |",
     "| median in the flattest-decile ROI | **`89.00`** |", True),
    ("D10 blur sigma", "md",
     "At **ROI-W**, `sigma = 0.7932 px`:",
     "At **ROI-W**, `sigma = 0.8932 px`:", True),
    ("D11 section 1 verdict", "md",
     "| **NO INSTRUMENT** | section 5h;",
     "| **PROMOTE** | section 5h;", True),
    ("D12 election component count", "md",
     "(`557` components in ROI-W, `154` in",
     "(`558` components in ROI-W, `154` in", True),
    ("D13 H8 fraction", "md",
     "`66.7 %` of `A2`'s `F4` reduction at ROI-W",
     "`76.7 %` of `A2`'s `F4` reduction at ROI-W", True),
    ("D14 void headline ratio", "md",
     "0.034 / 26.660 = 0.00127`", "0.034 / 26.660 = 0.00227`", True),
    # Data-side plants: the report is untouched, the measurement moves.
    ("D15 JSON K(M0) clears its bar", "k",
     ("subjects", "bee-3-cpl", "arms", "M0", "K"), 60.0, True),
    ("D16 JSON N1 no longer equals A0", "f",
     ("subjects", "bee-3-cpl", "named", "ROI-W", "arms", "N1", "F4"),
     0.0074, True),
    # INERT: prose with no claim in it. Must be ignored.
    ("I1  inert prose", "md",
     "the cut-out-sticker look",
     "the cutout-sticker look", False),
]


def run_verify(tmp: Path):
    env = dict(os.environ)
    env["M116_REPORT"] = str(tmp / "M116-promotion.md")
    env["M116_PATCH_OUT"] = str(tmp)
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, str(VERIFY)], env=env,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    base = Path(tempfile.mkdtemp(prefix="m116negctl_"))
    caught = missed = 0
    fp_inert = 0
    try:
        # Baseline must be GREEN, or nothing below means anything.
        shutil.copy2(REPORT, base / "M116-promotion.md")
        for j in ("scores-patch.json", "scores-patch2.json"):
            shutil.copy2(SRC_OUT / j, base / j)
        rc, out = run_verify(base)
        if rc != 0:
            print("BASELINE IS NOT GREEN — commissioning is meaningless.")
            print(out)
            return 2
        print(f"baseline: GREEN  ({out.strip().splitlines()[0]})\n")

        for name, kind, anchor, repl, must in PLANTS:
            tmp = Path(tempfile.mkdtemp(prefix="m116p_", dir=base))
            shutil.copy2(REPORT, tmp / "M116-promotion.md")
            for j in ("scores-patch.json", "scores-patch2.json"):
                shutil.copy2(SRC_OUT / j, tmp / j)

            if kind == "md":
                t = (tmp / "M116-promotion.md").read_text(encoding="utf-8")
                n = t.count(anchor)
                if n != 1:
                    raise SystemExit(
                        f"MUTATION TARGET NOT UNIQUE for {name}: {n} "
                        f"occurrence(s) of {anchor!r}. A plant that does not "
                        f"land reports a false GREEN.")
                (tmp / "M116-promotion.md").write_text(
                    t.replace(anchor, repl), encoding="utf-8")
            else:
                fn = "scores-patch.json" if kind == "k" else "scores-patch2.json"
                d = json.loads((tmp / fn).read_text(encoding="utf-8"))
                node = d
                for key in anchor[:-1]:
                    node = node[key]
                if anchor[-1] not in node:
                    raise SystemExit(f"MUTATION TARGET NOT FOUND for {name}")
                node[anchor[-1]] = repl
                (tmp / fn).write_text(json.dumps(d, indent=2), encoding="utf-8")

            rc, out = run_verify(tmp)
            red = (rc != 0)
            if must and red:
                caught += 1
                first = next((l.strip() for l in out.splitlines()
                              if l.strip().startswith(("P6", "P7", "s1"))),
                             "(red)")
                print(f"CAUGHT   {name}  -> {first}")
            elif must and not red:
                missed += 1
                print(f"MISSED   {name}  -> verifier stayed GREEN")
            elif not must and red:
                fp_inert += 1
                print(f"FALSE +  {name}  -> inert plant went RED")
                print(out)
            else:
                print(f"IGNORED  {name}  (inert, correctly ignored)")

        total = sum(1 for p in PLANTS if p[4])
        print(f"\n{caught}/{total} plants caught, {missed} missed, "
              f"{fp_inert} false positive(s) on the inert plant")
        return 0 if (missed == 0 and fp_inert == 0) else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
