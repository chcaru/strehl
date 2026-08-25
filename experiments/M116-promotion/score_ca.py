"""M116-promotion — campaign 4 scorer: lateral chromatic aberration.

Contract: prereg-ca.txt, committed at 188b55c before any CA arm was rendered.
Every bar below (CB1-CB9) is decided on the definitions frozen in that file.

Reads LINEAR renders only. The sRGB renders exist for the crops and no number
here comes from one.

Run: python score_ca.py
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage
from scipy.ndimage import uniform_filter

ROOT = Path(r"C:\dev\strehl-out\M116")
CA = ROOT / "ca"
PIN = "4beac7300e318f6f0aaf10b6a88e57f311b9e814"

SUBJECTS = ["bee-3-cpl", "flat-on-ruler-cpl",
            "tweezers-cpl", "flower-bud-with-background-fern-cpl"]
REPRO = {"bee-3-cpl", "flat-on-ruler-cpl"}          # M110 used these
TRANSFER = {"tweezers-cpl", "flower-bud-with-background-fern-cpl"}

EDGE_PCT = 98.0        # top 2% of luminance gradient — prereg section 3
NBANDS = 6             # bands 0..5; band 5 is the far-band baseline
HP_BOX = 5             # matches score.highpass
COH_MIN = 0.6
TENSOR_SIGMA = 2.0
MIN_PIX = 20000        # a band thinner than this is not scored

# Normalised radius bands, prereg section 3.
R_CENTRE = (0.00, 0.15)      # the trap: CA is radial and must vanish here
R_SUPPORT = (0.55, 0.788)    # inside the fitted support (M110 fact 56)
R_EXTRAP = (0.788, 1.01)     # beyond it (discipline 58)

DISPLAY_LEVEL = 65535.0 / 255.0   # "1 display level" for the CB8 gate


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def load(path: Path) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.ndim == 3 and a.shape[2] == 3, f"{path} is {a.shape}, want HxWx3"
    return a.astype(np.float32)


def lum(a: np.ndarray) -> np.ndarray:
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def highpass(p: np.ndarray) -> np.ndarray:
    """p must be 2-D so no separable filter can cross a non-spatial axis."""
    assert p.ndim == 2
    return p - uniform_filter(p, size=HP_BOX, mode="nearest")


def edge_geometry(g: np.ndarray):
    """Bands of distance from a strong edge, and normalised radius.

    Edges are found on the GREEN plane. Green is the profile's reference
    channel -- `OpticalProfile::compose` displaces R and B against it -- so the
    edge set is the SAME in both arms by construction and neither arm can
    select its own favourable edges. Selecting on a compared arm's luminance
    would let the treatment move the very pixels it is scored on.
    """
    gy, gx = np.gradient(g.astype(np.float32))
    mag = np.hypot(gy, gx)
    thr = np.percentile(mag, EDGE_PCT)
    edges = mag >= thr
    dist = ndimage.distance_transform_edt(~edges).astype(np.float32)
    band = np.clip(np.round(dist), 0, NBANDS - 1).astype(np.int8)

    h, w = g.shape
    yy = (np.arange(h, dtype=np.float32) - (h - 1) / 2.0)[:, None]
    xx = (np.arange(w, dtype=np.float32) - (w - 1) / 2.0)[None, :]
    rad = np.sqrt(yy * yy + xx * xx)
    rad /= float(np.hypot((h - 1) / 2.0, (w - 1) / 2.0))
    return band, rad.astype(np.float32), float(thr), int(edges.sum())


def oriented(g: np.ndarray) -> np.ndarray:
    """Structure-tensor coherence. Hairs and claws are locally 1-D."""
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


def profile(chroma: np.ndarray, band: np.ndarray, sel: np.ndarray):
    """Median |chroma| per distance band, within a radius selection."""
    out = []
    for b in range(NBANDS):
        m = sel & (band == b)
        n = int(m.sum())
        out.append(float(np.median(chroma[m])) if n >= MIN_PIX else float("nan"))
    return out


def excess(prof) -> float:
    """Edge-localised chroma excess: peak band minus far-band baseline."""
    if any(np.isnan(prof[i]) for i in (0, NBANDS - 1)):
        return float("nan")
    return prof[0] - prof[NBANDS - 1]


def half_max_width(prof) -> float:
    """Distance at which the profile falls to half its peak-over-baseline.

    Reported because M110 discipline 59 requires amplitude and extent be
    separated: a 60% amplitude drop must not be written up as a fringe that
    shrank.
    """
    base = prof[NBANDS - 1]
    pk = prof[0] - base
    if not np.isfinite(pk) or pk <= 0:
        return float("nan")
    half = base + pk / 2.0
    for b in range(1, NBANDS):
        if np.isfinite(prof[b]) and prof[b] <= half:
            lo, hi = prof[b - 1], prof[b]
            if lo == hi:
                return float(b)
            return float(b - 1) + float((lo - half) / (lo - hi))
    return float("nan")


def dpct(x_off: float, x_on: float) -> float:
    if not np.isfinite(x_off) or not np.isfinite(x_on) or x_off == 0:
        return float("nan")
    return 100.0 * (x_off - x_on) / x_off


def detail_log(off: np.ndarray, on: np.ndarray, m: np.ndarray) -> float:
    """log10(high-pass amplitude ON / OFF) over a mask. <0 means destroyed."""
    if m.sum() < MIN_PIX:
        return float("nan")
    a = float(highpass(off)[m].std())
    b = float(highpass(on)[m].std())
    if a <= 0 or b <= 0:
        return float("nan")
    return float(np.log10(b / a))


def plant_radial_red(a: np.ndarray, px: float = 0.5) -> np.ndarray:
    """CB3: synthesise a known lateral CA by displacing R radially outward.

    A null with no plant is a dead probe (fact 1548): M97q's bar F2 read zero
    and so did its deliberately broken version, because the quantity could not
    move. This gives the metric a difference it MUST be able to see.
    """
    h, w = a.shape[:2]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rmax = float(np.hypot(cy, cx))
    k = px / rmax                       # displacement of `px` at the corner
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    src_y = cy + (yy - cy) * (1.0 + k)
    src_x = cx + (xx - cx) * (1.0 + k)
    out = a.copy()
    out[:, :, 0] = ndimage.map_coordinates(
        a[:, :, 0], [src_y, src_x], order=1, mode="nearest")
    return out


def score_pair(off, on, band, rad, orient, label):
    """All per-arm-pair quantities, in every radius band."""
    c_off_r = np.abs(off[:, :, 0] - off[:, :, 1])
    c_on_r = np.abs(on[:, :, 0] - on[:, :, 1])
    c_off_b = np.abs(off[:, :, 2] - off[:, :, 1])
    c_on_b = np.abs(on[:, :, 2] - on[:, :, 1])

    res = {"label": label, "bands": {}}
    for name, (lo, hi) in (("centre", R_CENTRE), ("in_support", R_SUPPORT),
                           ("extrapolated", R_EXTRAP)):
        sel = (rad >= lo) & (rad < hi)
        pr_off = profile(c_off_r, band, sel)
        pr_on = profile(c_on_r, band, sel)
        pb_off = profile(c_off_b, band, sel)
        pb_on = profile(c_on_b, band, sel)
        xr_off, xr_on = excess(pr_off), excess(pr_on)
        xb_off, xb_on = excess(pb_off), excess(pb_on)

        # CB8 overshoot: the CONJUNCTION flip AND growth (M110 discipline 57).
        s = sel & (band == 0)
        sr_off = (off[:, :, 0] - off[:, :, 1])[s]
        sr_on = (on[:, :, 0] - on[:, :, 1])[s]
        gate = (np.abs(sr_off) >= DISPLAY_LEVEL) | (np.abs(sr_on) >= DISPLAY_LEVEL)
        ng = int(gate.sum())
        if ng >= 1000:
            flip = np.sign(sr_on[gate]) != np.sign(sr_off[gate])
            grow = np.abs(sr_on[gate]) > np.abs(sr_off[gate])
            over = float(100.0 * np.mean(flip & grow))
            flips = float(100.0 * np.mean(flip))
        else:
            over, flips = float("nan"), float("nan")

        res["bands"][name] = {
            "n_px": int(sel.sum()),
            "prof_RG_off": pr_off, "prof_RG_on": pr_on,
            "prof_BG_off": pb_off, "prof_BG_on": pb_on,
            "X_RG_off": xr_off, "X_RG_on": xr_on, "dX_RG_pct": dpct(xr_off, xr_on),
            "X_BG_off": xb_off, "X_BG_on": xb_on, "dX_BG_pct": dpct(xb_off, xb_on),
            "hmw_off": half_max_width(pr_off), "hmw_on": half_max_width(pr_on),
            "overshoot_pct": over, "flip_pct": flips, "n_gated": ng,
        }

    # CB6: the correction resamples R and B. Score the moved channels, and
    # luminance as the perceptual figure. The bar is decided on the WORST.
    res["D_R"] = detail_log(off[:, :, 0], on[:, :, 0], orient)
    res["D_B"] = detail_log(off[:, :, 2], on[:, :, 2], orient)
    res["D_L"] = detail_log(lum(off), lum(on), orient)
    res["D_worst"] = float(np.nanmin([res["D_R"], res["D_B"], res["D_L"]]))

    # Post-hoc diagnostic, disclosed as such in the report: green is the
    # profile's reference channel, so it should be untouched on a linear render.
    dg = np.abs(on[:, :, 1] - off[:, :, 1])
    res["green_max_abs_delta"] = float(dg.max())
    res["green_frac_moved"] = float(np.mean(dg > 0))
    return res


def main() -> int:
    out = {"pinned_sha": PIN, "prereg": "prereg-ca.txt @ 188b55c",
           "edge_pct": EDGE_PCT, "subjects": {}}

    for s in SUBJECTS:
        m = CA / "measure"
        p_off, p_on = m / f"{s}__OFF.tif", m / f"{s}__ON.tif"
        p_off2 = m / f"{s}__OFF2.tif"
        if not (p_off.exists() and p_on.exists()):
            print(f"  {s}: MISSING renders, skipped")
            continue
        print(f"== {s}")
        off, on = load(p_off), load(p_on)
        assert off.shape == on.shape, f"{s}: arms differ in shape"

        rec = {"shape": list(off.shape),
               "sha_off": sha256(p_off), "sha_on": sha256(p_on)}

        # CB1 null: the same arm, cold private cache, must be byte-identical.
        if p_off2.exists():
            rec["sha_off2"] = sha256(p_off2)
            rec["CB1_identical"] = rec["sha_off2"] == rec["sha_off"]
        # CB2 placebo: same config, different output path, another arm's cache.
        p_pl = m / f"{s}__PLACEBO.tif"
        if p_pl.exists():
            rec["sha_placebo"] = sha256(p_pl)
            rec["CB2_identical"] = rec["sha_placebo"] == rec["sha_off"]

        g = off[:, :, 1]
        band, rad, thr, nedge = edge_geometry(g)
        orient = oriented(g)
        rec["edge_threshold"] = thr
        rec["edge_px"] = nedge
        rec["oriented_px"] = int(orient.sum())

        rec["treated"] = score_pair(off, on, band, rad, orient, "OFF->ON")

        if p_pl.exists():
            pl = load(p_pl)
            rec["placebo"] = score_pair(off, pl, band, rad, orient, "OFF->PLACEBO")
            del pl

        # CB3 plant, on every subject: prove the metric can express a
        # difference on this exact wiring before any zero is called a null.
        planted = plant_radial_red(off, 0.5)
        rec["plant"] = score_pair(off, planted, band, rad, orient,
                                  "OFF->OFF+0.5px radial R")
        del planted, off, on

        out["subjects"][s] = rec
        print(f"   in-support dX(R-G) = {rec['treated']['bands']['in_support']['dX_RG_pct']:+.2f}%"
              f"   centre = {rec['treated']['bands']['centre']['dX_RG_pct']:+.2f}%"
              f"   D_worst = {rec['treated']['D_worst']:+.5f}")

    dst = CA / "scores-ca.json"
    dst.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
