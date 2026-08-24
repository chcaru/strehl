"""B15 -- is the 0.5060 % residual caused by the merge averaging clipped with
unclipped frames?

The shipped guard fires on `v_c >= ceil_c`, an equality against the container
ceiling. `write_merged` applies it to the MERGED value, but the merge averages
~55 frames per pixel. A sensel pinned at CONTAINER_MAX_DN in only *some* frames
averages to strictly below the ceiling, so the guard never fires -- while green
stays suppressed relative to red and blue, i.e. still magenta.

This reads the raw green planes directly and asks, per sensel, in what FRACTION
of frames it is pinned. Prediction registered in PREREGISTRATION.md B15:

    >= 95 % of pinned sensels at f == 1  ->  H-merge DEAD
    substantial mass at 0 < f < 1        ->  H-merge SUPPORTED

STRICTLY READ-ONLY on D:\\personal\\macro. Opens frames, writes nothing.
"""

import sys
from pathlib import Path

import numpy as np
import rawpy

CONTAINER_MAX = 16383


def green_planes(raw):
    """The two green sensels of each 2x2 CFA quad, as (G1, G2) planes.

    Sony ARW is RGGB, so within each quad greens sit at (0,1) and (1,0). Derived
    from the pattern rather than assumed, so a different CFA fails loudly.
    """
    pat = raw.raw_pattern
    img = raw.raw_image_visible
    h, w = img.shape
    h, w = h - (h % 2), w - (w % 2)
    img = img[:h, :w]
    out = []
    for dy in range(2):
        for dx in range(2):
            if raw.color_desc[pat[dy, dx]] == ord("G") or raw.color_desc.decode()[pat[dy, dx]] == "G":
                out.append(img[dy::2, dx::2])
    if len(out) != 2:
        raise SystemExit(f"expected 2 green sites in CFA, found {len(out)}")
    return out


def main():
    d = Path(sys.argv[1])
    stride = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    frames = sorted(d.glob("*.ARW"))
    if not frames:
        raise SystemExit(f"no .ARW under {d}")
    use = frames[::stride]
    print(f"{len(frames)} frames in {d.name}; sampling every {stride} -> {len(use)}")

    pinned = None
    total = 0
    for i, p in enumerate(use):
        with rawpy.imread(str(p)) as raw:
            g1, g2 = green_planes(raw)
            hit = (g1 >= CONTAINER_MAX) | (g2 >= CONTAINER_MAX)
        if pinned is None:
            pinned = np.zeros(hit.shape, dtype=np.uint16)
        pinned += hit.astype(np.uint16)
        total += 1
        if i % 5 == 0:
            print(f"  [{i + 1}/{len(use)}] {p.name}: {hit.sum():,} pinned green sensels")

    n = total
    ever = pinned > 0
    n_ever = int(ever.sum())
    print(f"\nsensels pinned in >= 1 of {n} frames: {n_ever:,} "
          f"({100.0 * n_ever / pinned.size:.4f} % of the green plane)")

    if n_ever == 0:
        print("INSTRUMENT CHECK FAILED: no saturation found at all. No conclusion.")
        sys.exit(4)

    f = pinned[ever].astype(np.float64) / n
    always = int((pinned[ever] == n).sum())
    partial = n_ever - always
    print(f"  f == 1 (pinned in EVERY frame) : {always:>12,}  {100.0 * always / n_ever:6.2f} %")
    print(f"  0 < f < 1 (pinned in SOME)     : {partial:>12,}  {100.0 * partial / n_ever:6.2f} %")

    if always == 0:
        print("INSTRUMENT CHECK FAILED: nothing is pinned in every frame.")
        sys.exit(4)

    print("\n  distribution of f over pinned sensels:")
    edges = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0001]
    hist, _ = np.histogram(f, bins=edges)
    for lo, hi, c in zip(edges[:-1], edges[1:], hist):
        bar = "#" * int(60 * c / max(hist.max(), 1))
        print(f"    [{lo:4.2f},{hi:5.2f})  {c:>12,}  {100.0 * c / n_ever:6.2f} %  {bar}")

    share_partial = 100.0 * partial / n_ever
    print(f"\n  mean f = {f.mean():.4f}   median f = {np.median(f):.4f}")
    if 100.0 * always / n_ever >= 95.0:
        verdict = "H-merge DEAD -- pinning is essentially all-or-nothing"
    elif share_partial >= 20.0:
        verdict = "H-merge SUPPORTED -- substantial partial pinning the guard cannot see"
    else:
        verdict = "H-merge WEAK -- partial pinning exists but is a small share"
    print(f"  B15 VERDICT: {verdict}")

    print(f"\n  registered comparison: the clip cleared ~74.7 % of the defect")
    print(f"  (2.0017 -> 0.5060). f == 1 share here is {100.0 * always / n_ever:.2f} %.")


if __name__ == "__main__":
    main()
