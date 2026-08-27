"""Commission the fixed-gain fix against BUILD-RESAMP's measurement.

BUILD-RESAMP measured that orch_smoothcrop.py's original per-block percentile stretch
gave identical 40 DN dust a 29x different apparent severity across two synthetic fields,
with the bias running the wrong way: the flatter -- cleaner -- field was amplified more
and therefore looked dirtiest. They were right, and the instruction I broadcast with the
tool ("use it before you call anything clean") invited exactly the cross-master ranking
that the bias invalidates.

This reproduces their two fields, runs both the old and the new rendering path, and
reports apparent severity for each. The fix is only real if the new path returns the same
apparent severity for the same defect in both fields. A fix asserted rather than measured
is how the original defect got shipped in the first place.
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from orch_smoothcrop import FIXED_W, HP_WIN, boxblur  # noqa: E402

N = 900
DUST_DN = 40.0
BASE = 61000.0


def field(kind, rng):
    """Two smooth fields differing only in how much low-level structure they carry."""
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    a = np.full((N, N), BASE, dtype=np.float32)
    a += (x + y) * 0.8
    if kind == "busy":
        a += rng.normal(0, 260, (N, N)).astype(np.float32)
        a += 700 * np.sin(x / 90.0) * np.cos(y / 130.0)
    else:
        a += rng.normal(0, 26, (N, N)).astype(np.float32)
    return a


def add_dust(a, depth=DUST_DN):
    yy, xx = np.mgrid[0:N, 0:N]
    for (cy, cx) in DUST_CENTRES:
        m = ((yy - cy) ** 2 + (xx - cx) ** 2) < R_IN ** 2
        a[m] -= depth
    return a


DUST_CENTRES = ((300, 300), (600, 620), (200, 700))
R_IN, R_OUT = 30, 60


def local_depth(v):
    """Depth of each planted disc against its OWN annulus, averaged.

    The first version of this compared the disc against a fixed distant patch, which in
    the busy field landed on a trough of the synthetic sinusoid and returned a NEGATIVE
    severity -- the reference was contaminated by exactly the large-scale structure the
    two fields differ in. A defect's depth is local by definition, so measure it locally;
    this is also the definition given to BUILD-BLEND ('peak-to-local-background depth').
    """
    yy, xx = np.mgrid[0:N, 0:N]
    depths = []
    for (cy, cx) in DUST_CENTRES:
        d2 = (yy - cy) ** 2 + (xx - cx) ** 2
        inside = d2 < (R_IN - 6) ** 2
        ring = (d2 > (R_IN + 8) ** 2) & (d2 < R_OUT ** 2)
        depths.append(float(v[ring].mean() - v[inside].mean()))
    return float(np.mean(depths))


def severity_old(a):
    lo, hi = np.percentile(a, 1.0), np.percentile(a, 99.0)
    span = max(hi - lo, 1.0)
    v = np.clip((a - lo) * (255.0 / span), 0, 255)
    return 65535.0 / span, local_depth(v)


def severity_new(a, w=None):
    w = FIXED_W if w is None else w
    res = a - boxblur(a, HP_WIN)
    scaled = (res + w) * (255.0 / (2 * w))
    clip = float(((scaled < 0) | (scaled > 255)).mean())
    v = np.clip(scaled, 0, 255)
    return 255.0 / (2 * w), local_depth(v), clip


def main():
    rng = np.random.default_rng(4242)
    fields = {k: add_dust(field(k, rng)) for k in ("busy", "flat")}

    print(f"identical {DUST_DN:.0f} DN dust discs planted in two smooth fields, "
          f"depth measured against each disc's own annulus\n")
    print(f"{'field':8s} {'OLD gain':>10s} {'OLD sev':>9s} "
          f"{'NEW gain':>10s} {'NEW sev':>9s} {'clip':>8s}")
    print("-" * 62)
    rows = []
    for k, a in fields.items():
        go, so = severity_old(a.copy())
        gn, sn, cn = severity_new(a.copy())
        rows.append((k, go, so, gn, sn, cn))
        print(f"{k:8s} {go:9.1f}x {so:8.2f} {gn:9.4f} {sn:8.2f} {cn*100:7.2f}%")

    o = [r[2] for r in rows]
    n = [r[4] for r in rows]
    o_ratio = max(o) / max(min(o), 1e-6)
    n_ratio = max(n) / max(min(n), 1e-6)
    gains_equal = abs(rows[0][3] - rows[1][3]) < 1e-9
    print()
    print(f"OLD display gain differed between fields    : "
          f"{rows[0][1]:.1f}x vs {rows[1][1]:.1f}x")
    print(f"NEW display gain identical by construction  : {gains_equal}")
    print(f"OLD apparent-severity ratio                 : {o_ratio:6.2f}x")
    print(f"NEW apparent-severity ratio                 : {n_ratio:6.2f}x")

    print("\nMECHANISM TEST -- is the residual ratio caused by clipping?")
    print("Prediction, registered before running: the busy field's own noise exceeds the "
          "+/-250 DN window, so it clips and its discs are compressed. Widening the "
          "window must collapse the ratio toward 1.0. If it does not, clipping is not "
          "the cause and I do not understand the residual.")
    print(f"\n{'window':>8s} {'busy sev':>9s} {'busy clip':>10s} "
          f"{'flat sev':>9s} {'flat clip':>10s} {'ratio':>7s}")
    print("-" * 58)
    ratios = {}
    for w in (250.0, 500.0, 1000.0, 2000.0):
        _, sb, cb = severity_new(fields["busy"].copy(), w)
        _, sf, cf = severity_new(fields["flat"].copy(), w)
        r = max(sb, sf) / max(min(sb, sf), 1e-6)
        ratios[w] = (r, cb)
        print(f"{w:7.0f}  {sb:8.2f} {cb*100:9.2f}% {sf:8.2f} {cf*100:9.2f}% {r:6.2f}x")

    wide_r, wide_clip = ratios[2000.0]
    responsive = min(n) > 3.0
    print()
    print(f"gain constant across fields (the reported defect)   : {gains_equal}")
    print(f"tool still responds in both fields (>3 of 255)      : {responsive}")
    print(f"clipping falls to near zero at the wide window      : {wide_clip*100:.2f}%")
    print(f"severity ratio at the wide window                   : {wide_r:.2f}x")
    explained = wide_clip < 0.01 and wide_r < 1.15
    if gains_equal and responsive and explained:
        print("\nCOMMISSIONED. The per-block gain bias BUILD-RESAMP measured is removed "
              "by construction -- gain is now a stated constant. The residual severity "
              "difference at the working window is CLIPPING, identified by the "
              "registered prediction above: it vanishes when the window is widened. "
              "The tool therefore reports clip% per master, and a comparison between "
              "masters is valid only where clip% is small on both.")
        return 0
    print("\nNOT COMMISSIONED. gain_equal="
          f"{gains_equal} responsive={responsive} clipping_explains={explained}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
