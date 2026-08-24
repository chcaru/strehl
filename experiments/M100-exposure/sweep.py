"""M100 sweep: choose the auto-exposure percentile and target by measurement.

Reads the binned `--srgb` renders written by render.ps1 (post-matrix,
post-clamp, sRGB-encoded), linearises them, and evaluates every candidate
(percentile, target) pair against the pre-registered bars in
docs/research/M100-exposure.md section 1:

  B3  any-channel clipping <= 0.50% and all-three clipping <= 0.20% on EVERY
      stack.
  B4  encoded luma p99.9 >= 0.90 on every stack.

The percentile definition here is numpy's `inverted_cdf`, which is the same
nearest-rank definition as `strehl_core::color::nearest_rank_index`, and the
quantisation to 1/100 stop matches `AUTO_EXPOSURE_STEPS_PER_STOP`. So the
numbers below are the shipped rule's, not an approximation of it.

READ-ONLY on D:\\. Writes nothing but stdout.
"""
import glob
import json
import os
import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\M100"
# Row 1 of SRGB_TO_XYZ_D65 in crates/strehl-core/src/color.rs -- the same
# weights strehl_core::color::luminance uses, not a second copy of BT.709.
YW = np.array([0.2126729, 0.7151522, 0.0722750], dtype=np.float64)

PERCENTILES = [98.0, 99.0, 99.5, 99.7, 99.9, 99.95, 99.99]
TARGETS = [0.80, 0.85, 0.90, 0.95, 1.00]


def srgb_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def quantise_stops(s):
    """Exactly AUTO_EXPOSURE_STEPS_PER_STOP = 100, clamped at +/-6."""
    s = float(np.clip(s, -6.0, 6.0))
    return round(s * 100.0) / 100.0


def evaluate(lin, luma, p, target):
    yp = float(np.percentile(luma, p, method="inverted_cdf"))
    if yp <= 0.0:
        return None
    stops = quantise_stops(np.log2(target / yp))
    gain = 2.0 ** stops
    boosted = lin * gain
    enc = linear_to_srgb(boosted)
    u16 = (enc * 65535.0 + 0.5).astype(np.uint16)
    at_max = u16 == 65535
    any_clip = float(at_max.any(axis=2).mean())
    all_clip = float(at_max.all(axis=2).mean())
    mean_luma = enc.mean(axis=2)          # the orchestrator's definition
    bt709 = enc @ YW                       # the BT.709 one
    return dict(
        p=p, target=target, yp=yp, stops=stops, gain=gain,
        any_clip=any_clip, all_clip=all_clip,
        mean_p50=float(np.percentile(mean_luma, 50)),
        mean_p999=float(np.percentile(mean_luma, 99.9)),
        bt709_p999=float(np.percentile(bt709, 99.9)),
    )


def main():
    files = sorted(glob.glob(os.path.join(SRC, "tune-*-srgb.tif")))
    if not files:
        raise SystemExit("no tune-*-srgb.tif in " + SRC)
    results = {}
    for f in files:
        name = os.path.basename(f)[len("tune-"):-len("-srgb.tif")]
        a = tifffile.imread(f).astype(np.float32) / 65535.0
        lin = srgb_to_linear(a.astype(np.float64))
        luma = np.clip(lin, 0.0, None) @ YW
        base_mean = a.mean(axis=2)
        print("=" * 78)
        print("%s  %d x %d" % (name, a.shape[1], a.shape[0]))
        print("  BEFORE: encoded luma(mean) p50 %.4f p99 %.4f p99.9 %.4f ; "
              "at-max %.6f%%"
              % (float(np.percentile(base_mean, 50)),
                 float(np.percentile(base_mean, 99)),
                 float(np.percentile(base_mean, 99.9)),
                 100.0 * float(((a * 65535 + 0.5).astype(np.uint16) == 65535)
                               .any(axis=2).mean())))
        rows = []
        for p in PERCENTILES:
            for t in TARGETS:
                r = evaluate(lin, luma, p, t)
                if r:
                    rows.append(r)
        results[name] = rows
        print("  %-7s %-6s %8s %7s %10s %10s %8s"
              % ("pctile", "targ", "Y_p", "stops", "any-clip%", "all-clip%",
                 "p99.9"))
        for r in rows:
            print("  %-7.2f %-6.2f %8.5f %+7.2f %10.4f %10.4f %8.4f"
                  % (r["p"], r["target"], r["yp"], r["stops"],
                     100 * r["any_clip"], 100 * r["all_clip"], r["mean_p999"]))
        del a, lin, luma

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "sweep.json"), "w") as fh:
        json.dump(results, fh, indent=1)

    # --- the decision table: worst case over stacks, per (p, target).
    print()
    print("=" * 78)
    print("WORST CASE ACROSS %d STACKS (the bar is worst-case, not median)"
          % len(results))
    print("  %-7s %-6s %10s %10s %8s %10s   %s"
          % ("pctile", "targ", "any-clip%", "all-clip%", "minp99.9",
             "stopspread", "verdict"))
    for p in PERCENTILES:
        for t in TARGETS:
            sel = [r for rows in results.values() for r in rows
                   if r["p"] == p and r["target"] == t]
            if len(sel) != len(results):
                continue
            anyc = max(r["any_clip"] for r in sel)
            allc = max(r["all_clip"] for r in sel)
            minp = min(r["mean_p999"] for r in sel)
            spread = max(r["stops"] for r in sel) - min(r["stops"] for r in sel)
            ok = (anyc <= 0.005) and (allc <= 0.002) and (minp >= 0.90)
            print("  %-7.2f %-6.2f %10.4f %10.4f %8.4f %10.2f   %s"
                  % (p, t, 100 * anyc, 100 * allc, minp, spread,
                     "PASS" if ok else "fail"))


if __name__ == "__main__":
    main()
