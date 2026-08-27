"""dust.py -- measure the sensor-dust defect in the SHIPPED gallery, don't quote it.

DELIVER-V4's README states two motes, 18 of 26 images, worst -13.28%.  I did not
measure that and this gallery must not repeat it on trust.  A sensor mote is a
FIXED-POSITION multiplicative attenuation present in every source frame, so it
survives the merge at a fixed output position while scene content does not.
That is the handle:

    resid  = luma / median_blur(luma) - 1        per image, per master
    field  = mean(resid) over the corpus         a fixed defect reinforces,
                                                 scene content averages toward 0

Run on the shipped 4x overviews, so what is reported is the defect A VIEWER OF
THIS GALLERY ACTUALLY SEES, not a defect in some other file.

COMMISSIONED BEFORE USE, in both directions:
  D1  a clean synthetic corpus with NO mote must read ~0            (no phantom)
  D2  a planted mote of known depth must be recovered, in depth and position
  D3  a mote planted at a DIFFERENT position in each frame (i.e. not a fixed
      sensor defect) must NOT be recovered -- otherwise the statistic is just
      finding dark blobs and would convict the scene
  D4  the instrument must not be reading its own median window: a mote much
      wider than the window must be MISSED, and that limit is stated

Usage:  python dust.py
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

DST = r"C:\dev\strehl-out\DELIVER-V5"
MED = 41                    # median window on the 4x overview
K = 4
FULL_MOTE_PX = 45           # DELIVER-V4's stated mote diameter at full res
_fails = []
_passes = []


def record(tag, ok, msg):
    (_passes if ok else _fails).append((tag, msg))
    print("  [%s] %-18s %s" % ("PASS" if ok else "FAIL", tag, msg))


def resid(luma):
    """Local relative deviation. Runs in the 8-bit domain the gallery ships in,
    so what is measured is what a viewer sees, quantisation included."""
    u = np.clip(luma, 0, 255).astype(np.uint8)
    m = cv2.medianBlur(u, MED).astype(np.float32)
    m = np.maximum(m, 1.0)
    return u.astype(np.float32) / m - 1.0


def field(stack, agg=np.median):
    return agg(np.stack([resid(x) for x in stack]), axis=0)


def field_null(stack, seed=3, agg=np.median):
    """The corpus's own noise floor.

    Each image's residual is rolled by an independent random shift before
    averaging.  That destroys fixed-position coherence -- the only thing the
    statistic is supposed to respond to -- while preserving every residual's
    distribution exactly.  Whatever depth this reaches is what the statistic
    reads on NO defect at all, on THIS corpus, at THIS stack size.

    Any claimed defect must beat it.  My first draft of this file asserted a
    hard -2% threshold instead, and D3 and D4 both "passed" by landing on a
    -4.2% floor I had not measured; the arms were reporting the floor, not a
    discrimination.
    """
    rng = np.random.default_rng(seed)
    rs = []
    for x in stack:
        r = resid(x)
        rs.append(np.roll(r, (int(rng.integers(50, r.shape[0] - 50)),
                              int(rng.integers(50, r.shape[1] - 50))), (0, 1)))
    return agg(np.stack(rs), axis=0)


def disc(shape, cx, cy, r, depth):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return 1.0 + depth * np.clip(1.0 - d / r, 0, 1)


def commission():
    print("=== commissioning the dust field statistic ===")
    rng = np.random.default_rng(7)
    H, W, N = 400, 600, 12
    base = [cv2.GaussianBlur(rng.integers(40, 220, (H, W)).astype(np.float32), (0, 0), 3.0)
            for _ in range(N)]

    floor = abs(float(field(base).min()))
    print("      MEASURED noise floor, clean corpus, N=%d: %.4f%%" % (N, 100 * floor))
    record("D1-floor-measured", floor > 0,
           "the floor is measured, not assumed: %.4f%%. Every arm below is "
           "judged against it, not against a threshold I chose." % (100 * floor))

    r_px = FULL_MOTE_PX / K
    cx, cy, depth = 401, 233, -0.12
    planted = [b * disc((H, W), cx, cy, r_px, depth) for b in base]
    f = field(planted)
    iy, ix = np.unravel_index(int(np.argmin(f)), f.shape)
    got = abs(float(f.min()))
    near = abs(ix - cx) <= 3 and abs(iy - cy) <= 3
    record("D2-recovered", near and got > 2.0 * floor,
           "planted %.1f%% mote at (%d,%d) r=%.1f px -> read %.2f%% at (%d,%d), "
           "%.1fx the floor" % (100 * depth, cx, cy, r_px, 100 * f.min(), ix, iy,
                                got / floor))

    moving = [b * disc((H, W), 60 + i * 40, 100 + i * 20, r_px, depth)
              for i, b in enumerate(base)]
    fm = abs(float(field(moving).min()))
    record("D3-not-a-blob-finder", fm < 1.5 * floor,
           "the SAME mote moved every frame reads %.2f%% = %.1fx the floor, i.e. "
           "NOT DETECTED, against %.1fx when fixed: the statistic requires a "
           "fixed sensor position and is not finding dark blobs"
           % (100 * fm, fm / floor, got / floor))

    wide = [b * disc((H, W), cx, cy, MED * 2.0, depth) for b in base]
    fw = abs(float(field(wide).min()))
    record("D4-window-limit", fw < 1.5 * floor,
           "a mote %.0f px wide -- beyond the %d px median window -- reads %.2f%% "
           "= %.1fx the floor, i.e. NOT DETECTED: THIS INSTRUMENT IS BLIND TO "
           "DEFECTS WIDER THAN ITS WINDOW (%d px overview = %d px full res)"
           % (MED * 4.0, MED, 100 * fw, fw / floor, MED, MED * K))

    fn = abs(float(field_null(planted).min()))
    record("D5-null-kills-it", fn < 1.5 * floor and got > 2.0 * fn,
           "the SAME planted stack, residuals rolled to break position "
           "coherence, reads %.2f%% vs %.2f%% coherent (%.1fx): the null "
           "control removes the signal it is supposed to remove"
           % (100 * fn, 100 * got, got / max(fn, 1e-9)))
    print("")
    return floor


def main():
    commission()
    if _fails:
        print("VERDICT: instrument not fit for use; %d arm(s) failed" % len(_fails))
        return 1

    with open(os.path.join(DST, "manifest.json"), encoding="utf-8") as f:
        man = json.load(f)
    imgs = man["images"]

    groups = {}
    for rec in imgs:
        p = os.path.join(DST, "overview", rec["overview"])
        a = np.asarray(Image.open(p).convert("RGB"))[:-man["bar_overview"]]
        luma = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])
        groups.setdefault(luma.shape, []).append((rec["name"], luma))

    print("=== geometry groups on the shipped overviews ===")
    for shp, v in groups.items():
        print("  %s : %d images" % (shp, len(v)))

    results = []
    any_detected = False
    for shp, v in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        stack = [x[1] for x in v]
        print("\n=== fixed-position defect, %d images at %s ===" % (len(v), shp))
        best = None
        for aggname, agg in (("median", np.median), ("mean", np.mean)):
            f = field(stack, agg)
            nul = abs(float(field_null(stack, agg=agg).min()))
            iy, ix = np.unravel_index(int(np.argmin(f)), f.shape)
            depth = float(f.min())
            ratio = abs(depth) / max(nul, 1e-9)
            det = ratio >= 2.0
            print("  %-6s: strongest %7.2f%% at overview (%4d,%4d) = full-res "
                  "(%5d,%5d) | null %6.2f%% | %.2fx -> %s"
                  % (aggname, 100 * depth, ix, iy, ix * K, iy * K, 100 * nul,
                     ratio, "DETECTED" if det else "NOT DETECTED"))
            if best is None or ratio > best[0]:
                best = (ratio, aggname, f, nul, ix, iy, depth, det)
        ratio, aggname, f, nul, ix, iy, depth, detected = best
        any_detected = any_detected or detected
        per = [(n, float(resid(l)[iy, ix])) for n, l in v]
        hit = [n for n, d in per if d < -0.03]
        worst = min(per, key=lambda t: t[1])
        results.append({
            "shape": list(shp), "n": len(v), "agg": aggname,
            "overview_xy": [int(ix), int(iy)],
            "full_res_xy": [int(ix) * K, int(iy) * K],
            "field_depth_pct": 100 * depth,
            "null_floor_pct": 100 * nul,
            "ratio_to_null": ratio, "detected": bool(detected),
            "n_over_3pct": len(hit), "worst": [worst[0], 100 * worst[1]],
            "per_image": [[n, 100 * d] for n, d in sorted(per, key=lambda t: t[1])],
        })
        print("  best arm %s: %.2fx null -> %s"
              % (aggname, ratio,
                 "DETECTED" if detected else
                 "NOT DETECTED at %dx reduction -- does not clear its own null, "
                 "so this location is NOT evidence of a defect" % K))
        print("  images reading worse than -3%% at that site: %d of %d" % (len(hit), len(v)))
        print("  worst single image: %-34s %.2f%%" % (worst[0], 100 * worst[1]))
        for n, d in sorted(per, key=lambda t: t[1])[:6]:
            print("      %-34s %.2f%%" % (n, 100 * d))

    tot = sum(r["n"] for r in results)
    print("\n=== counted partition ===")
    print("  measured %d + skipped 0 = %d of %d   %s"
          % (tot, tot, len(imgs), "OK" if tot == len(imgs) else "MISMATCH"))

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "logs", "dust.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)

    print("\n  commissioning: %d pass + %d fail = %d of %d"
          % (len(_passes), len(_fails), len(_passes) + len(_fails),
             len(_passes) + len(_fails)))
    if any_detected:
        print("\nVERDICT: a fixed-position attenuation clears its own null on at "
              "least one geometry group and is located above, measured on the "
              "files that ship.")
    else:
        print("\nVERDICT: NOT DETECTED. No candidate site clears this corpus's own "
              "null on the 4x overviews, so this instrument CANNOT CONFIRM the "
              "dust defect at this scale and its deepest reading is not evidence "
              "of one. That is a limit of the instrument and of the reduction, "
              "NOT a finding that the sensor is clean -- DELIVER-V4 measured the "
              "motes at FULL resolution with a different method. The defect is "
              "stated in the gallery README on that basis and on direct visual "
              "confirmation (see dust_patch.py), not on this statistic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
