"""Print the halo campaign's bar table, for transcription into the report."""

import json
from pathlib import Path

HALO = Path(r"C:\dev\strehl-out\M116\halo")
d = json.loads((HALO / "scores-halo.json").read_text())

print(f"pinned SHA {d['pinned_sha']}\n")
print(f"{'subject':<38} {'tau':>9} {'fg%':>6} {'H(H0)':>9} "
      f"{'dHALO%(H1)':>11} {'dHALO%(H2)':>11} {'bright%':>9}")
for s, r in d["subjects"].items():
    a = r["arms"]
    print(f"{s:<38} {r['mask']['tau']:>9.1f} {r['mask']['fg_pct']:>6.2f} "
          f"{a['H0']['halo']['H']:>9.5f} "
          f"{a['H1'].get('dHALO_pct', float('nan')):>+11.2f} "
          f"{a['H2'].get('dHALO_pct', float('nan')):>+11.2f} "
          f"{a['H1'].get('dHALO_bright_pct', float('nan')):>+9.2f}")

print(f"\n{'subject':<38} {'dD_tr(H1)':>10} {'dD_tr(H2)':>10} "
      f"{'dD_glob(H1)':>12} {'ctrl':>8} {'treated%':>9}")
for s, r in d["subjects"].items():
    a = r["arms"]
    ts = r["treated_sets"]
    tot = r["mask"]["shape"][0] * r["mask"]["shape"][1]
    print(f"{s:<38} {a['H1']['dD_treated']:>+10.5f} {a['H2']['dD_treated']:>+10.5f} "
          f"{a['H1']['dD_treated_global']:>+12.5f} "
          f"{a['H1']['dD_untreated_global']:>+8.5f} "
          f"{100.0 * ts['d40_px'] / tot:>9.3f}")

print(f"\n{'subject':<38} {'yoke/out H0':>12} {'H1':>9} {'rise%':>9}")
for s, r in d["subjects"].items():
    a = r["arms"]
    print(f"{s:<38} {a['H0']['yoke_noise']['ratio']:>12.4f} "
          f"{a['H1']['yoke_noise']['ratio']:>9.4f} "
          f"{a['H1'].get('yoke_noise_rise_pct', float('nan')):>+9.2f}")

print(f"\n{'subject':<38} {'HB5 trap':>9} {'H0 hash':>14} {'H3 hash':>14} "
      f"{'A0 replicate':>14}")
for s, r in d["subjects"].items():
    rep = r.get("A0_replicate")
    rp = ("IDENTICAL" if rep and rep["identical"]
          else ("DIFFERS" if rep else "n/a"))
    print(f"{s:<38} {str(r['HB5_trap_halo0_identical_to_H0']):>9} "
          f"{r['arms']['H0']['sha256']:>14} {r['arms']['H3']['sha256']:>14} {rp:>14}")

print(f"\n{'subject':<38} {'changed%':>9} {'beyond yoke':>12} {'in FG':>8} "
      f"{'max d':>8}")
for s, r in d["subjects"].items():
    c = r["HB6_containment"]
    print(f"{s:<38} {c['changed_pct']:>9.3f} {c['beyond_yoke_px']:>12,} "
          f"{c['in_fg_px']:>8,} {c['max_d']:>8.1f}")

print("\nHB2 (deciding):", json.dumps(d["HB2_selectivity"], indent=2))
print("\nbee gate 0:", json.dumps(
    {k: v for k, v in d["bee_gate0"].items() if not k.startswith("profile")},
    indent=2))
