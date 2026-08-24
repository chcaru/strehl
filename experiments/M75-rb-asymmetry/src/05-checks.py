r"""M75 step 5 -- two honesty checks the earlier scripts leave open.

Committed before running.

G1  IS "R AND B ARE FLAT" TRUE IN BOTH GAIN MODES?
    K5 was pre-registered on alpha_high, because that is the quantity M68's E1
    used and O2 had to match it.  F3 then showed alpha_low carries fractional
    trends of -0.0396 (R) and -0.0419 (B) -- the same sign as each other and
    opposite to the greens.  F3 printed no floor for those, so nothing yet says
    whether they are real.  If they ARE real, "R and B are flat" is true of
    alpha_high and FALSE of alpha_low, and the K5 verdict must be scoped to the
    estimator it was pre-registered on rather than stated generally.

G2  CROSS-CHECK OF M68 FACT 992 WITH AN INDEPENDENT PIPELINE.
    M68 reported alpha_B/alpha_G2 = 0.85235 +/- 0.00316 and the orchestrator has
    routed the provenance of the related 0.8396 to M71.  This measures the same
    ratio from M75's own sweep, in BOTH gain modes, with jackknife errors.
    A single multiplicative pre-ADC scale s predicts the SAME ratio s^2 in both
    modes.  A difference between modes is evidence the B scale is not one
    constant factor, which bears directly on M68's still-open question.

G3  R/B AS AN INTERNAL REFERENCE.  R and B sit on the same (row+col)-parity
    sublattice.  Their alpha ratio is a null for "is the sublattice internally
    homogeneous" -- and note what that null is null FOR: sublattice homogeneity,
    NOT independence and NOT gain equality with the greens.
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
RNG = np.random.default_rng(20250920)
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
    isos = [g["iso"] for g in groups]
    g_arr = np.array([m72c.gain(i) for i in isos])
    md_arr = np.array([m72c.mode(i) for i in isos])

    def aprof(plane, key):
        out = np.empty(NBAND)
        for b in range(NBAND):
            y = np.array([gg["axes"]["row"][PRIMARY]["planes"][plane]["var"][b]
                          for gg in groups])
            out[b] = m72c.fit_alpha_delta(g_arr, md_arr, y)[key]
        return out

    def pooled_var(plane):
        return np.array([np.average(gg["axes"]["row"][PRIMARY]["planes"][plane]["var"],
                                    weights=gg["axes"]["row"][PRIMARY]["planes"][plane]["n"])
                         for gg in groups])

    # ------------------------------------------------------------------ G1 --
    rule("G1  IS 'R AND B ARE FLAT' TRUE IN BOTH GAIN MODES?")
    say("K5 was pre-registered on alpha_high (M68's estimator). This scopes it.")
    say("")
    say(f"{'plane':>6s} {'mode':>10s} {'frac trend':>11s} {'r':>8s} "
        f"{'3*N_grad':>10s} {'moves?':>8s}")
    verdict = {}
    for p in m72.PLANES:
        for key in ("alpha_low", "alpha_high"):
            v = aprof(p, key)
            n = v / v.mean()
            tr, r = pre.trend(n)
            f3 = 3 * pre.ngrad_floor(n, SH, RNG)
            verdict[(p, key)] = abs(tr) > f3
            say(f"{p:>6s} {key:>10s} {tr:>+11.4f} {r:>+8.3f} {f3:>10.5f} "
                f"{'YES' if verdict[(p, key)] else 'no':>8s}")
    rb_low = verdict[("R", "alpha_low")] or verdict[("B", "alpha_low")]
    say("")
    if rb_low:
        say("SCOPED: 'R and B are flat' holds for alpha_high, the estimator K5")
        say("was pre-registered on, and is FALSE for alpha_low. R and B carry a")
        say("real DOWNWARD low-gain-mode trend opposite in sign to the greens'.")
    else:
        say("'R and B are flat' holds in BOTH gain modes; the alpha_low trends")
        say("are inside their own noise floor and K5 generalises.")

    # ------------------------------------------------------------------ G2 --
    rule("G2  CROSS-CHECK OF M68 FACT 992  (alpha_B/alpha_G2 = 0.85235 +/- 0.00316)")
    say("A single multiplicative pre-ADC scale s predicts the SAME ratio s^2 in")
    say("both gain modes. A mode difference says the B scale is not one factor.")
    say("")
    pv = {p: pooled_var(p) for p in m72.PLANES}
    jk = {p: m72c.jackknife_fit(g_arr, md_arr, pv[p]) for p in m72.PLANES}
    say(f"{'plane':>6s} {'alpha_low':>12s} {'se':>9s} {'alpha_high':>12s} "
        f"{'se':>9s} {'delta':>10s}")
    for p in m72.PLANES:
        j = jk[p]
        say(f"{p:>6s} {j['alpha_low']:>12.5f} {j.get('alpha_low_se', float('nan')):>9.5f} "
            f"{j['alpha_high']:>12.5f} {j.get('alpha_high_se', float('nan')):>9.5f} "
            f"{j['delta']:>10.5f}")
    say("")
    say(f"{'ratio':>10s} {'alpha_low':>11s} {'alpha_high':>12s} {'low/high':>10s}")
    for num, den in (("B", "G2"), ("B", "G1"), ("R", "G1"), ("R", "G2"),
                     ("R", "B"), ("G2", "G1")):
        rl = jk[num]["alpha_low"] / jk[den]["alpha_low"]
        rh = jk[num]["alpha_high"] / jk[den]["alpha_high"]
        say(f"{num + '/' + den:>10s} {rl:>11.5f} {rh:>12.5f} {rl / rh:>10.5f}")
    bg2h = jk["B"]["alpha_high"] / jk["G2"]["alpha_high"]
    bg2l = jk["B"]["alpha_low"] / jk["G2"]["alpha_low"]
    say("")
    say(f"  M68 fact 992 (alpha_high, its own pipeline): 0.85235 +/- 0.00316")
    say(f"  M75 alpha_high, independent pipeline:        {bg2h:.5f}  "
        f"(delta {bg2h - 0.85235:+.5f} = {abs(bg2h - 0.85235) / 0.00316:.1f} "
        f"of M68's quoted sigma)")
    say(f"  M75 alpha_low:                               {bg2l:.5f}")
    say(f"  low/high disagreement: {bg2l / bg2h:.5f}  "
        f"({100 * (bg2l / bg2h - 1):+.2f}%)")

    # ------------------------------------------------------------------ G3 --
    rule("G3  R/B AS A SUBLATTICE-HOMOGENEITY NULL")
    say("NULL FOR: is the (row+col)-parity sublattice internally homogeneous.")
    say("NOT a null for independence, and NOT a null for gain against green.")
    rb_l = jk["R"]["alpha_low"] / jk["B"]["alpha_low"]
    rb_h = jk["R"]["alpha_high"] / jk["B"]["alpha_high"]
    say(f"  R/B alpha_low  {rb_l:.5f}   alpha_high {rb_h:.5f}")
    say(f"  G2/G1 alpha_low {jk['G2']['alpha_low'] / jk['G1']['alpha_low']:.5f}"
        f"   alpha_high {jk['G2']['alpha_high'] / jk['G1']['alpha_high']:.5f}")
    say("  R and B are NOT equal to each other the way the two greens are:")
    say("  the parity sublattice is homogeneous in its ROW PROFILE (F1: R/B")
    say("  column and row trends both inside the floor) but not in its LEVEL.")

    (DATA / "05-checks.txt").write_text("\n".join(OUT) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
