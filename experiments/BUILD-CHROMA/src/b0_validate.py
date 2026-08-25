"""B0 -- instrument validation. Run this before believing anything B1 says.

Four checks, in increasing order of how much they can embarrass the instrument:

  V1  shift convention. Plant a known integer roll and confirm the phase
      correlator recovers it with the right SIGN. A sign error here would
      mis-register every frame and is otherwise invisible.

  V2  parabola accuracy on an analytic curve with a known vertex.

  V3  PLANTED PER-CHANNEL FOCUS OFFSET, as a dose-response ladder (rule 5).
      A synthetic bracket is built from a real, sharp CFA frame by blurring
      each channel with a defocus schedule whose minimum sits at a planted
      frame index. The full B1 operator chain -- same `focus`, same
      `parabola_peak` -- must recover the planted offset. The ladder runs
      0.00, 0.25, 0.50, 1.00, 2.00 frames, so the instrument's response is
      characterised rather than spot-checked at one dose.

  V4  the zero-dose arm of V3 is the instrument's own null: planted 0.00 must
      come back 0.00, on the same code path, with noise present.

Nothing here reads a rendered file, so none of the TIFF/PIL hazards apply.
"""

import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(__file__))
from common import (OUT, PLANES, WIN, frames, read_cfa, planes_of, focus,
                    ref_spectrum, phase_shift_ref, parabola_peak, dump)

RNG = np.random.default_rng(20260825)


# ----------------------------------------------------------------- V1 -----
def v1_shift_convention(tile):
    """Plant integer rolls; the recovered shift must equal the planted one."""
    spec = ref_spectrum(tile)
    rows = []
    for (py, px) in [(0, 0), (3, 0), (0, 5), (-4, 2), (7, -6), (-11, -9)]:
        # np.roll by +s moves content that was at p to p+s, so the scene point
        # at reference p appears in the rolled image at p+s. The convention in
        # `phase_shift_ref` must therefore return exactly (+py, +px).
        img = np.roll(np.roll(tile, py, axis=0), px, axis=1)
        dy, dx = phase_shift_ref(spec, img)
        rows.append({"planted": [py, px], "recovered": [dy, dx],
                     "ok": bool(round(dy) == py and round(dx) == px)})
    return rows


# ----------------------------------------------------------------- V2 -----
def v2_parabola():
    """Analytic Gaussian-ish peak at a known non-integer vertex."""
    rows = []
    for true_k in [12.0, 12.25, 12.5, 12.75, 13.0]:
        k = np.arange(30.0)
        y = np.exp(-0.5 * ((k - true_k) / 3.0) ** 2)[:, None]
        kh, _, _, interior, uni = parabola_peak(y.astype(np.float64))
        rows.append({"true": true_k, "recovered": float(kh[0]),
                     "err": float(kh[0] - true_k),
                     "interior": bool(interior[0]), "unimodal": bool(uni[0])})
    return rows


# ------------------------------------------------------------- V3 / V4 ----
def synth_stack(base, nk, k_peak, sigma_min=0.6, alpha=0.34, noise=True,
                gain=2.052, read_adu=2.0, noise_scale=1.0):
    """A synthetic through-focus bracket for one plane.

    Defocus blur grows away from the plane's own best-focus frame:
        sigma(k) = sqrt(sigma_min^2 + (alpha * (k - k_peak))^2)
    which is the standard geometric-defocus-plus-diffraction form and produces
    a smooth, unimodal sharpness peak at k_peak. `alpha = 0.34` was chosen so
    the resulting through-focus half-width is ~4 frames, matching the real
    brackets (M107 section 4.4 reports 3-4 frames).

    Noise is the MEASURED sensor noise, not a guess. With `g` electrons per ADU
    the shot-noise variance of a signal S ADU is S/g ADU^2, so

        var_ADU = S / g + read^2

    `g = 2.052 e-/ADU` and `read ~ 2 ADU` come from `b0b_noise.py`'s photon
    transfer on this very bracket (R^2 = 0.998 on four independent fits). The
    first version of this function used `var = S * 2.5`, which is 5.1x too much
    variance, and it destroyed every synthetic focus curve -- that failure is
    reported rather than quietly fixed, because it is the reason the noise is
    now measured instead of assumed.
    """
    out = np.empty((nk,) + base.shape, np.float32)
    for k in range(nk):
        s = np.sqrt(sigma_min ** 2 + (alpha * (k - k_peak)) ** 2)
        img = gaussian_filter(base, s, mode="nearest")
        if noise and noise_scale > 0:
            var = (np.maximum(img, 0.0) / gain + read_adu ** 2) * noise_scale ** 2
            img = img + RNG.normal(0.0, 1.0, img.shape) * np.sqrt(var)
        out[k] = img
    return out


