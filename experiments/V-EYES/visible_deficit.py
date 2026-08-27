"""Is the measured softness deficit VISIBLE at true 1:1, or only measurable?

A 19% deficit in a band-energy statistic and a visible loss of detail are
different claims, and only the second blocks a print-quality assertion. This cuts
the master and the per-site best frame at the SAME site, at a crop size the
viewer cannot resample away, and asks the question with the eye.

WHY THERE IS A POSITIVE CONTROL. "I could not see it" is worthless unless the
viewing path could have shown it. So the panel set contains the master degraded
by EXACTLY the measured deficit -- sigma solved by bisection so the crop's
high-pass energy lands on the measured ratio, not guessed. If that panel is
indistinguishable from the master too, the test has no power at this effect size
and the correct output is a refusal, not a clean bill of health. This project has
already shipped an instrument that was blind and read as green; a visual verdict
gets the same commissioning as a numeric one.

WHY THERE IS A NULL. The master against itself. If I report a difference between
two identical panels, my discrimination is confabulated and every other panel in
the set is void.

SITE CHOICE. Two modes, because they answer different questions and the first
run of this script conflated them.

`median` (default) is the HEADLINE test. The claim under audit is that the median
site holds ~81% of the per-site best frame's detail, so the site that tests it is
one whose own ratio sits at that median. Among the blocks within 2% of the median
it takes the highest-contrast one, so the crop contains structure an eye can
actually adjudicate rather than a flat patch that happens to score.

`worst` is a DIAGNOSTIC, not the headline, and the first run showed why it must
not be used as one. On 119MSDCF the worst live block scored 0.0216 -- the master
holding 2% of the frame's detail -- while over the whole 380 px crop containing
it the master led the frame 1.0433. A single 64 px block at the 0.3rd percentile
is an outlier (alignment residual, a moved element, a noise spike), not the
effect the headline describes. The bisection also could not reach 0.0216 at all,
bottoming out at 0.0806 against its 4.0 px ceiling, so the control was not a
control. A site that cannot be matched by the planted arm cannot be judged by it.

THE ENCODE IS COMMON-MODE AND STATED. All panels: linear -> /scale -> gamma 2.2
-> 8 bit, where `scale` comes from the MASTER crop alone and is reused verbatim.
Per-panel autoscaling would fabricate a contrast difference and this comparison
is exactly the one that would be destroyed by it.

A CAVEAT THAT RUNS AGAINST THE MASTER, stated because it cannot be removed: a
single frame is noisier than a merge over hundreds, and noise carries top-octave
energy and reads as acutance. The frame panel may look crisper partly because it
is grainier. The noise floor each panel subtracts is printed so the size of that
effect is visible rather than argued.

Usage:
  python visible_deficit.py <subject> [size]
"""

import pathlib
import sys

import cv2
import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from corpus_softness import BLOCK, SCRATCH, luma32, pick_tile  # noqa: E402
from softness_verdict3 import (  # noqa: E402
    build_envelope, contrast, detail, shift_of, warp,
)

CROP = 380  # V-EYES commissioning: viewer resolves 1 px detail to ~400 px.
OUT = pathlib.Path(r"C:\dev\strehl-out\V-EYES\visible")


def encode(a, scale):
    """Linear -> display, identical for every panel. Stated, not autoscaled."""
    v = np.clip(a / scale, 0.0, 1.0) ** (1.0 / 2.2)
    return (v * 255.0 + 0.5).astype(np.uint8)


def energy(a):
    f = a.astype(np.float32)
    hp = f - cv2.GaussianBlur(f, (0, 0), 1.5)
    return float((hp * hp).mean())


