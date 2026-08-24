"""Consolidated number sheet for the M95 arm-5 report.

Every number quoted in docs/research/M95-coverage.md is printed here, from the
JSON that the instruments wrote in this session. Nothing is recalled.
"""
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "out"


def load(name):
    p = OUT / name
    if not p.exists():
        sys.exit(f"missing {p} -- run the instrument first")
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    w0 = load("w0_warpstats.json")
    x7 = load("x7_scale.json")
    x7b = load("x7b_scale_field.json")
    x8 = load("x8_fix.json")
    x10c = load("x10c_planeres.json")
    x11 = load("x11_alias.json")

    print("=" * 72)
    print("W0  the real warp geometry the merge applies")
    print("=" * 72)
    c = w0["centre"]
    m = w0["mid-radius"]
    print(f"  placed frames                  : {w0['placed']}")
    print(f"  per-frame scale-1 range        : {w0['scale_minus_1_min']:+.3e} "
          f"to {w0['scale_minus_1_max']:+.3e}")
    print(f"  centre     frac(dx) mean/sd    : {c['fx_mean']:.4f} / {c['fx_sd']:.4f}")
    print(f"  mid-radius frac(dx) mean/sd    : {m['fx_mean']:.4f} / {m['fx_sd']:.4f}")
    print(f"  (a uniform phase has mean 0.5000 and sd 0.2887)")
    print(f"  centre     within 0.05px of int: {100 * c['frac_within_0p05_px']:.1f}%")
    print(f"  mid-radius within 0.05px of int: {100 * m['frac_within_0p05_px']:.1f}%")
    print(f"  centre     mean |displacement| : {c['disp_mean_px']:.2f} px, "
          f"max {c['disp_max_px']:.2f} px")
    print(f"  phase cycles swept by k=0.9315 : {w0['phase_cycles_k_0.9315']:.1f}")
    print(f"  phase cycles swept by k=0.9974 : {w0['phase_cycles_k_0.9974']:.1f}")

    print("\n" + "=" * 72)
    print("X7  FIRST ladder -- WITHDRAWN, tile-centred scale (defect)")
    print("=" * 72)
    for k in ("0.997", "0.9315"):
        print(f"  k={k:<8} cost {x7['B1_ladder'][k]:+.4f} dex")
    print(f"  its K1..K5 all passed, which is why the defect was invisible")
    print(f"  until the ladder disagreed with the end-to-end number by 8x.")

    print("\n" + "=" * 72)
    print("X7B  CORRECTED ladder -- scale about the FIELD centre")
    print("=" * 72)
    print(f"  controls: K1 null {x7b['K1_null']:+.6f}, K4 int-shift "
          f"{x7b['K4_integer_shift']:+.6f},")
    print(f"            K5 band-match {x7b['K5_bandmatch_lanczos8']:+.4f}, "
          f"K3 planted {x7b['K3_planted_sigma0p30']:+.4f}")
    print(f"  {'k':>8} {'enlargement':>12} {'cost (dex)':>12}")
    for k, v in x7b["B1_ladder"].items():
        kf = float(k)
        e = (1 / kf - 1) * 100 if kf else 0.0
        print(f"  {kf:>8.4f} {e:>11.2f}% {v:>+12.4f}")
    print(f"  spread over k=0.7..0.999      : {x7b['B1_spread_dex']:.4f} dex")
    print(f"  pre-registered MAGNITUDE fired: {x7b['B1_verdict_magnitude']}")
    print(f"  pre-registered PHASE fired    : {x7b['B1_verdict_phase']}")
    print(f"  B3 fixed band {x7b['B3_fixed_band_cost']:+.4f} vs matched "
          f"{x7b['B3_matched_band_cost']:+.4f}  bias {x7b['B3_bias_dex']:+.4f} dex")

    print("\n" + "=" * 72)
    print("X8  THE FIX, priced with the real 299-frame warps")
    print("=" * 72)
    print(f"  control K1 identity warp, no coverage : {x8['K1_null']:+.6f} dex")
    print(f"  K6 identity warp, coverage scale only : {x8['K6_cover_alone']:+.6f} dex")
    for a in ("NOW", "FIX", "SNAP"):
        v = x8[a]
        print(f"  {a:<5} cost {v['cost_dex']:+.4f} dex  sem {v['sem']:.4f}  "
              f"n={v['n']}  step {v['mean_step']:.4f}")
    print(f"  recovery from the fix : {x8['fix_recovery_dex']:+.4f} dex")
    print(f"  bar SHIPS (> +0.10)   : {x8['fix_ships']}")
    print(f"  bar DEAD  (< +0.03)   : {x8['fix_dead']}")

    print("\n" + "=" * 72)
    print("X10C  plane-resolution arm -- WITHDRAWN, unstable in sign")
    print("=" * 72)
    print(f"  controls all passed: K1 full {x10c['K1_null_full']:+.6f}, "
          f"K1 planes {x10c['K1_null_planes']:+.6f},")
    print(f"                      K4 {x10c['K4_integer_plane_shift']:+.6f}, "
          f"K3 {x10c['K3_planted_sigma0p30']:+.4f}")
    for k, v in x10c["arms"].items():
        print(f"  k={float(k):.4f}  full {v['full']:+.4f}  planes {v['planes']:+.4f}  "
              f"penalty {v['planes'] - v['full']:+.4f}")
    print(f"  a penalty that flips sign across two nearby k is not a measurement.")

    print("\n" + "=" * 72)
    print("X11  was the sign flip aliasing?  NO -- hypothesis refuted")
    print("=" * 72)
    print(f"  positive control, low-pass suppression : {x11['suppression']:.3e}x")
    print(f"  band power, full-res gather            : {x11['full_band_power']:.4e}")
    print(f"  band power, plane-res gather           : {x11['plane_band_power']:.4e}")
    print(f"  plane / full                           : {x11['plane_over_full']:.2f}x")
    print(f"  the plane gather emits LESS out-of-band energy, not more, so")
    print(f"  aliasing does not explain the sign flip. It stays undiagnosed.")

    print("\n" + "=" * 72)
    print("HEADLINE")
    print("=" * 72)
    now, fix = x8["NOW"]["cost_dex"], x8["FIX"]["cost_dex"]
    print(f"  Removing the coverage scale recovers {x8['fix_recovery_dex']:+.4f} dex.")
    print(f"  NOW {now:+.4f} -> FIX {fix:+.4f}: the fix is very slightly WORSE.")
    print(f"  SNAP {x8['SNAP']['cost_dex']:+.4f} dex: with integer offsets and unit")
    print(f"  scale the gather is free, so the entire cost is sub-pixel phase.")
    lad = x7b["B1_ladder"]
    print(f"  A 0.01% enlargement already costs {lad['0.9999']:+.4f} dex; a 735x")
    print(f"  larger 7.35% one costs {lad['0.9315']:+.4f}; a 42.86% one costs "
          f"{lad['0.7']:+.4f}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
