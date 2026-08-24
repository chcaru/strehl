"""Print every number arm 9 will report, straight out of the JSON.

Rule 21: a number recalled from notes is not a measurement. This exists so the
report is transcribed from a file rather than from memory, and so a verifier
can diff the report against one canonical dump.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
KS = ["nearest", "bilinear", "catmull-rom", "lanczos3"]


def main():
    k3 = json.loads((HERE / "out" / "k3_kernel.json").read_text(encoding="utf-8"))
    k5 = json.loads((HERE / "out" / "k5_port.json").read_text(encoding="utf-8"))
    p64 = json.loads((HERE / "out" / "k3_port64.json").read_text(encoding="utf-8"))
    k1 = json.loads((HERE / "out" / "k1_radius.json").read_text(encoding="utf-8"))

    r = k3["b23_ringing"]
    print("=== B23 ringing, contrast-gate ladder, overshoot in DN ===")
    print(f"  frame {Path(r['frame']).name}  crop {r['crop']}x{r['crop']} {r['unit']}")
    print(f"  p99 gradient {r['t99_dn']:.2f} DN   p99.9 {r['t999_dn']:.2f} DN")
    hdr = f"  {'gate':>5} {'pop':>10} {'pop%':>8}"
    for k in KS:
        hdr += f" | {k[:11]:>11} mean/max"
    print(hdr)
    for g in r["ladder"]:
        row = f"  {g['gate_dn']:>5.0f} {g['n']:>10d} {100 * g['n'] / r['ladder'][0]['n']:>7.4f}%"
        for kk in g["kernels"]:
            row += f" | {kk['mean_dn']:>8.4f}/{kk['max_dn']:<8.4f}"
        print(row)

    print("\n  ratio lanczos3 / catmull-rom, mean overshoot, per gate:")
    for g in r["ladder"]:
        d = {kk["kernel"]: kk for kk in g["kernels"]}
        cr, lz = d["catmull-rom"]["mean_dn"], d["lanczos3"]["mean_dn"]
        s = f"{lz / cr:.2f}x" if cr > 0 else ("inf" if lz > 0 else "0/0")
        print(f"    gate {g['gate_dn']:>5.0f}  cr {cr:.4f}  lz {lz:.4f}  ratio {s}")

    print("\n=== K22 power: synthetic 1000 DN step, half-pixel shift ===")
    for k in KS:
        v = r["k22_step"][k]
        print(f"  {k:<12} overshoot {v['overshoot_dn']:>10.4f} DN  {v['pct_of_step']:>8.4f}% of step  reach {v['reach_px']} px")

    print("\n=== spatial extent: mean overshoot DN vs Chebyshev distance from a gated edge ===")
    print(f"  {'kernel':<12} " + " ".join(f"d={i}".rjust(7) for i in range(7)))
    for k in KS:
        print(f"  {k:<12} " + " ".join(f"{x:>7.4f}" for x in r["radial"][k]))

    print("\n=== B24 election ===")
    e = k3["b24_election"]
    print(f"  {e['frames']} frames, stride {e['step']}, {e['crop']}x{e['crop']} quad crop, {e['n_pixels']} px compared")
    print(f"  camera {e['camera']} ISO {e['iso']}")
    print(f"  K23 null  catmull-rom vs itself          {100 * e['k23_null']:>10.6f}% of winners moved")
    print(f"  K24 power vs sigma=1.0 planted on fr 8   {100 * e['k24_power']:>10.6f}%")
    print(f"  B24       catmull-rom vs lanczos3        {100 * e['b24_lanczos3']:>10.6f}%")
    print(f"  ref       catmull-rom vs bilinear        {100 * e['ref_bilinear']:>10.6f}%")
    print(f"  planted frame's own win share            {100 * e['k24_planted_share']:>10.4f}%")
    print(f"  K24 as a share of what was reachable     {100 * e['k24_of_reachable']:>10.4f}%")
    print(f"  median rel margin where lanczos3 flipped {e['b24_median_margin']:.6f}")
    print(f"  median rel margin, all live pixels       {e['all_median_margin']:.6f}")
    print(f"  separation                               {e['all_median_margin'] / e['b24_median_margin']:.1f}x")
    print("  win share by frame: " + " ".join(f"{x:.3f}" for x in e["win_share"]))

    print("\n=== crops, lanczos3 minus catmull-rom (DN) ===")
    print(f"  window {k3['crops']['win']}x{k3['crops']['win']}  panels {', '.join(k3['crops']['panels'])}")
    for c in k3["diff_split"]:
        print(
            f"  x{c['x']:<5} y{c['y']:<5} p99.9|d| {c['p999_dn']:>7.2f}  "
            f"RMS edge {c['rms_edge_dn']:>7.3f}  RMS flat {c['rms_flat_dn']:>7.3f}  "
            f"edge/flat {c['edge_over_flat']:.2f}x"
        )
    w = k3["worst_overshoot"]
    print(f"  worst gated overshoot {w['dn']:.2f} DN at x{w['x']} y{w['y']}, local contrast {w['contrast_dn']:.1f} DN")

    print("\n=== B22 port, 64 phases ===")
    print(f"  phases probed {k5['n_phases']}")
    for k in KS:
        b = p64["b22_taps"][k]
        print(f"  {k:<12} support {b['support']:.1f}  taps {len(b['rows'][0]['w'])}  offsets {b['lo']}..{b['hi']}  max |dw| vs textbook {k5['tap_max_dw'][k]:.3e}")
    print(f"  step overshoot, python: catmull-rom {100 * k5['step_overshoot']['catmull-rom']:.4f}%  lanczos3 {100 * k5['step_overshoot']['lanczos3']:.4f}%")
    print(f"  catmull-rom closed form 1/16 = {100 * k5['catmull_rom_closed_form']:.4f}%")
    a = k5["arms"]
    print(f"  gather cost catmull-rom {a['catmull-rom'][0]:+.4f} +/- {a['catmull-rom'][1]:.4f} dex  n {a['catmull-rom'][2]}")
    print(f"  gather cost lanczos3    {a['lanczos3'][0]:+.4f} +/- {a['lanczos3'][1]:.4f} dex  n {a['lanczos3'][2]}")
    print(f"  kernel gain {k5['gain']:+.4f} dex   arm 8 {k5['arm8_gain']:+.4f} dex   |d| {abs(k5['gain'] - k5['arm8_gain']):.4f}")

    print("\n=== B20 b-spline prefilter radius ===")
    print(f"  z = {k1['z']:.10f}   decay 1/|z| = {1 / abs(k1['z']):.4f} per unit R")
    print(f"  exact IIR reference truncated at k = {k1['k_trunc']}")
    for row in k1["radius_sweep"]:
        print(f"  R={row['R']:>3}  taps {row['taps']:>3}  max |w - exact| {row['max_err']:.6e}")
    print(f"  B21 interpolation error at integer taps {k1['B21_interp_err']:.3e}  {'PASS' if k1['B21_pass'] else 'FAIL'}")
    print(f"  B20  ->  {'MET' if k1['B20_pass'] else 'NOT MET at any R tested'}   (R_chosen {k1['R_chosen']})")


if __name__ == "__main__":
    raise SystemExit(main())