def solve_sigma(a, target):
    """Blur that drops this crop's high-pass energy to `target` x its own."""
    e0 = energy(a)
    lo, hi = 0.01, 4.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        r = energy(cv2.GaussianBlur(a.astype(np.float32), (0, 0), mid)) / e0
        if r > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main():
    subject = sys.argv[1]
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
    d = SCRATCH / subject
    mtif = d / "MASTER.tiff"
    if not mtif.exists():
        print(f"no cached master for {subject}; render with corpus_softness --keep")
        return 1
    ftifs = sorted(d.glob("frame-*.tiff"))
    print(f"{subject}: {len(ftifs)} cached frames")

    mfull = luma32(tifffile.imread(str(mtif)))
    tx, ty = pick_tile(mfull, size)
    master = mfull[ty:ty + size, tx:tx + size].copy()
    del mfull

    tiles = []
    for ft in ftifs:
        t = luma32(tifffile.imread(str(ft)))[ty:ty + size, tx:tx + size].copy()
        dx, dy = shift_of(master, t)
        tiles.append(warp(t, dx, dy))

    cm = contrast(master, BLOCK)
    cfloor = float(np.percentile(cm, 65))
    env, win, valid = build_envelope(tiles, BLOCK, cfloor)
    live = (cm > cfloor) & valid
    md, mfloor = detail(master, BLOCK)
    ratio = md / np.maximum(env, 1e-12)

    # --- the M116 audit number, measured rather than asserted -----------------
    # A single GLOBAL frame is the weakest possible ceiling. Quantify how much
    # weaker it is than the per-site max on the same data, same sites, same
    # instrument -- this is the size of the error in any "sharper than the
    # sharpest single frame" claim.
    D = np.stack([detail(t, BLOCK)[0] for t in tiles])
    per_frame = np.array([d_[live].sum() for d_ in D])
    gbest = int(np.argmax(per_frame))
    r_global = float(np.median((md / np.maximum(D[gbest], 1e-12))[live]))
    r_site = float(np.median(ratio[live]))
    uniq = len(np.unique(win[live]))
    print(f"\n  sites live            {int(live.sum())}")
    print(f"  distinct winners      {uniq} of {len(tiles)} frames")
    print(f"  ratio vs PER-SITE max {r_site:.4f}")
    print(f"  ratio vs ONE GLOBAL   {r_global:.4f}  (frame {gbest})")
    print(f"  weak-ceiling inflation x{r_global / r_site:.2f}")

    # --- choose the site ------------------------------------------------------
    mode = sys.argv[3] if len(sys.argv) > 3 else "median"
    if mode == "worst":
        rr = np.where(live, ratio, np.inf)
        by, bx = np.unravel_index(int(np.argmin(rr)), rr.shape)
    else:
        # Blocks within 2% of the median ratio, then the one with most contrast:
        # the headline number, shown on structure rather than on a flat patch.
        near = live & (np.abs(ratio - r_site) < 0.02 * max(r_site, 1e-9))
        if not near.any():
            near = live & (np.abs(ratio - r_site) < 0.10 * max(r_site, 1e-9))
        cc = np.where(near, cm, -np.inf)
        by, bx = np.unravel_index(int(np.argmax(cc)), cc.shape)
        print(f"  site mode             median ({int(near.sum())} candidate blocks)")
    site_r = float(ratio[by, bx])
    wf = int(win[by, bx])
    cy, cx = by * BLOCK + BLOCK // 2, bx * BLOCK + BLOCK // 2
    y0 = int(np.clip(cy - CROP // 2, 0, size - CROP))
    x0 = int(np.clip(cx - CROP // 2, 0, size - CROP))
    print(f"  site                  block({bx},{by}) ratio={site_r:.4f} "
          f"winner=frame#{wf} ({ftifs[wf].stem})")
    print(f"  crop in master        ({tx + x0},{ty + y0}) {CROP}x{CROP}")

    mc = master[y0:y0 + CROP, x0:x0 + CROP]
    fc = tiles[wf][y0:y0 + CROP, x0:x0 + CROP]
    scale = float(np.percentile(mc, 99.5))
    sig = solve_sigma(mc, site_r)
    panels = {
        "A_master": mc,
        "B_bestframe": fc,
        "C_control_planted": cv2.GaussianBlur(mc.astype(np.float32), (0, 0), sig),
        "D_null_master": mc,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"\n  encode scale          {scale:.1f} DN (from master crop, reused)")
    print(f"  control sigma         {sig:.3f} px -> energy ratio "
          f"{energy(panels['C_control_planted']) / energy(mc):.4f} "
          f"(target {site_r:.4f})")
    print(f"  crop hp energy        master {energy(mc):.1f}  "
          f"frame {energy(fc):.1f}  ratio {energy(mc) / energy(fc):.4f}")
    print(f"  noise floor (block)   master {mfloor:.2f}  "
          f"frame {detail(tiles[wf], BLOCK)[1]:.2f}")
    for k, v in panels.items():
        p = OUT / f"{subject}_{k}.png"
        cv2.imwrite(str(p), encode(v, scale))
        print(f"  wrote {p}")

    # --- the staircase: where does a planted deficit BECOME visible? ----------
    # The first run of this script planted the measured deficit exactly and it
    # was indistinguishable from the master. That makes "not visible" unusable
    # on its own: it cannot separate "the effect is below threshold" from "this
    # viewing path has no power". So walk the effect size down until it IS
    # visible. The rung that first shows is the threshold of THIS path, and the
    # distance from the measured deficit to that rung is the honest headroom.
    print("\n  --- planted staircase (same crop, same encode) ---")
    for target in (0.80, 0.60, 0.40, 0.25, 0.10):
        s = solve_sigma(mc, target)
        b = cv2.GaussianBlur(mc.astype(np.float32), (0, 0), s)
        p = OUT / f"{subject}_L{int(target * 100):02d}.png"
        cv2.imwrite(str(p), encode(b, scale))
        print(f"  ratio {target:.2f}  sigma {s:.3f} px  -> {p.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
