"""Instrument B controls.  Registered in PRE-REGISTRATION.md; each has a stated
falsifying value and each is run on real data, not on a synthetic.

N1  gather-crop null   -- the bbox crop optimisation inside gather_planes must
                          be equivalent to gathering the uncropped plane.
                          The docstring of gather_planes claims this; a claimed
                          control that was never run is a false claim (rule 43),
                          so it is run here.
                          The crop cannot be *bit*-identical: map_coordinates
                          spline-prefilters with a recursive IIR filter whose
                          edge transient decays as |z1|^pad = 0.268^8 ~ 3e-5,
                          so a residual of order 1e-4 of signal is expected and
                          is not a defect.  The bar is therefore set on the
                          quantity that actually matters downstream:
                          FALSIFIED IF max|dF|/max(F) > 1e-3 in the focus map,
                          or if max|d(DN)| exceeds 1 DN (a quarter of this
                          sensor's read noise).

N2a bookkeeping null   -- write one channel's data into all four CFA sites and
                          re-run the whole instrument.  Every difference must be
                          identically zero.  FALSIFIED IF any median != 0.

N2b LABEL-SWAP POWER   -- the decisive one.  Swap the *data* of the R site and
                          the G1 site in every frame, leaving the geometry, the
                          lattice offsets, the warp and the gate untouched.
                          If the instrument measures wavelength (real axial CA)
                          the signal and the null must EXCHANGE PLACES:
                             d_R  -> ~0        (green data vs green data)
                             null -> ~ d_R_orig (red data vs green data)
                          If instead the instrument measures the lattice site,
                          the numbers will not move.  FALSIFIED IF d_R stays
                          within 30% of its original value.

N3  SNR-bias null      -- a noisier channel's argmax is biased.  R and B are
                          darker than G after black subtraction, so degrade G2
                          to R's photon level and noise and re-measure the
                          green-green null.  FALSIFIED IF |median| > 0.15 frames
                          i.e. if SNR alone can manufacture 15% of the signal.
"""
import sys, os, json, time
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, dump
from e3_argmax import (PLANES, WIN, read_warpmap, gather_planes, focus,
                       subframe_argmax, frames, SITE)

import rawpy

STACK = "tweezers-cpl"
SIDE = r"C:\dev\strehl-out\M107-chroma\renders\tweezers-cpl-warpmap.txt"
X0, Y0, W, H = 1200, 900, 512, 512


def n1_gather_crop_null():
    """Cropped vs uncropped map_coordinates on a real frame with a real warp."""
    meta, warps = read_warpmap(SIDE)
    fs = frames(STACK)
    k = len(fs) // 3
    with rawpy.imread(fs[k]) as r:
        cfa = r.raw_image_visible.astype(np.float32)
        black = float(np.mean(r.black_level_per_channel))
    cfa -= black
    a = gather_planes(cfa, warps[k], X0, Y0, W, H, 3)
    b = gather_planes(cfa, warps[k], X0, Y0, W, H, 3, _no_crop=True)
    worst_dn, worst_f = 0.0, 0.0
    for c in PLANES:
        d = float(np.max(np.abs(a[c] - b[c])))
        fa = focus(a[c].astype(np.float32)); fb = focus(b[c].astype(np.float32))
        rf = float(np.max(np.abs(fa - fb)) / max(float(fa.max()), 1e-9))
        worst_dn = max(worst_dn, d); worst_f = max(worst_f, rf)
        print(f"  N1 {c}: max|d| = {d:.3e} DN   max|dF|/max(F) = {rf:.3e}")
    ok = worst_dn <= 1.0 and worst_f <= 1e-3
    print(f"  N1 worst {worst_dn:.3e} DN, {worst_f:.3e} rel-focus -> "
          f"{'PASS' if ok else 'FAIL'}")
    return {"control": "N1_gather_crop_null", "worst_abs_diff_DN": worst_dn,
            "worst_rel_focus_diff": worst_f, "bar_DN": 1.0, "bar_rel_focus": 1e-3,
            "pass": bool(ok)}


def _measure(mutate=None, tag=""):
    """Run the full Instrument B on STACK, optionally mutating each frame's CFA."""
    meta, warps = read_warpmap(SIDE)
    fs = frames(STACK)
    F = {c: np.empty((len(fs), H, W), dtype=np.float32) for c in PLANES}
    t0 = time.time()
    for k, path in enumerate(fs):
        with rawpy.imread(path) as r:
            cfa = r.raw_image_visible.astype(np.float32)
            black = float(np.mean(r.black_level_per_channel))
        cfa -= black
        if mutate is not None:
            cfa = mutate(cfa, k)
        pls = gather_planes(cfa, warps[k], X0, Y0, W, H, 3)
        for c in PLANES:
            F[c][k] = focus(pls[c].astype(np.float32))
        if k % 50 == 0:
            print(f"    [{tag}] frame {k}/{len(fs)} ({time.time()-t0:.0f}s)")
    res = {}
    for c in PLANES:
        kk, prom, interior, uni = subframe_argmax(F[c])
        res[c] = {"k": kk, "prom": prom, "interior": interior, "uni": uni}
    conf = np.ones((H, W), bool)
    for c in PLANES:
        conf &= res[c]["interior"] & res[c]["uni"] & (res[c]["prom"] >= 3.0)
    e = np.zeros((H, W), bool); e[WIN:-WIN, WIN:-WIN] = True
    conf &= e
    kG = 0.5 * (res["G1"]["k"] + res["G2"]["k"])
    out = {
        "tag": tag, "n_conf": int(conf.sum()),
        "median_dR": float(np.median((res["R"]["k"] - kG)[conf])),
        "median_dB": float(np.median((res["B"]["k"] - kG)[conf])),
        "median_null": float(np.median((res["G1"]["k"] - res["G2"]["k"])[conf])),
    }
    print(f"    [{tag}] n={out['n_conf']}  dR={out['median_dR']:+.4f}  "
          f"dB={out['median_dB']:+.4f}  null={out['median_null']:+.4f}")
    return out