def v3_planted(base_planes, nk=41, doses=(0.0, 0.25, 0.5, 1.0, 2.0), noise=True,
               noise_scale=1.0):
    """Dose-response ladder on a planted per-channel offset.

    Green is planted at the centre frame. Red is planted `-dose` frames from
    green and blue `-0.6*dose`, reproducing the SAME-SIDE structure the real
    lens shows (SYNTHESIS fact 1416) rather than a symmetric straddle -- a null
    must match the treatment in structure, not just in magnitude (rule 3).
    """
    k0 = (nk - 1) / 2.0
    rows = []
    for dose in doses:
        planted = {"R": k0 - dose, "G1": k0, "G2": k0, "B": k0 - 0.6 * dose}
        F = {}
        for c in PLANES:
            st = synth_stack(base_planes[c], nk, planted[c], noise=noise,
                             noise_scale=noise_scale)
            F[c] = np.stack([focus(st[k], WIN)[WIN:-WIN, WIN:-WIN].ravel()
                             for k in range(nk)])
        res = {}
        for c in PLANES:
            kh, _, prom, interior, uni = parabola_peak(F[c].astype(np.float64))
            res[c] = (kh, prom, interior & uni)
        promstat = {c: [float(np.percentile(res[c][1], q)) for q in (5, 50, 95)]
                    for c in PLANES}
        okstat = {c: float((res[c][2]).mean()) for c in PLANES}
        # Gate as a LADDER, not a rule of thumb (rule 5): the recovered offset
        # is reported as a function of the prominence threshold so the reader
        # can see whether the answer depends on where the gate is put.
        kG = 0.5 * (res["G1"][0] + res["G2"][0])
        dR = res["R"][0] - kG
        dB = res["B"][0] - kG
        null = res["G1"][0] - res["G2"][0]
        ladder = []
        for thr in (1.0, 1.2, 1.5, 2.0, 3.0):
            conf = np.ones_like(res["R"][2])
            for c in PLANES:
                conf &= res[c][2] & (res[c][1] >= thr)
            ladder.append({
                "thr": thr, "n": int(conf.sum()),
                "dR": float(np.median(dR[conf])) if conf.any() else None,
                "dB": float(np.median(dB[conf])) if conf.any() else None,
                "null": float(np.median(null[conf])) if conf.any() else None})
        # the headline arm uses the loosest gate that still requires a valid,
        # interior, unimodal peak in all four planes
        conf = np.ones_like(res["R"][2])
        for c in PLANES:
            conf &= res[c][2] & (res[c][1] >= 1.2)
        rows.append({
            "dose": dose,
            "planted_dR": -dose, "planted_dB": -0.6 * dose,
            "prom_pctiles": promstat, "frac_interior_unimodal": okstat,
            "gate_ladder": ladder,
            "n_conf": int(conf.sum()), "n_tot": int(conf.size),
            "rec_dR": float(np.median(dR[conf])) if conf.any() else None,
            "rec_dB": float(np.median(dB[conf])) if conf.any() else None,
            "rec_null": float(np.median(null[conf])) if conf.any() else None,
            "err_dR": float(np.median(dR[conf]) + dose) if conf.any() else None,
            "err_dB": float(np.median(dB[conf]) + 0.6 * dose) if conf.any() else None,
            "iqr_dR": [float(np.percentile(dR[conf], 25)),
                       float(np.percentile(dR[conf], 75))] if conf.any() else None,
        })
        r = rows[-1]
        fmt = lambda v: "  none" if v is None else f"{v:+.4f}"
        print(f"   dose {dose:4.2f}  planted dR={-dose:+.3f} dB={-0.6*dose:+.3f}"
              f"   recovered dR={fmt(r['rec_dR'])} dB={fmt(r['rec_dB'])}"
              f"   NULL={fmt(r['rec_null'])}  (n={r['n_conf']}/{r['n_tot']})")
        print(f"        prom p50 R={promstat['R'][1]:.2f} G1={promstat['G1'][1]:.2f}"
              f"  interior&unimodal frac R={okstat['R']:.3f} G1={okstat['G1']:.3f}")
    return rows


