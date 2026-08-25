"""M116-promotion — why the CB4 trap fired, settled on the pixels.

CB4 was pre-registered on the premise that lateral CA is radial, so the
correction must move nothing at the frame centre. It fired. Before explaining
that away I read the source, and the premise was MINE and it was WRONG:

  optics.rs:323   A7C2_FE100GM_2XTC_X4CPL.translation = (0.6294, -0.4240)
  optics.rs:251+  `compose` APPLIES it:  b -> (t.b.re*s + tx, t.b.im*s + ty)
  optics.rs:375   the translation-free variant `_RADIAL` exists but is NOT in
                  `PROFILES`, so it cannot be selected by key

So the shipped correction is a radial rescale, which does vanish at r = 0,
PLUS a uniform translation of red, which does not. |t| = 0.7589 plane px
everywhere in the frame, centre included.

The source declines to attribute that term: optics.rs:75 says "the radial
coefficient is lateral CA; the translation may be lattice, may be" something
else, and a test named `the_translation_is_not_claimed_to_be_optical` pins
that it stays documented as unattributed.

There were two candidate explanations and they differ in MAGNITUDE, so the
pixels can choose between them:

  (a) the documented translation term      -> |shift| = 0.7589 px
  (b) a violated precondition. `compose`'s docstring warns it "scales about
      the coordinate ORIGIN, not about the plane centre" and that feeding it
      absolute coordinates "would introduce a uniform red offset of order
      eps * half_diagonal ~ 1.5 sensels".

(b) is REFUTED at the source: `warpmap::gather_checked` computes
(cx, cy) = (w/2, h/2) and calls `t.apply_at(px, py, cx, cy)`, so coordinates
are already plane-centre-relative and the precondition holds. This script
confirms that independently, on the render, by measuring the shift.

Run: python ca_centre_shift.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from skimage.registration import phase_cross_correlation

CA = Path(r"C:\dev\strehl-out\M116\ca")

# optics.rs:323, read at the pinned SHA. Plane px.
TX, TY = 0.6294, -0.4240
TMAG = float(np.hypot(TX, TY))

SUBJECTS = ["bee-3-cpl", "flat-on-ruler-cpl",
            "tweezers-cpl", "flower-bud-with-background-fern-cpl"]
WIN = 512          # central window side, in output px
UPSAMPLE = 100     # 0.01 px resolution


def central(a: np.ndarray, ch: int) -> np.ndarray:
    h, w = a.shape[:2]
    cy, cx = h // 2, w // 2
    r = WIN // 2
    return a[cy - r:cy + r, cx - r:cx + r, ch].astype(np.float64)


def shift_of(ref: np.ndarray, mov: np.ndarray):
    """Sub-pixel shift of `mov` relative to `ref`, in (dy, dx) output px."""
    s, _, _ = phase_cross_correlation(ref, mov, upsample_factor=UPSAMPLE,
                                      normalization=None)
    return float(s[0]), float(s[1])


def main() -> int:
    rows = []
    for s in SUBJECTS:
        p_off, p_on = CA / "measure" / f"{s}__OFF.tif", CA / "measure" / f"{s}__ON.tif"
        if not (p_off.exists() and p_on.exists()):
            print(f"  {s}: missing renders, skipped")
            continue
        off, on = tifffile.imread(p_off), tifffile.imread(p_on)

        # Red, the channel the profile moves most.
        dy_r, dx_r = shift_of(central(off, 0), central(on, 0))
        # Green, the reference channel: eps is zero for it, so it must not move.
        dy_g, dx_g = shift_of(central(off, 1), central(on, 1))

        # The output plane is the BINNED plane -- one output px per 2x2 CFA
        # quad -- and the profile's translation is quoted in PLANE px, which is
        # the same grid the deinterleaved sites live on. So no rescale.
        mag_r = float(np.hypot(dy_r, dx_r))
        rows.append({
            "subject": s,
            "red_dy": dy_r, "red_dx": dx_r, "red_mag": mag_r,
            "green_dy": dy_g, "green_dx": dx_g,
            "green_mag": float(np.hypot(dy_g, dx_g)),
            "predicted_mag": TMAG,
            "abs_err_px": abs(mag_r - TMAG),
        })
        print(f"{s:<38} red shift (dx,dy) = ({dx_r:+.4f}, {dy_r:+.4f}) px"
              f"  |d| = {mag_r:.4f}   predicted {TMAG:.4f}"
              f"   err {abs(mag_r - TMAG):.4f}")
        print(f"{'':<38} green shift        = ({dx_g:+.4f}, {dy_g:+.4f}) px"
              f"  |d| = {np.hypot(dy_g, dx_g):.4f}  (must be ~0)")

    if rows:
        med = float(np.median([r["red_mag"] for r in rows]))
        print(f"\nmedian measured red shift at the frame centre : {med:.4f} px")
        print(f"translation term in optics.rs:323             : {TMAG:.4f} px")
        print(f"the 'absolute coordinates' failure mode would be ~1.5 px")
        verdict = ("(a) the documented translation term"
                   if abs(med - TMAG) < 0.15 else
                   "NEITHER cleanly -- report as unresolved")
        print(f"VERDICT: {verdict}")
        (CA / "centre-shift.json").write_text(
            json.dumps({"predicted_mag_px": TMAG, "rows": rows,
                        "median_red_mag_px": med, "verdict": verdict},
                       indent=2), encoding="utf-8")
        print(f"wrote {CA / 'centre-shift.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
