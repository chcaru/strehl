"""
b6_discriminate.py -- LoCA or lateral CA? The brief demands both discriminators.

There are three arguments here, and they are deliberately of different kinds so
that they do not all fail together.

(1) STRUCTURAL. This is the strongest one and it costs nothing to make.
    The estimator returns the position of a maximum along the FRAME axis. A
    lateral magnification error is a spatial displacement that is the same in
    every frame of the bracket. Translating a structure sideways changes which
    pixels see it; it does not change which frame is sharpest. So a
    k-independent spatial displacement cannot move a peak along k, and the
    instrument is blind to pure lateral CA by construction.
    The one leak is focus breathing: if magnification changes through the
    bracket then the lateral displacement is weakly k-dependent. That leak is
    bounded empirically by (2) and (3).

(2) INTERCEPT AT THE OPTICAL CENTRE. Lateral CA is a radial magnification
    error: it is exactly zero on the axis and grows with radius. LoCA is a
    focus-depth error and has no reason to vanish on the axis. So fit the
    per-channel offset against radius and read off the intercept. If the
    intercept is indistinguishable from zero, this is lateral. If the intercept
    carries essentially the whole effect, it is axial.
    This is the discriminator the brief asks for, and it is the one M107 could
    not perform: it measured a single 512x512 ROI per stack and therefore had
    no radial lever at all.

(3) SIGN CONSISTENCY. Lateral CA reverses direction across the centre; axial CA
    does not. Reported as the fraction of confident points with a negative
    offset, beside the same fraction for the G1-G2 null.

Rule 4 is live here. On coffee-bean the NULL itself trends with radius
(R2 0.56, p 0.001), so radius is not a clean axis on that stack and a raw
radial fit there is not interpretable on its own. Every fit is therefore run
twice -- on the raw statistic and on the null-corrected statistic -- and both
are printed side by side in the same table, per rule 3.
"""
import json
import os

import numpy as np

from common import OUT, PLANES, dump
import b2_analyse as b2

# Fact 1414 (M107): the shipped lateral coefficients, in ppm of radius.
EPS_LATERAL = {"R": -704.5e-6, "B": +68.4e-6}


def boot_fit(r, v, nboot=4000, seed=7):
    """Line fit with a bootstrap over tiles. Returns intercept and slope CIs.

    The bootstrap resamples TILES, not points, because the box support
    correlates points within a tile and resampling points would understate the
    interval by roughly the square root of the points-per-tile.
    """
    ok = np.isfinite(v)
    r, v = r[ok], v[ok]
    n = r.size
    if n < 4:
        return None
    A = np.polyfit(r, v, 1)
    rng = np.random.default_rng(seed)
    ic, sl = np.empty(nboot), np.empty(nboot)
    for i in range(nboot):
        j = rng.integers(0, n, n)
        if np.ptp(r[j]) < 1e-9:
            ic[i], sl[i] = np.nan, np.nan
            continue
        p = np.polyfit(r[j], v[j], 1)
        sl[i], ic[i] = p[0], p[1]
    ic, sl = ic[np.isfinite(ic)], sl[np.isfinite(sl)]
    return {
        "n_tiles": int(n),
        "slope": float(A[0]),
        "slope_ci": [float(np.percentile(sl, 2.5)), float(np.percentile(sl, 97.5))],
        "intercept_at_r0": float(A[1]),
        "intercept_ci": [float(np.percentile(ic, 2.5)), float(np.percentile(ic, 97.5))],
        "r_min": float(r.min()), "r_max": float(r.max()),
        "value_at_rmax": float(np.polyval(A, r.max())),
    }


def run(stacks=("lavendar-cpl", "coffee-bean", "couch-fibers-cpl", "bee-2-cpl"),
        thr=1.5):
    out = []
    for stack in stacks:
        try:
            z = b2.load(stack)
        except FileNotFoundError:
            continue
        res, nt, npt = b2.peaks(z)
        track_ok = np.repeat(z["track_res"] <= 2.0, npt)
        conf = b2.gate(res, thr, track_ok)
        kG = 0.5 * (res["G1"]["k"] + res["G2"]["k"])
        dR = res["R"]["k"] - kG
        dB = res["B"]["k"] - kG
        dN = res["G1"]["k"] - res["G2"]["k"]

        tr = z["rad"].reshape(nt, npt).mean(axis=1)
        ent = {"stack": stack, "n_conf": int(conf.sum()), "fits": {}}
        tv = {}
        for lbl, v in (("dR", dR), ("dB", dB), ("NULL", dN)):
            t, keep = b2.tilewise(v, conf, nt, npt)
            tv[lbl] = (t, keep)
        # null-corrected arms (rule 4: the control trends on this axis on
        # at least one stack, so the raw fit alone is not interpretable)
        for lbl in ("dR", "dB"):
            t, keep = tv[lbl]
            tn, keepn = tv["NULL"]
            k = keep & keepn
            ent["fits"][lbl] = boot_fit(tr[keep], t[keep])
            ent["fits"][lbl + "_minus_NULL"] = boot_fit(tr[k], t[k] - tn[k])
        t, keep = tv["NULL"]
        ent["fits"]["NULL"] = boot_fit(tr[keep], t[keep])

        ent["sign"] = {
            "dR_neg": float(np.mean(dR[conf] < 0)),
            "dB_neg": float(np.mean(dB[conf] < 0)),
            "NULL_neg": float(np.mean(dN[conf] < 0)),
        }
        # What a pure lateral error would look like on this axis, for scale.
        rmax = float(tr.max())
        ent["lateral_reference"] = {
            "red_displacement_at_rmax_px": abs(EPS_LATERAL["R"]) * rmax,
            "blue_displacement_at_rmax_px": abs(EPS_LATERAL["B"]) * rmax,
            "note": "spatial displacement in plane px; a k-independent shift "
                    "cannot move a peak along the frame axis",
        }
        out.append(ent)
    return out


def show(out):
    print("\n===== LoCA vs lateral CA =====")
    print("Discriminator 2: intercept at the optical centre.")
    print("Lateral CA must be ZERO at r=0. Axial CA need not be.\n")
    print(f"{'stack':<18}{'stat':<18}{'nT':>4}{'intercept@r0':>15}"
          f"{'  95% CI':<22}{'@r_max':>9}{'slope/px':>12}")
    for e in out:
        for lbl in ("dR", "dR_minus_NULL", "dB", "dB_minus_NULL", "NULL"):
            f = e["fits"].get(lbl)
            if not f:
                continue
            ci = f"[{f['intercept_ci'][0]:+.3f},{f['intercept_ci'][1]:+.3f}]"
            print(f"{e['stack']:<18}{lbl:<18}{f['n_tiles']:>4}"
                  f"{f['intercept_at_r0']:>+15.4f}{ci:>22}"
                  f"{f['value_at_rmax']:>+9.3f}{f['slope']:>+12.2e}")
        print()
    print("Discriminator 3: sign consistency (lateral reverses across centre)")
    print(f"{'stack':<18}{'dR<0':>8}{'dB<0':>8}{'NULL<0':>9}{'n':>8}")
    for e in out:
        s = e["sign"]
        print(f"{e['stack']:<18}{100*s['dR_neg']:>7.1f}%{100*s['dB_neg']:>7.1f}%"
              f"{100*s['NULL_neg']:>8.1f}%{e['n_conf']:>8}")


if __name__ == "__main__":
    o = run()
    show(o)
    dump("b6_discriminate", o)
