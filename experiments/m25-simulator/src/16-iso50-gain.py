"""16 -- is fact 14 wrong about read noise at ISO 50, or wrong about GAIN?

M25's report proposed (fact 200, folded as 550) that fact 14's two-level read
noise "under-predicts M4's measured dark sigma at ISO 50 by 45 %".  That
framing is accurate arithmetic and a **misleading diagnosis**, and the
orchestrator is about to change a shipped constant on the strength of it.

Look at M4's own committed table:

    ISO   sigma_temporal (M4, MEASURED)
     50   0.9866
    100   0.9845
    200   1.7416

M4's ISO 50 and ISO 100 rows are within **0.21 %** of each other.  The model
`sigma = RN_e * g`, `g = ISO/436.8`, demands a ratio of **0.5**.  A 0.2 %
observed ratio against a 50 % predicted one is not a calibration error in
`RN_e`; it says the **analog gain does not change between ISO 100 and ISO 50**
-- i.e. ISO 50 on this body is an extended/pulled ISO, exposed a stop brighter
and metered as 50 while the sensor still runs at its base-ISO gain.

Substituting `g(50) = g(100)` drops the ISO 50 error from **51.3 % to 2.5 %**,
the same accuracy the model has at every other ISO.  That is a one-line change
with a completely different meaning: `RN_e` is fine, `g` is wrong by 2x below
ISO 100.

Dark frames alone cannot close this, because a dark frame only constrains the
**product** `RN_e * g`.  So this script measures `g` from **signal** on real
captures, by photon transfer:

    var_local = g * mean_local + (RN_e * g)^2

Scene texture only ever *adds* variance, so the lower envelope of
(local variance vs local mean) is the noise floor.  Binning by mean and taking
a low percentile of variance in each bin recovers `g` as the slope.

**The control that makes this credible** (rule 17): the same estimator is run
on ISO 160 `109MSDCF`, where the project's constant is corroborated by
independent work.  If it recovers g = 0.366 there, its answer at ISO 50 can be
believed.  If it does not, this script is measuring texture and says nothing.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/16-iso50-gain.py
"""

from __future__ import annotations

