"""ORCH — three-way VISUAL comparison: strehl vs enfuse vs focus-stack.

Every head-to-head number in this project is statistical. The owner's
acceptance criterion is visual. This emits 1:1 crops of the same feature from
all three mergers so the comparison can be *looked at*.

The three arms are the same half-bracket of the same subject through three
different mergers, already placed in a common container by the noise harness,
so this adds no resampling of its own.

Two confounds are handled explicitly and both are stated in the output:

1. GEOMETRY. The three aligners do not agree to the pixel. Registration is by
   FFT phase correlation and is applied as an INTEGER shift only -- sub-pixel
   resampling would add blur to the very quantity being judged.

2. TONE. The arms do not share a tone curve, and an unmatched tone curve makes
   a visual comparison a comparison of tone. Each comparator crop is mapped to
   strehl's crop by a linear gain+offset fitted on that crop. Gain scales
   signal and noise together, so SNR is preserved -- this cannot manufacture or
   hide a noise difference. The fitted gain is printed for every crop.

Site selection is deliberately NOT "where it looks best" (see veiling 129).
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

ARMS = Path(r"C:\dev\strehl-out\V-NOISE2\119\arms")
OUT = Path(r"C:\dev\strehl-out\ORCH-3WAY")
CROP = 400          # <= 400 px: a visual verdict above this is not 1:1
TILE = 256          # site-selection grid
SEED = 20260827


def green(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    if a.ndim == 3 and a.shape[2] >= 3:
        a = a[:, :, 1]
    return a


def rgb(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    return a[:, :, :3]


def phase_shift(ref: np.ndarray, mov: np.ndarray, win: int = 2048):
    """Integer (dy, dx) that best aligns `mov` onto `ref`, by phase correlation."""
    h, w = ref.shape
    cy, cx = h // 2, w // 2
    half = win // 2
    a = ref[cy - half:cy + half, cx - half:cx + half].astype(np.float64)
    b = mov[cy - half:cy + half, cx - half:cx + half].astype(np.float64)
    a = a - a.mean()
    b = b - b.mean()
    # Hann window, so the edges of the patch do not dominate the correlation.
    wnd = np.hanning(win)[:, None] * np.hanning(win)[None, :]
    A = np.fft.rfft2(a * wnd)
    B = np.fft.rfft2(b * wnd)
    R = A * np.conj(B)
    mag = np.abs(R)
    mag[mag == 0] = 1.0
    r = np.fft.irfft2(R / mag, s=(win, win))
    peak = np.unravel_index(np.argmax(r), r.shape)
    dy = peak[0] if peak[0] < win // 2 else peak[0] - win
    dx = peak[1] if peak[1] < win // 2 else peak[1] - win
    return int(dy), int(dx), float(r.max())


def energy_grid(g: np.ndarray, tile: int = TILE) -> np.ndarray:
    h, w = g.shape
    ny, nx = h // tile, w // tile
    gg = g[: ny * tile, : nx * tile].astype(np.float32)
    gg = gg.reshape(ny, tile, nx, tile)
    dy = np.abs(np.diff(gg, axis=1)).mean(axis=(1, 3))
    dx = np.abs(np.diff(gg, axis=3)).mean(axis=(1, 3))
    return 0.5 * (dy + dx)


def pick_sites(g: np.ndarray):
    """Return [(label, y, x)] -- deliberately not chosen for flattery."""
    e = energy_grid(g)
    ny, nx = e.shape
    flat = e.ravel()
    # 'worst on subject': the least-resolved place that is still ON the subject.
    # The floor exists because without it 'worst' lands on empty backdrop, which
    # says nothing about the merge (veiling 129, second order).
    floor = np.percentile(flat, 55)
    on_subject = np.where(flat >= floor)[0]
    worst = on_subject[np.argmin(flat[on_subject])]
    best = int(np.argmax(flat))
    rng = np.random.default_rng(SEED)
    rand = int(rng.choice(on_subject))
    sites = []
    for label, idx in (("worst-on-subject", worst), ("random", rand), ("best", best)):
        iy, ix = divmod(int(idx), nx)
        y = iy * TILE + TILE // 2 - CROP // 2
        x = ix * TILE + TILE // 2 - CROP // 2
        y = max(0, min(g.shape[0] - CROP, y))
        x = max(0, min(g.shape[1] - CROP, x))
        sites.append((label, int(y), int(x)))
    return sites


def to8(a: np.ndarray) -> np.ndarray:
    if a.dtype == np.uint8:
        return a.astype(np.float32) * 257.0
    return a.astype(np.float32)


def display(a: np.ndarray, exposure: float, gamma: float = 2.2) -> np.ndarray:
    """Identical viewing transform for every panel.

    The arms are LINEAR renders and are far too dark to judge by eye. This is a
    display transform, not a correction: the same exposure and the same gamma
    are applied to all three panels, so it cannot change their ordering. It is
    applied AFTER the photometric fit so the fit stays linear.
    """
    x = np.clip(a / 65535.0 * exposure, 0.0, 1.0)
    return np.clip(np.power(x, 1.0 / gamma) * 255.0, 0, 255).astype(np.uint8)


def photometric_fit(src: np.ndarray, ref: np.ndarray):
    """Least-squares gain+offset mapping src -> ref, fitted on this crop."""
    s = src.reshape(-1).astype(np.float64)
    r = ref.reshape(-1).astype(np.float64)
    A = np.stack([s, np.ones_like(s)], axis=1)
    coef, *_ = np.linalg.lstsq(A, r, rcond=None)
    return float(coef[0]), float(coef[1])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {
        "strehl": ARMS / "strehl-A.tiff",
        "enfuse": ARMS / "coh-enfuse-A.tif",
        "focus-stack": ARMS / "coh-fs15-A.tif",
    }
    for k, p in paths.items():
        if not p.exists():
            sys.exit(f"missing arm {k}: {p}")

    print("loading green planes for registration ...")
    g = {k: green(p) for k, p in paths.items()}
    ref = g["strehl"]

    shifts = {"strehl": (0, 0, 1.0)}
    for k in ("enfuse", "focus-stack"):
        shifts[k] = phase_shift(ref, g[k])
        print(f"  {k:12s} shift dy={shifts[k][0]:+d} dx={shifts[k][1]:+d} "
              f"peak={shifts[k][2]:.4f}")

    sites = pick_sites(ref)
    print("sites (chosen on strehl, by measured gradient energy):")
    for label, y, x in sites:
        print(f"  {label:18s} y={y} x={x}")

    print("loading RGB ...")
    im = {k: rgb(p) for k, p in paths.items()}
    del g

    manifest = {"subject": "119MSDCF", "arms": {k: str(v) for k, v in paths.items()},
                "crop_px": CROP, "shifts": {k: [v[0], v[1]] for k, v in shifts.items()},
                "sites": [], "note": "integer-shift registration only; per-crop "
                                     "linear gain+offset to strehl"}

    for label, y, x in sites:
        panels, labels = [], []
        base = to8(im["strehl"][y:y + CROP, x:x + CROP])
        # One exposure per SITE, derived from the strehl panel and reused for
        # every arm, so no arm gets its own stretch.
        p99 = float(np.percentile(base / 65535.0, 99.5))
        expo = float(np.clip(0.9 / max(p99, 1e-4), 1.0, 64.0))
        rec = {"label": label, "y": y, "x": x, "exposure": round(expo, 3), "fits": {}}
        for k in ("strehl", "enfuse", "focus-stack"):
            dy, dx, _ = shifts[k]
            yy, xx = y - dy, x - dx
            yy = max(0, min(im[k].shape[0] - CROP, yy))
            xx = max(0, min(im[k].shape[1] - CROP, xx))
            c = to8(im[k][yy:yy + CROP, xx:xx + CROP])
            if k == "strehl":
                gain, off = 1.0, 0.0
            else:
                gain, off = photometric_fit(c, base)
                c = c * gain + off
            rec["fits"][k] = {"gain": round(gain, 5), "offset": round(off, 2)}
            panels.append(display(c, expo))
            labels.append(f"{k}  (gain {gain:.3f})" if k != "strehl" else "strehl")

        pad = 8
        W = CROP * 3 + pad * 4
        H = CROP + pad * 2 + 22
        sheet = Image.new("RGB", (W, H), (24, 24, 24))
        for i, (p, lab) in enumerate(zip(panels, labels)):
            sheet.paste(Image.fromarray(p), (pad + i * (CROP + pad), pad + 22))
            ImageDraw.Draw(sheet).text((pad + i * (CROP + pad), 5), lab, fill=(235, 235, 235))
        ImageDraw.Draw(sheet).text((W - 210, 5), f"display x{expo:.1f} g2.2 (all panels)",
                                   fill=(150, 150, 150))
        name = f"119MSDCF__{label}.png"
        sheet.save(OUT / name)
        print(f"  wrote {name}  expo x{expo:.1f}  " + "  ".join(
            f"{k}:g={rec['fits'][k]['gain']:.3f}" for k in rec["fits"]))
        manifest["sites"].append(rec)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{len(sites)} montages -> {OUT}")


if __name__ == "__main__":
    main()
