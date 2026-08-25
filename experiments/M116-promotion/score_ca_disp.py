"""M116-promotion — campaign 4b: lateral CA measured as a DISPLACEMENT.

Contract: prereg-ca2.txt, committed at bc38182 before this scored anything.

Campaign 4's chroma-excess metric failed its own registered plant (CB3) because
its baseline can go negative on a strongly coloured subject. Lateral CA is a
displacement, so this measures the displacement: the sub-pixel shift of R
against G, per radius annulus, per azimuthal sector, projected on the radial
direction. Phase correlation keys on structure, so subject colour cannot
masquerade as a fringe, and the quantity has a true zero.

Reads LINEAR renders only.

Run: python score_ca_disp.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage
from scipy.ndimage import uniform_filter
from skimage.registration import phase_cross_correlation

CA = Path(r"C:\dev\strehl-out\M116\ca")
PIN = "4beac7300e318f6f0aaf10b6a88e57f311b9e814"

SUBJECTS = ["bee-3-cpl", "flat-on-ruler-cpl",
            "tweezers-cpl", "flower-bud-with-background-fern-cpl"]
TRANSFER = {"tweezers-cpl", "flower-bud-with-background-fern-cpl"}

# Annuli in normalised radius. The first is the CD2 trap; 0.55-0.788 is the
# fitted support (M110 fact 56); beyond 0.788 the profile extrapolates.
ANNULI = [(0.00, 0.12), (0.12, 0.30), (0.30, 0.45), (0.45, 0.55),
          (0.55, 0.67), (0.67, 0.788), (0.788, 0.90), (0.90, 1.00)]
SUPPORT = (0.55, 0.788)
NSECT = 8
WIN = 384          # sector window side, output px
UPSAMPLE = 100     # 0.01 px
MIN_STRUCT = 8.0   # a window flatter than this carries no registration info
COH_MIN = 0.6
TENSOR_SIGMA = 2.0
HP_BOX = 5
MIN_PIX = 20000
PLANT_PX = 0.50


def load(p: Path) -> np.ndarray:
    a = tifffile.imread(p)
    assert a.ndim == 3 and a.shape[2] == 3, f"{p} is {a.shape}"
    return a.astype(np.float32)


def lum(a):
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def highpass(p):
    assert p.ndim == 2
    return p - uniform_filter(p, size=HP_BOX, mode="nearest")


def oriented(g):
    gy, gx = np.gradient(g.astype(np.float32))
    jxx = ndimage.gaussian_filter(gx * gx, TENSOR_SIGMA)
    jyy = ndimage.gaussian_filter(gy * gy, TENSOR_SIGMA)
    jxy = ndimage.gaussian_filter(gx * gy, TENSOR_SIGMA)
    tr = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        coh = np.where(tr > 0, (2.0 * disc) / np.maximum(tr, 1e-30), 0.0)
    return coh >= COH_MIN


def detail_log(off, on, m):
    if m.sum() < MIN_PIX:
        return float("nan")
    a = float(highpass(off)[m].std())
    b = float(highpass(on)[m].std())
    if a <= 0 or b <= 0:
        return float("nan")
    return float(np.log10(b / a))


def radial_displacement(a: np.ndarray, ch: int, ref_ch: int = 1):
    """Radial shift of `ch` against `ref_ch`, per annulus, in output px.

    Sampled in NSECT sectors per annulus. The shift is projected onto the
    sector's outward radial unit vector, so a positive value means the channel
    is imaged LARGER than the reference -- which is what a longer focal length
    for that wavelength produces, and what the profile's `eps` describes.
    """
    h, w = a.shape[:2]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rmax = float(np.hypot(cy, cx))
    r = WIN // 2
    out = []
    for (lo, hi) in ANNULI:
        rad_px = 0.5 * (lo + hi) * rmax
        vals, used = [], 0
        for k in range(NSECT):
            th = 2.0 * np.pi * k / NSECT
            uy, ux = np.sin(th), np.cos(th)
            py, px = int(round(cy + rad_px * uy)), int(round(cx + rad_px * ux))
            if not (r <= py < h - r and r <= px < w - r):
                continue
            gwin = a[py - r:py + r, px - r:px + r, ref_ch].astype(np.float64)
            cwin = a[py - r:py + r, px - r:px + r, ch].astype(np.float64)
            # A window with no structure carries no registration information;
            # including it would average a meaningless shift into the median.
            if float(highpass(gwin).std()) < MIN_STRUCT:
                continue
            s, _, _ = phase_cross_correlation(gwin, cwin,
                                              upsample_factor=UPSAMPLE,
                                              normalization=None)
            # `s` is the shift to apply to `cwin` to match `gwin`, in (dy, dx).
            # The channel's own displacement is the negation of that.
            dy, dx = -float(s[0]), -float(s[1])
            vals.append(dy * uy + dx * ux)     # project on the radial direction
            used += 1
        out.append({"r_lo": lo, "r_hi": hi,
                    "rd_px": float(np.median(vals)) if vals else float("nan"),
                    "n_sectors": used})
    return out


def plant_radial(a: np.ndarray, px: float) -> np.ndarray:
    """Displace R radially outward by `px` at the corner. CD1's calibration."""
    h, w = a.shape[:2]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    k = px / float(np.hypot(cy, cx))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    out = a.copy()
    # A PULL: to make the channel appear LARGER by (1+k), sample at (1+k)*z.
    out[:, :, 0] = ndimage.map_coordinates(
        a[:, :, 0], [cy + (yy - cy) * (1.0 + k), cx + (xx - cx) * (1.0 + k)],
        order=3, mode="nearest")
    return out