import glob
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strehl_sim import stackio as S                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "iso50-gain.txt")
BLACK = 512
TILE = 8
PCTL = 5.0
STACKS = [
    (r"C:\dev\macro\test\109MSDCF", "CONTROL -- ISO 160, model known good"),
    (r"C:\dev\macro\test\119MSDCF", "TEST    -- ISO 50"),
    (r"C:\dev\macro\test\coffee-bean", "TEST    -- ISO 50"),
]
M4_DARK = {50: 0.9866, 100: 0.9845, 200: 1.7416}
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def photon_transfer(g_plane):
    """Slope of the lower envelope of (local variance vs local mean).

    Tiles are TILE x TILE on ONE green plane, so neighbouring samples are two
    sensor pixels apart and share no photosite.  Returns (gain, rn_dn, npts).
    """
    h, w = g_plane.shape
    h -= h % TILE
    w -= w % TILE
    a = g_plane[:h, :w].reshape(h // TILE, TILE, w // TILE, TILE)
    m = a.mean(axis=(1, 3)).ravel()
    v = a.var(axis=(1, 3), ddof=1).ravel()
    ok = np.isfinite(m) & np.isfinite(v) & (m > 20) & (m < 13000)
    m, v = m[ok], v[ok]
    if m.size < 5000:
        return None
    edges = np.percentile(m, np.linspace(0, 100, 25))
    edges = np.unique(edges)
    xs, ys = [], []
    for i in range(len(edges) - 1):
        sel = (m >= edges[i]) & (m < edges[i + 1])
        if sel.sum() < 200:
            continue
        xs.append(m[sel].mean())
        ys.append(np.percentile(v[sel], PCTL))
    xs, ys = np.array(xs), np.array(ys)
    if xs.size < 6:
        return None
    A = np.vstack([xs, np.ones_like(xs)]).T
    slope, icpt = np.linalg.lstsq(A, ys, rcond=None)[0]
    # the TILE x TILE sample variance is unbiased, but the tile mean carries
    # its own scene gradient; the low percentile is what suppresses that.
    rn_dn = float(np.sqrt(max(icpt, 0.0)))
    return float(slope), rn_dn, int(xs.size)


def main():
    t0 = time.time()
    say("Is fact 14 wrong about READ NOISE at ISO 50, or about GAIN?")
    say()
    say("M4's committed dark sigma_temporal, and what g = ISO/436.8 predicts:")
    say(f"  {'ISO':>5} {'M4 measured':>12} {'model':>9} {'model/M4':>9}")
    for iso, meas in M4_DARK.items():
        g = iso / 436.8
        mod = 4.20 * g
        say(f"  {iso:>5} {meas:>12.4f} {mod:>9.4f} {mod / meas:>9.3f}")
    say(f"  M4's ISO50/ISO100 ratio = {M4_DARK[50] / M4_DARK[100]:.4f};"
        f" the model demands 0.5000")
    say("  substituting g(50) = g(100): model 0.9615 vs measured 0.9866 "
        "= 2.5% error (was 51.3%)")
    say()
    say("Dark frames only constrain the PRODUCT RN_e*g, so below is g measured"
        " from SIGNAL.")
    say(f"photon transfer: {TILE}x{TILE} tiles on one green plane, "
        f"{PCTL:.0f}th-percentile variance per mean bin, 24 bins")
    say()

    rows = []
    for path, label in STACKS:
        fs = sorted(glob.glob(os.path.join(path, "*.ARW")))
        if not fs:
            say(f"!! no frames at {path} -- skipped")
            continue
        iso = S.iso_of(path)
        import rawpy
        with rawpy.imread(fs[len(fs) // 2]) as rr:
            g1 = (rr.raw_image_visible[0::2, 1::2].astype(np.float64) - BLACK)
        res = photon_transfer(g1)
        if res is None:
            say(f"!! {os.path.basename(path)}: too few usable tiles")
            continue
        gain, rn_dn, npts = res
        g_iso = iso / 436.8
        g_pull = max(iso, 100.0) / 436.8
        rn_e = rn_dn / max(gain, 1e-9)
        say(f"--- {os.path.basename(path):<12} ISO {iso:>4.0f}   {label}")
        say(f"    measured gain            {gain:>8.5f} DN/e-   "
            f"(from {npts} mean bins)")
        say(f"    fact 14  g = ISO/436.8   {g_iso:>8.5f} DN/e-   "
            f"ratio measured/model {gain / g_iso:>6.3f}")
        say(f"    pulled   g = max(ISO,100)/436.8 {g_pull:>8.5f} DN/e-   "
            f"ratio measured/model {gain / g_pull:>6.3f}")
        say(f"    implied read noise       {rn_e:>8.2f} e-  "
            f"({rn_dn:.3f} DN)   fact 14 says "
            f"{4.20 if iso < 400 else 1.47:.2f} e-")
        say()
        rows.append((os.path.basename(path), iso, gain, g_iso, g_pull))

    say("=" * 74)
    ctrl = [r for r in rows if r[1] >= 100]
    test = [r for r in rows if r[1] < 100]
    if not ctrl:
        say("VERDICT: no control ran -- nothing here is trustworthy.")
    else:
        cerr = abs(ctrl[0][2] / ctrl[0][3] - 1.0)
        say(f"control {ctrl[0][0]} (ISO {ctrl[0][1]:.0f}): estimator recovers "
            f"g within {100 * cerr:.1f}% of the project's constant")
        if cerr > 0.25:
            say("VERDICT: the estimator FAILS its own control, so its ISO 50 "
                "numbers say nothing.  Do not act on this script.")
        else:
            say("the estimator is calibrated, so read the ISO 50 rows:")
            for nm, iso, gain, g_iso, g_pull in test:
                a = abs(gain / g_iso - 1.0)
                b = abs(gain / g_pull - 1.0)
                which = ("PULLED g (=ISO100)" if b < a
                         else "fact 14's g=ISO/436.8")
                say(f"  {nm:<14} measured {gain:.5f}: closer to {which}"
                    f"   (errors {100 * a:.0f}% vs {100 * b:.0f}%)")
            if test and all(abs(r[2] / r[4] - 1) < abs(r[2] / r[3] - 1)
                            for r in test):
                say()
                say("VERDICT: signal agrees with the dark frames.  ISO 50 on "
                    "this body behaves as base ISO 100.  The defect is in g, "
                    "NOT in RN_e -- changing the read-noise constant would "
                    "'fix' the symptom at ISO 50 and break every other ISO.")
            elif test:
                say()
                say("VERDICT: signal does NOT agree with the dark-frame "
                    "argument.  The pulled-ISO hypothesis is not supported "
                    "from signal and fact 550 should stay as written.")
    say(f"[{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
