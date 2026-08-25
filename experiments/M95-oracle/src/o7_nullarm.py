"""O7 -- the null arm, and a planted truth. PRE-REGISTERED; committed before run.

WHY THIS EXISTS. o5 measured D = +1.3343 / +2.8310 / +2.7989 % on the three
detail ROIs, against a one-frame sensitivity of +11.5 to +13.0 %. But its flat
control fired at +1.6251 % against a pre-registered bar of |flat| < 1 %, so some
of D is not election error. o6 tested my own first hypothesis -- that the floor
is the elector's sigma divisor -- and REFUTED it: moving the divisor onto the
oracle changed the flat floor by +0.0998 pp of +1.6251 %. So the floor is real
and I do not yet know what it is.

ROI-FLAT is also the wrong null. It has contrast 1.18 and no detail, so it does
not merely remove focus dependence, it removes the thing being elected. A floor
measured there is not obviously the floor operating on a detailed ROI.

THE NULL THIS SCRIPT BUILDS instead keeps everything except the answer:

  ARM A   real detail, real per-frame LEVEL variation, real noise magnitude,
          299 frames -- but every frame carries the SAME scene, so no frame is
          sharper than any other. Any D here is floor by construction.
  ARM A2  identical, except every frame is put at the same level. The only
          remaining difference between frames is the noise realisation, so D
          here is pure argmax-on-noise disagreement. A minus A2 is the level
          contribution, isolated.
  ARM B   the same scene with a planted focus ramp, sigma_f = rate*|f - f0|,
          applied by fft_blur (o3c showed scipy.ndimage is wrong by up to
          7.94 % at sigma=0.25 and this is exactly that regime). The true best
          frame is then EXACTLY f0 at every pixel, so election error can be
          read directly in frames with no yardstick at all.

STATED LIMITATION, not discovered afterwards. The scene S is built from one real
frame, so it carries that frame's own noise at variance v/2. Under arm B that
embedded noise is blurred along with the scene, so it peaks at f0 too and makes
the planted peak easier to find than a real one. It inflates findability for
BOTH rules, so the elector-minus-oracle difference is a LOWER bound on real
election error. P5b bounds the inflation by pre-smoothing S.

PRE-REGISTERED BARS. Written before any of these numbers existed.

  N4   D_null (arm A) per ROI.
  N4b  D_flat (arm A2) per ROI.
  P5   mean |argmax - f0| for each rule, arm B, rates 0.05 and 0.20 px/frame.
  P5b  P5 repeated on LOWDRIFT with S pre-smoothed by sigma=0.8.

  VERDICT ON THE ELECTION, decided by (D_real - D_null) on the three detail ROIs
  where D_real is o5's headline:

    < +0.5 pp on all three          -> the o5 deficit is instrument floor. The
                                       election is exonerated to that bound and
                                       election error is below this instrument's
                                       resolution.
    > +1.0 pp on two or more        -> real election error of that size. Convert
                                       to frames with o5's P1r yardstick.
    otherwise                       -> BOUNDED, not resolved.

  KILL SWITCH, checked first. At rate 0.20 px/frame the ORACLE's mean |offset
  from f0| must be < 25 frames. It was handed a peak; if it cannot find one the
  instrument is retired and NO verdict is issued from this script.

  P5 HEADLINE, independent of D entirely: elector mean |offset| minus oracle
  mean |offset|, in frames, at each rate. If the elector is more than 2 frames
  worse than the oracle at rate 0.20, that is direct evidence of election error
  that does not pass through the deficit statistic at all.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import o2lib as O  # noqa: E402
from o3_commission import CUBE, OUTD, fft_blur  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROIS = ["ROI-LOWDRIFT", "ROI-MIDDRIFT", "ROI-HIGHDRIFT", "ROI-FLAT"]
D_REAL = {"ROI-LOWDRIFT": 1.3343, "ROI-MIDDRIFT": 2.8310,
          "ROI-HIGHDRIFT": 2.7989, "ROI-FLAT": 1.6251}
RATES = [0.05, 0.20]
SEED = 20250824


def synth(scene, black, level, noise, sigma, seed):
    """One synthetic frame pair. Blur the SIGNAL, then add noise -- optics, then sensor."""
    s = scene * level
    if sigma > 0.0:
        s = fft_blur(s, sigma)
    s = s + black
    sd = np.sqrt(noise.var(s))
    r1 = np.random.default_rng(seed)
    r2 = np.random.default_rng(seed + 500000)
    return s + r1.normal(0.0, 1.0, s.shape) * sd, s + r2.normal(0.0, 1.0, s.shape) * sd


def run_arm(scene, black, levels, noise, n, sigmas, seed0):
    """Selection argmaxes on G1, evaluation scores gathered on G2. Two passes."""
    be = bo = ae = ao = None
    for f in range(n):
        a, _ = synth(scene, black, levels[f], noise, sigmas[f], seed0 + f)
        se = O.elector_score(a, noise)
        so = O.oracle_score(a, noise)
        if be is None:
            be, bo = se.copy(), so.copy()
            ae = np.zeros(se.shape, dtype=np.int32)
            ao = np.zeros(so.shape, dtype=np.int32)
        else:
            m = se > be
            be[m], ae[m] = se[m], f
            m = so > bo
            bo[m], ao[m] = so[m], f
    ve = np.zeros(ae.shape, dtype=np.float64)
    vo = np.zeros(ao.shape, dtype=np.float64)
    for f in range(n):
        _, b = synth(scene, black, levels[f], noise, sigmas[f], seed0 + f)
        s = O.oracle_score(b, noise)
        m = ae == f
        if m.any():
            ve[m] = s[m]
        m = ao == f
        if m.any():
            vo[m] = s[m]
    d = 1.0 - float(ve.mean()) / float(vo.mean())
    return dict(D_pct=d * 100.0, ae=ae, ao=ao,
                same_pct=float(np.mean(ae == ao)) * 100.0)


def main() -> int:
    t0 = time.time()
    meta = json.load(open(os.path.join(CUBE, "cube_meta.json"), encoding="utf-8"))
    n, black = meta["n"], meta["black"]

    f1 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g1.npy"), mmap_mode="r")[::12],
                    dtype=np.float64)
    f2 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g2.npy"), mmap_mode="r")[::12],
                    dtype=np.float64)
    noise, fit = O.fit_noise(f1.reshape(-1, f1.shape[-1]), f2.reshape(-1, f2.shape[-1]), black)
    print(f"noise model: {noise}  R^2={fit['r2']:.5f}")
    del f1, f2

    f0 = n // 2
    res = {"n": n, "f0": f0, "rois": {}}

    for ri, nm in enumerate(ROIS):
        print("\n" + "=" * 74)
        print(nm)
        g1 = np.load(os.path.join(CUBE, f"{nm}.g1.npy"), mmap_mode="r")
        g2 = np.load(os.path.join(CUBE, f"{nm}.g2.npy"), mmap_mode="r")

        lv = np.array([float(np.asarray(g1[f], dtype=np.float64).mean()) - black
                       for f in range(n)])
        best, bi = -1e30, 0
        for f in range(0, n, 4):
            s = float(O.oracle_score(np.asarray(g1[f], dtype=np.float64), noise).mean())
            if s > best:
                best, bi = s, f
        scene = (np.asarray(g1[bi], dtype=np.float64)
                 + np.asarray(g2[bi], dtype=np.float64)) * 0.5 - black
        levels = lv / lv[bi]
        print(f"  scene from frame {bi}   level spread {100*(lv.max()/lv.min()-1):.2f} %"
              f"   contrast {scene.max()/max(scene.mean(),1e-9):.2f}")
        del g1, g2

        zero = np.zeros(n)
        seedr = SEED + ri * 1000000

        a = run_arm(scene, black, levels, noise, n, zero, seedr)
        a2 = run_arm(scene, black, np.ones(n), noise, n, zero, seedr + 7000)
        print(f"  N4   arm A  level-varying null   D = {a['D_pct']:+.4f} %"
              f"   agree {a['same_pct']:.2f} %")
        print(f"  N4b  arm A2 level-flattened null D = {a2['D_pct']:+.4f} %"
              f"   agree {a2['same_pct']:.2f} %")
        print(f"       level contribution to floor = {a['D_pct']-a2['D_pct']:+.4f} pp")

        dr = D_REAL[nm]
        print(f"  D_real (o5) {dr:+.4f} %   minus D_null {a['D_pct']:+.4f} %"
              f"   = {dr-a['D_pct']:+.4f} pp")

        bres = []
        for rate in RATES:
            sg = np.array([rate * abs(f - f0) for f in range(n)])
            b = run_arm(scene, black, levels, noise, n, sg, seedr + 13000)
            oe = float(np.mean(np.abs(b["ae"] - f0)))
            oo = float(np.mean(np.abs(b["ao"] - f0)))
            me = float(np.median(np.abs(b["ae"] - f0)))
            mo = float(np.median(np.abs(b["ao"] - f0)))
            bres.append(dict(rate=rate, D_pct=b["D_pct"],
                             elector_mean_off=oe, oracle_mean_off=oo,
                             elector_med_off=me, oracle_med_off=mo,
                             gap_frames=oe - oo, same_pct=b["same_pct"]))
            print(f"  P5   rate {rate:.2f} px/frame  |off from f0|: elector "
                  f"mean {oe:7.3f} med {me:5.1f} | oracle mean {oo:7.3f} med {mo:5.1f}"
                  f"  gap {oe-oo:+.3f} frames   D {b['D_pct']:+.4f} %")

        entry = dict(scene_frame=bi, level_spread_pct=100 * (lv.max() / lv.min() - 1),
                     N4_D_pct=a["D_pct"], N4_agree=a["same_pct"],
                     N4b_D_pct=a2["D_pct"], N4b_agree=a2["same_pct"],
                     level_pp=a["D_pct"] - a2["D_pct"],
                     D_real_pct=dr, excess_pp=dr - a["D_pct"], planted=bres)

        if nm == "ROI-LOWDRIFT":
            sm = fft_blur(scene, 0.8)
            sg = np.array([0.20 * abs(f - f0) for f in range(n)])
            b = run_arm(sm, black, levels, noise, n, sg, seedr + 21000)
            oe = float(np.mean(np.abs(b["ae"] - f0)))
            oo = float(np.mean(np.abs(b["ao"] - f0)))
            print(f"  P5b  scene pre-smoothed sigma=0.8, rate 0.20: elector mean "
                  f"{oe:7.3f} | oracle mean {oo:7.3f}  gap {oe-oo:+.3f} frames")
            entry["p5b"] = dict(elector_mean_off=oe, oracle_mean_off=oo,
                                gap_frames=oe - oo, D_pct=b["D_pct"])

        res["rois"][nm] = entry
        del a, a2

    print("\n" + "=" * 74)
    steep = [res["rois"][r]["planted"][-1] for r in ROIS]
    worst_oracle = max(s["oracle_mean_off"] for s in steep)
    print(f"KILL SWITCH: worst oracle mean |offset| at rate 0.20 = "
          f"{worst_oracle:.3f} frames (bar: < 25)")
    if worst_oracle >= 25.0:
        print("INSTRUMENT RETIRED -- the oracle cannot find a peak it was given.")
        res["verdict"] = "INSTRUMENT RETIRED"
    else:
        det = [r for r in ROIS if r != "ROI-FLAT"]
        ex = [res["rois"][r]["excess_pp"] for r in det]
        print(f"excess (D_real - D_null) on detail ROIs = "
              f"{['%+.4f pp' % e for e in ex]}")
        if all(e < 0.5 for e in ex):
            v = "FLOOR -- ELECTION EXONERATED TO THIS BOUND"
        elif sum(1 for e in ex if e > 1.0) >= 2:
            v = "REAL ELECTION ERROR"
        else:
            v = "BOUNDED, NOT RESOLVED"
        print(f"N4 VERDICT: {v}")
        res["verdict"] = v
        gaps = [s["gap_frames"] for s in steep]
        print(f"P5 gaps at rate 0.20 (elector minus oracle, frames) = "
              f"{['%+.3f' % g for g in gaps]}  bar: > 2 frames is direct evidence")

    print(f"\nelapsed {time.time()-t0:.1f} s")
    with open(os.path.join(OUTD, "o7_nullarm.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=float)
    print(f"wrote {os.path.join(OUTD, 'o7_nullarm.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
