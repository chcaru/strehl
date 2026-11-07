"""Fixed previously frozen HDR display/crops; no RAW or engine work."""
import os
for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):os.environ[k]="1"
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('h',R/'experiments/multi-stack-2026-10-28/challenge/prepare-review.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
old=R/'outputs/multi-stack/slide-hdr-pair-6';new=R/'outputs/multi-stack/completion/hdr-precision-03';prior=R/'outputs/multi-stack/completion/hdr-precision-01'
load=lambda p:json.loads(p.read_text())
a,b,c=[load(p/'alignment.json') for p in (old,new,prior)]
assert a['warpmap']==b['warpmap']==c['warpmap']
ra,rb,rc=[load(p/'render-report.json') for p in (old,new,prior)]
assert ra['canvas']==rb['canvas']==rc['canvas']==[26,17,3464,2310]
assert rb['recipe']['precision_focus_reference']=='equal-observation'
assert ra.get('development_reference_pass',ra['reference_pass'])==rb['development_reference_pass']==rc['development_reference_pass']==1
assert [(f['path'],f['photometric_gain']) for f in ra['frames']]==[(f['path'],f['photometric_gain']) for f in rb['frames']]==[(f['path'],f['photometric_gain']) for f in rc['frames']]
rois=load(R/'experiments/multi-stack-2026-10-28/review/hdr-roi-mapped-frozen.json')['rois']
for q in rois:q['origins']['precision03']=next(iter(q['origins'].values()))
out=R/'outputs/multi-stack/completion/independent-photographs/hdr-precision03'
h.render(new/'master.tiff',out,R/'experiments/multi-stack-2026-10-28/review/hdr-physical-reference-transform.json','precision03',rois=rois)
h.write_json(out/'comparison-binding.json',{'exact_warpmap':True,'same_canvas':rb['canvas'],'same_development_reference_pass':1,'same_ordered_source_gains':True,'new_recipe':rb['recipe'],'old_equal_report_sha256':h.digest(old/'render-report.json'),'precision01_report_sha256':h.digest(prior/'render-report.json'),'precision03_report_sha256':h.digest(new/'render-report.json')})
