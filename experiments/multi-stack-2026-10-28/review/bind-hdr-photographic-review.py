"""Bind the completed, frozen HDR photographic review; no image or RAW computation."""
import hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
labels=['slide-hdr-pair-6','hdr-short-7','hdr-long-7']
views=['physical-reference','highlight-headroom']
manifest={'schema':'strehl.independent-hdr-photographic-review.v1','complete_overviews_viewed':6,'native_crops_viewed':72,'crop_size':[384,384],'views':views,'inputs':{},'arms':[]}
for name in ['hdr-photographic-freeze.json','hdr-roi-mapped-frozen.json','hdr-three-arm-binding.json','hdr-review-rois.json','hdr-physical-reference-transform.json','hdr-highlight-headroom-transform.json','display-srgb.icc','prepare-hdr-displays.py']:
 manifest['inputs'][name]=sha(HERE/name)
for label in labels:
 p=ROOT/'outputs/multi-stack'/label
 report=load(p/'render-report.json')
 arm={'label':label,'build':report['build'],'renderer_source_sha256':report['renderer_source_sha256'],'completed_sha256':sha(p/'completed.json'),'render_report_sha256':sha(p/'render-report.json'),'source_count':len(report['frames']),'groups':report['groups'],'canvas':report['canvas'],'invalid_output_pixels':report['invalid_output_pixels'],'passes':[],'displays':[]}
 for pass_id in sorted(set(v['pass'] for v in report['frames'])):
  rows=[v for v in report['frames'] if v['pass']==pass_id]
  arm['passes'].append({'pass':pass_id,'sources':len(rows),'covered_pixels_unique':sorted(set(v['covered_pixels'] for v in rows)),'clipped_min':min(v['clipped_pixels'] for v in rows),'clipped_max':max(v['clipped_pixels'] for v in rows),'clipped_sum_across_frames':sum(v['clipped_pixels'] for v in rows),'gains':sorted(set(v['photometric_gain'] for v in rows))})
 for view in views:
  p=HERE/'hdr-displays-complete'/view/label/'readback.json'; b=load(p)
  assert len(b['rois'])==12 and all(v['size']==[384,384] for v in b['rois'])
  arm['displays'].append({'view':view,'readback_path':str(p.relative_to(ROOT)),'readback_sha256':sha(p),'master':b['master'],'complete_display_sha256':b['complete_display_sha256'],'overview_sha256':b['overview_sha256'],'native_crops':b['rois']})
 manifest['arms'].append(arm)
(HERE/'hdr-photographic-review-binding.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'manifest_sha256':sha(HERE/'hdr-photographic-review-binding.json'),'complete_overviews_viewed':6,'native_crops_viewed':72,'arm_builds':[{k:a[k] for k in ['label','build','renderer_source_sha256']} for a in manifest['arms']]}))
