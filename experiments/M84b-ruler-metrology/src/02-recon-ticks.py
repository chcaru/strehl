"""M84 step 02 - RECONNAISSANCE 3. Tick structure and local compression.

Still pre-registration reconnaissance (declared in PREREGISTRATION.md section 0).

  R4  What is the actual tick comb on the flat-on ruler? Fundamental or harmonic?
  R5  What is the local tick period in the angled stack's in-focus band?
  R6  Native-resolution crops of both, so the design is made against pixels.

Reads READ-ONLY from D:\\personal\\macro.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import rawpy
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CORPUS = pathlib.Path(r"D:\personal\macro")


def green_luma(path: pathlib.Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = float(np.max(raw.black_level_per_channel))
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    g1 = cfa[0:h:2, 1:w:2]
    g2 = cfa[1:h:2, 0:w:2]
    return 0.5 * (g1 + g2) - black


def png(sub: np.ndarray, path: pathlib.Path) -> None:
    lo, hi = np.percentile(sub, [0.5, 99.5])
    img = np.clip((sub - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    Image.fromarray((img * 255).astype(np.uint8)).save(path)


def spectrum_report(prof: np.ndarray, label: str, top: int = 6) -> list[dict]:
    p = prof - np.mean(prof)
    n = len(p)
    spec = np.abs(np.fft.rfft(p * np.hanning(n))) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0)
    lo = max(1, int(np.searchsorted(freqs, 3.0 / n)))
    hi = int(np.searchsorted(freqs, 0.45))
    order = lo + np.argsort(spec[lo:hi])[::-1][:top]
    rows = []
    total = float(np.sum(spec[lo:hi]))
    for k in order:
        rows.append({"period_px": float(1.0 / freqs[k]), "rel_power": float(spec[k] / total)})
    print(f"  {label}: " + ", ".join(f"{r['period_px']:.2f}px({r['rel_power']:.3f})" for r in rows))
    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rep: dict[str, object] = {}

    flat = sorted((CORPUS / "flat-on-ruler-cpl").glob("*.ARW"))
    plane = green_luma(flat[19])
    h, w = plane.shape
    print(f"flat plane {w}x{h}")
    png(plane[h - 700 : h, 0:1400], OUT / "native-flat-f019-comb.png")
    png(plane[h - 700 : h, 1400:2800], OUT / "native-flat-f019-comb2.png")

    flat_rows = []
    for y in (int(h * 0.82), int(h * 0.88), int(h * 0.94), h - 30):
        prof = plane[y - 12 : y + 12, :].mean(axis=0)
        flat_rows.append({"y": y, "peaks": spectrum_report(prof, f"flat y={y}")})
        np.save(OUT / f"flat-prof-y{y}.npy", prof)
    rep["flat_spectra"] = flat_rows

    # Direct tick localisation: threshold the profile and take run centroids.
    y = h - 30
    prof = plane[y - 12 : y + 12, :].mean(axis=0)
    sm = np.convolve(prof, np.ones(9) / 9.0, mode="same")
    thr = 0.5 * (np.percentile(sm, 5) + np.percentile(sm, 95))
    dark = sm < thr
    runs = []
    i = 0
    while i < len(dark):
        if dark[i]:
            j = i
            while j < len(dark) and dark[j]:
                j += 1
            if j - i >= 8:
                runs.append(0.5 * (i + j - 1))
            i = j
        else:
            i += 1
    d = np.diff(runs)
    print(f"flat y={y}: {len(runs)} dark runs; gaps min={d.min():.2f} med={np.median(d):.2f} max={d.max():.2f}")
    print("  gaps:", np.round(d, 2).tolist())
    rep["flat_runs"] = {"y": y, "centres": [float(r) for r in runs], "gaps": [float(x) for x in d]}

    ang = sorted((CORPUS / "highly-angled-ruler-mm-cpl").glob("*.ARW"))
    ang_rows = []
    for fi, col_tile in ((40, 13), (120, 14), (200, 16), (298, 18)):
        pl = green_luma(ang[fi])
        x0 = col_tile * 128 - 200
        x1 = col_tile * 128 + 328
        png(pl[600:1800, x0:x1], OUT / f"native-ang-f{fi:03d}-band.png")
        yb = 1200
        prof = pl[yb - 60 : yb + 60, x0:x1].mean(axis=0)
        ang_rows.append(
            {"frame": fi, "x0": x0, "x1": x1, "y": yb,
             "peaks": spectrum_report(prof, f"ang f{fi:03d} x[{x0}:{x1}]")}
        )
        np.save(OUT / f"ang-prof-f{fi:03d}.npy", prof)
    rep["angled_spectra"] = ang_rows

    (OUT / "02-recon.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