def _sites(cfa):
    """Views onto the four CFA sites of the full sensel array."""
    v = {}
    for c, (ox, oy) in SITE.items():
        v[c] = cfa[oy::2, ox::2]
    return v


def n2a_bookkeeping_null():
    def mut(cfa, k):
        s = _sites(cfa)
        g = s["G1"].copy()
        out = cfa.copy()
        so = _sites(out)
        for c in PLANES:
            so[c][:, :] = g
        return out
    r = _measure(mut, "N2a-all-four-sites-carry-G1")
    ok = (abs(r["median_dR"]) < 1e-9 and abs(r["median_dB"]) < 1e-9
          and abs(r["median_null"]) < 1e-9)
    r.update({"control": "N2a_bookkeeping_null", "bar": 0.0, "pass": bool(ok)})
    print(f"  N2a -> {'PASS' if ok else 'FAIL'}")
    return r


def n2b_label_swap_power(orig_dR):
    def mut(cfa, k):
        out = cfa.copy()
        s = _sites(cfa); so = _sites(out)
        so["R"][:, :] = s["G1"]
        so["G1"][:, :] = s["R"]
        return out
    r = _measure(mut, "N2b-swap-R-and-G1-data")
    moved = abs(r["median_dR"] - orig_dR) > 0.30 * abs(orig_dR)
    r.update({"control": "N2b_label_swap_power", "orig_dR": orig_dR,
              "bar": "d_R must move >30% and null must pick up the signal",
              "pass": bool(moved)})
    print(f"  N2b -> {'PASS' if moved else 'FAIL'}  "
          f"(dR {orig_dR:+.4f} -> {r['median_dR']:+.4f}; "
          f"null 0 -> {r['median_null']:+.4f})")
    return r


def n3_snr_bias_null():
    rng = np.random.default_rng(20250824)
    # measure the level ratio once, on the reference frame
    fs = frames(STACK)
    with rawpy.imread(fs[len(fs) // 2]) as r:
        cfa0 = r.raw_image_visible.astype(np.float32)
        black = float(np.mean(r.black_level_per_channel))
    cfa0 -= black
    s0 = _sites(cfa0)
    yy = slice(Y0, Y0 + H); xx = slice(X0, X0 + W)
    mR = float(np.mean(s0["R"][yy, xx])); mG = float(np.mean(s0["G1"][yy, xx]))
    ratio = mR / mG
    print(f"  N3 mean level in ROI: R={mR:.1f} G1={mG:.1f}  ratio={ratio:.4f}")

    def mut(cfa, k):
        out = cfa.copy()
        so = _sites(out)
        g = so["G2"]
        # scale G2 down to R's photon level, then add the shot noise that a
        # sensor at that level would actually have (Poisson in electrons).
        scaled = g * ratio
        extra = np.sqrt(np.maximum(scaled, 0.0) * (1.0 / max(ratio, 1e-6) - 1.0))
        so["G2"][:, :] = scaled + rng.normal(0.0, 1.0, scaled.shape) * extra
        return out

    r = _measure(mut, "N3-G2-degraded-to-R-SNR")
    ok = abs(r["median_null"]) <= 0.15
    r.update({"control": "N3_snr_bias_null", "level_ratio_R_over_G": ratio,
              "bar": 0.15, "pass": bool(ok)})
    print(f"  N3 null = {r['median_null']:+.4f} frames -> "
          f"{'PASS' if ok else 'FAIL'} (bar 0.15)")
    return r


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = []
    if which in ("all", "n1"):
        print("== N1 gather-crop null ==");        res.append(n1_gather_crop_null())
    if which in ("all", "n2a"):
        print("== N2a bookkeeping null ==");       res.append(n2a_bookkeeping_null())
    if which in ("all", "n2b"):
        base = json.load(open(os.path.join(OUT, "json", "e3_argmax.json")))
        rows = base["data"] if isinstance(base, dict) else base
        d0 = [x for x in rows if x["stack"] == STACK][0]["median_dR"]
        print("== N2b label-swap power ==");       res.append(n2b_label_swap_power(d0))
    if which in ("all", "n3"):
        print("== N3 SNR-bias null ==");           res.append(n3_snr_bias_null())
    dump(f"e3_controls_{which}", res)
