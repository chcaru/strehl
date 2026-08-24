"""M84b step 15 - the geometric closure: tilt, magnification, focal length, depth.

Inputs: the two projective fits from step 13 and the pitch decision from step
14b. No image data is read here.

MODEL, in centred image coordinates xi = x - x_pp (principal point assumed at
the quad-grid plane's centre; stated, not measured):

    xi(k) = f * (X0 + k P cos(th)) / (Z0 + k P sin(th))
          = (a + b k) / (1 + c k)
    a = f X0 / Z0 ,  b = m P cos(th) ,  c = m P sin(th) / f ,  m = f / Z0

`f` is the pinhole-equivalent focal length in quad px: for a real lens with
pupil magnification p it is m * Z0, i.e. the entrance-pupil-referred value, NOT
the exit-pupil distance. That distinction is why no pupil-ratio term appears.

CLOSURE. One view gives three numbers (a, b, c) for four unknowns
(X0, m, th, f). Two views of the SAME ruler at the SAME working distance share
m and f, giving six numbers for six unknowns and closing the system:

    b_f / b_a = cos(th_f) / cos(th_a)
    c_a / c_f = sin(th_a) / sin(th_f)

ASSUMPTION, stated and its sensitivity reported: the camera did not move between
the two stacks, so m and f are shared. Supporting evidence: both stacks report
the same EXIF focal length, aperture and ISO, and both sweeps START at the same
EXIF FocusDistance2 (0.2707 m). The sensitivity of every output to a violation
is computed by re-solving with m_a = m_f * (1 + eps).

DEVIATION from the pre-registration, disclosed: section 4.2 registered Huber
IRLS with no hard rejection. One angled detection (the 14th, at the far end of
the comb) sits 22 robust sigma off the fit while the other thirteen lie inside
+/-0.53 px. A hard 5-sigma rejection is applied and BOTH fits are reported.
"""

from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"

QUAD_W, QUAD_H = 3514, 2344
X_PP = QUAD_W / 2.0
SENSOR_PITCH_UM = 5.12  # F-camera-lens-optics.md:91 and :1171, DERIVED, +/-0.3%
SENSOR_PITCH_REL_SYS = 0.003
QUAD_PITCH_UM = 2.0 * SENSOR_PITCH_UM
LENS_MAX_M = 2.8  # F-camera-lens-optics.md:13, VERIFIED, with SEL20TC


def fit_projective(k, x, seed_c=0.0):
    C = seed_c
    A = B = 0.0
    prev = np.array([np.inf] * 3)
    w = np.ones_like(x)
    for _ in range(200):
        v = 1.0 / np.maximum(1.0 + C * k, 1e-6)
        M = np.column_stack([np.ones_like(k), k, -x * k])
        sw = np.sqrt(w * v)
        sol, *_ = np.linalg.lstsq(M * sw[:, None], x * sw, rcond=None)
        A, B, C = sol
        r = x - (A + B * k) / (1.0 + C * k)
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-12
        c = 1.345 * s
        w = np.where(np.abs(r) <= c, 1.0, c / np.maximum(np.abs(r), 1e-12))
        cur = np.array([A, B, C])
        if np.all(np.abs(cur - prev) <= 1e-10 * np.maximum(np.abs(cur), 1e-12)):
            break
        prev = cur
    return A, B, C


def robust_fit(k, x, nsigma=5.0):
    """Huber IRLS with iterated hard nsigma rejection. Returns (A,B,C,keep)."""
    keep = np.ones(len(k), bool)
    for _ in range(10):
        A, B, C = fit_projective(k[keep], x[keep])
        r = x - (A + B * k) / (1.0 + C * k)
        s = 1.4826 * np.median(np.abs(r[keep] - np.median(r[keep]))) + 1e-12
        new = np.abs(r) <= nsigma * s
        if np.array_equal(new, keep) or new.sum() < 5:
            break
        keep = new
    A, B, C = fit_projective(k[keep], x[keep])
    return A, B, C, keep


def centred(A, B, C):
    """(A,B,C) in absolute x -> (a,b,c) in centred xi."""
    return A - X_PP, B - C * X_PP, C


