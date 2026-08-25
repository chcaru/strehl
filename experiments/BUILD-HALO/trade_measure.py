"""The trade, both axes, one table.

ORCH asked for the honest shape of it: how much halo reduction, at how much
couch-fibers softening, across the range of the fix's strength.  Two axes, two
subjects, one knob.

THE HALO AXIS is measured against a SINGLE FRAME, not against another merge.
`STREHL_ONLY_FRAME=221` renders the background-focused frame with no election
at all, so it cannot contain a selection artifact; frame 221 is what the far
background of this subject actually elects, read off the election map rather
than guessed.  The halo is then the merge's departure from that frame in the
near-edge band, referenced to a far band so that the scene's own illumination
field -- which is common to both terms and is real, not an artefact -- cancels.
That referencing is not optional: it is the confound that killed two earlier
attempts at this measurement, ORCH's and mine.

NO GRADIENT OR HIGH-PASS ENERGY IS USED TO SCORE THE HALO.  A high-pass score
is satisfied by injected structure and has already fooled two agents on this
exact artefact.  What is scored here is a signed departure in DN from a
no-election reference, which injected structure cannot flatter.

THE TEXTURE AXIS IS A PLACEBO, WHICH IS WHY IT IS TRUSTWORTHY.  couch-fibers
has no depth silhouettes, so the fix has nothing to treat and the correct
result is a no-op.  The primary number is therefore deviation from the off arm
-- any deviation at all is damage, and it needs no interpretation and no
threshold.  A local-SD ratio is reported beside it to give the deviation a
DIRECTION (softer or sharper), and it carries the high-pass caveat: read it
only for its sign, and only next to the placebo number that cannot be gamed.

THE MASK IS FROZEN ACROSS ARMS.  It is computed once from the off arm's
election map.  Recomputing it per arm would let the fix move its own goalposts:
a stronger collapse changes the winner field, which would change the
silhouette, which would change which pixels the halo is measured over.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
from depth_profile import depth_mask, luma  # noqa: E402

TRADE = Path(r"C:\dev\strehl-out\TRADE")
VEIL = Path(r"C:\dev\strehl-out\VEIL")
HALO_SUBJ = "flower-bud-with-background-fern-cpl"
TEX_SUBJ = "couch-fibers-cpl"
ARMS = ["off", "default", "tau064", "tau032", "tau016", "tau008", "tau004"]

NEAR = (1, 20)      # the window zone: where the merge departs from single frames
FAR = 300           # reference: far enough that the merge and the frame agree


def arm_path(subj, arm):
    return TRADE / f"{subj}-{arm}.tif"


def frozen_mask():
    """Depth silhouette, computed ONCE from the off arm's election map."""
    emap = VEIL / f"{HALO_SUBJ}-election.tif"
    if not emap.exists():
        sys.exit(f"missing election map {emap}")
    elect = tifffile.imread(str(emap))
    if elect.ndim == 3:
        elect = elect[..., 0]
    m_plane, _ = depth_mask(elect)
    return m_plane


def to_render_grid(m_plane, shape):
    scale = shape[0] / m_plane.shape[0]
    if abs(scale - round(scale)) > 1e-6:
        sys.exit(f"non-integer grid ratio {scale}")
    scale = int(round(scale))
    m = m_plane if scale == 1 else np.repeat(np.repeat(m_plane, scale, 0), scale, 1)
    if m.shape != shape:
        m = m[:shape[0], :shape[1]]
        if m.shape != shape:
            m = np.pad(m, [(0, shape[i] - m.shape[i]) for i in range(2)], mode="edge")
    return m, scale


