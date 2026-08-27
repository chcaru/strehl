"""Are the dark blobs in the smooth merge tiles optical dust, or merge artefacts?

This is my lane's central question -- retouch or reshoot -- asked about a defect
class none of my instruments ever sampled.  It has one clean discriminator:

    Dust in the optical path is present in EVERY frame, so it must appear in
    BOTH arms.  A blob present in the merge and absent from the source frame
    at the same coordinates was MADE BY THE MERGE.

The eye cannot settle it from the 1:1 render, because at a +/-25 DN stretch the
frame arm is noise-saturated (sd 70.4 DN against the merge's 24.0) and shows a
uniform salt-and-pepper field.  Reading "no discs in the frame" off that image
would be reading a deaf instrument as a silent one -- the exact failure ORCH
documented tonight.  So the frame arm is not asked to show a disc at 1:1; it is
asked for the MEAN DEPTH over the disc's own footprint, where averaging N~2000
px converts 70 DN of pixel noise into ~1.5 DN of uncertainty on the mean.

Every depth below is therefore quoted with its own uncertainty, and the
detection floor is stated rather than implied.  "Absent" here means "absent at
or above X DN", with X printed.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402
from smoothlook import detrend  # noqa: E402

TILES = os.path.join(tri.OUT, "tiles")
SUBS = ["highly-angled-ruler-mm-cpl", "pencil-steep-angle-cpl",
        "pencil-flatter-angle-cpl"]
BLOB_SIGMA = 8.0     # << blob scale, so blobs survive; >> pixel noise
MIN_PX = 300         # a blob smaller than this cannot be ORCH's 40-100 px dust


def find_blobs(res: np.ndarray, k: float = 4.0):
    """Dark connected components in the detrended merge, k robust sigma down.

    ROBUST scale, not `std`: the blobs are exactly the large excursions that
    inflate a standard deviation, so an sd-based threshold is raised by the
    signal it is trying to find and goes quiet as the defect gets worse.  On
    this corpus that was not hypothetical -- sd gave -55 DN on a tile whose
    picture shows about fifteen discs, and found one.
    """
    from scipy import ndimage
    sm = ndimage.gaussian_filter(res, BLOB_SIGMA)
    mad = float(np.median(np.abs(sm - np.median(sm))))
    thr = float(np.median(sm)) - k * 1.4826 * mad
    lab, n = ndimage.label(sm < thr)
    out = []
    for i in range(1, n + 1):
        m = lab == i
        # Reject blobs touching the border: a partial disc has an unusable
        # annulus and its depth is measured against content outside the tile.
        if m.sum() < MIN_PX:
            continue
        if m[0, :].any() or m[-1, :].any() or m[:, 0].any() or m[:, -1].any():
            continue
        out.append(m)
    return out, thr


def depth(res: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    """Mean depth in the mask relative to a surrounding annulus, and its sd.

    Relative to an annulus, not to zero: the detrend leaves a slowly varying
    pedestal and an absolute mean would read that pedestal as signal.
    """
    from scipy import ndimage
    ring = ndimage.binary_dilation(mask, iterations=25) & ~ndimage.binary_dilation(
        mask, iterations=6)
    if ring.sum() < 50:
        return float("nan"), float("nan")
    d = float(res[mask].mean() - res[ring].mean())
    # uncertainty on the difference of two means, from the pixel noise
    sd = float(res[ring].std())
    se = sd * np.sqrt(1.0 / mask.sum() + 1.0 / ring.sum())
    return d, se


def commission(frame_res: np.ndarray) -> tuple[float, float]:
    """Plant a disc of known depth in the FRAME arm; report recovery + floor.

    Without this the frame arm's null means nothing.  Anchored: a plant that
    fails to land raises rather than returning a flattering recovery.
    """
    from scipy import ndimage
    h, w = frame_res.shape
    yy, xx = np.mgrid[0:h, 0:w]
    disc = ((yy - h // 3) ** 2 + (xx - w // 3) ** 2) <= 25.0 ** 2
    assert disc.sum() > MIN_PX, "PLANT DID NOT LAND -- disc below MIN_PX"
    planted = 6.0
    spiked = frame_res.copy()
    spiked[disc] -= planted
    got, se = depth(spiked, disc)
    assert np.isfinite(got), "PLANT DID NOT LAND -- non-finite recovery"
    base, _ = depth(frame_res, disc)          # same footprint, no plant
    return (got - base) / -planted, 3.0 * se  # recovery fraction, 3-sigma floor


def main() -> int:
    import json
    for sub in SUBS:
        z = np.load(os.path.join(TILES, f"{sub}.FLAT.npz"))
        mr = detrend(z["merge"].astype(np.float32))
        fr = detrend(z["frame"].astype(np.float32))
        rec, floor = commission(fr)
        blobs, thr = find_blobs(mr)
        with open(os.path.join(tri.OUT, "compare", sub + ".json"),
                  encoding="utf-8") as fh:
            site = json.load(fh)["sites"]["FLAT"]
        print(f"\n{sub}   ({len(blobs)} blobs >= {MIN_PX} px, robust "
              f"threshold {thr:.2f} DN)")
        # CONTROL: the two arms must actually be the same content, or a blob
        # "absent from the frame" is just a blob that moved out of the window.
        print(f"   registration: ncc {site.get('ncc'):.4f}  "
              f"dx {site.get('dx')} dy {site.get('dy')}"
              f"{'   <== POOR MATCH, arms may not correspond'
                 if (site.get('ncc') or 0) < 0.7 else ''}")
        print(f"   frame arm commissioned: planted disc recovered at "
              f"{rec:.2f}x, 3-sigma floor {floor:.2f} DN"
              f"{'   <== DEAF, null is meaningless' if rec < 0.5 else ''}")
        # CONTROL 2: run the SAME detector on the frame arm independently.  If
        # the frame has no dark blob ANYWHERE in the tile, then no registration
        # error can explain the absence at the footprint -- there is nothing
        # anywhere for a shift to have moved out of place.
        fblobs, fthr = find_blobs(fr)
        print(f"   frame arm, same detector: {len(fblobs)} blob(s) anywhere in "
              f"the tile (robust threshold {fthr:.2f} DN)")
        for i, m in enumerate(blobs):
            dm, sm_ = depth(mr, m)
            df, sf = depth(fr, m)
            if not np.isfinite(df):
                continue
            # Ask for a MAGNITUDE, not a boolean.  "Is it in the frame too?"
            # answers yes to a 15 DN dip under a 750 DN merge blob; "how much
            # of it is in the frame?" reports 2% and polices itself.
            share = df / dm if dm else float("nan")
            v = (f"{share * 100:5.1f}% of the merge blob is in the frame"
                 if share > 0.5 else
                 f"MERGE-MADE: only {max(share, 0) * 100:.1f}% present in "
                 f"frame (sensitive to {3 * sf:.2f} DN)")
            print(f"   blob {i:2d} {int(m.sum()):6d}px  merge {dm:9.2f} "
                  f"+/-{sm_:5.2f}   frame {df:8.2f} +/-{sf:5.2f}   {v}")

        # STACK every blob into one footprint.  A single 800 px disc leaves the
        # frame arm's mean uncertain to ~2.5 DN; twenty of them together cut
        # that by sqrt(20).  This is the only version of the measurement with
        # the sensitivity to separate "optical, in every frame" from
        # "made by the merge" at the amplitude these discs actually have.
        if len(blobs) > 1:
            allm = np.zeros_like(blobs[0])
            for m in blobs:
                allm |= m
            dm, sm_ = depth(mr, allm)
            df, sf = depth(fr, allm)
            share = df / dm if dm else float("nan")
            print(f"   STACKED {len(blobs)} blobs, {int(allm.sum())}px:  "
                  f"merge {dm:8.2f} +/-{sm_:5.2f}   frame {df:7.2f} "
                  f"+/-{sf:5.2f}   -> {share * 100:5.1f}% of the merge depth "
                  f"is present in the frame")

        # Look at what was measured.  A number describing a region nobody has
        # seen is how subject content gets reported as a defect.
        if blobs:
            from PIL import Image, ImageDraw
            from scipy import ndimage
            cell = mr.shape[0]
            im = Image.new("RGB", (2 * cell + 12, cell + 26), (16, 16, 16))
            for j, res in enumerate((mr, fr)):
                v8 = np.clip(res / 25.0 * 127.0 + 128.0, 0, 255).astype(np.uint8)
                im.paste(Image.fromarray(np.dstack([v8] * 3)), (j * (cell + 12), 0))
            dr = ImageDraw.Draw(im)
            for m in blobs:
                edge = m & ~ndimage.binary_erosion(m, iterations=2)
                ys, xs = np.nonzero(edge)
                for j in (0, 1):
                    for yy, xx in zip(ys[::3], xs[::3]):
                        dr.point((int(xx) + j * (cell + 12), int(yy)),
                                 fill=(255, 40, 40))
            dr.text((4, cell + 6), f"{sub}   LEFT merge / RIGHT frame, "
                    f"+/-25 DN, red = measured footprint", fill=(235, 235, 235))
            p = os.path.join(tri.OUT, "smooth", f"blobs-{sub}.png")
            im.save(p)
            print(f"   overlay -> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
