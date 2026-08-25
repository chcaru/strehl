"""M95 arm 13g -- closing arithmetic. No new experiment, no new free parameter.

This script introduces NO new bar and NO new fitted quantity. Every input is a
number already printed by a registered arm in this session, and every output is
arithmetic over those numbers plus the x16_tiles.npz cache. It exists because two
things were left dangling and both are answerable without another decode.

DANGLING THING 1 -- arm 13f's F1 FAILED. The detail tiles span 2092.9-14171.2 DN
and the calibration set spans 3208.7-14930.9 DN, so the low end is extrapolated
and the headline currently carries the word EXTRAPOLATED. That is a real defect
but it is a BOUNDED one: I can simply drop the detail tiles that fall outside the
calibration range and see whether the headline moves. If it does not, the
extrapolation is harmless and I can say so with a number instead of a hope.

DANGLING THING 2 -- p = 1.0751 is GREATER THAN 1, and I owe an account of that.
For a sensor, in-band noise power is

    P(L) = read + shot*L + prnu*L^2

Read noise is level-independent and DRAGS THE LOG-LOG SLOPE BELOW 1. Photo
response non-uniformity is proportional to L^2 and pushes it ABOVE 1. Measuring
p = 1.0751 therefore says PRNU-like multiplicative structure slightly outweighs
read noise in this band, which is exactly what one expects at ISO 100 on a
well-exposed frame -- and it means the two competing mechanisms are BOUNDED IN
OPPOSITE DIRECTIONS, which is what makes arm 13f's F3 threshold usable.

That matters because arm 13f showed the verdict only flips if p drops to 0.90,
which is 29.9 standard errors below the fit. The only physical mechanism that
pushes p below 1 is read noise, and arm 13 already measured its size directly:
a dark frame's in-band power against a detail tile's. That measurement bounds how
far below 1 p can possibly be pulled, so the question "could p really be 0.90?"
has an answer from data rather than from argument.

Some caution is owed in the other direction too, and it is stated here rather
than hidden. If part of the p > 1 excess is not PRNU but residual scene structure
in the never-focusing tiles -- brighter background having more surviving in-band
structure -- then the correction is slightly too aggressive and S_detail is
slightly UNDERSTATED. The p = 1 row is the guard against that: it is the value p
takes if every multiplicative effect, real or spurious, is removed.
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")


def jload(name):
    with open(os.path.join(OUT, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


def main():
    x11, x15, x16 = jload("x11_bandsignal.json"), jload("x15_defocusptc.json"), jload("x16_robust.json")
    z = np.load(os.path.join(OUT, "x16_tiles.npz"))
    P, L, ng = z["P"], z["L"], int(z["ng"])
    p_hat, se = x16["p_hat"], x16["p_se"]

    print("=" * 78)
    print("M95 arm 13g -- closing arithmetic over already-registered artifacts")
    print("=" * 78)

    print("\n[1] Arm 13f's F1 extrapolation FAILURE, bounded rather than argued")
    cal_lo, cal_hi = x16["cal_L_min"], x16["cal_L_max"]
    Pd, Ld = P[:, ng:], L[:, ng:]
    order = np.argsort(Pd, axis=0)
    i_max, i_min = order[-1, :], order[0, :]
    ar = np.arange(Pd.shape[1])
    R = Pd[i_min, ar] / Pd[i_max, ar]
    ratL = Ld[i_max, ar] / Ld[i_min, ar]
    S_all = 1.0 - R * ratL ** p_hat
    inside = (Ld[i_min, ar] >= cal_lo) & (Ld[i_min, ar] <= cal_hi) & \
             (Ld[i_max, ar] >= cal_lo) & (Ld[i_max, ar] <= cal_hi)
    n_in, n_all = int(inside.sum()), len(ar)
    print(f"    calibration range {cal_lo:.1f} - {cal_hi:.1f} DN")
    print(f"    {n_in} of {n_all} detail tiles lie entirely inside it "
          f"({100.0 * n_in / n_all:.1f}%)")
    print(f"    S_detail, all {n_all} tiles          {float(np.median(S_all)):+.4f}")
    print(f"    S_detail, {n_in} interpolated tiles  {float(np.median(S_all[inside])):+.4f}")
    print(f"    movement from dropping the extrapolated tiles: "
          f"{abs(float(np.median(S_all[inside])) - float(np.median(S_all))):.4f}")

    print("\n[2] How far below 1 can p be dragged? Read noise, measured not assumed")
    pd_det, pd_dark = x11["partD"]["band_power_detail"], x11["partD"]["band_power_dark"]
    f_read = pd_dark / pd_det
    print(f"    arm 13 in-band power, 40 detail tiles : {pd_det:.4e}")
    print(f"    arm 13 in-band power, dark frame      : {pd_dark:.4e}")
    print(f"    read-noise fraction of in-band power  : {f_read:.3e} "
          f"({100.0 * f_read:.4f}%)")
    print(f"    P(L) = read + shot*L + prnu*L^2, so read noise alone bounds the")
    print(f"    log-log slope at p >= 1 - f_read = {1.0 - f_read:.6f}")
    p20 = x16["F3_p_at_0.20"]
    need = 1.0 - p20
    print(f"    arm 13f: the verdict only flips at p = {p20:+.4f}, i.e. a drag of "
          f"{need:.4f} below 1")
    print(f"    required drag / measured read-noise bound = {need / f_read:.0f}x")
    print(f"    -> reaching p = {p20:.2f} needs a level-independent noise term "
          f"{need / f_read:.0f}x larger")
    print(f"       than the one the dark frame actually shows.")

    print("\n[3] The verdict across every level model considered this session")
    rows = [("p = 0     M-none, refuted at 95% by arm 13e", x16["F3_S_at_p0"]),
            ("p = 1     pure shot noise, read/PRNU free ", x16["F3_S_at_p1"]),
            ("p = 1.0751 measured, arm 13e/13f          ", x16["S_detail"])]
    for name, v in rows:
        tag = "NOISE-DOMINATED" if v <= 0.20 else "REAL SIGNAL" if v >= 0.50 else "PARTIAL"
        print(f"    {name}  S_detail {v:+.4f}   [{tag}]")
    lo, hi = x15["S_detail_ci"]
    print(f"    95% CI on p propagated into S_detail: [{lo:+.4f}, {hi:+.4f}]")

    print("\n[4] What this says about the +0.1160 dex figure")
    frac = float(np.median(S_all))
    print(f"    fraction of 0.30-0.48 cyc/px band power that is real subject "
          f"detail: {100.0 * frac:.1f}%")
    print(f"    fraction that is sensor noise + demosaic response to noise: "
          f"{100.0 * (1.0 - frac):.1f}%")
    print(f"    the band the kernel gain was scored on is therefore "
          f"{100.0 * (1.0 - frac):.0f}% noise")

    J = {"n_detail_tiles": n_all, "n_interpolated": n_in,
         "S_all": float(np.median(S_all)), "S_interpolated": float(np.median(S_all[inside])),
         "S_extrap_movement": float(abs(np.median(S_all[inside]) - np.median(S_all))),
         "band_power_detail": pd_det, "band_power_dark": pd_dark,
         "read_fraction": f_read, "p_lower_bound_from_read": 1.0 - f_read,
         "p_at_flip": p20, "drag_required": need, "drag_over_read_bound": need / f_read,
         "S_at_p0": x16["F3_S_at_p0"], "S_at_p1": x16["F3_S_at_p1"],
         "S_at_phat": x16["S_detail"], "S_ci": [lo, hi],
         "signal_pct": 100.0 * frac, "noise_pct": 100.0 * (1.0 - frac)}
    with open(os.path.join(OUT, "x17_close.json"), "w", encoding="utf-8") as fh:
        json.dump(J, fh, indent=1)
    print("\nwrote out/x17_close.json")


if __name__ == "__main__":
    main()
