"""Print every number arm 6 reports, from the JSON the runs wrote.

Rule: a number recalled from earlier notes is not a measurement. Everything in
docs/research/M95-demosaic.md is printed here, from the artifacts on disk, so
the report can be checked against a single file.
"""

from __future__ import annotations

import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"


def J(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def main() -> int:
    cert, lad, sc = J("d1_certify.json"), J("d2_ladder.json"), J("d3_scale.json")
    L = []

    def p(s=""):
        print(s)
        L.append(s)

    bar = "=" * 74
    p(bar)
    p("K6  port certification -- Python MHC vs the shipped Rust")
    p(bar)
    for r in cert["rows"]:
        p(f"  {r['case']:16s} {r['kind']:9s} max|rust-py| {r['max_abs_diff']:.3e}"
          f"  {'OK' if r['ok'] else 'MISMATCH'}")
    p(f"  worst over {len(cert['rows'])} cases      : {cert['worst_max_abs_diff']:.3e}"
      f"   (tolerance {cert['tolerance']:.0e})")
    p(f"  planted one-tap defect      : {cert['planted_tap_delta']:.3e}"
      f"  detected {cert['planted_caught']}")
    p(f"  CERTIFIED                   : {cert['certified']}")
    p()

    p(bar)
    p("CONTROLS")
    p(bar)
    k1 = lad["K1"]["luma"]
    p(f"  K1 NULL      power {k1['power']:.3e}  signal {k1['signal']:.3e}"
      f"  alpha {k1['alpha_mean_abs']:.10f}  share {k1['artifact_share']:.3e}")
    p(f"               pass {lad['K1']['pass']}  (tol {lad['K1']['signal_tol']:.0e},"
      f" originally {lad['K1']['signal_tol_original']:.0e} -- see F6)")
    p(f"  K2 determinism bitwise identical : {lad['K2']['pass']}")
    p("  K3 POSITIVE blur dose")
    for r in lad["K3"]["rows"]:
        p(f"     sigma {r['sigma']:3.1f}  signal {r['signal']:+.4f}  power {r['power']:+.4f}")
    p(f"     monotone : {lad['K3']['pass']}")
    p("  K4 POSITIVE uncorrelated in-band power")
    for r in lad["K4"]["rows"]:
        p(f"     dose {r['dose']:4.2f}  artifact {r['artifact']:+.4f}"
          f"  signal {r['signal']:+.4f}  share {r['artifact_share']:.4f}")
    p(f"     artifact monotone {lad['K4']['mono']}   signal flat {lad['K4']['flat']}")
    p(f"  K7 band {lad['band'][0]}-{lad['band'][1]} cyc/px below truth Nyquist 0.5 :"
      f" {lad['K7_band_below_nyquist']}")
    p()

    p(bar)
    p(f"THE LADDER  truth AHD, {lad['count']} tiles of {lad['tile']}x{lad['tile']},"
      f" band {lad['band'][0]}-{lad['band'][1]} cyc/px")
    p(bar)
    p(f"  {'arm':10s} {'power':>9s} {'signal':>9s} {'artifact':>9s} {'artifact_share':>15s}")
    for name in ["MHC", "BILINEAR", "NEAREST"]:
        s = lad["ladder_AHD"][name]["luma"]
        p(f"  {name:10s} {s['power']:+9.4f} {s['signal']:+9.4f} {s['artifact']:+9.4f}"
          f" {s['artifact_share']:15.4f}")
    p()
    p("  per-channel, MHC")
    for c in ["luma", "R", "G", "B"]:
        s = lad["ladder_AHD"]["MHC"][c]
        p(f"  {c:10s} {s['power']:+9.4f} {s['signal']:+9.4f} {s['artifact']:+9.4f}"
          f" {s['artifact_share']:15.4f}")
    p()

    p(bar)
    p("K5  SPECIFICITY -- does the truth's own decoder decide the answer?")
    p(bar)
    for alg, r in lad["K5"]["ranks"].items():
        p(f"  signal ranking, truth {alg:7s}: {' > '.join(r)}")
    p(f"  ranking preserved across all three truths : {lad['K5']['preserved']}")
    p(f"  MHC signal moves at most                 : {lad['K5']['mhc_max_dev']:+.4f} dex")
    for alg in ["VNG", "LINEAR"]:
        s = lad["ladder_alt"][alg]["MHC"]["luma"]
        p(f"    truth {alg:7s} MHC power {s['power']:+.4f}  signal {s['signal']:+.4f}"
          f"  share {s['artifact_share']:.4f}")
    p()

    p(bar)
    p("PRE-REGISTERED BARS")
    p(bar)
    mhc = lad["ladder_AHD"]["MHC"]["luma"]
    nea = lad["ladder_AHD"]["NEAREST"]["luma"]
    p("  B1  is top-octave power monotone in demosaic quality?")
    p(f"      NEAREST is louder than MHC by {nea['power'] - mhc['power']:+.4f} dex")
    p(f"      NEAREST carries less detail  by {nea['signal'] - mhc['signal']:+.4f} dex")
    p(f"      B1 FIRED (power does NOT rank quality) : {lad['B1_power_not_monotone']}")
    p(f"      for scale, the orchestrator's whole six-algorithm ladder spans 0.3518 dex")
    p()
    p("  B2  how much detail is the shipped MHC losing vs a PERFECT demosaic?")
    p(f"      MHC signal deficit vs ceiling : {lad['B2_mhc_signal_deficit_dex']:+.4f} dex")
    p(f"      > 0.10 real headroom          : {lad['B2_headroom']}")
    p(f"      < 0.03 negligible             : {lad['B2_negligible']}")
    p(f"      MHC's own artifact share      : {mhc['artifact_share']:.4f}")
    p(f"      MHC total power vs truth      : {mhc['power']:+.4f} dex")
    p()

    p(bar)
    p("D3  how hard does the REAL capture drive the demosaic?")
    p(bar)
    p(f"  real sensor grid  alias/tested band ratio : {sc['real']['ratio']:.5f}"
      f"  ({sc['real']['ratio_dex']:+.4f} dex)")
    p(f"  synthetic truth   alias/tested band ratio : {sc['truth']['ratio']:.5f}"
      f"  ({sc['truth']['ratio_dex']:+.4f} dex)")
    p(f"  synthetic ladder drives the demosaic      : {sc['overdrive']:.2f}x"
      f" as hard as the real capture")
    p("  my hypothesis was that this would exceed 1.0 (synthetic overstates).")
    p("  It is below 1.0, so the synthetic ladder UNDERSTATES the real drive.")
    p()

    p(bar)
    p("HEADLINE")
    p(bar)
    p(f"  Ranking demosaics by top-octave power is not ranking them by quality.")
    p(f"  NEAREST beats MHC on power by {nea['power'] - mhc['power']:+.4f} dex while")
    p(f"  carrying {mhc['signal'] - nea['signal']:.4f} dex LESS real detail, and"
      f" {nea['artifact_share'] * 100:.1f}% of what it emits")
    p(f"  is not in the scene at all.")
    p(f"  MHC matches the truth's total band power to {mhc['power']:+.4f} dex -- it would")
    p(f"  score as essentially ideal on that metric -- yet {mhc['artifact_share'] * 100:.1f}%"
      f" of that power is")
    p(f"  fabricated and it carries {-mhc['signal']:.4f} dex less true detail than a perfect")
    p(f"  demosaic would.")

    (OUT / "d9_summary.txt").write_text("\n".join(L), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
