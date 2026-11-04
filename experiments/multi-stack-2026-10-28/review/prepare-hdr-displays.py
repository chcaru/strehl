"""Released complete HDR comparison; frozen transforms/ROIs, no RAW inputs."""
import hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
labels=['slide-hdr-pair-6','hdr-short-7','hdr-long-7']
freeze=load(HERE/'hdr-roi-mapped-frozen.json')
base=load(ROOT/'outputs/multi-stack/slide-hdr-pair-6/render-report.json')
byid={v['frame']:v for v in base['frames']}
fields=['luma_beta','color_beta','beta_samples','beta_realizations','photometric_gain','covered_pixels','clipped_pixels','path','pass']
verified=[]
for label,expected in zip(labels,[126,61,65]):
 p=ROOT/'outputs/multi-stack'/label
 r=load(p/'render-report.json'); a=load(p/'alignment.json'); c=load(p/'calibration.json')
 assert (p/'completed.json').is_file()
 assert r['canvas']==freeze['canvas_plane'] and r['invalid_output_pixels']==0
 assert hashlib.sha256(a['warpmap'].encode()).hexdigest()==freeze['warpmap_sha256']
 assert len(r['frames'])==expected
 assert r.get('development_reference_pass',r['reference_pass'])==1
 assert c[1]['white_balance']==[2.7392578125,1.,1.560546875]
 assert all(all(v[k]==byid[v['frame']][k] for k in fields) for v in r['frames'])
 verified.append({'label':label,'render_report_sha256':sha(p/'render-report.json'),'source_count':len(r['frames']),'groups':r['groups'],'development_reference_pass':1,'white_balance':c[1]['white_balance'],'color_matrix':c[1]['color_matrix'],'canvas':r['canvas'],'warpmap_sha256':freeze['warpmap_sha256'],'all_source_operator_gain_and_support_fields_equal_fused':True})
rois={'schema':'strehl.independent-review-rois.v1','size':384,'mapping_sha256':sha(HERE/'hdr-roi-mapped-frozen.json'),'rois':[]}
for item in freeze['rois']:
 rois['rois'].append({**item,'origins':{label:item['origins']['shared-hdr-gauge'] for label in labels}})
(HERE/'hdr-review-rois.json').write_text(json.dumps(rois,indent=2)+'\n')
(HERE/'hdr-three-arm-binding.json').write_text(json.dumps(verified,indent=2)+'\n')
script=ROOT/'experiments/multi-stack-2026-10-28/challenge/prepare-review.py'
spec=importlib.util.spec_from_file_location('frozen_review',script); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for view in ['physical-reference','highlight-headroom']:
 for label in labels:
  dest=HERE/'hdr-displays-complete'/view/label
  module.render(ROOT/'outputs/multi-stack'/label/'master.tiff',dest,HERE/('hdr-'+view+'-transform.json'),label,rois=rois["rois"])
  print(json.dumps({'view':view,'label':label,'destination':str(dest),'readback_sha256':sha(dest/'readback.json')}),flush=True)
