"""M87 step 58 -- per-island depth test: subject structure or background intrusion?

WHY THIS SUPERSEDES 57's P-A. In 57 I compared the islands' median elected
frame index against the GLOBAL medians of background and subject. That test is
invalid and I should have seen it before running: the elected index IS depth,
so it is a function of position. A subject 4000 px tall spans many frames, and
its global median says nothing about the depth immediately around any given
island. The comparison has to be LOCAL. This is the fourth instrument defect I
have found in my own harness on this milestone, and the third that a registered
prediction rather than inspection caught.

THE TEST. For every island of area >= MIN_AREA:
  isl_idx   median elected index inside the island
  sub_idx   median elected index in the surrounding SUBJECT ring (dilate the
            island by RING px, keep the part that is not bright)
  bg_idx    median elected index in the nearest background, within NEARBG px
An island is called SUBJECT-DEPTH when |isl-sub| < |isl-bg|, BACKGROUND-DEPTH
otherwise.

WHY EITHER ANSWER IS INFORMATIVE:
  BACKGROUND-DEPTH -> the election imported the background at a spot the
      background cannot physically reach. Same family as the veil, and a veil
      correction has a chance of reaching it.
  SUBJECT-DEPTH    -> the island is at the depth of the surface around it, i.e.
      it is the subject's OWN structure -- a specular highlight or a pale bract
      -- merely brighter than Otsu's threshold. Then it is NOT a defect at all,
      ORCH's reading of the render is wrong, and a correction that removes it
      is destroying real signal. That is the more consequential outcome and it
      is the one that would embarrass the fix.

CONTROLS, registered, both required before the islands' verdict may be read.
The discriminator has to be shown able to return BOTH answers. Both controls
use IDENTICAL geometry -- a disc of matched area at a subject location that has
background within reach -- and differ only in the planted depth:
  C-NULL   disc left alone            -> must read SUBJECT-DEPTH
  C-PLANT  elected index inside the disc overwritten with the local
           background's -> must read BACKGROUND-DEPTH
C-PLANT is the positive control: a null only shows the instrument is quiet, and
only a planted effect shows it can respond at all.
Bars: both >= 80% correct on DECIDABLE sites.

DECIDABILITY, and why it is not a let-off. Where the local subject and the
local background happen to elect nearly the same frame, NO depth test can
separate them -- the question is empty there, not merely hard. So a site counts
only when |sub - bg| >= SEP_MIN frames. C-PLANT measures what fraction of sites
are decidable at all, which is the honest denominator for the real verdicts.
My first attempt at these controls dropped the discs in FAR BACKGROUND, where
by construction no subject ring exists, so nothing was classifiable and C-BG
scored 0/0 -- mis-specified in exactly the way my earlier SHUF area control was.

Crops of the largest islands are written for me to LOOK at, because a depth
number cannot tell a specular highlight from a bright bract and my eye can.
"""

import json
import pathlib

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage as ndi

CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
OUTDIR = pathlib.Path(r"C:\dev\strehl-out\M87-islands")
GAL = pathlib.Path(r"C:\dev\strehl-out\ORCH-gallery")

MIN_AREA = 100
RING = 15
NEARBG = 60
SEP_MIN = 10
PAD = 90
CTRL_BAR = 0.80
RNG = np.random.default_rng(8701)


