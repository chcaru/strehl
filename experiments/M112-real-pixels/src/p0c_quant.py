r"""M112 Phase 0c -- is the Phase 0 verdict exposed to quantisation?

WHY THIS EXISTS
---------------
The orchestrator withdrew the two-question quantisation triage rule after it was
refuted three times (V-M113 value-vs-position, M111 term disparity, M115 the
band-SNR factorisation). M112's statistic is a **band power ratio**, which is
M115's exact algebraic case, and it reads pixel VALUE not feature POSITION,
which is V-M113's exposed class. So M112 cannot clear itself by the shape of its
expression. This file does the two things the withdrawal asks for: expand the
algebra, then measure a dose-response control.

THE ALGEBRA (expanded before running -- see PREDICTION below)
------------------------------------------------------------
M95's per-tile statistic, verbatim from `x8_fix.arm`:

    cost = band_ratio(base, 1.0) - band_ratio(g, step)
         = log10(Phi_b / Plo_b) - log10(Phi_g / Plo_g)

where `base` is the UNRESAMPLED control crop and `g` is the gathered tile.
A uniform quantiser adds an approximately white floor `q` to every bin:

    cost(q) = log10[ (Phi_b + q)(Plo_g + q) / ( (Plo_b + q)(Phi_g + q) ) ]

Plo >> q and Plo_b ~= Plo_g (resampling barely touches 0.02-0.10 cyc/px), so the
low-band factor is ~1 and

    cost(q) ~= log10[ (Phi_b + q) / (Phi_g + q) ]   -->  0   as q grows.

So the COST is compressed toward zero -- M115's hazard, in the direction that
makes a real effect look absent.

But the decision number is not the cost, it is the RECOVERY, and the control
term cancels out of it exactly:

    recovery(q) = cost_NOW(q) - cost_FIX(q) = log10[ (Phi_FIX + q) / (Phi_NOW + q) ]

Both arms resample the SAME quantised source, so the floor is filtered by each
arm's own kernel along with the signal, Phi_arm = |H_arm|^2 (Phi_true + q), and

    recovery(q) = log10( |H_FIX|^2 / |H_NOW|^2 )      -- q cancels exactly.

Two further consequences of the same expansion, both of which matter:

  (a) Adding a common floor to numerator and denominator is SIGN-PRESERVING and
      magnitude-shrinking. It moves a log-ratio toward 0 and never through it.
      **A compression toward zero cannot manufacture a negative reading from a
      positive truth.** M112's headline is -0.0030 dex, i.e. negative, so the
      hazard cannot be what produced the no-go.

  (b) The cancellation in `recovery` is exact only if both arms filter the floor
      identically. They do not quite: NOW gathers at step 0.9315 and FIX at
      1.0014, so |H| differs. The residual is second order.

PREDICTION, registered here before the run (rule 20 / the M115 standard)
-----------------------------------------------------------------------
  P-A  The individual costs NOW and FIX compress monotonically toward 0 as the
       level count falls, because their control term is unresampled and its
       floor is unfiltered.
  P-B  The RECOVERY is markedly more robust than the individual costs, because
       the floor cancels in the arm-to-arm ratio.
  P-C  The decision does not flip at any dose above V-M113's threshold of ~12
       distinct levels per window: recovery stays far below the +0.10 dex bar.
  P-D  REFONLY, the positive control, stays large (order +0.18 dex) until the
       level count approaches single digits, proving the channel still carries a
       real effect at each dose and that a small reading means a small effect
       rather than a dead instrument.

If any of these is contradicted, REPORT THE NUMBER THAT DOES NOT FIT rather than
banking the favourable half.

No sharpness arithmetic is defined here either: `arm()` and `band_ratio` are
imported from M95's committed source exactly as Phase 0 did. The only thing this
file adds is a quantiser applied to the INPUT.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "experiments" / "M95-coverage" / "src"))
import m95cov as M          # noqa: E402  M95's instrument, verbatim
import x8_fix as X          # noqa: E402  M95's harness, verbatim

BASE = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
SIDECAR = Path(r"C:\dev\strehl-out\M106\warpmap-corpus-snapshot.txt")
K_BEE = 0.9315

# Level ladder. `None` is the undosed arm. The rest bracket V-M113's stated
# hazard region (immunity ends ~12 distinct levels, sign inverts at 2) by three
# decades above and by going below it.
LEVELS = [None, 4096, 1024, 256, 64, 16, 12, 8, 4, 2]


def quantise(img, levels):
    """Uniform requantisation to `levels` steps across the image's own range."""
    if levels is None:
        return img
    lo, hi = float(img.min()), float(img.max())
    u = (img - lo) / (hi - lo)
    return lo + np.round(u * (levels - 1)) / (levels - 1) * (hi - lo)


