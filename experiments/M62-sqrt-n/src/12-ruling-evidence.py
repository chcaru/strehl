import json, math, sys

d = json.load(open('out/10-acceptance-m64.json'))
print('overall     :', d['overall'], '|', d['reason'])
print('determinism :', json.dumps(d['determinism']))
print('power_ok    :', d['power_ok'], ' power_lost:', d['power_lost'])
print('binary sha  :', d['provenance']['binary_sha256'][:16],
      ' crates_dirty:', d['provenance']['crates_dirty'],
      ' head:', d['provenance']['repo_head'][:8])
print()
for k in ['DEFAULT', 'SELECTOR-shipped', 'SELECTOR-same-binary', 'ESTIMATOR-explicit']:
    s = d['summary'][k]
    eff = s.get('efficiency')
    eff = 'n/a' if eff is None else f'{eff:.6f}'
    print(f"{k:<22} {s['ratio_mean']:.6f}  sd={s['ratio_sd_between_seeds']:.6f} "
          f"se={s['bootstrap_se_seed0']:.6f} eff={eff} "
          f"n_eff={s['cli'].get('mean_n_eff')} -> {s['verdict']}")
r = d['summary']['DEFAULT']['ratio_mean']
print(f'\nDEFAULT vs sqrt30 = {r/math.sqrt(30)-1:+.4%}   (pre-registered tol +-2.00%)')
print(f'DEFAULT per seed  = {d["summary"]["DEFAULT"]["ratio_per_seed"]}')
print(f'DEFAULT == SELECTOR-shipped bytes? '
      f'{d["summary"]["DEFAULT"]["out_sha256"] == d["summary"]["SELECTOR-shipped"]["out_sha256"]}')

# instrument arms vs M62's committed baseline
base = json.load(open('out/10-acceptance-preM64.json'))
print('\ninstrument + reference arms vs preM64 baseline:')
for k in sorted(d['summary']):
    if k not in base['summary']:
        continue
    a, b = d['summary'][k].get('ratio_mean'), base['summary'][k].get('ratio_mean')
    if a is None or b is None:
        print(f'  {k:<24} {d["summary"][k]["verdict"]:<12} baseline {base["summary"][k].get("verdict")}')
        continue
    print(f'  {k:<24} {a:.9f}  baseline {b:.9f}  identical={a==b}')
