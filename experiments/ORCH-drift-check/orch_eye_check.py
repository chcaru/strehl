"""ORCH: did my eye read the noise comparison backwards?

I published, from a 1:1 visual reading of `119MSDCF__worst-on-subject.png`, that
`enfuse` is "visibly cleaner than us" in the flat field, and said this made the
measured 1.618x ratio "visible, not merely measured".

A verifier lane then reported the absolute sigmas: strehl 52.96/60.70/56.01,
enfuse 85.70/110.04/89.97 (x1000, lower = cleaner), and 85.70/52.96 = 1.618 --
the published ratio is comparator-over-strehl, so WE are the cleaner arm and my
sentence has the sign backwards.

Panels are not swapped: `panels` and `labels` are appended in the same loop
iteration keyed on the same variable, and the arm filenames in SETS are
`strehl-A.tiff` / `coh-enfuse-A.tif` / `coh-fs15-A.tif`.

So either my eye was wrong, or the site I looked at differs from the population
the sigma was measured over. This settles it by measuring noise on the EXACT
pixels I judged, in the exact display state I judged them in.

Two statistics, because they can disagree and the disagreement is informative:

  sigma_hp   high-frequency residual: std of (panel - 3px blur). This is grain.
  sigma_mid  mid-band residual, 20-60px. This is mottle.

Both are computed AFTER the display transform and AFTER the per-channel gain,
i.e. on the actual 8-bit pixels that reached my eye -- not on the linear data.
A statistic measured somewhere other than where the verdict was formed cannot
overturn the verdict.
"""
import json
from pathlib import Path

import numpy as np
import tifffile

ARMS = Path(r"C:\dev\strehl-out\V-NOISE2\119\arms")
MANIFEST = Path(r"C:\dev\strehl-out\DELIVER-V5\vs-the-field\manifest-119MSDCF.json")
FILES = {"strehl": "strehl-A.tiff", "enfuse": "coh-enfuse-A.tif",
         "focus-stack": "coh-fs15-A.tif"}
CROP = 400


def boxblur(a, r):
    if r < 1:
        return a
    k = 2 * r + 1
    p = np.pad(a, ((r, r), (0, 0)), mode="reflect")
    c = np.concatenate([np.zeros((1, p.shape[1]), a.dtype), np.cumsum(p, axis=0)], axis=0)
    o = (c[k:] - c[:-k]) / k
    p = np.pad(o, ((0, 0), (r, r)), mode="reflect")
    c = np.concatenate([np.zeros((p.shape[0], 1), a.dtype), np.cumsum(p, axis=1)], axis=1)
    o = (c[:, k:] - c[:, :-k]) / k
    assert o.shape == a.shape, f"boxblur changed shape {a.shape} -> {o.shape}"
    return o


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def main():
    man = json.loads(MANIFEST.read_text())
    site = None
    for s in man["sites"]:
        if s.get("label") == "worst-on-subject":
            site = s
            break
    if site is None:
        raise SystemExit("worst-on-subject not in manifest -- cannot locate the "
                         "pixels the verdict was formed on")
    y, x = site["y"], site["x"]
    expo = site["exposure"]
    fits = site["fits"]
    print(f"site worst-on-subject  y={y} x={x}  exposure x{expo:.4g}")

    out = {}
    for k, fn in FILES.items():
        a = tifffile.imread(str(ARMS / fn)).astype(np.float32)   # 16-bit units
        dy, dx = fits[k]["shift"]
        c = a[y + dy:y + dy + CROP, x + dx:x + dx + CROP, :3]
        g = np.array(fits[k]["gain"], dtype=np.float32)
        o = np.array(fits[k]["offset"], dtype=np.float32)
        c = c * g[None, None, :] + o[None, None, :]
        # Exactly display(): the pixels that reached my eye.
        v = np.clip(c / 65535.0 * expo, 0.0, 1.0)
        disp = srgb(v) * 255.0
        hp, mid = [], []
        for ch in range(3):
            p = disp[..., ch]
            hp.append(float(np.std(p - boxblur(p, 1))))
            mid.append(float(np.std(boxblur(p, 10) - boxblur(p, 30))))
        out[k] = (np.array(hp), np.array(mid))
        print(f"  {k:12s} sigma_hp  {hp[0]:6.3f}/{hp[1]:6.3f}/{hp[2]:6.3f}"
              f"   sigma_mid {mid[0]:6.3f}/{mid[1]:6.3f}/{mid[2]:6.3f}   (8-bit codes)")

    print()
    s_hp, s_mid = out["strehl"]
    for k in ("enfuse", "focus-stack"):
        o_hp, o_mid = out[k]
        rh = float(np.mean(o_hp / np.maximum(s_hp, 1e-9)))
        rm = float(np.mean(o_mid / np.maximum(s_mid, 1e-9)))
        vh = "strehl cleaner" if rh > 1 else "COMPARATOR CLEANER"
        vm = "strehl cleaner" if rm > 1 else "COMPARATOR CLEANER"
        print(f"  {k}/strehl  grain {rh:.3f} -> {vh}    mottle {rm:.3f} -> {vm}")


if __name__ == "__main__":
    main()
