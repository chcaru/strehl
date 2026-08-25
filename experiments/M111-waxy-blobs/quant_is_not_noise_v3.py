"""Third and final transfer test: tile size as the lever that reaches low level
counts with adequate sample at every rung.

v2 returned VOID on its own registered adequacy gate: only 2 level bands
carried n >= 20, because this capture is high-contrast almost everywhere and a
128 px window nearly always holds >512 distinct levels. That was the right
call by the gate and the wrong instrument for the question.

The fix is not to relax the gate. Level count per window is set by the window
as much as by the scene -- which is the whole content of discipline P65 -- so
sweeping TILE SIZE walks the level-count axis directly, with a full sample at
every rung and no change to the physics.

What v2 did establish, at adequate sample and below the registered bar:
  levels [128,512)  n=36   round +10.35 %  dither +582.50 %  ratio 20.04x
  levels [512,inf)  n=448  round  +1.79 %  dither   +4.81 %  ratio  2.37x
and, on the full 486-tile sample, rounding REMOVED gradient energy while dither
added it on 9.05 % of tiles.

PRE-REGISTERED, before these numbers exist:

  H1 ADEQUACY FIRST. Every tile-size rung carries n >= 100. Any rung below that
     is void and I read nothing off it.
  H2 TRANSFER. At the smallest window, equal-variance white dither inflates
     gradient energy at least 3x more than deterministic rounding of the same
     step.
  H3 GRADIENT, the discriminating one. The dither/rounding ratio rises
     monotonically as window size (and hence level count) falls. A flat offset
     would mean the correlation account is wrong even if H2 passes.
  H4 SIGN. The fraction of tiles where rounding REMOVES gradient energy while
     dither ADDS it rises as windows shrink. Dither cannot produce a negative
     change at all, so a non-zero fraction means a dither-based control cannot
     reproduce even the SIGN of quantisation damage.
  H5 SELF-REFUTATION. If H2 and H3 both fail, the mechanism does not transfer
     to spatial gradient statistics, and I report that against my own
     hypothesis rather than quoting v2's favourable bands.

Reads only from C:\\dev\\strehl-out\\. Writes only
C:\\dev\\strehl-out\\M111-pil-audit\\quant_is_not_noise_v3.json.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M111-pil-audit"
MERGED = os.path.join(r"C:\dev\strehl-out\ORCH-thennow", "marker-HEAD-8f46f04.tif")
STEP = 256.0
SEED = 20260824
TILES = [8, 12, 16, 24, 32, 48, 64, 96, 128]


def luma(a):
    return (0.2126 * a[..., 0].astype(np.float64)
            + 0.7152 * a[..., 1].astype(np.float64)
            + 0.0722 * a[..., 2].astype(np.float64))


def gemean(y):
    gy, gx = np.gradient(y)
    return float(np.sqrt(gx * gx + gy * gy).mean())


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    mt = tifffile.imread(MERGED)
    assert mt.dtype == np.uint16
    sigma = STEP / np.sqrt(12.0)
    y = luma(mt[300:mt.shape[0] - 300, 300:mt.shape[1] - 300])
    print("field %s   step %.0f DN   dither sigma %.2f DN (matched variance)"
          % (y.shape, STEP, sigma))

    print("\n%6s %7s %9s %10s %11s %12s %11s"
          % ("tile", "n", "levels", "round %", "dither %", "dither/round", "sign flip %"))
    print("-" * 74)
    rows = []
    for t in TILES:
        stride = max(t, 96)
        lv, dr, dd, flip = [], [], [], []
        for y0 in range(0, y.shape[0] - t, stride * 3):
            for x0 in range(0, y.shape[1] - t, stride * 3):
                win = y[y0:y0 + t, x0:x0 + t]
                base = gemean(win)
                if base < 0.05:
                    continue
                a = 100.0 * (gemean(np.round(win / STEP) * STEP) - base) / base
                b = 100.0 * (gemean(win + rng.normal(0.0, sigma, win.shape)) - base) / base
                lv.append(int(np.unique(np.round(win)).size))
                dr.append(a)
                dd.append(b)
                flip.append(1.0 if (a < 0 < b) else 0.0)
        n = len(dr)
        dr, dd = np.asarray(dr), np.asarray(dd)
        ratio = float(np.median(np.abs(dd) / np.maximum(np.abs(dr), 1e-9))) if n else float("nan")
        r = {"tile": t, "n": n, "median_levels": float(np.median(lv)) if n else float("nan"),
             "median_round_pct": float(np.median(dr)) if n else float("nan"),
             "median_dither_pct": float(np.median(dd)) if n else float("nan"),
             "median_ratio": ratio,
             "frac_sign_flip": float(np.mean(flip)) if n else float("nan"),
             "void": n < 100}
        rows.append(r)
        print("%6d %7d %9.0f %10.2f %11.2f %12.2f %11.2f%s"
              % (t, n, r["median_levels"], r["median_round_pct"], r["median_dither_pct"],
                 ratio, 100.0 * r["frac_sign_flip"], "  VOID" if r["void"] else ""))

    live = [r for r in rows if not r["void"]]
    h1 = len(live) == len(rows)
    h2 = bool(live and live[0]["median_ratio"] >= 3.0)
    rr = [r["median_ratio"] for r in live]
    h3 = all(rr[i] >= rr[i + 1] for i in range(len(rr) - 1))
    ff = [r["frac_sign_flip"] for r in live]
    h4 = all(ff[i] >= ff[i + 1] for i in range(len(ff) - 1))
    h5 = not (h2 or h3)

    print("\n[pre-registered gates]")
    print("  H1 every rung n >= 100                : %s  (%d of %d live)"
          % ("PASS" if h1 else "FAIL", len(live), len(rows)))
    print("  H2 smallest window dither >= 3x round : %s  (%.2fx at tile %d)"
          % ("PASS" if h2 else "FAIL", live[0]["median_ratio"] if live else float("nan"),
             live[0]["tile"] if live else -1))
    print("  H3 ratio monotone as windows shrink   : %s" % ("PASS" if h3 else "FAIL"))
    print("  H4 sign-flip fraction monotone        : %s  (%.1f%% -> %.1f%%)"
          % ("PASS" if h4 else "FAIL", 100.0 * ff[0] if ff else float("nan"),
             100.0 * ff[-1] if ff else float("nan")))
    print("  H5 self-refutation                    : %s" % ("FIRED" if h5 else "not fired"))
    verdict = ("MECHANISM TRANSFERS: a dither control overstates quantisation damage to "
               "gradient statistics, and cannot reproduce its sign" if (h2 and h3) else
               ("MECHANISM DOES NOT TRANSFER" if h5 else "PARTIAL"))
    print("\nVERDICT: %s" % verdict)
    doc = {"step_dn": STEP, "dither_sigma_dn": sigma, "seed": SEED, "rows": rows,
           "gates": {"H1": bool(h1), "H2": bool(h2), "H3": bool(h3), "H4": bool(h4),
                     "H5_fired": bool(h5)}, "verdict": verdict}
    dst = os.path.join(OUT, "quant_is_not_noise_v3.json")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1))
    print("wrote %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
