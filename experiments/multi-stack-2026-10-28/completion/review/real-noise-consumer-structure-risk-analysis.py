"""Frozen transfer criterion before opening nonflat results; no data-dependent masks."""
from pathlib import Path
from collections import defaultdict
import argparse,json,hashlib,statistics
p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
rows=[]
for mode in ['flat','quadratic','cubic','focus','shift']:
 rows.extend(json.loads((a.root/(mode+'.json')).read_text(encoding='utf-8'))['rows'])
groups=defaultdict(list)
for r in rows:
 if r['fixed_pixels']>0:groups[(r['mode'],r['hdr'],r['divisor'],r['arm'])].append(r)
summary=[]
for (mode,hdr,div,arm),rs in sorted(groups.items()):
 unit=defaultdict(list)
 for r in rs:unit[(r['base'],r['seed'])].append(r)
 estimates=[]
 for (base,seed),subset in sorted(unit.items()):
  n=sum(r['fixed_pixels']for r in subset)
  def mean(k):return sum(r[k]*r['fixed_pixels']for r in subset)/n
  estimates.append(dict(base=base,seed=seed,pixels_across_correlated_states_components=n,reference_risk_delta=mean('independent_reference_risk_delta_vs_equal'),known_risk_delta=mean('known_truth_risk_delta_vs_equal'),known_mse=mean('output_truth_mse'),reference_mse=mean('reference_truth_mse'),projection=None if mode=='flat'else mean('known_signal_projection')))
 record=dict(mode=mode,hdr=hdr,divisor=div,arm=arm,units=estimates,reference_risk_delta=statistics.mean(v['reference_risk_delta']for v in estimates),known_risk_delta=statistics.mean(v['known_risk_delta']for v in estimates),known_mse=statistics.mean(v['known_mse']for v in estimates),reference_mse=statistics.mean(v['reference_mse']for v in estimates))
 if mode!='flat':
  record['projection']=statistics.mean(v['projection']for v in estimates)
  record['known_signal_retention_095_105']=all(.95<=v['projection']<=1.05 for v in estimates)
  record['reference_claims_gain_despite_known_damage']=record['reference_risk_delta']<0 and record['known_risk_delta']>0
 summary.append(record)
record=dict(schema='strehl.structure-risk-analysis.v1',input_root=str(a.root),analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),threshold_note='Fixed .95..1.05 known signal projection, written before nonflat results were opened; no amplitude/autofit correction. This is a diagnostic retention criterion, not a camera quality guarantee.',unit_note='Mean and full replicate range across base+synthetic acquisition seed. Two states and colors share estimator inputs; no pixel CI or independent-row count.',summary=summary,empty_qualified_rows=sum(r['fixed_pixels']==0 for r in rows),all_rows=len(rows),input_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in a.root.glob('*.json')})
a.out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
for r in summary:
 if r['arm']in['precision','constant','blur','mild-blur','shift']:print(r['mode'],r['hdr'],r['divisor'],r['arm'],'risk',round(r['reference_risk_delta'],3),'truth',round(r['known_risk_delta'],3),'transfer',round(r.get('projection',0),5))