def otsu(v):
    h, e = np.histogram(v.ravel(), 512)
    h = h.astype(np.float64)
    c, m = h.cumsum(), (h * ((e[:-1] + e[1:]) / 2)).cumsum()
    tot, mt = c[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        sb = (mt * c / tot - m) ** 2 / (c * (tot - c))
    return float(e[1:][np.nanargmax(sb)])


def classify(mask, sl, bright, arg):
    """Local depth verdict for one blob, computed inside its padded bbox."""
    sub = mask[sl], bright[sl], arg[sl]
    m, br, ag = sub
    if m.sum() < 10:
        return None
    grow = ndi.binary_dilation(m, iterations=RING)
    ring_sub = grow & ~m & ~br
    near_bg = ndi.binary_dilation(m, iterations=NEARBG) & ~m & br
    if ring_sub.sum() < 20 or near_bg.sum() < 20:
        return None
    isl = float(np.median(ag[m]))
    sdx = float(np.median(ag[ring_sub]))
    bdx = float(np.median(ag[near_bg]))
    return {"isl": isl, "sub": sdx, "bg": bdx, "area": int(m.sum()),
            "sep": abs(sdx - bdx), "decidable": bool(abs(sdx - bdx) >= SEP_MIN),
            "d_sub": abs(isl - sdx), "d_bg": abs(isl - bdx),
            "verdict": "SUBJECT" if abs(isl - sdx) < abs(isl - bdx) else "BACKGROUND"}


def bbox_slice(objs, i, shape):
    sy, sx = objs[i]
    return (slice(max(sy.start - PAD, 0), min(sy.stop + PAD, shape[0])),
            slice(max(sx.start - PAD, 0), min(sx.stop + PAD, shape[1])))


def planted(cand, areas, bright, arg, shape, n, mode):
    """Drop matched-area discs at subject sites that have background in reach.

    mode 'null'  -> elected index untouched; truth is SUBJECT-depth.
    mode 'plant' -> elected index inside the disc overwritten with the local
                    background's median; truth is BACKGROUND-depth.
    Identical geometry in both arms, so any difference in verdict is the
    planted depth and nothing else.
    """
    ys, xs = np.where(cand)
    out = []
    for _ in range(n):
        a = float(RNG.choice(areas))
        r = max(int(round(np.sqrt(a / np.pi))), 3)
        j = RNG.integers(len(ys))
        cy, cx = int(ys[j]), int(xs[j])
        sl = (slice(max(cy - r - PAD, 0), min(cy + r + PAD, shape[0])),
              slice(max(cx - r - PAD, 0), min(cx + r + PAD, shape[1])))
        loc = np.zeros(shape, bool)
        gy, gx = np.ogrid[sl[0], sl[1]]
        loc[sl] = ((gy - cy) ** 2 + (gx - cx) ** 2) <= r * r
        ag = arg
        if mode == "plant":
            probe = classify(loc, sl, bright, arg)
            if probe is None:
                continue
            ag = arg.copy()
            ag[loc] = int(round(probe["bg"]))
        c = classify(loc, sl, bright, ag)
        if c:
            out.append(c)
    return out


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    sel = np.load(CACHE / "25-flower-alone-sel.npy").astype(np.float32)
    arg = np.load(CACHE / "25-flower-alone-argbest.npy").astype(np.int32)
    tau = otsu(sel)
    bright = sel > tau
    lab, n = ndi.label(bright)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    border.discard(0)
    bg = np.isin(lab, list(border))
    island = bright & ~bg
    ilab, ni = ndi.label(island)
    objs = ndi.find_objects(ilab)
    areas = ndi.sum(island, ilab, range(1, ni + 1))
    d2bg = ndi.distance_transform_edt(~bg)
    print(f"binned {sel.shape}  tau {tau:.1f}  {ni} island components")

    rows = []
    for i in range(ni):
        if areas[i] < MIN_AREA:
            continue
        sl = bbox_slice(objs, i, sel.shape)
        m = ilab == (i + 1)
        c = classify(m, sl, bright, arg)
        if c:
            c["id"] = i + 1
            c["luma"] = float(np.median(sel[m]))
            c["d2bg"] = float(d2bg[m].min())
            rows.append(c)
    rows.sort(key=lambda z: -z["area"])
    dec = [r for r in rows if r["decidable"]]
    nb = sum(1 for r in dec if r["verdict"] == "BACKGROUND")
    print(f"\nislands with area >= {MIN_AREA}: {len(rows)}, of which "
          f"{len(dec)} DECIDABLE (|sub-bg| >= {SEP_MIN} frames)")
    print(f"  among decidable:  BACKGROUND-depth {nb}   SUBJECT-depth {len(dec) - nb}")
    print(f"\n  {'id':>4} {'area':>7} {'d2bg':>5} {'isl':>5} {'sub':>5} {'bg':>5} "
          f"{'sep':>5} {'|d_sub|':>8} {'|d_bg|':>7}  verdict")
    for r in rows[:18]:
        tag = r["verdict"] if r["decidable"] else "(undecidable)"
        print(f"  {r['id']:>4} {r['area']:>7} {r['d2bg']:>5.0f} {r['isl']:>5.0f} "
              f"{r['sub']:>5.0f} {r['bg']:>5.0f} {r['sep']:>5.0f} "
              f"{r['d_sub']:>8.0f} {r['d_bg']:>7.0f}  {tag}")

    print("\n=== CONTROLS (matched geometry, planted depth) ===")
    d_bright = ndi.distance_transform_edt(~bright)
    cand = ~bright & (d_bright > 8) & (d_bright < NEARBG - 12)
    A = [r["area"] for r in rows]
    c_null = planted(cand, A, bright, arg, sel.shape, 60, "null")
    c_plant = planted(cand, A, bright, arg, sel.shape, 60, "plant")
    dn = [c for c in c_null if c["decidable"]]
    dp = [c for c in c_plant if c["decidable"]]
    r_sub = sum(1 for c in dn if c["verdict"] == "SUBJECT") / max(len(dn), 1)
    r_bg = sum(1 for c in dp if c["verdict"] == "BACKGROUND") / max(len(dp), 1)
    print(f"  C-NULL   {len(dn):>3}/{len(c_null)} decidable  -> SUBJECT    "
          f"{100 * r_sub:6.1f}%   bar >= {100 * CTRL_BAR:.0f}%   "
          f"{'PASS' if r_sub >= CTRL_BAR and dn else 'FAIL'}")
    print(f"  C-PLANT  {len(dp):>3}/{len(c_plant)} decidable  -> BACKGROUND "
          f"{100 * r_bg:6.1f}%   bar >= {100 * CTRL_BAR:.0f}%   "
          f"{'PASS' if r_bg >= CTRL_BAR and dp else 'FAIL'}")
    ok = bool(dn) and bool(dp) and r_sub >= CTRL_BAR and r_bg >= CTRL_BAR
    print(f"  discriminator usable: {'YES' if ok else 'NO -- islands verdict is VACUOUS'}")

    print("\nbrightness (binned merge units)")
    print(f"  island median {np.median([r['luma'] for r in rows]):.0f}"
          f"   bg median {np.median(sel[bg]):.0f}"
          f"   subject median {np.median(sel[~bright]):.0f}   tau {tau:.0f}")

    # crops of the largest islands, at full render resolution, for my own eyes
    img = tifffile.imread(GAL / "flower-bud-alone-cpl-srgb.tif")
    sy, sx = img.shape[0] / sel.shape[0], img.shape[1] / sel.shape[1]
    for r in rows[:6]:
        sl = bbox_slice(objs, r["id"] - 1, sel.shape)
        y0, y1 = int(sl[0].start * sy), int(sl[0].stop * sy)
        x0, x1 = int(sl[1].start * sx), int(sl[1].stop * sx)
        c = img[y0:y1, x0:x1]
        p = OUTDIR / f"island-{r['id']:04d}-a{r['area']}-{r['verdict']}.png"
        Image.fromarray((c / 257).astype(np.uint8)).save(p)
        print(f"  wrote {p.name}  ({x1 - x0}x{y1 - y0})")

    json.dump({"n_islands": int(ni), "scored": rows, "tau": tau,
               "sep_min": SEP_MIN, "n_decidable": len(dec),
               "frac_background_decidable": nb / max(len(dec), 1),
               "ctrl_null_subject_rate": r_sub, "ctrl_plant_bg_rate": r_bg,
               "ctrl_null_n_decidable": len(dn), "ctrl_plant_n_decidable": len(dp),
               "controls_pass": bool(ok), "bar": CTRL_BAR,
               "luma": {"island": float(np.median([r["luma"] for r in rows])),
                        "bg": float(np.median(sel[bg])),
                        "subject": float(np.median(sel[~bright]))}},
              open(DATA / "58-island-depth.json", "w"), indent=1)


if __name__ == "__main__":
    main()
