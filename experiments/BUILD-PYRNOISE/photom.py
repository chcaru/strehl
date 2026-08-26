"""Is the admission test's rejection of leaf-2-cpl a property of the subject,
or a MISSING TERM in the test? The orchestrator asked for exactly this, and
`gated.py` has just made it the live question.

WHAT HAS ALREADY BEEN RULED OUT for leaf-2-cpl's admission failure:
  * drift / misregistration -- compensated with a +/-24 px per-frame NCC search
    (the +/-10 search had SATURATED), and the ratio did not fall: 1.494 -> 1.520
    at the claim's patch. It got slightly WORSE.
  * bracket-wide averaging -- restricting the temporal sd to each pixel's k
    sharpest frames barely moved it (1.494 -> 1.401 at k=3). The region is not
    stationary even across the frames a merge would use.
  * the bar -- a synthetic stationary bracket built from this subject's own
    pixels reads 0.702, and 109MSDCF's admitted patch reads 1.117, against
    leaf-2-cpl's 1.494-3.11. Nothing in [0.75, 1.40] changes the verdict.

WHAT HAS NOT BEEN RULED OUT, and is named by the run's own banner:

    gain span       : 1.1010 (max/min across 182 frames)
    --- photometric normalisation (M99, OPT-IN) --- mode : on

  The MERGE fits and removes a per-frame gain. A SINGLE FRAME cannot -- there is
  nothing to normalise against -- so the single frames the admission test reads
  carry a level drift of up to 10% that neither arm ever sees. A 3% level
  wobble on a 3000 DN patch is ~90 DN of temporal sd, which is the same size as
  this patch's entire measured excess. If that is what the test is reading, the
  test is charging the subject for a term the merge removes, and the rejection
  is an artifact of the instrument.

  Direction of the error, stated before measuring: removing a per-frame gain can
  only LOWER the temporal sd, so this control can only ever WEAKEN my own
  rejection. It cannot manufacture one.

THE CONTROLS.
  I1  per-frame multiplicative gain removed (each frame's patch scaled to the
      common mean). This is what the merge's photometric normalisation does.
  I2  per-frame additive offset removed. Distinguishes a gain drift from a
      black-level drift; the merge fits a gain, so if I2 explains it and I1
      does not, the merge does NOT remove it and the subject is still at fault.
  I3  the per-frame patch-mean series itself, compared against the banner's own
      `gain span 1.1010`. An independent read of the same physical quantity.
  I4  the same correction applied to 109MSDCF, whose banner-quoted drift is
      0.91% -- the QUIETEST stack in the corpus. A correction that is real must
      barely move an already-quiet subject. If I1 moves 109MSDCF as much as it
      moves leaf-2-cpl, it is removing something other than drift.
  I5  the whole-plane admissible-patch count, before and after. This is the
      number that decides whether leaf-2-cpl can carry a flat-ROI noise claim.
"""

import json
import pathlib
import sys

import numpy as np

import admission
import pyrnoise as pn

RENDERS = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\renders")
CLAIM = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\claim")


def load(sub):
    d = RENDERS / sub
    frames = sorted(p.stem for p in d.glob("frame*.tif"))
    return {f: pn.green(d / f"{f}.tif") for f in frames}, frames


def admission_corrected(imgs, frames, roi, mode="none"):
    """Admission with a per-frame level term removed before the temporal sd.

    The spatial term is deliberately left alone: a scalar gain multiplies a
    frame's noise and its signal together, so hp_sd already scales with it and
    re-scaling would double-count. Only the temporal estimate is corrected.
    """
    pad = pn.BOX
    x, y, w, h = roi
    big = np.stack([imgs[f][y - pad:y + h + pad, x - pad:x + w + pad].astype(np.float64)
                    for f in frames])
    core = big[:, pad:-pad, pad:-pad]
    means = core.reshape(len(frames), -1).mean(axis=1)
    if mode == "gain":
        core = core * (means.mean() / means)[:, None, None]
    elif mode == "offset":
        core = core - (means - means.mean())[:, None, None]
    temporal = float(core.std(axis=0, ddof=1).mean())
    spatial = float(np.mean([pn.hp_sd(b) for b in big]))
    return temporal / spatial, temporal, spatial, means


