"""M113 K12 - IS THERE RINGING WHERE n_eff IS SMALL?

The orchestrator's stated weakest point in the GO case, and it is a good one.
My anti-ringing result (fact 1466) rests on a mean-field argument: mean n_eff is
55.3, so each output pixel averages many frames at many sub-pixel phases and
phase-dependent ringing cancels. That argument has NO FORCE where n_eff = 1.
Fact 1374 measured 9.902x under exactly that condition -- one frame, half-pixel
phase -- and n_eff == 1 is not a corner case here: it is 38.77% of quads.

STAGE A IS A POSITIVE CONTROL ON MY OWN INSTRUMENT, and it comes first because
everything I have already published about ringing depends on it. k5b reported
0.9924x / 1.0039x and I never demonstrated the census CAN detect ringing. A
control that cannot fail is worthless (discipline 748, which is my own finding
turned on myself). So: apply the SAME census to a single image resampled at a
half-pixel phase, where ringing is known to exist. If it does not light up
there, the census is a dead instrument, fact 1466 is void, and I have to say so.

Everything runs on the PLANE grid, 3516x2344, which is both the merge's native
output grid and the n_eff map's grid -- 1:1, so no resampling enters the
analysis and no interpolation of mine can manufacture or hide an artefact.

MASKS. Discipline 752: the stratifying mask must not come from the arm under
test. The arm under test is lanczos3. Primary mask is CATMULL-ROM's n_eff -- the
incumbent default, which also makes the question the decision-relevant one
("in the regions where today's render averages few frames, what happens if I
switch?"). NEAREST's n_eff is carried as an independence check. lanczos3's own
n_eff map is loaded ONLY to quantify mask disagreement, never to stratify.
"""
import json
import os

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
R = r"C:\dev\strehl-out\M113\render3"
NB = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], bool)


def luma(p):
    a = tifffile.imread(p).astype(np.float64)
    return 0.25 * a[..., 0] + 0.50 * a[..., 1] + 0.25 * a[..., 2]


def cr_w(p):
    o = np.array([-1, 0, 1, 2]); t = p - o; a = np.abs(t)
    return np.where(a <= 1.0, 1.5*a**3 - 2.5*a**2 + 1.0,
                    np.where(a < 2.0, -0.5*a**3 + 2.5*a**2 - 4.0*a + 2.0, 0.0)), o


def l3_w(p):
    o = np.array([-2, -1, 0, 1, 2, 3]); t = p - o
    v = np.where(np.abs(t) < 3.0, np.sinc(t) * np.sinc(t / 3.0), 0.0)
    return v / v.sum(), o


def shift(a, p, wf):
    w, o = wf(p)
    t = np.zeros_like(a)
    for wi, oi in zip(w, o):
        t += wi * np.roll(a, -int(oi), axis=1)
    r = np.zeros_like(a)
    for wi, oi in zip(w, o):
        r += wi * np.roll(t, -int(oi), axis=0)
    return r


def extrema_density(v, mask=None):
    """Strict local extrema per Mpx. Filters run on the FULL image so every
    pixel has a real 8-neighbourhood; the mask only selects what is counted."""
    f = v.astype(np.float32)
    lo = f < ndimage.minimum_filter(f, footprint=NB)
    hi = f > ndimage.maximum_filter(f, footprint=NB)
    if mask is None:
        n = f.size
        return (lo.sum() + hi.sum()) / (n / 1e6)
    n = int(mask.sum())
    if n == 0:
        return float("nan")
    return float((lo[mask].sum() + hi[mask].sum()) / (n / 1e6))


def overshoot_p999(out, src, mask=None):
    """M95's statistic: excursion beyond the source's own 3x3 [min,max]
    envelope, as a fraction of the local range. A monotone kernel cannot
    exceed the envelope at all; a negative-lobe kernel can."""
    emax = ndimage.maximum_filter(src, footprint=NB)
    emin = ndimage.minimum_filter(src, footprint=NB)
    rng = np.maximum(emax - emin, 1e-9)
    over = np.maximum(np.maximum(out - emax, emin - out), 0.0) / rng
    w = over if mask is None else over[mask]
    if w.size == 0:
        return float("nan")
    return float(np.percentile(w, 99.9))