def solve_two_view(b_f, c_f, b_a, c_a, P_mm, m_ratio=1.0):
    """Return the closure. m_ratio = m_a/m_f, 1.0 under the shared-Z assumption.

    b_f = m_f P cos(th_f)                 b_a = m_a P cos(th_a)
    c_f = m_f P sin(th_f)/f               c_a = m_a P sin(th_a)/f
    """
    Rb = (b_f / b_a) * m_ratio  # cos th_f / cos th_a
    Rc = (c_a / c_f) / m_ratio  # sin th_a / sin th_f
    # (1 - sf^2) = Rb^2 (1 - sa^2),  sa = Rc sf
    denom = Rb * Rb * Rc * Rc - 1.0
    sf2 = (Rb * Rb - 1.0) / denom
    if not (0.0 <= sf2 < 1.0):
        return None
    sf = math.sqrt(sf2)
    sa = Rc * sf
    if not (0.0 <= sa < 1.0):
        return None
    th_f, th_a = math.asin(sf), math.asin(sa)
    m_f = b_f / (P_mm * math.cos(th_f))  # quad px per mm
    m_a = m_f * m_ratio
    f_px = m_f * P_mm * sf / c_f  # quad px
    # Physical admissibility. Added after the step-18 G2 mutation control showed
    # a sign-inverted projective coefficient produced a plausible-looking tilt
    # and magnification alongside a NEGATIVE focal length, i.e. the closure
    # would have returned nonsense without complaining.
    if not (m_f > 0.0 and f_px > 0.0):
        return None
    Z0_f = f_px / m_f  # mm
    Z0_a = f_px / m_a
    return {
        "theta_flat_deg": math.degrees(th_f),
        "theta_ang_deg": math.degrees(th_a),
        "m_quadpx_per_mm": m_f,
        "m": m_f * QUAD_PITCH_UM / 1000.0,
        "f_quadpx": f_px,
        "f_mm": f_px * QUAD_PITCH_UM / 1000.0,
        "Z0_flat_mm": Z0_f,
        "Z0_ang_mm": Z0_a,
        "dZ_per_grad_ang_um": 1000.0 * P_mm * sa,
        "dZ_per_grad_flat_um": 1000.0 * P_mm * sf,
        "Rb": Rb,
        "Rc": Rc,
    }