def main():
    print("=" * 78)
    print("IS THE ADMISSION TEST MISSING A PHOTOMETRIC TERM?")
    print("=" * 78)

    leaf, lf = load("leaf-2-cpl")
    rois = {"leaf claim patch": (292, 500, 100, 100),
            "leaf pinned patch": (284, 702, 100, 100),
            "leaf best window": (504, 312, 100, 100)}
    print(f"\nI1/I2/I3  leaf-2-cpl, {len(lf)} of 182 frames "
          f"(banner: gain span 1.1010 across the full 182)")
    print(f"   {'patch':<20}{'level':>9}{'span':>8}{'raw':>8}{'-gain':>8}{'-offset':>9}")
    store = {}
    for lbl, roi in rois.items():
        r0, t0, s0, mn = admission_corrected(leaf, lf, roi, "none")
        r1 = admission_corrected(leaf, lf, roi, "gain")[0]
        r2 = admission_corrected(leaf, lf, roi, "offset")[0]
        span = mn.max() / mn.min()
        print(f"   {lbl:<20}{mn.mean():9.0f}{span:8.4f}{r0:8.3f}{r1:8.3f}{r2:9.3f}"
              f"   {'PASS' if r1 <= admission.BAR else 'FAIL'} after gain removal")
        store[lbl] = {"raw": r0, "gain": r1, "offset": r2, "span": float(span),
                      "level": float(mn.mean())}

    print(f"\nI4  the same correction on 109MSDCF -- banner-quoted drift 0.91%,")
    print(f"    the quietest stack in the corpus. A real drift correction must")
    print(f"    barely move it. If it moves as much as leaf-2-cpl, it is removing")
    print(f"    something other than drift and I1 proves nothing.")
    m9, f9 = load("109MSDCF")
    for lbl, roi in (("109 admitted patch", (1416, 264, 256, 256)),):
        r0, t0, s0, mn = admission_corrected(m9, f9, roi, "none")
        r1 = admission_corrected(m9, f9, roi, "gain")[0]
        r2 = admission_corrected(m9, f9, roi, "offset")[0]
        print(f"   {lbl:<20}{mn.mean():9.0f}{mn.max() / mn.min():8.4f}{r0:8.3f}{r1:8.3f}{r2:9.3f}")
        print(f"     leaf's raw->gain move  {store['leaf claim patch']['raw']:.3f} ->"
              f" {store['leaf claim patch']['gain']:.3f}"
              f"  ({(1 - store['leaf claim patch']['gain'] / store['leaf claim patch']['raw']) * 100:+.1f}%)")
        print(f"     109's  raw->gain move  {r0:.3f} -> {r1:.3f}  ({(1 - r1 / r0) * 100:+.1f}%)")
        store[lbl] = {"raw": r0, "gain": r1, "offset": r2,
                      "span": float(mn.max() / mn.min()), "level": float(mn.mean())}

    print(f"\nI5  whole-plane admissible-patch count on leaf-2-cpl, before and after")
    H, W = leaf[lf[0]].shape
    w = h = 100
    raw, gain = [], []
    for yy in range(160, H - h - 160, 128):
        for xx in range(160, W - w - 160, 128):
            roi = (xx, yy, w, h)
            raw.append(admission.admission(leaf, lf, roi)[0])
            gain.append(admission_corrected(leaf, lf, roi, "gain")[0])
    raw = np.array(raw)
    gain = np.array(gain)
    print(f"   {len(raw)} windows of {w}x{h}")
    print(f"     raw            admissible {int((raw <= admission.BAR).sum()):4d}"
          f"   median {np.median(raw):.2f}   min {raw.min():.2f}")
    print(f"     gain-corrected admissible {int((gain <= admission.BAR).sum()):4d}"
          f"   median {np.median(gain):.2f}   min {gain.min():.2f}")
    print(f"     median reduction from removing the per-frame level: "
          f"{(1 - np.median(gain) / np.median(raw)) * 100:.1f}%")

    json.dump({"patches": store, "raw": raw.tolist(), "gain": gain.tolist()},
              open(CLAIM / "_photom.json", "w"), indent=1, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main())
