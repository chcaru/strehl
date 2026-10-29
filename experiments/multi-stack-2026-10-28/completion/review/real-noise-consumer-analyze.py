"""Frozen-mask CFA repeatability summaries; no independence or SNR inference."""
from pathlib import Path
import argparse, json, hashlib, collections
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
r=json.loads((a.run/'report.json').read_text());groups=collections.defaultdict(lambda:collections.defaultdict(list))
for row in r['rows']:
    groups[(row['window_base'],row['roi'],row['color'])][row['arm']].append(row)
metrics=['raw_half_difference_squared_dn2','centered_half_difference_squared_dn2','signed_mean_difference_dn','mean_signal_dn']
rows=[]
for key,arms in sorted(groups.items()):
    assert set(arms)=={'short','long','equal-repeat','precision-repeat'}
    keys=[{v['tile'] for v in values} for values in arms.values()];assert all(k==keys[0] for k in keys)
    stats={arm:{metric:sum(v['stats'][metric] for v in values)/len(values) for metric in metrics} for arm,values in arms.items()}
    invalid={arm:sum(v['stats']['invalid_pixels'] for v in values) for arm,values in arms.items()};assert not any(invalid.values()),invalid
    rows.append({'window_base':key[0],'roi':key[1],'color':key[2],'tiles':len(keys[0]),'stats':stats,'precision_to_equal_raw_semivariance':stats['precision-repeat'][metrics[0]]/stats['equal-repeat'][metrics[0]],'precision_to_long_raw_semivariance':stats['precision-repeat'][metrics[0]]/stats['long'][metrics[0]]})
summary={'schema':'strehl.real-noise-consumer-summary.v1','input_report_sha256':hashlib.sha256((a.run/'report.json').read_bytes()).hexdigest(),'cache_disk_hits':r['cache_disk_hits'],'raw_decodes':r['raw_decodes'],'rows':rows,'scope':'Paired actual-core CFA repeatability on complete frozen source-qualified masks. Two temporal samples per window produce one difference. Pixel/tile support is spatially correlated; guide reuse correlates windows. Green-dependent adaptive decisions remain unqualified. Not pure sensor variance or developed RGB SNR.','ratios_are_descriptive_not_confidence_intervals':True}
lookup={(v['window_base'],v['roi'],v['tile'],v['color'],v['arm']):v for v in r['rows']}
for out in rows:
    ratios=[]
    for key,v in lookup.items():
        if key[0]!=out['window_base'] or key[1]!=out['roi'] or key[3]!=out['color'] or key[4]!='precision-repeat':continue
        other=lookup[key[:4]+('equal-repeat',)]
        for x,y in zip(v['spatial_blocks'],other['spatial_blocks']):
            assert x['origin_quad_local']==y['origin_quad_local']
            ratios.append(x['stats']['raw_half_difference_squared_dn2']/y['stats']['raw_half_difference_squared_dn2'])
    ratios.sort();n=len(ratios)
    out['block_ratio_descriptive']={'count':n,'minimum':ratios[0],'q25':ratios[(n-1)//4],'median':ratios[(n-1)//2],'q75':ratios[3*(n-1)//4],'maximum':ratios[-1],'blocks_below_one':sum(v<1 for v in ratios),'not_independent':True,'no_confidence_interval':True}
a.out.write_text(json.dumps(summary,indent=2)+'\n')
for row in rows:
 print(row['window_base'],row['roi'],row['color'],'tiles',row['tiles'],'precision/equal',round(row['precision_to_equal_raw_semivariance'],4),'precision/long',round(row['precision_to_long_raw_semivariance'],4),'drifts',{k:round(v['signed_mean_difference_dn'],3) for k,v in row['stats'].items()})
