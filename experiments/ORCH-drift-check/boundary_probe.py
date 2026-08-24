"""Does the tool's own boundary flag know which stack is mush?

`flowers-cpl` renders as a featureless waxy blob at 100% in the frame centre.
`leaf-2-cpl` renders with detail visually indistinguishable from pure selection.
If the confidence machinery is worth anything, those two must separate on a
number the tool already prints, WITHOUT being told which is which.

The tool prints, per gate:

  gate   tol(DN-norm)   mean n_eff   n_eff=1 %   boundary %   pred sigma gain

`boundary %` is the fraction of pixels whose elected frame sits at the first or
last rung of the bracket -- the tool's structural "no frame in focus here"
signal. The prediction registered BEFORE running:

  flowers-cpl boundary % > leaf-2-cpl boundary %, by a margin large enough to
  read as a class difference rather than scene noise.

If that fails, the mush is NOT a coverage failure and the boundary flag does not
detect it -- which is a more interesting result than a pass, and kills the
"just shoot more frames" answer.

Parses the FIXED-WIDTH TABLE, never the prose (discipline 672 -- fact 1356 was
a regex that scraped the number 212 out of the phrase "Fact 212").
"""
import re
import subprocess
import sys
import time
from pathlib import Path

EXE = Path(r"C:\dev\blog\death-of-software\projects\strehl\.cargo-target-orch\release\strehl.exe")
OUT = Path(r"C:\dev\strehl-out\ORCH-boundary")
OUT.mkdir(parents=True, exist_ok=True)

STACKS = [
    ("flowers-cpl", r"D:\personal\macro\flowers-cpl"),
    ("leaf-2-cpl", r"D:\personal\macro\leaf-2-cpl"),
    ("bee-3-cpl", r"D:\personal\macro\bee-3-cpl"),
]

#  2.00      0.043032       10.734       0.53%       13.29%         0.3297x
ROW = re.compile(
    r"^\s*([0-9.]+)\s+([0-9.eE+-]+)\s+([0-9.]+)\s+([0-9.]+)%\s+([0-9.]+)%\s+([0-9.]+)x\s*$"
)


def run(name, path):
    t0 = time.time()
    p = subprocess.run(
        [str(EXE), "stack", path, "--gate", "2", "--srgb", "--auto-exposure",
         "-o", str(OUT / f"{name}.tif")],
        capture_output=True, text=True, errors="replace",
    )
    dt = time.time() - t0
    if p.returncode != 0:
        print(f"  FAILED rc={p.returncode}")
        print(p.stderr[-2000:])
        return None
    blob = p.stdout + p.stderr

    rows = []
    for line in blob.splitlines():
        m = ROW.match(line)
        if m:
            rows.append(tuple(float(x) for x in m.groups()))
    if not rows:
        print("  NO TABLE ROW MATCHED -- dumping candidate lines")
        for line in blob.splitlines():
            if "n_eff" in line or "boundary" in line:
                print("   |", line)
        return None

    gate, tol, neff, neff1, boundary, pred = rows[-1]

    # Range asserts -- discipline 673. A boundary % is a percentage; an n_eff on
    # an N-frame stack is in [1, N]. Anything outside is a parse bug, not data.
    assert 0.0 <= boundary <= 100.0, f"boundary out of range: {boundary}"
    assert 0.0 <= neff1 <= 100.0, f"n_eff=1 %% out of range: {neff1}"
    assert 1.0 <= neff <= 400.0, f"n_eff out of range: {neff}"
    assert abs(gate - 2.0) < 1e-9, f"parsed the wrong gate row: {gate}"

    print(f"  gate {gate}  n_eff {neff:.3f}  n_eff=1 {neff1:.2f}%  "
          f"boundary {boundary:.2f}%  pred {pred:.4f}x   [{dt:.1f}s]")
    return dict(name=name, neff=neff, neff1=neff1, boundary=boundary,
                pred=pred, secs=dt)


def main():
    res = []
    for name, path in STACKS:
        if not Path(path).is_dir():
            print(f"{name}: MISSING {path}")
            continue
        print(f"{name}:")
        r = run(name, path)
        if r:
            res.append(r)

    print("\n" + "=" * 78)
    print(f"{'stack':<16}{'n_eff':>9}{'n_eff=1 %':>12}{'boundary %':>13}{'pred':>9}")
    for r in res:
        print(f"{r['name']:<16}{r['neff']:>9.3f}{r['neff1']:>12.2f}"
              f"{r['boundary']:>13.2f}{r['pred']:>9.4f}")

    by = {r["name"]: r for r in res}
    if "flowers-cpl" in by and "leaf-2-cpl" in by:
        f, l = by["flowers-cpl"]["boundary"], by["leaf-2-cpl"]["boundary"]
        print()
        print(f"PREDICTION: flowers boundary %% > leaf boundary %%")
        print(f"MEASURED  : flowers {f:.2f}%  leaf {l:.2f}%   "
              f"ratio {f / l if l else float('inf'):.2f}x")
        print("VERDICT   : " + ("PASS -- the tool knows the mushy stack is uncovered"
                                if f > l else
                                "FAIL -- boundary flag does NOT explain the mush"))


if __name__ == "__main__":
    sys.exit(main())