def halo_axis():
    ref_p = arm_path(HALO_SUBJ, "f221")
    if not ref_p.exists():
        print(f"  reference frame not rendered yet: {ref_p.name}")
        return []
    ref = luma(ref_p)

    m_plane = frozen_mask()
    m, scale = to_render_grid(m_plane, ref.shape)
    # ~m is essential: distance_transform_edt returns 0 INSIDE the mask, so
    # without it the near band swallows the subject itself.
    d = ndimage.distance_transform_edt(~m)
    near_sel = (d >= NEAR[0]) & (d < NEAR[1]) & ~m
    far_sel = (d > FAR) & ~m
    print(f"  mask {m.mean():.1%} of frame, grid ratio {scale}x, "
          f"window support {14 * scale} px")
    print(f"  near band {NEAR[0]}-{NEAR[1]} px: {int(near_sel.sum()):,} px    "
          f"far reference >{FAR} px: {int(far_sel.sum()):,} px")
    if near_sel.sum() < 5000 or far_sel.sum() < 20000:
        sys.exit("bands too small to trust")

    rows = []
    for arm in ARMS:
        p = arm_path(HALO_SUBJ, arm)
        if not p.exists():
            continue
        diff = luma(p) - ref
        near = float(np.median(diff[near_sel]))
        far = float(np.median(diff[far_sel]))
        # In DN of a 16-bit render, referenced so the illumination field cancels.
        rows.append((arm, (near - far) * 65535.0))
    return rows


def texture_axis():
    off_p = arm_path(TEX_SUBJ, "off")
    if not off_p.exists():
        print(f"  off arm not rendered yet: {off_p.name}")
        return []
    off = luma(off_p)
    k = 3
    mean0 = ndimage.uniform_filter(off, k)
    sd0 = np.sqrt(np.clip(ndimage.uniform_filter(off * off, k) - mean0 * mean0, 0, None))
    # Judge softening only where there is texture to lose.
    textured = sd0 > np.median(sd0)
    print(f"  textured pixels (local SD above its own median): "
          f"{int(textured.sum()):,} of {off.size:,}")

    rows = []
    for arm in ARMS:
        p = arm_path(TEX_SUBJ, arm)
        if not p.exists():
            continue
        a = luma(p)
        dev = (a - off) * 65535.0
        rms = float(np.sqrt(np.mean(dev * dev)))
        p999 = float(np.percentile(np.abs(dev), 99.9))
        changed = float(np.mean(np.abs(dev) > 0.5))
        mean1 = ndimage.uniform_filter(a, k)
        sd1 = np.sqrt(np.clip(ndimage.uniform_filter(a * a, k) - mean1 * mean1, 0, None))
        ratio = float(np.median(sd1[textured]) / np.median(sd0[textured]))
        rows.append((arm, rms, p999, changed, ratio))
    return rows


def main():
    print("=" * 78)
    print("THE TRADE: halo reduction against couch-fibers softening")
    print("=" * 78)

    print(f"\nHALO AXIS -- {HALO_SUBJ}")
    print("  merge minus the background-focused single frame (221), near-edge")
    print("  band referenced to the far field. 0 = the merge agrees with a")
    print("  render that has no election in it. Signed DN of 65535.\n")
    h = halo_axis()
    if h:
        base = dict(h).get("off")
        print(f"  {'arm':<10} {'halo (DN)':>12} {'vs off':>10}")
        print("  " + "-" * 34)
        for arm, v in h:
            rel = "" if base in (None, 0) else f"{100.0 * v / base:>9.0f}%"
            print(f"  {arm:<10} {v:>+12.1f} {rel:>10}")

    print(f"\n\nTEXTURE AXIS -- {TEX_SUBJ} (no depth silhouettes: a no-op is correct)")
    print("  deviation from the off arm. Any deviation is damage; the SD ratio")
    print("  gives it a direction (<1 = softer).\n")
    t = texture_axis()
    if t:
        print(f"  {'arm':<10} {'rms dev':>9} {'p99.9':>9} {'px moved':>10} {'SD ratio':>10}")
        print("  " + "-" * 52)
        for arm, rms, p999, changed, ratio in t:
            print(f"  {arm:<10} {rms:>9.2f} {p999:>9.1f} {changed:>9.2%} {ratio:>10.4f}")

    if h and t:
        print("\n\nTHE TRADE, BOTH AXES TOGETHER")
        th = dict(h)
        base = th.get("off")
        print(f"  {'arm':<10} {'halo (DN)':>12} {'halo left':>11} "
              f"{'texture SD':>12} {'texture lost':>14}")
        print("  " + "-" * 63)
        for arm, rms, p999, changed, ratio in t:
            v = th.get(arm)
            if v is None:
                continue
            left = "" if base in (None, 0) else f"{100.0 * v / base:>10.0f}%"
            print(f"  {arm:<10} {v:>+12.1f} {left:>11} {ratio:>12.4f} "
                  f"{100.0 * (1 - ratio):>13.2f}%")


if __name__ == "__main__":
    main()