def main():
    img0 = M.load_luma(BASE)
    # Tiles are chosen ONCE, on the undosed image, and reused at every dose.
    # Re-picking per dose would let the tile choice absorb the effect.
    tiles = M.pick_tiles(img0)

    X.MAP = SIDECAR
    X.MAP_ALT = SIDECAR
    X.K_COVER = K_BEE
    plane, rows, src = X.read_warps()
    idx = np.linspace(0, len(rows) - 1, X.NFRAMES).round().astype(int)
    warps = [rows[i] for i in idx]
    ref = [r for r in rows if int(r[0]) == 149] or [rows[len(rows) // 2]]

    print(f"source  : {BASE.name}  {img0.shape[1]}x{img0.shape[0]}")
    print(f"sidecar : {src}  ({len(rows)} placed, sampling {len(warps)})")
    print(f"tiles   : {len(tiles)}   band {M.BAND} cyc/px   k_cover {K_BEE}\n")
    print(f"{'levels':>8s} {'meas/tile':>10s} {'NOW':>9s} {'FIX':>9s} "
          f"{'recovery':>10s} {'REFONLY':>9s} {'decision':>9s}")

    out = []
    for lv in LEVELS:
        img = quantise(img0, lv)
        meas = int(np.median([np.unique(img[ty:ty + M.TILE, tx:tx + M.TILE]).size
                              for ty, tx in tiles]))
        now, _ = X.arm(img, tiles, warps, True)
        fix, _ = X.arm(img, tiles, warps, False)
        rn, _ = X.arm(img, tiles, ref, True)
        rf, _ = X.arm(img, tiles, ref, False)
        rec = float(now.mean() - fix.mean())
        refonly = float(rn.mean() - rf.mean())
        dec = "SHIP" if rec > 0.10 else "DEAD"
        out.append({"levels": lv, "measured_levels_per_tile": meas,
                    "NOW": float(now.mean()), "FIX": float(fix.mean()),
                    "recovery": rec, "REFONLY": refonly, "decision": dec})
        print(f"{str(lv):>8s} {meas:>10d} {now.mean():>+9.4f} {fix.mean():>+9.4f} "
              f"{rec:>+10.4f} {refonly:>+9.4f} {dec:>9s}")

    base = out[0]
    print("\n--- registered predictions ---")
    costs_compress = all(abs(o["NOW"]) <= abs(base["NOW"]) + 5e-3 for o in out[1:])
    rec_span = max(abs(o["recovery"] - base["recovery"]) for o in out[1:])
    now_span = max(abs(o["NOW"] - base["NOW"]) for o in out[1:])
    safe = [o for o in out if o["measured_levels_per_tile"] >= 12]
    flips = [o for o in safe if o["decision"] != "DEAD"]
    print(f"P-A costs compress toward 0            : {'HELD' if costs_compress else 'CONTRADICTED'}")
    print(f"P-B recovery more robust than cost     : "
          f"{'HELD' if rec_span < now_span else 'CONTRADICTED'} "
          f"(recovery moves {rec_span:.4f}, NOW moves {now_span:.4f})")
    print(f"P-C decision never flips above 12 lv   : {'HELD' if not flips else 'CONTRADICTED'}")
    print(f"P-D positive control alive at each dose: "
          f"{'HELD' if all(o['REFONLY'] > 0.10 for o in safe) else 'CONTRADICTED'}")
    print(f"\nworst recovery at any dose >= 12 levels: "
          f"{max(o['recovery'] for o in safe):+.4f} dex  (bar +0.10)")

    (HERE.parents[1] / "out" / "p0c.json").write_text(
        json.dumps({"base": str(BASE), "sidecar": str(SIDECAR), "k_cover": K_BEE,
                    "band": list(M.BAND), "n_tiles": len(tiles),
                    "n_frames": len(warps), "ladder": out}, indent=1),
        encoding="utf-8")


if __name__ == "__main__":
    main()
