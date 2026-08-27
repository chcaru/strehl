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

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "DELIVER-V5"))
from build import tag_png  # noqa: E402

# Each entry is one subject for which all three mergers have been run over the
# SAME frames. `linear` says whether the arms are linear renders (which need a
# display transform to be judged at all) or already tone-mapped.
SETS = {
    "119MSDCF": {
        "dir": Path(r"C:\dev\strehl-out\V-NOISE2\119\arms"),
        "arms": {"strehl": "strehl-A.tiff", "enfuse": "coh-enfuse-A.tif",
                 "focus-stack": "coh-fs15-A.tif"},
        "linear": True,
        "note": "one half-bracket, linear noise-measurement arms",
    },
    "coffee-bean": {
        "dir": Path(r"C:\dev\strehl-out\V-SPEED\coffee-bean\out"),
        "arms": {"strehl": "r0-strehl.tif", "enfuse": "r0-srgb-enfuse.tif",
                 "focus-stack": "r0-srgb-fs.tif"},
        "linear": False,
        "note": "full 105-frame stack, sRGB end-to-end arms",
    },
}

OUT = Path(r"C:\dev\strehl-out\DELIVER-V5\vs-the-field")
CROP = 400          # <= 400 px: a visual verdict above this is not 1:1
TILE = 256          # site-selection grid
SEED = 20260827

# Two guards, both of which fired on real data and both of which stop a
# misregistered pair being published as a quality comparison.
#
# A tone difference between two renderers is a smooth global property, so on
# any one crop the fitted gain should sit close to the whole frame's. A crop
# that needs a very different gain is not showing the same content. The band is
# generous for tone and still refuses content mismatch.
GAIN_BAND = (0.7, 1.4)
# A genuine local residual after a global alignment is a few pixels.
MAX_LOCAL_RESIDUAL = 8