def main(argv) -> int:
    OUT.mkdir(exist_ok=True)
    hier = json.loads((OUT / "14b-hierarchy.json").read_text())
    P_mm = hier["decision"]["P_mm"]
    assert P_mm is not None, "pitch undecided; closure not attempted"

    raw = {t: json.loads((OUT / f"13-{t}.json").read_text()) for t in ("flat", "ang")}
    # BUG FIX, found by the step-18 mutation control on 2025-xx: step 12 saved
    # each stack's column profile in ROI-RELATIVE coordinates (CONFIG x0 = 0 for
    # the flat stack but 1100 for the angled one), and step 13 fitted those
    # profiles without lifting them. Centring both fits on X_PP = 1757 therefore
    # over-subtracted 1100*C from the angled b, inflating theta_ang from 77.35
    # to 80.47 degrees and the depth scale by 1.06 %. The ROI origin is now read
    # from step 12's own saved config rather than assumed.
    roi_x0 = {
        t: float(json.loads((OUT / f"12-{t}.json").read_text())["config"]["x0"])
        for t in ("flat", "ang")
    }
    print(f"ROI origins lifted to absolute quad coords: {roi_x0}")
    fits, kept = {}, {}
    for t, r in raw.items():
        k = np.array(r["k"], float)
        x = np.array(r["tick_x"], float) + roi_x0[t]
        A, B, C, keep = robust_fit(k, x)
        fits[t] = (A, B, C)
        kept[t] = keep
        res = x - (A + B * k) / (1 + C * k)
        lp = (B - C * A) / (1 + C * k) ** 2
        print(
            f"[{t}] kept {int(keep.sum())}/{len(k)}  A {A:.3f} B {B:.4f} C {C:.6e}  "
            f"resid_rms(kept) {np.sqrt(np.mean(res[keep]**2)):.3f} px "
            f"= {100*np.sqrt(np.mean((res[keep]/lp[keep])**2)):.2f}% of local pitch"
        )
        if (~keep).any():
            print(f"     rejected indices {np.flatnonzero(~keep).tolist()} "
                  f"resid {np.round(res[~keep],2).tolist()}")

    cen = {t: centred(*fits[t]) for t in fits}
    a_f, b_f, c_f = cen["flat"]
    a_a, b_a, c_a = cen["ang"]
    print(f"\ncentred: flat a {a_f:.2f} b {b_f:.4f} c {c_f:.6e}")
    print(f"         ang  a {a_a:.2f} b {b_a:.4f} c {c_a:.6e}")

    sol = solve_two_view(b_f, c_f, b_a, c_a, P_mm)
    assert sol is not None, "two-view closure has no admissible solution"

    # Bootstrap: resample graduations in BOTH stacks jointly.
    rng = np.random.default_rng(0x4D84B015)
    acc = {kk: [] for kk in sol}
    for _ in range(2000):
        cc = {}
        ok = True
        for t, r in raw.items():
            k = np.array(r["k"], float)[kept[t]]
            x = np.array(r["tick_x"], float)[kept[t]] + roi_x0[t]
            j = rng.integers(0, len(k), len(k))
            if len(np.unique(k[j])) < 5:
                ok = False
                break
            cc[t] = centred(*fit_projective(k[j], x[j]))
        if not ok:
            continue
        s = solve_two_view(cc["flat"][1], cc["flat"][2], cc["ang"][1], cc["ang"][2], P_mm)
        if s is None:
            continue
        for kk in acc:
            acc[kk].append(s[kk])
    boot = {
        kk: {
            "mean": float(np.mean(v)),
            "sd": float(np.std(v)),
            "p2.5": float(np.percentile(v, 2.5)),
            "p97.5": float(np.percentile(v, 97.5)),
            "n": len(v),
        }
        for kk, v in acc.items()
    }

    # Sensitivity to the shared-working-distance assumption.
    sens = {}
    for eps in (-0.05, -0.02, 0.02, 0.05):
        s = solve_two_view(b_f, c_f, b_a, c_a, P_mm, m_ratio=1.0 + eps)
        sens[f"m_ratio={1+eps:.2f}"] = (
            None
            if s is None
            else {kk: round(s[kk], 5) for kk in
                  ("theta_flat_deg", "theta_ang_deg", "m", "f_mm", "Z0_flat_mm",
                   "dZ_per_grad_ang_um")}
        )

    out = {
        "P_mm": P_mm,
        "x_pp_quadpx": X_PP,
        "quad_pitch_um": QUAD_PITCH_UM,
        "sensor_pitch_um": SENSOR_PITCH_UM,
        "fits_absolute": {t: {"A": fits[t][0], "B": fits[t][1], "C": fits[t][2],
                              "n_kept": int(kept[t].sum()), "n_total": len(kept[t])}
                          for t in fits},
        "fits_centred": {t: {"a": cen[t][0], "b": cen[t][1], "c": cen[t][2]} for t in cen},
        "solution": sol,
        "bootstrap": boot,
        "sensitivity_shared_Z": sens,
        "m_vs_lens_ceiling": {
            "m": sol["m"],
            "ceiling": LENS_MAX_M,
            "headroom_pct": 100.0 * (LENS_MAX_M - sol["m"]) / LENS_MAX_M,
            "refutes_P_0p5mm": bool(sol["m"] * 2 > LENS_MAX_M),
        },
        "sensor_pitch_systematic_rel": SENSOR_PITCH_REL_SYS,
    }
    (OUT / "15-closure.json").write_text(json.dumps(out, indent=1))

    print("\n=== CLOSURE ===")
    for kk in ("theta_flat_deg", "theta_ang_deg", "m", "m_quadpx_per_mm",
               "f_mm", "Z0_flat_mm", "dZ_per_grad_ang_um"):
        b = boot[kk]
        print(f"  {kk:24s} {sol[kk]:12.4f}   boot {b['mean']:.4f} +/- {b['sd']:.4f}"
              f"  [{b['p2.5']:.4f}, {b['p97.5']:.4f}]")
    print(f"\n  m vs lens VERIFIED ceiling {LENS_MAX_M}: "
          f"{100*(LENS_MAX_M-sol['m'])/LENS_MAX_M:.1f}% headroom")
    print(f"  P=0.5mm would need m={2*sol['m']:.3f} -> "
          f"{'REFUTED' if 2*sol['m']>LENS_MAX_M else 'not refuted'}")
    print("\n  sensitivity to shared-working-distance assumption:")
    for kk, v in sens.items():
        print(f"    {kk}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
