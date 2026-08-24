"""C1/C2/C3/C5 — is the sub-pixel shift estimator admissible?

Run BEFORE the real measurement. If any of these fails, the arm stops.

C2  null      : a crop against itself must read (0, 0)
C1  positive  : planted phase-ramp shifts must be recovered to 0.03 px
C3  crosscheck: skimage's upsampled-correlation estimator must agree to 0.05 px
C5  stimulus  : the planted shift is a pure phase ramp (exact translation), and
                this script shows what happens if you use an interpolating
                shift instead -- that is the mislabelled-stimulus trap.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m95c as C  # noqa: E402

BIN = os.path.join(C.OUT, "armF-f183.tif")
S = 256


def pick_detail_crops(g, n=6, s=S):
    """Highest-detail non-overlapping crops, by local gradient energy.

    Detail matters: a flat crop has no structure to register and the phase fit
    would be fitting noise. Choosing the crops by an objective criterion rather
    than by eye also keeps the selection out of my hands.
    """
    h, w = g.shape
    step = s
    cand = []
    for y in range(0, h - s, step):
        for x in range(0, w - s, step):
            t = g[y : y + s, x : x + s].astype(np.float64)
            e = float(np.mean(np.abs(np.diff(t, axis=0))) + np.mean(np.abs(np.diff(t, axis=1))))
            cand.append((e, y, x))
    cand.sort(reverse=True)
    return [(y, x) for _e, y, x in cand[:n]]


def main():
    img = C.load_tif(BIN)
    print("binned render: %s %s" % (img.shape, img.dtype))
    g = img[:, :, 1].astype(np.float64)
    crops = pick_detail_crops(g)
    print("detail crops (y,x): %s" % crops)

    results = {"crops": crops, "C1": [], "C2": [], "C3": [], "C5": []}
    ok = True

    # ---------------- C2: null ----------------
    print("\n== C2 null: a vs a ==")
    worst2 = 0.0
    for y, x in crops:
        a = C.crop(g, y, x, S)
        dy, dx, _rms = C.phase_ramp_shift(a, a)
        worst2 = max(worst2, abs(dy), abs(dx))
        results["C2"].append({"y": y, "x": x, "dy": dy, "dx": dx})
    print("worst |component| = %.6f px  (bar 0.01)" % worst2)
    c2ok = worst2 < 0.01
    ok &= c2ok
    print("C2: %s" % ("PASS" if c2ok else "FAIL"))

    # ---------------- C1: positive ----------------
    print("\n== C1 positive: planted phase-ramp shifts ==")
    plants = [(0.0, 0.0), (0.25, 0.25), (0.5, 0.5), (-0.5, -0.5), (0.75, -0.25), (0.1, 0.4)]
    worst1 = 0.0
    for py, px in plants:
        errs = []
        for y, x in crops:
            a = C.crop(g, y, x, S)
            b = C.shift_by(a, py, px)
            dy, dx, _ = C.phase_ramp_shift(a, b)
            errs.append((dy - py, dx - px))
        e = max(max(abs(u), abs(v)) for u, v in errs)
        worst1 = max(worst1, e)
        mdy = float(np.mean([dy for dy, _ in errs]))
        mdx = float(np.mean([dx for _, dx in errs]))
        print(
            "  planted (%+.2f, %+.2f)  worst err %.5f px   mean err (%+.5f, %+.5f)"
            % (py, px, e, mdy, mdx)
        )
        results["C1"].append(
            {"plant_dy": py, "plant_dx": px, "worst_err": e, "mean_err_dy": mdy, "mean_err_dx": mdx}
        )
    print("worst error over all plants = %.5f px  (bar 0.03)" % worst1)
    c1ok = worst1 < 0.03
    ok &= c1ok
    print("C1: %s" % ("PASS" if c1ok else "FAIL"))

    # ---------------- C3: independent cross-check ----------------
    print("\n== C3 cross-check vs skimage phase_cross_correlation ==")
    from skimage.registration import phase_cross_correlation

    worst3 = 0.0
    for py, px in plants:
        for y, x in crops[:3]:
            a = C.crop(g, y, x, S)
            b = C.shift_by(a, py, px)
            mine = C.phase_ramp_shift(a, b)[:2]
            # skimage returns the shift that must be applied to `b` to match
            # `a`, i.e. the negative of our convention.
            sk, _err, _p = phase_cross_correlation(a, b, upsample_factor=100)
            theirs = (-float(sk[0]), -float(sk[1]))
            d = max(abs(mine[0] - theirs[0]), abs(mine[1] - theirs[1]))
            worst3 = max(worst3, d)
            results["C3"].append(
                {
                    "plant": [py, px],
                    "y": y,
                    "x": x,
                    "mine": list(mine),
                    "skimage": list(theirs),
                    "delta": d,
                }
            )
    print("worst disagreement = %.5f px  (bar 0.05)" % worst3)
    c3ok = worst3 < 0.05
    ok &= c3ok
    print("C3: %s" % ("PASS" if c3ok else "FAIL"))

    # ---------------- C5: stimulus validity ----------------
    # Not a pass/fail gate on the arm; it is the demonstration of WHY the
    # stimulus is a phase ramp. An interpolating shift is a different operator:
    # it translates AND blurs, so the pair (a, b) is no longer related by a pure
    # translation and any translation estimator is being asked a question with
    # no exact answer.
    print("\n== C5 stimulus validity: phase ramp vs scipy.ndimage.shift ==")
    from scipy.ndimage import shift as ndshift

    for py, px in [(0.5, 0.5), (0.25, 0.25)]:
        y, x = crops[0]
        a = C.crop(g, y, x, S)
        b_ramp = C.shift_by(a, py, px)
        b_interp = ndshift(a, (py, px), order=3, mode="reflect")
        r = C.phase_ramp_shift(a, b_ramp)
        i = C.phase_ramp_shift(a, b_interp)
        # How much high-frequency energy the interpolating shift destroyed.
        hp_a = C.highpass(a, 2.0)
        hp_r = C.highpass(b_ramp, 2.0)
        hp_i = C.highpass(b_interp, 2.0)
        keep_r = float(np.std(hp_r) / np.std(hp_a))
        keep_i = float(np.std(hp_i) / np.std(hp_a))
        print(
            "  plant (%+.2f,%+.2f): ramp -> (%+.4f,%+.4f) HF %.4fx | "
            "ndimage -> (%+.4f,%+.4f) HF %.4fx"
            % (py, px, r[0], r[1], keep_r, i[0], i[1], keep_i)
        )
        results["C5"].append(
            {
                "plant": [py, px],
                "ramp": list(r[:2]),
                "ramp_hf_keep": keep_r,
                "ndimage": list(i[:2]),
                "ndimage_hf_keep": keep_i,
            }
        )

    results["verdict"] = {
        "C1_pass": bool(c1ok),
        "C2_pass": bool(c2ok),
        "C3_pass": bool(c3ok),
        "C1_worst_err_px": worst1,
        "C2_worst_px": worst2,
        "C3_worst_delta_px": worst3,
        "admissible": bool(ok),
    }
    C.jdump("c1_controls.json", results)
    print("\nINSTRUMENT ADMISSIBLE: %s" % ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
