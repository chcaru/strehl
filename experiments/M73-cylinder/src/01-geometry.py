"""M73 step 01 — recover the bottle's geometry from INTENSITY ONLY.

Nothing in this file computes a focus measure, a winner index or an admitted
set. That is the point: M67's pre-registration binds this milestone to fitting
the geometry from the subject's own appearance and **never** from the field
being scored.

Two independent axis estimators, both on the frame-mean green luma:

* **E1 shading isophotes.** A cylinder lit from roughly the camera direction has
  an intensity that varies across the axis and is constant along it. Heavily
  low-pass the mean image and take the structure tensor's *minor* eigenvector.
  Reports the anisotropy, so a flat (uninformative) shading field is visible.
* **E2 text baselines.** Lines of text on a wrapped label run around the
  circumference, i.e. perpendicular to the axis. High-pass, threshold to an ink
  mask, and find the angle whose projection profile has maximum variance.

It also settles whether the **silhouette** exists (M67 requires the
circumferential arm's radius fit to come from it) and measures the text row
period, which the residual's spectral test needs.

Rule 32: every `raw_image_visible` read copies inside the `with` block.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import rawpy
from PIL import Image
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CORPUS = pathlib.Path(r"D:\personal\macro")
STACKS = ["wrapped-text-1", "wrapped-text-2"]

# Every 8th frame. The mean over a subset is a mean image; the axis and the ink
# template are properties of the subject, not of the sampling.
STRIDE = 8

# Low-pass sigma in plane px for the SHADING estimate. The measured text row
# pitch is 375 plane px, and a Gaussian attenuates a sinusoid of wavelength L by
# exp(-2 pi^2 sigma^2 / L^2): sigma = 120 leaves 13% of the row modulation,
# which is enough to capture the structure tensor. sigma = 400 leaves 4e-10.
SHADE_SIGMA = 400.0

# Low-pass sigma for the INK template's local background. This one must NOT be
# huge: it is removing the print's large-scale layout so the threshold isolates
# glyphs rather than dark panels.
INK_SIGMA = 60.0


def green_luma(path: pathlib.Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = float(np.max(raw.black_level_per_channel))
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    return 0.5 * (cfa[0:h:2, 1:w:2] + cfa[1:h:2, 0:w:2]) - black


def structure_tensor_axis(img: np.ndarray) -> tuple[float, float]:
    """Direction of LEAST intensity variation, in degrees from the +y axis.

    Returns (angle_deg, anisotropy) where anisotropy is
    `(l_major - l_minor) / (l_major + l_minor)`; 0 means the field is isotropic
    and the direction means nothing.
    """
    gy, gx = np.gradient(img)
    jxx = float(np.mean(gx * gx))
    jyy = float(np.mean(gy * gy))
    jxy = float(np.mean(gx * gy))
    j = np.array([[jxx, jxy], [jxy, jyy]])
    vals, vecs = np.linalg.eigh(j)
    minor = vecs[:, 0]  # eigenvector of the smallest eigenvalue: (x, y)
    # Angle from the +y axis, positive toward +x, folded to (-90, 90].
    ang = np.degrees(np.arctan2(minor[0], minor[1]))
    if ang > 90.0:
        ang -= 180.0
    if ang <= -90.0:
        ang += 180.0
    aniso = float((vals[1] - vals[0]) / (vals[1] + vals[0] + 1e-30))
    return float(ang), aniso


def projection_profile_score(mask: np.ndarray, angle_deg: float) -> float:
    """Variance of the ink mask's projection onto the axis at `angle_deg`.

    `angle_deg` is the assumed AXIS direction, measured from +y toward +x. Text
    baselines are perpendicular to it, so the projection that separates rows is
    the one taken ALONG the baseline, i.e. the sum over the baseline direction.
    """
    rot = ndimage.rotate(
        mask.astype(np.float32), angle=-angle_deg, reshape=False, order=1, mode="nearest"
    )
    # After rotating by -angle the axis is vertical, so text rows are horizontal
    # and the row sums separate them. Trim the border the rotation fabricated.
    m = int(0.10 * min(rot.shape))
    core = rot[m:-m, m:-m]
    prof = core.mean(axis=1)
    return float(np.var(prof))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, dict] = {}
    for stack in STACKS:
        d = CORPUS / stack
        frames = sorted(d.glob("*.ARW"))
        if not frames:
            print(f"FATAL: {d} holds no ARW files", file=sys.stderr)
            return 2
        picked = frames[::STRIDE]
        cache = OUT / f"meanimg-{stack}.npy"
        if cache.exists():
            mean_img = np.load(cache)
        else:
            acc = None
            for p in picked:
                g = green_luma(p)
                acc = g if acc is None else acc + g
            mean_img = (acc / len(picked)).astype(np.float32)
            np.save(cache, mean_img)
        h, w = mean_img.shape
        print(f"\n=== {stack}: {len(frames)} frames, mean over {len(picked)} ===")
        print(f"plane {w} x {h}")

        # ---- silhouette check ------------------------------------------------
        # A silhouette needs background: pixels far darker than the label. Report
        # the darkest border strip against the label's own body statistics.
        body = float(np.median(mean_img))
        edges = {
            "left": float(np.median(mean_img[:, :64])),
            "right": float(np.median(mean_img[:, -64:])),
            "top": float(np.median(mean_img[:64, :])),
            "bottom": float(np.median(mean_img[-64:, :])),
        }
        print(f"label body median : {body:.1f} DN above black")
        for k, v in edges.items():
            print(f"  {k:<6} strip    : {v:.1f} DN  ({100.0 * v / body:.1f}% of body)")

        # ---- E1: shading isophotes -------------------------------------------
        shade = ndimage.gaussian_filter(mean_img, SHADE_SIGMA, mode="nearest")
        ang_shade, aniso_shade = structure_tensor_axis(shade)
        # The two marginal profiles say WHY, which the angle alone does not.
        colp = shade.mean(axis=0)  # varies with x: across a vertical axis
        rowp = shade.mean(axis=1)  # varies with y: along a vertical axis
        c_ptp = float(np.ptp(colp))
        r_ptp = float(np.ptp(rowp))
        print(f"E1 shading axis   : {ang_shade:+.3f} deg from +y   anisotropy {aniso_shade:.4f}")
        print(
            f"   shading swing  : across-x {c_ptp:.1f} DN ({100.0 * c_ptp / body:.1f}%), "
            f"along-y {r_ptp:.1f} DN ({100.0 * r_ptp / body:.1f}%)"
        )

        # ---- ink template ----------------------------------------------------
        detail = mean_img - ndimage.gaussian_filter(mean_img, INK_SIGMA, mode="nearest")
        # Ink is dark: the negative tail of the high-pass.
        thresh = float(np.percentile(detail, 12.0))
        ink = detail < thresh
        print(f"ink threshold     : {thresh:.1f} DN   ink fraction {ink.mean():.4f}")

        # ---- E2: text baselines ----------------------------------------------
        coarse = np.arange(-12.0, 12.01, 1.0)
        scores = [projection_profile_score(ink[::4, ::4], a) for a in coarse]
        best_coarse = float(coarse[int(np.argmax(scores))])
        fine = np.arange(best_coarse - 1.0, best_coarse + 1.001, 0.1)
        fscores = [projection_profile_score(ink[::2, ::2], a) for a in fine]
        ang_text = float(fine[int(np.argmax(fscores))])
        print(f"E2 text axis      : {ang_text:+.3f} deg from +y   (coarse {best_coarse:+.1f})")
        print(f"E1 - E2           : {ang_shade - ang_text:+.3f} deg")

        # ---- text row pitch, at E2's angle ------------------------------------
        rot = ndimage.rotate(
            ink.astype(np.float32), angle=-ang_text, reshape=False, order=1, mode="nearest"
        )
        m = int(0.10 * min(rot.shape))
        prof = rot[m:-m, m:-m].mean(axis=1)
        prof = prof - prof.mean()
        spec = np.abs(np.fft.rfft(prof * np.hanning(len(prof)))) ** 2
        freqs = np.fft.rfftfreq(len(prof), d=1.0)
        lo = np.searchsorted(freqs, 1.0 / 900.0)
        hi = np.searchsorted(freqs, 1.0 / 90.0)
        k = lo + int(np.argmax(spec[lo:hi]))
        pitch = 1.0 / freqs[k]
        print(f"text row pitch    : {pitch:.1f} plane px  (rows in view {len(prof) / pitch:.2f})")

        np.save(OUT / f"meanimg-{stack}.npy", mean_img.astype(np.float32))
        np.save(OUT / f"ink-{stack}.npy", ink)
        Image.fromarray((ink[::4, ::4] * 255).astype(np.uint8)).save(OUT / f"ink-{stack}.png")
        sh = shade[::4, ::4]
        Image.fromarray(
            (255 * (sh - sh.min()) / max(float(np.ptp(sh)), 1e-6)).astype(np.uint8)
        ).save(OUT / f"shade-{stack}.png")

        report[stack] = {
            "frames": len(frames),
            "mean_over": len(picked),
            "plane": [w, h],
            "body_median_dn": body,
            "edge_medians_dn": edges,
            "axis_shading_deg": ang_shade,
            "shading_anisotropy": aniso_shade,
            "shading_swing_across_x_dn": c_ptp,
            "shading_swing_along_y_dn": r_ptp,
            "axis_text_deg": ang_text,
            "ink_fraction": float(ink.mean()),
            "text_row_pitch_px": float(pitch),
        }

    (OUT / "01-geometry.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nwrote", OUT / "01-geometry.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