def sharpest_frame(stack, probe=24):
    """Index of the globally sharpest frame, by total green gradient energy."""
    fs = frames(stack)
    ks = np.linspace(0, len(fs) - 1, probe).astype(int)
    best, bk = -1.0, ks[0]
    for k in ks:
        g = planes_of(read_cfa(fs[k]))["G1"][900:1400, 1400:2100]
        e = float(focus(g.astype(np.float32), WIN).mean())
        if e > best:
            best, bk = e, k
    return int(bk), fs[bk]


def v5_sat_equivalence(plane):
    """The fast summed-area box mean must equal `uniform_filter` exactly.

    B1 reads its focus values off a summed-area table for speed. If that path
    disagreed with the reference filter the whole measurement would be of a
    different operator than the one documented. Checked at interior points.
    """
    from common import grad_energy, integral, box_at
    from scipy.ndimage import uniform_filter
    g = grad_energy(plane.astype(np.float32))
    ref = uniform_filter(g, WIN, mode="nearest")
    sat = integral(g)
    ys, xs = np.mgrid[40:200:7, 40:200:7]
    fast = box_at(sat, ys, xs, WIN)
    slow = ref[ys, xs]
    rel = np.abs(fast - slow) / np.maximum(np.abs(slow), 1e-9)
    return {"n": int(ys.size), "max_rel_err": float(rel.max()),
            "max_abs_err": float(np.abs(fast - slow).max()),
            "ok": bool(rel.max() < 1e-5)}


if __name__ == "__main__":
    stack = sys.argv[1] if len(sys.argv) > 1 else "lavendar-cpl"
    print(f"== B0 validation, base frame from {stack} ==")
    bk, bpath = sharpest_frame(stack)
    print(f"   sharpest probe frame: index {bk}  {os.path.basename(bpath)}")
    pl = planes_of(read_cfa(bpath))
    base = {c: pl[c][1000:1256, 1500:1756].astype(np.float32) for c in PLANES}

    print("-- V1 shift convention --")
    v1 = v1_shift_convention(base["G1"].astype(np.float64))
    for r in v1:
        print(f"   planted {r['planted']}  recovered {r['recovered']}  "
              f"{'OK' if r['ok'] else 'FAIL'}")

    print("-- V2 parabola vertex --")
    v2 = v2_parabola()
    for r in v2:
        print(f"   true {r['true']:.2f}  recovered {r['recovered']:.4f}  "
              f"err {r['err']:+.4f}")

    print("-- V5 summed-area vs uniform_filter --")
    v5 = v5_sat_equivalence(base["G1"])
    print(f"   n={v5['n']}  max rel err {v5['max_rel_err']:.2e}  "
          f"{'OK' if v5['ok'] else 'FAIL'}")

    print("-- V3 planted per-channel offset, at MEASURED sensor noise --")
    v3 = v3_planted(base, noise=True)
    print("-- V3b planted per-channel offset, noise-free --")
    v3b = v3_planted(base, doses=(0.0, 0.5, 1.0), noise=False)
    print("-- V3c noise ladder at dose 1.00: where does the instrument break? --")
    v3c = []
    for ns in (0.5, 1.0, 2.0, 4.0):
        print(f"   noise x{ns}")
        v3c.append({"noise_scale": ns,
                    "rows": v3_planted(base, doses=(1.0,), noise=True,
                                       noise_scale=ns)})

    dump("b0_validate", {"stack": stack, "base_frame": bk,
                         "v1_shift": v1, "v2_parabola": v2,
                         "v5_sat": v5,
                         "v3_planted_noisy": v3, "v3_planted_clean": v3b,
                         "v3c_noise_ladder": v3c})
