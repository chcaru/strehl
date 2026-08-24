"""S10 -- determinism, the negative controls, and whether the binned default
throws away resolution the sensor actually captured.

R5  the same command must produce the same bytes.
R6  three negative controls, each built so that a working harness MUST reject
    it. If any of them passes, every positive result in this milestone is void.
R7  G1 - G2. The two green photosites in a quad sit one sensor pixel apart on
    the diagonal. Binning averages them. If the scene were band-limited to the
    binned Nyquist their difference would be pure noise, and the noise level is
    known from the profile. Any excess is real detail the default output
    discards -- and, being above the binned Nyquist, folds.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m93lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")
MERGED = os.path.join(L.OUT, "armM-gate0-binlin.tif")
BLACK, RANGE = 512.0, 14848.0
WIN = 512
GAIN, READ_E = 0.224103, 4.20


def to_u16(g):
    return np.floor(np.clip((g - BLACK) / RANGE, 0, 1) * 65535.0 + 0.5).astype(np.uint16)


def main() -> int:
    rois = json.load(open(os.path.join(OUTDIR, "s2b_rois.json"), encoding="utf-8"))["chosen"]
    focus = json.load(open(os.path.join(OUTDIR, "s3_focus.json"), encoding="utf-8"))["res"]
    armf = json.load(open(os.path.join(OUTDIR, "s4_armF.json"), encoding="utf-8"))["binlin"]
    merged = L.read_tif_green(MERGED)
    cube = np.load(os.path.join(L.OUT, "m93_crops_v2.npy"), mmap_mode="r")
    out = {}

    print("=" * 78)
    print("R5 -- determinism")
    print("=" * 78)
    sha0 = L.sha256(MERGED)
    rep = os.path.join(L.OUT, "armM-gate0-binlin-REPEAT.tif")
    if not os.path.exists(rep):
        L.run_strehl(["stack", L.STACK, "-o", rep, "--gate", "0"], align="0")
    sha1 = L.sha256(rep)
    print(f"  original : {sha0}")
    print(f"  repeat   : {sha1}")
    print(f"  R5 VERDICT: {'PASS' if sha0 == sha1 else 'FAIL'}")
    out["R5"] = dict(sha_original=sha0, sha_repeat=sha1, verdict="PASS" if sha0 == sha1 else "FAIL")
    assert sha0 == sha1

    print()
    print("=" * 78)
    print("R6 -- negative controls. Each MUST fail. If one passes, nothing above holds.")
    print("=" * 78)
    nm = "ROI-LOWDRIFT"
    x, y = rois[nm]["x"], rois[nm]["y"]
    kk = list(rois).index(nm)
    elected = np.load(os.path.join(L.OUT, f"m93_elected_{nm}.npy"))
    m = merged[y : y + WIN, x : x + WIN]
    r6 = {}

    # R6a -- a frame that was NOT elected anywhere in this ROI.
    counts = np.bincount(elected[elected >= 0].ravel(), minlength=299)
    unelected = int(np.argmin(counts))
    fr = L.read_tif_green(armf[str(183)]["tif"])[y : y + WIN, x : x + WIN]
    pred_un = to_u16(np.asarray(cube[unelected, kk], dtype=np.float64))
    ex_un = float((pred_un == m).mean())
    sel = elected == 183
    ex_el = float((fr[sel] == m[sel]).mean())
    print(f"  R6a  frame 183 (elected on {int(sel.sum())} px) matches there : {100*ex_el:8.4f}%  <- must be ~100")
    print(f"       frame {unelected} (elected on {counts[unelected]} px) matches ROI-wide: "
          f"{100*ex_un:8.4f}%  <- must be ~0")
    ok_a = ex_el > 0.999 and ex_un < 0.05
    print(f"       R6a VERDICT: {'PASS (harness discriminates)' if ok_a else 'FAIL'}")
    r6["a"] = dict(elected_exact=ex_el, unelected_exact=ex_un, unelected_frame=unelected,
                   verdict="PASS" if ok_a else "FAIL")

    # R6b -- the same merged data, shifted one pixel. Nothing should match.
    m_shift = merged[y : y + WIN, x + 1 : x + 1 + WIN]
    pred = to_u16(np.asarray(cube[:, kk], dtype=np.float64))
    any_shift = float(((pred == m_shift[None]).sum(axis=0) > 0).mean())
    any_true = float(((pred == m[None]).sum(axis=0) > 0).mean())
    print(f"  R6b  correct registration : {100*any_true:8.4f}% of px match some frame  <- must be ~100")
    print(f"       shifted by ONE pixel : {100*any_shift:8.4f}% of px match some frame  <- must collapse")
    ok_b = any_true > 0.99 and any_shift < 0.5
    print(f"       R6b VERDICT: {'PASS' if ok_b else 'FAIL'}   "
          f"(collapse factor {any_true/max(any_shift,1e-9):.1f}x)")
    r6["b"] = dict(true=any_true, shifted=any_shift, verdict="PASS" if ok_b else "FAIL")

    # R6c -- plant a 3 DN offset in a 64x64 patch and require detection.
    m_bad = m.copy()
    m_bad[100:164, 100:164] += 3.0
    n_before = int((pred == m[None]).sum(axis=0).reshape(WIN, WIN)[100:164, 100:164].sum())
    n_after = int((pred == m_bad[None]).sum(axis=0).reshape(WIN, WIN)[100:164, 100:164].sum())
    print(f"  R6c  planted +3 DN on a 64x64 patch: candidate matches in the patch "
          f"{n_before} -> {n_after}  <- must collapse")
    ok_c = n_after < 0.1 * n_before
    print(f"       R6c VERDICT: {'PASS' if ok_c else 'FAIL'}")
    r6["c"] = dict(before=n_before, after=n_after, verdict="PASS" if ok_c else "FAIL")
    out["R6"] = r6
    assert ok_a and ok_b and ok_c

    print()
    print("=" * 78)
    print("R7 -- G1 - G2: detail the binned default averages away")
    print("=" * 78)
    paths = sorted(
        os.path.join(L.STACK, f) for f in os.listdir(L.STACK) if f.lower().endswith(".arw")
    )
    r7 = {}
    for nm2 in list(rois):
        pk = focus[nm2]["peak_frame"]
        rf = L.decode_raw(paths[pk])
        cfa = rf.cfa.astype(np.float64)
        g1 = cfa[0::2, 1::2]
        g2 = cfa[1::2, 0::2]
        h = min(g1.shape[0], g2.shape[0])
        w = min(g1.shape[1], g2.shape[1])
        x2, y2 = rois[nm2]["x"], rois[nm2]["y"]
        a = g1[y2 : y2 + WIN, x2 : x2 + WIN]
        b = g2[y2 : y2 + WIN, x2 : x2 + WIN]
        d = 0.5 * (a - b)
        s = 0.5 * (a + b)
        sig = float(s.mean() - BLACK)
        var_site = GAIN * sig + (READ_E * GAIN) ** 2
        pred_sd = np.sqrt(var_site / 2.0)  # sd of (G1-G2)/2, rho = 0
        meas_sd = float(d.std())
        r7[nm2] = dict(frame=pk, signal_dn=sig, pred_sd=float(pred_sd), meas_sd=meas_sd,
                       ratio=meas_sd / float(pred_sd),
                       excess_var_frac=float(1 - (pred_sd**2) / meas_sd**2))
        print(f"  {nm2:<14} frame {pk:3d}  signal {sig:7.1f} DN | "
              f"(G1-G2)/2 sd: model {pred_sd:6.2f} DN, measured {meas_sd:7.2f} DN "
              f"-> {meas_sd/pred_sd:5.2f}x | "
              f"{100*r7[nm2]['excess_var_frac']:5.1f}% of that variance is scene, not noise")
    out["R7"] = r7
    det = [r7[n]["ratio"] for n in r7 if n != "ROI-FLAT"]
    print()
    print(f"  detail ROIs {min(det):.2f}-{max(det):.2f}x the noise model; "
          f"flat control {r7['ROI-FLAT']['ratio']:.2f}x")
    print("  The flat control is the discriminator: it is the same sensor, same")
    print("  binning, same noise -- and it is defocused, so it has no sub-quad detail.")

    dst = os.path.join(OUTDIR, "s10_controls.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote          : {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
