#!/usr/bin/env python3
"""n8_noisecoupling.py -- is `H` a chroma statistic or a noise statistic?

WHY THIS EXISTS
    ORCH (Sec.98) measured that a ratio-valued metric indicts the system for
    getting better: merging N frames divides noise by ~sqrt(N), so any statistic
    with noise in the denominator improves for free, and any statistic that IS a
    noise measure moves for free too.

    Sec.11 of BUILD-HIGHLIGHT compared a SINGLE frame against a STACK using
    `H_highfreq_chroma` = RMS of the high-pass chroma over the mask. High-pass
    plus RMS is the standard construction of a NOISE estimator. If H is
    noise-coupled, that comparison measured the merge's noise reduction and
    charged it to chroma.

    l2_falsecolour's own selftest plants false colour and asserts H responds by
    >20x. That test is faithful and it cannot catch this: it establishes that H
    is sensitive to chroma, never that H is INSENSITIVE to noise. A correct
    commissioning does not establish that you measured the right quantity.

WHAT IT DOES
    1. Measures the real noise floor of K1 (single) and K3 (stack) in DN, so the
       ladder below has a measured landmark rather than a nominal one.
    2. Injects independent Gaussian noise into the STACK across a ladder and
       re-measures every statistic this lane publishes.
    3. Reports, per statistic, the fractional move -- including the ones that do
       NOT move. `cr_med`/`cb_med` are signed medians and should be immune to
       symmetric noise; if they moved, the ladder would be corrupting the image
       rather than isolating noise, and nothing else in the table could be read.

USAGE
    python n8_noisecoupling.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_falsecolour import stats  # noqa: E402

LADDER = r"C:\dev\strehl-out\BUILD-HIGHLIGHT\ladder"
K1 = os.path.join(LADDER, "K1-single-demo.tif")  # single frame
K3 = os.path.join(LADDER, "K3-stack-demo.tif")   # the stack

# Statistic parameters are held IDENTICAL across every rung. Absolute values are
# not compared against the stored Sec.11 run (whose parameters were not
# identified -- stated in Sec.14.5); every number here is relative to this
# script's own sigma=0 rung, which is the anchor.
PARAMS = dict(bright_pct=99.5, full_res=True, select_on="luma", population="specular")

KEYS = [
    ("H_highfreq_chroma", "H   high-freq chroma (RMS)"),
    ("L_lowfreq_chroma", "L   low-freq chroma (RMS)"),
    ("HL_ratio", "H/L ratio"),
    ("cr_med", "cr  signed median (R-G)/Y"),
    ("cb_med", "cb  signed median (B-G)/Y"),
    ("RAD_corner_over_centre", "RAD corner/centre"),
]


def noise_dn(u16: np.ndarray) -> float:
    """Robust noise estimate in DN from adjacent-pixel differences on green.

    sigma = 1.4826 * MAD(dI) / sqrt(2). The median picks the typical (flat)
    pixel, so structure inflates this far less than a plain standard deviation
    -- but it is still an UPPER BOUND wherever texture is dense.
    """
    g = u16[..., 1].astype(np.float32)
    d = np.diff(g[::4, ::4], axis=1)  # decimate: this is a floor estimate, not a map
    med = np.median(d)
    mad = np.median(np.abs(d - med))
    return float(1.4826 * mad / np.sqrt(2.0))


def main() -> int:
    print("=" * 96)
    print("n8 -- NOISE COUPLING OF THE SEC.11 STATISTIC")
    print("=" * 96)

    print("\n[1] measured noise floor of the two Sec.11 arms (green, DN)")
    floors = {}
    for name, path in (("K1 single", K1), ("K3 stack", K3)):
        a = tifffile.imread(path)
        floors[name] = noise_dn(a)
        print(f"    {name:<12} {floors[name]:8.2f} DN")
        del a
    ratio = floors["K1 single"] / floors["K3 stack"]
    extra = float(np.sqrt(max(floors["K1 single"] ** 2 - floors["K3 stack"] ** 2, 0.0)))
    print(f"    single/stack noise ratio : {ratio:.2f}x")
    print(f"    noise the merge removed  : {extra:.1f} DN in quadrature")
    print("    -> to imitate un-merging, add ~%.0f DN to the stack." % extra)

    print("\n[2] ladder: inject independent noise into the STACK, re-measure everything")
    base = tifffile.imread(K3).astype(np.float32) / 65535.0
    rng = np.random.default_rng(20260826)

    rungs = [0.0, 15.0, 30.0, 60.0, extra, 120.0, 240.0]
    rungs = sorted(set(round(r, 1) for r in rungs))

    hdr = "    %-9s %-9s %-8s " % ("sigma_DN", "meas_DN", "n_mask") + " ".join(
        "%-11s" % k[:11] for k, _ in KEYS
    )
    print(hdr)
    print("    " + "-" * (len(hdr) - 4))

    rows = []
    for s in rungs:
        if s == 0.0:
            noisy = base
        else:
            noisy = base + rng.standard_normal(base.shape, dtype=np.float32) * (s / 65535.0)
            np.clip(noisy, 0.0, 1.0, out=noisy)
        meas = noise_dn((noisy * 65535.0).astype(np.uint16))
        st = stats(noisy, **PARAMS)
        rows.append((s, meas, st))
        cells = []
        for k, _ in KEYS:
            v = st.get(k)
            cells.append("%-11s" % ("None" if v is None else f"{v:.5f}"))
        print("    %-9.1f %-9.2f %-8d " % (s, meas, st["n_mask"]) + " ".join(cells))
        if noisy is not base:
            del noisy

    print("\n[3] fractional move from the sigma=0 anchor")
    z = rows[0][2]
    hdr2 = "    %-28s " % "statistic" + " ".join("%-11s" % f"{r[0]:.0f}DN" for r in rows[1:])
    print(hdr2)
    print("    " + "-" * (len(hdr2) - 4))
    for k, label in KEYS:
        b = z.get(k)
        if b is None or b == 0:
            print("    %-28s  (anchor is None/0, not comparable)" % label)
            continue
        cells = []
        for r in rows[1:]:
            v = r[2].get(k)
            cells.append("%-11s" % ("None" if v is None else f"{100 * (v - b) / abs(b):+.1f}%"))
        print("    %-28s " % label + " ".join(cells))

    print("\n[4] verdict against Sec.11's effect size")
    hb = z["H_highfreq_chroma"]
    tgt = min(rows[1:], key=lambda r: abs(r[0] - extra))
    hm = tgt[2]["H_highfreq_chroma"]
    move = 100 * (hm - hb) / abs(hb)
    print(f"    Sec.11 reported a single-vs-stack move in H of  +6.7% (native) / -6.3% (binned)")
    print(f"    adding back the {tgt[0]:.0f} DN the merge removed moves H by {move:+.1f}%")
    if abs(move) > 0:
        print(f"    -> noise alone is {abs(move) / 6.7:.1f}x the size of the reported effect")
    print("\n    CONTROL: cr_med / cb_med are signed medians and must NOT move. If they")
    print("    did, the ladder is damaging the image rather than isolating noise and")
    print("    no row above may be read.")

    # ------------------------------------------------------------------
    # [5] POSITIVE CONTROL. Sections 2-4 are a NULL: H did not move. A null from
    #     an instrument never shown to speak is worth nothing -- it is the
    #     "clean vs deaf" rule, and it applies to my own ladder. Push the noise
    #     until H moves, so the silence above acquires a stated amplitude.
    #
    #     Mechanism, stated BEFORE the run so it can be wrong: the mask selects
    #     SPECULAR pixels, and cr = (R-G)/Y is divided by a large Y there. Sensor
    #     noise sigma therefore enters chroma as ~sigma*sqrt(2)/Y, which at
    #     Y~0.9 and sigma=90 DN is ~0.002 against an H of ~0.18 -- a 85:1 ratio
    #     that vanishes in quadrature. If that is right, H should need noise of
    #     order H*Y/sqrt(2) ~ 0.12 full-scale ~ 7600 DN to move materially.
    # ------------------------------------------------------------------
    print("\n[5] POSITIVE CONTROL -- how much noise DOES move H?")
    print("    (a null from an instrument never shown to speak is not evidence)")
    hdr3 = "    %-9s %-9s %-12s %-10s" % ("sigma_DN", "meas_DN", "H", "move")
    print(hdr3)
    print("    " + "-" * (len(hdr3) - 4))
    crossed = {}
    for s in (500.0, 1000.0, 2000.0, 4000.0, 8000.0):
        noisy = base + rng.standard_normal(base.shape, dtype=np.float32) * (s / 65535.0)
        np.clip(noisy, 0.0, 1.0, out=noisy)
        meas = noise_dn((noisy * 65535.0).astype(np.uint16))
        st = stats(noisy, **PARAMS)
        h = st["H_highfreq_chroma"]
        mv = 100 * (h - hb) / abs(hb)
        print("    %-9.0f %-9.2f %-12.5f %+.2f%%" % (s, meas, h, mv))
        for thr in (1.0, 6.7):
            if thr not in crossed and abs(mv) >= thr:
                crossed[thr] = s
        del noisy

    print()
    for thr in (1.0, 6.7):
        if thr in crossed:
            print(f"    H first moves >= {thr:.1f}% at about {crossed[thr]:.0f} DN of added noise")
        else:
            print(f"    H never reached {thr:.1f}% anywhere on this ladder")
    if 6.7 in crossed:
        print(
            f"    -> that is {crossed[6.7] / extra:.0f}x the {extra:.0f} DN the merge actually removed,"
        )
        print(
            f"       and {crossed[6.7] / floors['K1 single']:.0f}x the total noise present in the "
            "single frame."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
