"""Print one render's per-frame fusion report (STREHL_HIGHLIGHT_REPORT), final pass only.

  python summarise.py <fusion.jsonl>
"""
import json
import sys

rows = [json.loads(line) for line in open(sys.argv[1], encoding='utf-8')]
# The last whole-frame record per plane is the final pass's fold (a lateral-CA preview
# renders first; the restoration's reference crops re-plan a few bands, `partial`).
last = {}
for r in rows:
    if r.get('partial') and r['plane'] in last and not last[r['plane']].get('partial'):
        continue
    last[r['plane']] = r
print('plane comp  ratio  corr_EV  handover(med,spread,n)   shift_px      patched  w=1  pinned unrepl comp_pin  base_m1 comp_m1  steps_s')
for p in sorted(last):
    d = last[p]
    if 'refused' in d:
        print(f"{p:5} {d['companion_plane']:4}  REFUSED: {d['refused']}")
        continue
    h = d.get('handover_median_spread_sites') or [float('nan')] * 3
    print(f"{p:5} {d['companion_plane']:4} {d['ratio']:6.3f} {d['correction_ev']:+7.3f}  "
          f"{h[0]:.4f} {h[1]:.4f} {int(h[2]):6}  "
          f"{d['shift_px'][0]:+.2f},{d['shift_px'][1]:+.2f}  {d['patched_sites']:8} {d['weight_one_sites']:7} "
          f"{d['base_pinned_sites']:6} {d['pinned_not_fully_replaced']:5} {d['companion_near_pin']:5}  "
          f"{str(d.get('base_member1_only')):5} {'yes' if d.get('companion_member1_only') else 'no':3}  "
          f"{' '.join('%.2f' % s for s in d.get('seconds_load_shift_bright_ratio_sites_gather', []))}")
fused = [d for d in last.values() if 'refused' not in d]
if fused:
    hs = sorted(d['handover_median_spread_sites'][0] for d in fused if d.get('handover_median_spread_sites'))
    print(f"fused {len(fused)} of {len(last)}; hand-over medians {hs[0]:.4f}..{hs[-1]:.4f} (median {hs[len(hs)//2]:.4f}); "
          f"pinned-not-fully-replaced total {sum(d['pinned_not_fully_replaced'] for d in fused)}; "
          f"fusion seconds total {sum(d['seconds'] for d in fused):.1f}")
