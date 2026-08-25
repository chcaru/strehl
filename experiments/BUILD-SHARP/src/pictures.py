"""BUILD-SHARP step 3: the pictures. Clean, paired, one display transform.

Every arm in a pair is developed with the SAME exposure and the SAME tone
curve, derived ONCE from the reference arm and then applied to both. This is
not a nicety. A per-image auto-exposure is a per-image gain, and M20's C3
control measured a naive gradient statistic moving 8.25x under an
information-free gain change -- an eye is no more immune than a statistic.

No annotations of any kind are drawn. `baseline-full/` has debug ROI rectangles
burned in and those are not evidence, they are furniture.

Development goes through `scripts/crop_set.py`, unmodified, so these PNGs are
byte-comparable with the project's own baseline crops rather than being a
private pipeline nobody has checked.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import crop_set as CS  # noqa: E402

RENDERS = Path(r"C:\dev\strehl-out\BUILD-SHARP\renders")
OUT = Path(r"C:\dev\strehl-out\BUILD-SHARP\pictures")
ROI_PLAN = Path(r"C:\dev\strehl-out\roi-plan.json")


def read_linear(path: Path) -> np.ndarray:
    import tifffile

    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, not uint16 (rule 7)"
    return a.astype(np.float64)


def develop(lin: np.ndarray, gain: float) -> np.ndarray:
    """Camera-native linear -> sRGB 8-bit, at a GIVEN gain (never auto)."""
    rgb = lin * gain / 65535.0
    rgb = rgb @ np.asarray(CS.A7C2_CAM_TO_SRGB).T
    rgb = np.clip(rgb, 0.0, 1.0)
    # sRGB EOTF^-1
    a = 0.0031308
    enc = np.where(rgb <= a, 12.92 * rgb, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
    return np.clip(enc * 255.0 + 0.5, 0, 255).astype(np.uint8)


def shared_gain(lin: np.ndarray, pct: float = 99.7, target: float = 0.92) -> float:
    """One exposure for the whole pair, from the REFERENCE arm only."""
    v = lin.reshape(-1, lin.shape[-1]).max(axis=1)
    p = np.percentile(v[v > 0], pct)
    return float(target * 65535.0 / max(p, 1.0))


def save_png(arr: np.ndarray, path: Path, width: int | None = None):
    from PIL import Image

    im = Image.fromarray(arr, "RGB")
    if width and im.width != width:
        im = im.resize((width, round(im.height * width / im.width)),
                       Image.Resampling.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=True)
    return path


def rois_for(subject: str, n: int, shape) -> list[tuple[str, int, int]]:
    """The FROZEN ROI plan. Never `plan --force` (it voids every comparison).

    Stored as [x, y] pairs, on the BINNED grid. `scale` maps them onto whatever
    grid the render is on, so a full-resolution render and a binned one crop the
    same physical detail.
    """
    out = []
    if ROI_PLAN.exists():
        plan = json.loads(ROI_PLAN.read_text())
        entry = plan.get(subject) or plan.get("subjects", {}).get(subject) or {}
        pts = []
        rois = entry.get("rois") if isinstance(entry, dict) else None
        if isinstance(rois, dict):
            pts = rois.get("detail") or rois.get("edge") or []
        elif isinstance(entry, dict):
            for key in ("detail", "detail_rois", "rois"):
                v = entry.get(key)
                if isinstance(v, list):
                    pts = v
                    break
        elif isinstance(entry, list):
            pts = entry
        scale = shape[1] / 3516.0
        for i, xy in enumerate(pts[:n]):
            x, y = int(xy[0] * scale), int(xy[1] * scale)
            out.append((f"roi{i}", x, y))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--tag", default="ab")
    ap.add_argument("--full-width", type=int, default=1800)
    ap.add_argument("--crop", type=int, default=500,
                    help="100%% crop size, in OUTPUT pixels; no rescaling is "
                         "applied to crops, which is what 100%% means")
    ap.add_argument("--restore", action="store_true",
                    help="apply the gather-MTF restoration to the AFTER arm")
    ap.add_argument("--gain-cap", type=float, default=1.7)
    a = ap.parse_args()

    pa = RENDERS / a.subject / a.before / "linear.tif"
    pb = RENDERS / a.subject / a.after / "linear.tif"
    for p in (pa, pb):
        if not p.exists():
            print(f"missing {p}")
            return 1

    A = read_linear(pa)
    B = read_linear(pb)
    if A.shape != B.shape:
        print(f"shape mismatch {A.shape} vs {B.shape}")
        return 1
    print(f"{a.subject}: {A.shape}, before={a.before} after={a.after}")

    if a.restore:
        import restore as R
        g = B[:, :, 1].mean() / max(B[:, :, 1].mean(), 1e-9)
        for c in range(3):
            B[:, :, c], diag = R.restore(B[:, :, c], grid_factor=2.0,
                                         gain_cap=a.gain_cap)
        B = np.clip(B, 0, 65535)
        print("restore:", json.dumps({k: round(v, 5) for k, v in diag.items()}))
        del g

    gain = shared_gain(A)
    print(f"shared display gain (from BEFORE arm only): {gain:.6f}")

    da = develop(A, gain)
    db = develop(B, gain)

    root = OUT / a.subject
    p1 = save_png(da, root / f"{a.tag}-full-BEFORE.png", a.full_width)
    p2 = save_png(db, root / f"{a.tag}-full-AFTER.png", a.full_width)
    print(f"full: {p1}\n      {p2}")

    # 100% crops. Coordinates come from the frozen plan where it has them; where
    # it does not, fall back to the highest-detail tiles of the BEFORE arm, so
    # the choice is never made on the treatment.
    rois = rois_for(a.subject, 3, A.shape)
    if not rois:
        g = A[:, :, 1]
        s = a.crop
        H, W = g.shape
        best = []
        for y in range(s, H - 2 * s, s):
            for x in range(s, W - 2 * s, s):
                t = g[y:y + s, x:x + s]
                lap = np.abs(np.diff(t, 2, 0)[:, :-2] + np.diff(t, 2, 1)[:-2, :])
                best.append((float(lap.mean()), x, y))
        best.sort(reverse=True)
        picked, rois = [], []
        for score, x, y in best:
            if all(abs(x - px) > 2 * s or abs(y - py) > 2 * s for px, py in picked):
                picked.append((x, y))
                rois.append((f"detail{len(rois)}", x, y))
            if len(rois) == 3:
                break
        print("crop ROIs chosen on the BEFORE arm (highest Laplacian):", picked)

    s = a.crop
    for name, x, y in rois:
        x = int(np.clip(x - s // 2, 0, A.shape[1] - s))
        y = int(np.clip(y - s // 2, 0, A.shape[0] - s))
        ca = da[y:y + s, x:x + s]
        cb = db[y:y + s, x:x + s]
        save_png(ca, root / f"{a.tag}-crop-{name}-BEFORE.png")
        save_png(cb, root / f"{a.tag}-crop-{name}-AFTER.png")
        pair = np.concatenate([ca, np.full((s, 8, 3), 255, np.uint8), cb], axis=1)
        save_png(pair, root / f"{a.tag}-crop-{name}-PAIR.png")
        print(f"crop {name} at ({x},{y}) {s}x{s} -> "
              f"{root / f'{a.tag}-crop-{name}-PAIR.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
