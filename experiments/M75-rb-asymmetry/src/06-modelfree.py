r"""M75 step 6 -- the same question with NO model at all.  Committed before running.

Everything in K5, F3 and G1 rests on a three-parameter fit (alpha_low,
alpha_high, delta) to 11 ISO points.  Those three parameters are not orthogonal:
at low ISO the delta term is a large share of the variance, so alpha_low and
delta trade off, while at high ISO alpha*G^2 dominates and alpha_high is nearly
free of delta.  The band-resolved delta trends from src/03-criteria.py are
+0.018 (R), -0.030 (G1), -0.037 (G2), +0.014 (B) -- OPPOSITE in sign to the
alpha trends and split by the same partition, which is exactly the signature a
fit degeneracy would leave.

I therefore do not want to assert "alpha_high is the trustworthy one" from the
structure of the fit.  H1 below removes the fit entirely: the per-band RAW
temporal variance at each ISO separately, normalised to its own mean.  No
gain model, no dual-gain switch, no delta, no Sheppard term -- just the
measured variance of the frames.

H1  RAW per-band variance row profile, per plane, at every ISO.
H2  The same for the ratio profiles, so K1's reproduction of M68 can be
    checked without the fit that both M68 and M75 used.
H3  Does the trend evolve smoothly with ISO, or step at the dual-gain
    boundary (ISO 400)?  A physical row-dependent scale should not care where
    the chip switches gain mode; a fit artefact plausibly would.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
M72SRC = HERE.parent.parent / "M72-green-correlation" / "src"
DATA = HERE.parent / "data"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


m72 = _load("m72", M72SRC / "01-green-correlation.py")
m72c = _load("m72c", M72SRC / "02-criteria.py")
pre = _load("pre", HERE / "01-preregistration.py")

NBAND = pre.NBAND
PRIMARY = "k6"
SH = 400
RNG = np.random.default_rng(20250921)
OUT: list[str] = []


def say(s: str = "") -> None:
    print(s)
    OUT.append(s)


def rule(t: str) -> None:
    say("")
    say("=" * 78)
    say(t)
    say("=" * 78)


def main() -> int:
    blob = json.loads((DATA / "02-band-sweep.json").read_text(encoding="utf-8"))
    groups = sorted(blob["groups"], key=lambda g: g["iso"])

    def raw(gg, plane):
        v = np.array(gg["axes"]["row"][PRIMARY]["planes"][plane]["var"], float)
        return v / v.mean()

    rule("H1  RAW per-band variance row profile -- NO FIT")
    say("Each cell is the OLS trend over the full sensor height of the raw")
    say("temporal variance profile, normalised to its own mean. 3*N_grad floor")
    say("in brackets. No gain model is used anywhere in this table.")
    say("")
    say(f"{'ISO':>6s} {'mode':>5s} " + " ".join(f"{p:>17s}" for p in m72.PLANES))
    trends = {p: [] for p in m72.PLANES}
    for gg in groups:
        cells = []
        for p in m72.PLANES:
            v = raw(gg, p)
            tr, r = pre.trend(v)
            f3 = 3 * pre.ngrad_floor(v, SH, RNG)
            trends[p].append(tr)
            mark = "*" if abs(tr) > f3 else " "
            cells.append(f"{tr:>+8.4f}[{f3:.4f}]{mark}")
        say(f"{gg['iso']:>6d} {m72c.mode(gg['iso']):>5d} " + " ".join(cells))
    say("")
    say("* = trend exceeds its own 3-sigma N_grad floor.")

    rule("H2  RAW ratio profiles -- M68's E1 without the fit")
    say(f"{'ISO':>6s} " + " ".join(f"{k:>12s}" for k in
                                   ("B/G2", "R/G1", "R/B", "G2/G1")))
    for gg in groups:
        cells = []
        for k in ("B/G2", "R/G1", "R/B", "G2/G1"):
            n, d = k.split("/")
            vn = np.array(gg["axes"]["row"][PRIMARY]["planes"][n]["var"], float)
            vd = np.array(gg["axes"]["row"][PRIMARY]["planes"][d]["var"], float)
            v = vn / vd
            cells.append(f"{pre.trend(v / v.mean())[0]:>+12.4f}")
        say(f"{gg['iso']:>6d} " + " ".join(cells))
    say("")
    say("These are FRACTIONAL trends in the variance ratio. M68's E1 and M75's")
    say("K1 reported the ABSOLUTE trend of the fitted alpha_high ratio, so the")
    say("numbers are not directly comparable in magnitude -- only in sign,")
    say("shape and which planes carry them.")

    rule("H3  DOES THE TREND STEP AT THE DUAL-GAIN BOUNDARY (ISO 400)?")
    say("A physical row-dependent scale should not care where the chip")
    say("switches gain mode. A fit degeneracy plausibly would.")
    say("")
    isos = np.array([gg["iso"] for gg in groups], float)
    lo = isos < 400
    hi = isos >= 400
    say(f"{'plane':>6s} {'mean trend ISO<400':>19s} {'mean trend ISO>=400':>20s} "
        f"{'step':>9s}")
    for p in m72.PLANES:
        t = np.array(trends[p])
        say(f"{p:>6s} {t[lo].mean():>+19.4f} {t[hi].mean():>+20.4f} "
            f"{t[hi].mean() - t[lo].mean():>+9.4f}")
    say("")
    say("full per-ISO green trend, to see whether it is smooth in ISO:")
    for p in ("G1", "G2"):
        say(f"  {p:>3s} " + " ".join(f"{t:+.3f}" for t in trends[p]))
    for p in ("R", "B"):
        say(f"  {p:>3s} " + " ".join(f"{t:+.3f}" for t in trends[p]))
    say("  ISO " + " ".join(f"{int(i):>6d}" for i in isos))

    (DATA / "06-modelfree.txt").write_text("\n".join(OUT) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