def main():
    res = {}
    print("=" * 78)
    print("STAGE A  POSITIVE CONTROL -- can this census see ringing at all?")
    print("=" * 78)
    nn = luma(os.path.join(R, "lin-nn.tif"))
    src = nn[600:2000, 900:2600].copy()
    print(f"  source: nearest arm, plane grid, crop {src.shape}, half-pixel phase")
    a = {}
    for nm, wf in (("catmull-rom", cr_w), ("lanczos3", l3_w)):
        o = shift(src, 0.5, wf)
        c = src[8:-8, 8:-8]
        d = extrema_density(o[8:-8, 8:-8])
        ov = overshoot_p999(o[8:-8, 8:-8], c)
        a[nm] = dict(extrema_per_Mpx=d, overshoot_p999=ov)
        print(f"    {nm:12s} extrema {d:9.0f}/Mpx   p99.9 overshoot "
              f"{100*ov:7.3f}% of local range")
    re_ = a["lanczos3"]["extrema_per_Mpx"] / a["catmull-rom"]["extrema_per_Mpx"]
    ro = (a["lanczos3"]["overshoot_p999"] /
          max(a["catmull-rom"]["overshoot_p999"], 1e-12))
    print(f"    RATIO lanczos3/catmull-rom : extrema {re_:.4f}x   overshoot {ro:.3f}x")
    print(f"    fact 1374 measured 9.902x by an overshoot statistic like this one.")
    powered = ro > 2.0
    print(f"    INSTRUMENT HAS POWER: {powered}  (overshoot ratio > 2.0 required)")
    if not powered:
        print("    *** the census cannot see ringing that is known to be there.")
        print("    *** fact 1466 would be resting on a dead instrument.")
    res["A_positive_control"] = dict(arms=a, extrema_ratio=re_, overshoot_ratio=ro,
                                     has_power=bool(powered))

    print()
    print("=" * 78)
    print("STAGE B  n_eff maps -- sanity, and how much the mask choice matters")
    print("=" * 78)
    ne = {k: tifffile.imread(os.path.join(R, f"neff-{k}.tif")).astype(np.int32)
          for k in ("cr", "l3", "nn")}
    for k, v in ne.items():
        print(f"    {k}: shape {v.shape}  range {v.min()}..{v.max()}  mean {v.mean():.3f}  "
              f"n_eff==1 {100*(v==1).mean():.2f}%")
    agree = float((ne["cr"] == ne["nn"]).mean())
    both1 = float(((ne["cr"] == 1) == (ne["nn"] == 1)).mean())
    print(f"    cr vs nn n_eff: identical at {100*agree:.2f}% of quads; "
          f"agree on 'is n_eff==1' at {100*both1:.2f}%")
    res["B_maps"] = {k: dict(mean=float(v.mean()), pct_1=float(100*(v==1).mean()))
                     for k, v in ne.items()}
    res["B_maps"]["cr_nn_identical_pct"] = 100*agree
    res["B_maps"]["cr_nn_agree_is1_pct"] = 100*both1

    print()
    print("=" * 78)
    print("STAGE C  is low n_eff where the EDGES are? (does the census have power there)")
    print("=" * 78)
    cr = luma(os.path.join(R, "lin-cr.tif"))
    l3 = luma(os.path.join(R, "lin-l3.tif"))
    rng5 = (ndimage.maximum_filter(nn, size=5) - ndimage.minimum_filter(nn, size=5))
    g = np.hypot(*np.gradient(nn))
    STRATA = [("n_eff == 1", 1, 1), ("2", 2, 2), ("3-4", 3, 4), ("5-8", 5, 8),
              ("9-16", 9, 16), ("17-32", 17, 32), ("33-64", 33, 64),
              ("65-128", 65, 128), ("129+", 129, 10**9)]
    print(f"    {'stratum':12s} {'% of quads':>11s} {'median 5x5 range':>18s} "
          f"{'median |grad|':>14s}")
    for nm, lo, hi in STRATA:
        m = (ne["cr"] >= lo) & (ne["cr"] <= hi)
        if m.sum() == 0:
            continue
        print(f"    {nm:12s} {100*m.mean():10.2f}% {np.median(rng5[m]):18.1f} "
              f"{np.median(g[m]):14.1f}")
    gthr = float(np.percentile(g, 90.0))
    print(f"    global top-decile gradient threshold: {gthr:.1f} DN")

    print()
    print("=" * 78)
    print("STAGE D  STRATIFIED EXCESS-EXTREMA CENSUS on the two merged arms")
    print("=" * 78)
    for maskname, nemask in (("catmull-rom n_eff (incumbent, primary)", ne["cr"]),
                             ("nearest n_eff (independent third arm)", ne["nn"])):
        print(f"\n  --- stratified by {maskname} ---")
        print(f"    {'stratum':12s} {'n quads':>10s} {'cr /Mpx':>10s} {'l3 /Mpx':>10s} "
              f"{'l3/cr':>8s} {'EDGE l3/cr':>11s} {'edge n':>9s}")
        rows = {}
        for nm, lo, hi in STRATA:
            m = (nemask >= lo) & (nemask <= hi)
            if m.sum() < 5000:
                continue
            dc = extrema_density(cr, m)
            dl = extrema_density(l3, m)
            me = m & (g >= gthr)
            if me.sum() >= 5000:
                ec = extrema_density(cr, me)
                el = extrema_density(l3, me)
                er = el / ec
            else:
                er = float("nan")
            rows[nm] = dict(n=int(m.sum()), cr=dc, l3=dl, ratio=dl/dc,
                            edge_ratio=er, edge_n=int(me.sum()))
            print(f"    {nm:12s} {int(m.sum()):10d} {dc:10.0f} {dl:10.0f} "
                  f"{dl/dc:8.4f} {er:11.4f} {int(me.sum()):9d}")
        res["D_" + ("cr" if "incumbent" in maskname else "nn")] = rows

    json.dump(res, open(os.path.join(OUT, "k12_neff_ringing.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k12_neff_ringing.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())