def green(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    if a.ndim == 3 and a.shape[2] >= 3:
        a = a[:, :, 1]
    return a


def rgb(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    return a[:, :, :3]


def phase_shift(ref: np.ndarray, mov: np.ndarray, win: int = 2048,
                cy: int | None = None, cx: int | None = None):
    """Integer (dy, dx) that best aligns `mov` onto `ref`, by phase correlation.

    `cy`/`cx` select the window centre. Called once globally and then again per
    crop: the arms do not share a canvas (measured 7032 vs 7028 px wide on
    `coffee-bean`) and different aligners leave different residual distortion,
    so a single global shift does not hold across a 33 MP frame. A crop
    registered by the global shift alone landed on different content and the
    photometric fit reported a gain of 0.094 -- which is how this was found.
    """
    h, w = ref.shape
    cy = h // 2 if cy is None else cy
    cx = w // 2 if cx is None else cx
    half = win // 2
    cy = int(np.clip(cy, half, h - half))
    cx = int(np.clip(cx, half, w - half))
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


def display(a: np.ndarray, exposure: float) -> np.ndarray:
    """Identical viewing transform for every panel.

    The arms are LINEAR renders and are far too dark to judge by eye. This is a
    display transform, not a correction: the same exposure and the same transfer
    function are applied to all three panels, so it cannot change their
    ordering. It is applied AFTER the photometric fit so the fit stays linear.

    The transfer is the real sRGB curve rather than a 2.2 power law, so the
    montage is genuinely in the space its ICC tag will claim. A gamma-2.2 image
    tagged as sRGB is a small lie, and the delivery audit would have accepted it
    silently -- it checks that a profile is present, not that it is true.
    """
    x = np.clip(a / 65535.0 * exposure, 0.0, 1.0)
    lo = x * 12.92
    hi = 1.055 * np.power(np.maximum(x, 1e-8), 1.0 / 2.4) - 0.055
    s = np.where(x <= 0.0031308, lo, hi)
    return np.clip(s * 255.0 + 0.5, 0, 255).astype(np.uint8)


def photometric_fit(src: np.ndarray, ref: np.ndarray):
    """Least-squares gain+offset mapping src -> ref, fitted PER CHANNEL.

    Per channel, not joint, and the distinction decides what the montage means.
    A joint fit leaves any white-balance difference between the two pipelines
    standing in the image, where it reads as a colour cast -- and a colour cast
    is indistinguishable by eye from chroma noise, which is exactly the quantity
    this montage exists to judge. Fitting each channel separately removes the
    cast (a low-frequency, per-channel scale) while leaving coloured speckle (a
    high-frequency, per-pixel disagreement) completely untouched, so the two
    causes separate instead of being confused.

    Returns (gains, offsets) as 3-vectors.
    """
    gains, offs = [], []
    for c in range(3):
        s = src[:, :, c].reshape(-1).astype(np.float64)
        r = ref[:, :, c].reshape(-1).astype(np.float64)
        A = np.stack([s, np.ones_like(s)], axis=1)
        coef, *_ = np.linalg.lstsq(A, r, rcond=None)
        gains.append(float(coef[0]))
        offs.append(float(coef[1]))
    return np.array(gains), np.array(offs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject", choices=sorted(SETS), nargs="?", default="119MSDCF")
    args = ap.parse_args()
    spec = SETS[args.subject]
    subject = args.subject

    OUT.mkdir(parents=True, exist_ok=True)
    paths = {k: spec["dir"] / v for k, v in spec["arms"].items()}
    for k, p in paths.items():
        if not p.exists():
            sys.exit(f"missing arm {k}: {p}")
        if p.stat().st_size < 1_000_000:
            # A live lane is writing in some of these trees; a zero-length or
            # truncated arm would silently become a black panel.
            sys.exit(f"arm {k} is only {p.stat().st_size} bytes -- truncated or "
                     f"mid-write, refusing: {p}")

    print(f"subject {subject} -- {spec['note']}")
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

    # Global per-channel scale implied by the whole frame, used only as the
    # expectation the per-crop fit is checked against. A crop that needs a very
    # different scale from the whole image is not looking at the same content.
    gscale = {}
    for k in ("enfuse", "focus-stack"):
        gs = []
        for c in range(3):
            a = np.median(to8(im["strehl"][::16, ::16, c]))
            b = np.median(to8(im[k][::16, ::16, c]))
            gs.append(float(a / max(b, 1e-6)))
        gscale[k] = np.array(gs)
        print(f"  {k:12s} whole-frame scale {gs[0]:.3f}/{gs[1]:.3f}/{gs[2]:.3f}")

    manifest = {"subject": subject, "linear_arms": spec["linear"], "note": spec["note"],
                "arms": {k: str(v) for k, v in paths.items()},
                "crop_px": CROP, "shifts": {k: [v[0], v[1]] for k, v in shifts.items()},
                "sites": [], "method": "integer-shift registration only; per-channel "
                                       "linear gain+offset to strehl"}

    nrefused = [0]
    for label, y, x in sites:
        panels, labels = [], []
        base = to8(im["strehl"][y:y + CROP, x:x + CROP])
        if spec["linear"]:
            # One exposure per SITE, derived from the strehl panel and reused
            # for every arm, so no arm gets its own stretch.
            p99 = float(np.percentile(base / 65535.0, 99.5))
            expo = float(np.clip(0.9 / max(p99, 1e-4), 1.0, 64.0))
        else:
            # Already tone-mapped. Applying an sRGB curve to an sRGB image would
            # encode it twice and lift the shadows into a false rendition, so
            # these arms are shown exactly as the pipelines produced them.
            expo = 1.0
        rec = {"label": label, "y": y, "x": x, "exposure": round(expo, 3), "fits": {}}
        refused = []
        for k in ("strehl", "enfuse", "focus-stack"):
            if k == "strehl":
                dy, dx = 0, 0
            else:
                # Refine the shift on THIS crop's neighbourhood, not the frame's.
                dy, dx, pk = phase_shift(g["strehl"], g[k], win=1024,
                                         cy=y + CROP // 2, cx=x + CROP // 2)
                gy, gx, _ = shifts[k]
                # A genuine local residual after a global alignment is small. A
                # large disagreement is not a residual, it is a correlation
                # failure -- measured at dx=+74 on one coffee-bean site, which
                # then produced a NEGATIVE fitted gain because the patch was
                # anti-correlated content.
                if abs(dy - gy) > MAX_LOCAL_RESIDUAL or abs(dx - gx) > MAX_LOCAL_RESIDUAL:
                    refused.append(
                        f"{k}: per-crop shift dy={dy:+d} dx={dx:+d} disagrees with "
                        f"global dy={gy:+d} dx={gx:+d} by more than "
                        f"{MAX_LOCAL_RESIDUAL} px (peak {pk:.4f}) -- registration "
                        f"failed on this crop")
                    dy, dx = gy, gx
            yy, xx = y - dy, x - dx
            yy = max(0, min(im[k].shape[0] - CROP, yy))
            xx = max(0, min(im[k].shape[1] - CROP, xx))
            c = to8(im[k][yy:yy + CROP, xx:xx + CROP])
            if k == "strehl":
                gain, off = np.ones(3), np.zeros(3)
            else:
                gain, off = photometric_fit(c, base)
                # GUARD. The fitted gain must be near the whole-frame scale. A
                # crop that needs a wildly different scale is not on the same
                # content, and publishing it would be publishing a misregistered
                # pair as if it were a quality comparison.
                ratio = gain / np.maximum(gscale[k], 1e-6)
                if np.any(ratio < GAIN_BAND[0]) or np.any(ratio > GAIN_BAND[1]):
                    refused.append(
                        f"{k}: fitted gain {gain[0]:.3f}/{gain[1]:.3f}/{gain[2]:.3f} "
                        f"vs whole-frame {gscale[k][0]:.3f}/{gscale[k][1]:.3f}/"
                        f"{gscale[k][2]:.3f} (shift dy={dy:+d} dx={dx:+d})")
                c = c * gain[None, None, :] + off[None, None, :]
            rec["fits"][k] = {"gain": [round(float(v), 5) for v in gain],
                              "offset": [round(float(v), 2) for v in off],
                              "shift": [dy, dx]}
            panels.append(display(c, expo) if spec["linear"]
                          else np.clip(c / 257.0 + 0.5, 0, 255).astype(np.uint8))
            labels.append(
                f"{k}  (RGB gain {gain[0]:.3f}/{gain[1]:.3f}/{gain[2]:.3f})"
                if k != "strehl" else "strehl  (reference)")

        pad = 8
        W = CROP * 3 + pad * 4
        H = CROP + pad * 2 + 22
        sheet = Image.new("RGB", (W, H), (24, 24, 24))
        for i, (p, lab) in enumerate(zip(panels, labels)):
            sheet.paste(Image.fromarray(p), (pad + i * (CROP + pad), pad + 22))
            ImageDraw.Draw(sheet).text((pad + i * (CROP + pad), 5), lab, fill=(235, 235, 235))
        ImageDraw.Draw(sheet).text(
            (W - 250, 5),
            f"display x{expo:.1f} sRGB (all panels)" if spec["linear"]
            else "as-rendered, no display transform",
            fill=(150, 150, 150))
        name = f"{subject}__{label}.png"
        if refused:
            rec["refused"] = refused
            nrefused[0] += 1
            print(f"  REFUSED {name}")
            for r in refused:
                print(f"      {r}")
            manifest["sites"].append(rec)
            continue
        sheet.save(OUT / name)
        tag_png(str(OUT / name))
        print(f"  wrote {name}  expo x{expo:.1f}  " + "  ".join(
            f"{k}:g={'/'.join(f'{v:.3f}' for v in rec['fits'][k]['gain'])}"
            for k in rec["fits"]))
        manifest["sites"].append(rec)

    manifest["refused"] = nrefused[0]
    (OUT / f"manifest-{subject}.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{subject}: {len(sites)} sites = {len(sites)-nrefused[0]} written + {nrefused[0]} refused -> {OUT}")


if __name__ == "__main__":
    main()
