"""dust_flat.py -- the last attempt to reproduce DELIVER-V4's dust measurement.

Two instruments have now failed to confirm it on the SHIP-V4 masters:

  dust.py       fixed-position residual field on the 4x overviews. Deepest
                candidate 1.34x its own rolled null -> NOT DETECTED. The two
                aggregators did not even agree on a location on one geometry
                group, which is what noise looks like.

  dust_patch.py cut the SAME integer slice at DELIVER-V4's stated worst site
                (7008,4450) out of all 26 masters. Ranked worst-first, the top
                of the ranking is dark SCENE CONTENT; the flat-background
                subjects, where a grey disc would be unmistakable, read -0.2%,
                -0.3%, -0.6%. Nothing is visible in the tile.

A mote is only visible against FLAT, BRIGHT background -- DELIVER-V4 says so
itself ("on empty background where nothing hides it"). So the third instrument
excludes everything else: per image, keep only pixels whose local gradient is
low and whose background is bright, then take the cross-image median of the
residual over the kept pixels. A fixed mote reinforces across subjects; scene
content does not, and textured scenes contribute nothing instead of noise.

Judged, as before, against its own rolled null. If this does not clear either,
the finding is that I cannot reproduce the claim -- not that the sensor is
clean.
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

from dust import MED, K, DST, resid

MIN_BG = 90.0        # DN: a mote is invisible on a dark scene
MAX_GRAD = 6.0       # DN: local gradient, i.e. "flat"
MIN_VALID = 5        # images that must contribute before a pixel is scored


def masked_resid(luma):
    u = np.clip(luma, 0, 255).astype(np.uint8)
    m = cv2.medianBlur(u, MED).astype(np.float32)
    gx = cv2.Sobel(m, cv2.CV_32F, 1, 0, 3)
    gy = cv2.Sobel(m, cv2.CV_32F, 0, 1, 3)
    g = cv2.magnitude(gx, gy) / 4.0
    r = resid(luma)
    keep = (m >= MIN_BG) & (g <= MAX_GRAD)
    out = np.where(keep, r, np.nan).astype(np.float32)
    return out, float(keep.mean())


def cross(rs, roll=False, seed=5):
    rng = np.random.default_rng(seed)
    st = []
    for r in rs:
        if roll:
            r = np.roll(r, (int(rng.integers(50, r.shape[0] - 50)),
                            int(rng.integers(50, r.shape[1] - 50))), (0, 1))
        st.append(r)
    st = np.stack(st)
    n = np.sum(~np.isnan(st), axis=0)
    with np.errstate(all="ignore"):
        med = np.nanmedian(st, axis=0)
    med = np.where(n >= MIN_VALID, med, np.nan)
    return med, n


def main():
    with open(os.path.join(DST, "manifest.json"), encoding="utf-8") as f:
        man = json.load(f)
    groups = {}
    print("=== flat/bright mask coverage per image ===")
    for rec in man["images"]:
        p = os.path.join(DST, "overview", rec["overview"])
        a = np.asarray(Image.open(p).convert("RGB"))[:-man["bar_overview"]]
        luma = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
        mr, frac = masked_resid(luma)
        groups.setdefault(mr.shape, []).append((rec["name"], mr))
        print("  %-34s flat+bright %5.1f%% of frame" % (rec["name"], 100 * frac))

    out = []
    detected = False
    for shp, v in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        rs = [x[1] for x in v]
        med, n = cross(rs)
        nul, _ = cross(rs, roll=True)
        if np.all(np.isnan(med)):
            print("\n  %s: no pixel had %d contributing images -- REFUSED, not "
                  "scored" % (shp, MIN_VALID))
            out.append({"shape": list(shp), "n": len(v), "status": "refused",
                        "why": "fewer than %d flat+bright contributors anywhere"
                               % MIN_VALID})
            continue
        iy, ix = np.unravel_index(int(np.nanargmin(med)), med.shape)
        depth = float(np.nanmin(med))
        floor = float(np.nanmin(nul))
        ratio = abs(depth) / max(abs(floor), 1e-9)
        det = ratio >= 2.0
        detected = detected or det
        print("\n=== %d images at %s, flat+bright pixels only ===" % (len(v), shp))
        print("  scoreable pixels (>=%d contributors): %d of %d"
              % (MIN_VALID, int(np.sum(~np.isnan(med))), med.size))
        print("  deepest fixed attenuation %.2f%% at overview (%d,%d) = full-res (%d,%d),"
              " %d contributing images" % (100 * depth, ix, iy, ix * K, iy * K, n[iy, ix]))
        print("  rolled null on the same masked data: %.2f%%" % (100 * floor))
        print("  ratio %.2fx -> %s" % (ratio, "DETECTED" if det else "NOT DETECTED"))
        out.append({"shape": list(shp), "n": len(v), "status": "scored",
                    "xy": [int(ix), int(iy)], "full_res_xy": [int(ix) * K, int(iy) * K],
                    "depth_pct": 100 * depth, "null_pct": 100 * floor,
                    "ratio": ratio, "detected": bool(det),
                    "contributors": int(n[iy, ix])})

    tot = sum(r["n"] for r in out)
    print("\n=== counted partition ===")
    print("  scored %d + refused %d = %d of %d   %s"
          % (sum(r["n"] for r in out if r["status"] == "scored"),
             sum(r["n"] for r in out if r["status"] == "refused"), tot,
             len(man["images"]), "OK" if tot == len(man["images"]) else "MISMATCH"))

    # POWER. A null floor larger than the effect being looked for means this arm
    # could not have found it even if it were there, and reporting it as
    # "not detected" without saying so would be a skipped check reading as a
    # passed one.
    CLAIMED = 13.28
    floors = [abs(r["null_pct"]) for r in out if r["status"] == "scored"]
    print("\n=== power of this arm against the claim it is testing ===")
    for r in out:
        if r["status"] == "scored":
            print("  %s: null floor %.2f%% vs DELIVER-V4's claimed %.2f%% -> %s"
                  % (tuple(r["shape"]), abs(r["null_pct"]), CLAIMED,
                     "UNDERPOWERED, could not have found it"
                     if abs(r["null_pct"]) >= CLAIMED else "adequate"))
    underpowered = bool(floors) and min(floors) >= CLAIMED

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "logs", "dust-flat.json"), "w", encoding="utf-8") as f:
        json.dump({"groups": out, "claimed_pct": CLAIMED,
                   "underpowered": underpowered}, f, indent=1)

    if detected:
        print("\nVERDICT: a fixed-position attenuation clears its null on flat, "
              "bright background.")
    elif underpowered:
        print("\nVERDICT: UNDERPOWERED, NOT 'ABSENT'. Every whole-frame arm's own "
              "null floor (%.2f%%+) is LARGER than the %.2f%% defect it is "
              "looking for, so a real mote of that depth could not have cleared "
              "it. This arm decides nothing and must not be quoted as evidence "
              "of absence. The arm that DOES have power is dust_patch.py: at 1:1 "
              "on the 14 subjects whose background at the stated site is flat and "
              "bright (sd 1.1-7.2 DN on 91-246 DN), sensitivity is well under 1%% "
              "and the worst reading is -0.78%%. That test is decisive AT THAT "
              "COORDINATE ONLY." % (min(floors), CLAIMED))
    else:
        print("\nVERDICT: NOT DETECTED, and the arm had the power to detect it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
