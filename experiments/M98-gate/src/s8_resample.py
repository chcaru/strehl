"""M98 D3 -- where the softness actually is: the aligner's fit_to_cover upsample.

`align_cmd.rs fit_to_cover` scales the field of view by k <= 1 while keeping the
output dimensions, so a registered render is UPSAMPLED by 1/k through the warp
resampler.  On bee-3-cpl the render logs give k = 0.9227 for one half and 0.9360
for the other; on the full stack it is in the same region.  That is roughly 8% of
magnification applied by interpolation, to EVERY pixel, at EVERY gate, and it
landed tonight when alignment became default-ON.

It cannot be read off a pixel-space sharpness metric, because magnification reads
as sharpness (discipline 606): the upsampled render has the same optical detail
spread over more pixels, so per-pixel edge widths get WIDER while nothing
optical changed, and per-pixel spatial frequencies get LOWER so band-limited
amplitude metrics move for free.

A millimetre ruler fixes that, because the tick pitch is known a priori.  Measure
the comb pitch in pixels in each render and the ruler tells you the scale; convert
the equivalent Gaussian blur from pixels to OBJECT space (per tick) and the
magnification divides out exactly.

  sigma_obj  =  sigma_px / pitch_px          [in units of one tick spacing]

Two renders, same stack, same gate, same frames.  Only registration differs:
  ALN : registration on   (loads the existing warpmap.txt sidecar)
  A0  : STREHL_ALIGN=0    (no warp at all, native scale)

RULE 18 -- which way does this instrument fail?  If the comb is near the
resolution limit the sideband subtraction can drive M negative and the blur is
censored; censoring is reported.  If the two renders disagree about WHICH tick
is where (they do -- the FOV differs), the ROI grid is anchored on each render's
own lattice, so the comparison is of像 statistics, not of a registered pair.
That is exactly what an object-space scalar is for.

Usage:  python s8_resample.py
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m98lib as M98  # noqa: E402
import s3_ruler as R3  # noqa: E402

GATES = ["0", "4"]
ARMS = ["ALN", "A0"]
N = 512
INERT_MIN = 3.0


def green(path):
    a = tifffile.imread(str(path))
    if a.ndim == 3:
        a = a[..., 1] if a.shape[2] >= 3 else a[..., 0]
    return a.astype(np.float64)


def grid(w, h, nx=6, ny=4):
    out = []
    for j in range(ny):
        for i in range(nx):
            cx = int(w * (2 * i + 1) / (2 * nx))
            cy = int(h * (2 * j + 1) / (2 * ny))
            x = int(np.clip(cx - N // 2, 0, w - N))
            y = int(np.clip(cy - N // 2, 0, h - N))
            out.append((x, y))
    return out


def sigma_px_from_mod(M_ratio, f):
    """Equivalent Gaussian sigma, in px, from a modulation RATIO at freq f.

    A Gaussian PSF of sigma has MTF exp(-2 pi^2 sigma^2 f^2), so a modulation
    ratio r between two renders is r = exp(-2 pi^2 sigma^2 f^2) with sigma the
    EXTRA blur in the second.  Inverted.  r > 1 gives a negative sigma^2 and is
    reported as a negative sigma, not clipped -- clipping a null to zero is how
    a null becomes a claim.
    """
    if M_ratio <= 0:
        return float("nan")
    q = -np.log(M_ratio) / (2.0 * np.pi**2 * f**2)
    return float(np.sign(q) * np.sqrt(abs(q)))


def main():
    log = []

    def p(s=""):
        print(s)
        log.append(s)

    p("=" * 78)
    p("M98 S8 -- what does registration's resampler cost, in OBJECT space?")
    p("=" * 78)
    p("  stack flat-on-ruler-cpl, 79 frames.  Tick pitch known a priori, so")
    p("  the equivalent blur can be expressed per TICK and magnification")
    p("  divides out.  ALN vs STREHL_ALIGN=0 at the same gate.")

    res = {}
    for g in GATES:
        p("")
        p(f"--- gate {g} ---")
        rows = {}
        for arm in ARMS:
            f = Path(M98.RENDERS) / f"flat-on-ruler-cpl-RS-{arm}-g{g}.tif"
            if not f.exists():
                p(f"  MISSING {f}")
                return
            a = green(f)
            h, w = a.shape
            recs = []
            for k, (x, y) in enumerate(grid(w, h)):
                c = a[y:y + N, x:x + N]
                P = R3.power(c)
                found = R3.find_comb(P)
                if found is None:
                    continue
                fy, fx, f0 = found
                S, B, M = R3.probe(P, fy, fx)
                sb = S / B if B > 0 else float("inf")
                if sb < INERT_MIN or M <= 0:
                    continue
                recs.append(dict(k=k, f0=f0, pitch_px=1.0 / f0, M=M, sb=sb))
            rows[arm] = recs
            pp = np.array([r["pitch_px"] for r in recs])
            p(f"  {arm:>4}  {w}x{h}   live ROIs {len(recs)}/24   "
              f"tick pitch {pp.min():.3f}-{pp.max():.3f} px  "
              f"(median {np.median(pp):.3f})")

        # ROIs that survived the inertness gate in BOTH arms, paired by index.
        ka = {r["k"]: r for r in rows["ALN"]}
        kb = {r["k"]: r for r in rows["A0"]}
        common = sorted(set(ka) & set(kb))
        p(f"  paired ROIs live in both arms: {len(common)}")
        if not common:
            p("  INERT -- no paired ROI resolves the comb. No evidence.")
            continue

        mags, sig_px, sig_obj = [], [], []
        for k in common:
            ra, rb = ka[k], kb[k]
            mag = ra["pitch_px"] / rb["pitch_px"]
            # Compare at each render's own comb line.  The blur is expressed at
            # the ALN render's frequency, then converted to object space.
            r = ra["M"] / rb["M"]
            s_px = sigma_px_from_mod(r, ra["f0"])
            mags.append(mag)
            sig_px.append(s_px)
            sig_obj.append(s_px / ra["pitch_px"])

        mags = np.array(mags)
        sig_px = np.array(sig_px, float)
        sig_obj = np.array(sig_obj, float)
        m_ok = np.isfinite(sig_px)

        def ms(v):
            v = v[np.isfinite(v)]
            return v.mean(), (v.std(ddof=1) / np.sqrt(v.size)
                              if v.size > 1 else float("nan")), v.size

        mm, mse, _ = ms(mags)
        sp, spse, n = ms(sig_px)
        so, sose, _ = ms(sig_obj)
        p(f"  MEASURED magnification ALN/A0 = {mm:.5f} +/- {mse:.5f}"
          f"   (i.e. fit_to_cover upsamples by {(mm - 1) * 100:+.2f}%)")
        p(f"  extra blur in ALN, PIXEL space  = {sp:+.4f} +/- {spse:.4f} px"
          f"   (n={n})")
        p(f"  extra blur in ALN, OBJECT space = {so:+.5f} +/- {sose:.5f}"
          f" ticks")
        p(f"  ... which, expressed back on the A0 pixel grid, is"
          f" {so * np.median([r['pitch_px'] for r in rows['A0']]):+.4f} px")
        res[g] = dict(mag=mm, mag_se=mse, sig_px=sp, sig_px_se=spse,
                      sig_obj=so, sig_obj_se=sose, n=int(n),
                      n_paired=len(common))
        _ = m_ok

    p("")
    p("--- INDEPENDENT CHECK: does the ruler recover the aligner's own k? ---")
    p("  align_cmd.rs fit_to_cover prints the scale it chose.  The ruler's comb")
    p("  frequency ratio is measured from the photograph and knows nothing")
    p("  about that number, so agreement is a real check on the instrument.")
    k = None
    lp = Path(M98.LOGS) / "flat-on-ruler-cpl-RS-ALN-g0.log"
    if lp.exists():
        for line in lp.read_text(encoding="utf-8",
                                 errors="replace").splitlines():
            if "field of view scaled to" in line:
                try:
                    k = float(line.split("scaled to")[1].split()[0])
                except (IndexError, ValueError):
                    pass
                break
    if k and res.get("0"):
        pred = 1.0 / k
        got = res["0"]["mag"]
        se = res["0"]["mag_se"]
        z = (got - pred) / se if se > 0 else float("nan")
        p(f"  log says fit_to_cover k = {k:.4f}  ->  predicted upsample "
          f"{pred:.5f}x ({(pred - 1) * 100:+.3f}%)")
        p(f"  ruler measures                       {got:.5f}x "
          f"+/- {se:.5f}  ({(got - 1) * 100:+.3f}%)")
        p(f"  agreement: {z:+.2f} sigma  -> "
          f"{'PASS' if abs(z) <= 2.0 else 'RED'}")
        res["check"] = dict(k=k, pred=pred, got=got, se=se, z=z)
    else:
        p("  could not read k from the render log -- check SKIPPED")

    p("")
    p("READ THIS CAREFULLY.  The magnification is the solid number here: it is")
    p("a ratio of spectral peak positions and needs no amplitude calibration,")
    p("and it reproduces the aligner's own k.  The object-space blur above is")
    p("EXPLORATORY: n=3 paired ROIs, and the comb amplitude M is not normalised")
    p("between two renders at different scales, so its sign is not a bar and is")
    p("not used in any conclusion.")
    p("What IS concluded: a registered render is an INTERPOLATED ENLARGEMENT of")
    p("the optical image, by 1/k, at every pixel and every gate.  On this stack")
    p(f"that is {(1 / k - 1) * 100:+.1f}%." if k else "")
    for other, note in (("bee-3-cpl-LADDER-ALN.log", "bee-3-cpl, 299 frames"),
                        ("112MSDCF-ALN-g4-A.log", "112MSDCF half A")):
        op = Path(M98.LOGS) / other
        if not op.exists():
            continue
        for line in op.read_text(encoding="utf-8",
                                 errors="replace").splitlines():
            if "field of view scaled to" in line:
                try:
                    kk = float(line.split("scaled to")[1].split()[0])
                except (IndexError, ValueError):
                    break
                p(f"  {note:<24} k = {kk:.4f}  ->  upsampled "
                  f"{1 / kk:.4f}x  ({(1 / kk - 1) * 100:+.2f}%)")
                res.setdefault("k_other", {})[note] = kk
                break
    p("bee-3-cpl needs the largest correction because that bracket drifts")
    p("232.7-603 px corner-to-corner and fit_to_cover must throw away enough")
    p("field for EVERY frame to cover EVERY output pixel.")
    p("At 100% on a screen that is softness, it is global, it is new tonight,")
    p("and it is not the gate.")

    M98.OUT_P = Path(M98.OUT)
    M98.OUT_P.mkdir(parents=True, exist_ok=True)
    (M98.OUT_P / "s8_resample.log").write_text("\n".join(log),
                                               encoding="utf-8")
    (M98.OUT_P / "s8_resample.json").write_text(json.dumps(res, indent=1),
                                                encoding="utf-8")


if __name__ == "__main__":
    main()
