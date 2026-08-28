r"""ORCH job 2 -- adjudicate the MID-SCALE ring axis (0-140 px window, 170-300
px null), the axis that reported RING on 5 of 14 in docs/research/
V-RIM-verification.md.  This is a DIFFERENT scale and a DIFFERENT estimator
from rimv6 and the tight-scale acquittal does not reach it.

The instrument is imported UNCHANGED from experiments/V-RIM/src: vrimlib.py,
vrim_rays.py, ringstat.py.  Nothing in those files is edited.

Four tests, the same four that killed the tight-scale axis:

  PATH   what did it actually read?  render_all.ps1 rendered its own linear
         TIFFs with a binary pinned at commit 1cacb61 into
         C:\dev\strehl-out\V-RIM\lin.  Neither that tree nor that binary
         exists any more.  So the axis is re-run here on the DELIVERABLE.
  SPEC   does the detector convict a curve with no ring in it?  Two ways: a
         synthetic profile, and -- with no modelling assumptions at all -- the
         subject's OWN far-field fluctuation transplanted into the ring
         window on top of a monotone rise.
  FOREIGN Zerene PMax and never-stacked single captures.  coffee-bean is in
         both the RING five and the never-stacked set, so it is the single
         most informative subject available.
  USM    the reading converted into an unsharp-mask amount, so a human can
         adjudicate by eye instead of by percent.
"""
import io
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
import vrim_rays                                                   # noqa: E402
import ringstat                                                    # noqa: E402
from ringstat import ring_and_null, dip, RING_LO, RING_HI, NULL_LO, NULL_HI

SCRATCH = r"D:\strehl-out\V-RIM"
RINGJS = os.path.join(SCRATCH, "ring")
DELIV = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"

# the five the mid-scale axis convicted, plus the three it could not decide
FIVE = ["bee-3-cpl", "flower-bud-alone-cpl",
        "flower-bud-with-background-fern-cpl", "lavendar-cpl", "coffee-bean"]
OTHER = ["bee-1-cpl", "bee-2-cpl", "109MSDCF", "119MSDCF"]


def detect(rec):
    """The published rule, reproduced from summarise.py line for line."""
    s = rec["straight"]
    r, n = ring_and_null(s["grid"], s["med"], s["far"])
    return r, n, (r["frac"] >= 3 * max(n["frac"], 0.0005))


def load(label):
    p = Path(RINGJS) / (label + "-rays.json")
    return json.loads(p.read_text()) if p.exists() else None


def cmd_run(labels, srcdir=DELIV, ext=".tiff"):
    for lab in labels:
        p = Path(srcdir) / (lab + ext)
        if not p.exists():
            print("MISSING %s" % p)
            continue
        if (Path(RINGJS) / (lab + "-rays.json")).exists():
            print("skip %s (have json)" % lab)
            continue
        vrim_rays.run(p, lab, RINGJS)


def cmd_score(labels):
    print("=" * 96)
    print("MID-SCALE AXIS RE-RUN ON THE DELIVERABLE (ORCH-FAITHFUL/faithful)")
    print("  published numbers came from C:\\dev\\strehl-out\\V-RIM\\lin, a render")
    print("  by a binary pinned at 1cacb61. That tree and that binary are GONE.")
    print("=" * 96)
    print("%-38s %9s %8s %8s %8s %8s %10s"
          % ("subject", "rays", "ring%", "t_peak", "null%", "ratio", "verdict"))
    out = []
    for lab in labels:
        d = load(lab)
        if d is None:
            print("%-38s  NO JSON" % lab)
            continue
        if not d.get("straight"):
            print("%-38s  rays did not register" % lab)
            continue
        r, n, det = detect(d)
        a = d["all"]
        pol = "dark-on-bright" if a["inner"] < a["far"] else "BRIGHT-on-dark"
        ratio = r["frac"] / max(n["frac"], 1e-9)
        v = "RING" if det else "no ring"
        if pol != "dark-on-bright":
            v = "polarity"
        print("%-38s %9d %+7.2f%% %8.0f %7.2f%% %7.1fx %10s"
              % (lab, d["straight"]["n"], 100 * r["frac"], r["t_peak"],
                 100 * n["frac"], ratio, v))
        out.append(dict(subject=lab, ring=r, null=n, det=bool(det), pol=pol,
                        far=a["far"], inner=a["inner"], n=d["straight"]["n"]))
    return out