def band_mean(rows, lo, hi):
    v = [r["rd_px"] for r in rows
         if r["r_lo"] >= lo - 1e-9 and r["r_hi"] <= hi + 1e-9
         and np.isfinite(r["rd_px"])]
    return float(np.mean(v)) if v else float("nan")


def main() -> int:
    out = {"pinned_sha": PIN, "prereg": "prereg-ca2.txt @ bc38182",
           "plant_px": PLANT_PX, "subjects": {}}

    for s in SUBJECTS:
        p_off, p_on = CA / "measure" / f"{s}__OFF.tif", CA / "measure" / f"{s}__ON.tif"
        if not (p_off.exists() and p_on.exists()):
            print(f"  {s}: MISSING renders, skipped")
            continue
        print(f"== {s}")
        off, on = load(p_off), load(p_on)

        rec = {}
        rec["rd_off"] = radial_displacement(off, 0)
        rec["rd_on"] = radial_displacement(on, 0)
        rec["gd_off"] = radial_displacement(off, 2)          # blue, also moved
        rec["green_null_off"] = radial_displacement(off, 1, ref_ch=1)

        # CD3 null: green against itself must be exactly zero, and it is the
        # only quantity here that is zero by construction rather than by
        # measurement -- so it checks the harness, not the optics.
        planted = plant_radial(off, PLANT_PX)
        rec["rd_plant"] = radial_displacement(planted, 0)
        del planted

        # CD7 do-no-harm, on the channels the correction actually resamples.
        orient = oriented(off[:, :, 1])
        rec["D_R"] = detail_log(off[:, :, 0], on[:, :, 0], orient)
        rec["D_B"] = detail_log(off[:, :, 2], on[:, :, 2], orient)
        rec["D_L"] = detail_log(lum(off), lum(on), orient)
        rec["D_worst"] = float(np.nanmin([rec["D_R"], rec["D_B"], rec["D_L"]]))
        rec["oriented_px"] = int(orient.sum())

        sup_off = band_mean(rec["rd_off"], *SUPPORT)
        sup_on = band_mean(rec["rd_on"], *SUPPORT)
        rec["support_rd_off"] = sup_off
        rec["support_rd_on"] = sup_on
        rec["support_Q"] = (float(1.0 - abs(sup_on) / abs(sup_off))
                            if np.isfinite(sup_off) and sup_off != 0
                            else float("nan"))
        rec["centre_rd_off"] = rec["rd_off"][0]["rd_px"]
        rec["centre_rd_on"] = rec["rd_on"][0]["rd_px"]
        # CD1: the plant must be RECOVERED, at the outermost annulus scored.
        outer = [i for i, r in enumerate(rec["rd_off"])
                 if np.isfinite(r["rd_px"])][-1]
        rec["plant_recovered_px"] = (rec["rd_plant"][outer]["rd_px"]
                                     - rec["rd_off"][outer]["rd_px"])
        rec["plant_annulus"] = [rec["rd_off"][outer]["r_lo"],
                                rec["rd_off"][outer]["r_hi"]]
        rec["is_transfer"] = s in TRANSFER

        out["subjects"][s] = rec
        print(f"   RD_off(support) = {sup_off:+.4f} px   RD_on = {sup_on:+.4f} px"
              f"   Q = {rec['support_Q']:+.3f}")
        print(f"   centre  off {rec['centre_rd_off']:+.4f}  on {rec['centre_rd_on']:+.4f}"
              f"   | plant recovered {rec['plant_recovered_px']:+.4f} of {PLANT_PX:+.2f}"
              f"   | D_worst {rec['D_worst']:+.5f}")
        del off, on

    dst = CA / "scores-ca-disp.json"
    dst.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