def cmd_spec(labels):
    """SPECIFICITY at the level of the detector itself, with the subject's own
    noise. Build a curve that has NO ring by construction: a monotone rise to
    the far level, plus the fluctuation actually measured in that subject's
    own far field (t=150..300, detrended) transplanted into t=0..140. Any
    RING the detector then reports is a false positive on that subject's real
    backdrop noise."""
    print()
    print("=" * 96)
    print("SPECIFICITY -- subject's own far-field noise transplanted into the")
    print("  ring window on a monotone rise. NO RING EXISTS in these curves.")
    print("=" * 96)
    print("%-38s %8s %8s %8s %9s %8s"
          % ("subject", "real%", "fake%", "null%", "fake/null", "verdict"))
    rows = []
    rng = np.random.default_rng(4242)
    for lab in labels:
        d = load(lab)
        if d is None or not d.get("straight"):
            continue
        s = d["straight"]
        grid = np.asarray(s["grid"], float)
        med = np.asarray(s["med"], float)
        far = float(s["far"])
        r0, n0 = ring_and_null(grid, med, far)
        far_m = (grid >= 150) & (grid <= 300)
        seg = med[far_m]
        # detrend the far field linearly; what is left is its fluctuation
        x = grid[far_m]
        A = np.vstack([x, np.ones_like(x)]).T
        co = np.linalg.lstsq(A, seg, rcond=None)[0]
        resid = seg - A @ co
        hits, fr = 0, []
        for k in range(24):
            fake = med.copy()
            # monotone rise: the real profile's own cumulative maximum, which
            # is non-decreasing by construction, so it holds no ring
            mono = np.maximum.accumulate(med)
            fake[:] = mono
            src = rng.permutation(len(resid))
            win = (grid >= RING_LO) & (grid <= RING_HI)
            nw = int(win.sum())
            reps = int(np.ceil(nw / len(resid)))
            pool = np.concatenate([resid[np.roll(src, j)] for j in range(reps)])
            fake[win] = mono[win] + pool[:nw]
            rf, nf = ring_and_null(grid, fake, far)
            fr.append(rf["frac"])
            if rf["frac"] >= 3 * max(nf["frac"], 0.0005):
                hits += 1
        fr = np.array(fr)
        print("%-38s %+7.2f%% %+7.2f%% %7.2f%% %8s %8s"
              % (lab, 100 * r0["frac"], 100 * fr.mean(), 100 * n0["frac"],
                 "%d/24" % hits, "FALSE POS" if hits else "clean"))
        rows.append(dict(subject=lab, real=r0["frac"], fake_mean=float(fr.mean()),
                         fake_max=float(fr.max()), null=n0["frac"], hits=hits))
    return rows


def cmd_window():
    """The window asymmetry, on pure noise, with no image at all.

    ringstat.dip requires recovery: recov = max(med[b:]) - med[b], where the
    tail runs to the END OF THE GRID and not to the end of the window. A pair
    in the RING window (b <= 140) is scored against a 160-point tail. A pair
    in the NULL window (b <= 300) can be scored against a tail of length 0.
    So the two windows are not the same test, and the rule ring >= 3 x null
    inherits whatever that difference is worth."""
    print()
    print("=" * 96)
    print("WINDOW ASYMMETRY -- identical noise, no ring, no image.")
    print("  Feed pure correlated noise to the SAME dip() in both windows.")
    print("=" * 96)
    rng = np.random.default_rng(11)
    grid = np.arange(-40.0, 300.0 + 1e-9, 1.0)
    from scipy import ndimage as ndi
    print("%10s %10s %10s %9s %10s" % ("corr len", "ring%", "null%", "ratio",
                                       ">=3x rate"))
    rows = []
    for cl in (1.0, 2.0, 4.0, 8.0):
        rs, ns, hits = [], [], 0
        for k in range(200):
            z = rng.normal(0, 1, grid.size)
            z = ndi.gaussian_filter1d(z, cl)
            z = z / z.std() * 0.01           # 1% of far, flat: NO ring
            med = 1.0 + z
            r, n = ring_and_null(grid, med, 1.0)
            rs.append(r["frac"]); ns.append(n["frac"])
            if r["frac"] >= 3 * max(n["frac"], 0.0005):
                hits += 1
        rs, ns = np.array(rs), np.array(ns)
        print("%10.1f %9.2f%% %9.2f%% %8.2fx %9s"
              % (cl, 100 * rs.mean(), 100 * ns.mean(),
                 rs.mean() / max(ns.mean(), 1e-9), "%d/200" % hits))
        rows.append(dict(corr=cl, ring=float(rs.mean()), null=float(ns.mean()),
                         hits=hits))
    return rows


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    what = sys.argv[1]
    if what == "run":
        cmd_run(sys.argv[2:] if len(sys.argv) > 2 else FIVE + OTHER)
    elif what == "score":
        doc = dict(score=cmd_score(FIVE + OTHER))
        json.dump(doc, io.open(os.path.join(SCRATCH, "ring_score.json"), "w",
                               encoding="utf-8"), indent=1, default=float)
    elif what == "spec":
        doc = dict(spec=cmd_spec(FIVE + OTHER))
        json.dump(doc, io.open(os.path.join(SCRATCH, "ring_spec.json"), "w",
                               encoding="utf-8"), indent=1, default=float)
    elif what == "window":
        doc = dict(window=cmd_window())
        json.dump(doc, io.open(os.path.join(SCRATCH, "ring_window.json"), "w",
                               encoding="utf-8"), indent=1, default=float)
