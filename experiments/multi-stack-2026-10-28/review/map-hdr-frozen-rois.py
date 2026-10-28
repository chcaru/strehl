import json,hashlib,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
freeze=HERE/'hdr-photographic-freeze.json'; f=json.loads(freeze.read_text())
p=ROOT/'outputs/multi-stack/slide-hdr-pair-6'
r=json.loads((p/'render-report.json').read_text()); a=json.loads((p/'alignment.json').read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert hashlib.sha256(a['warpmap'].encode()).hexdigest()==f['inputs']['new_warpmap_sha256']
canvas=r['canvas']; assert canvas==[26,17,3464,2310]
rows=[]
for item in f['rois']:
 center=item['full_candidate_native_center']
 continuous=[center[d]-2*canvas[d]-191.5 for d in range(2)]
 origin=[math.floor(v+.5) for v in continuous]
 assert all(0<=origin[d] and origin[d]+384<=2*canvas[d+2] for d in range(2))
 rows.append({**item,'origins':{'shared-hdr-gauge':origin,'slide-hdr-pair-6':origin},'continuous_origin':continuous,'rounding_error_pixels':[origin[d]-continuous[d] for d in range(2)]})
passes=[]
for pass_index in range(2):
 frames=[v for v in r['frames'] if v['pass']==pass_index]
 passes.append({'pass':pass_index,'frames':len(frames),'every_frame_full_canvas_covered':all(v['covered_pixels']==canvas[2]*canvas[3] for v in frames),'every_frame_original_footprint_unclipped':all(v['clipped_pixels']==0 for v in frames),'clipped_footprint_min':min(v['clipped_pixels'] for v in frames),'clipped_footprint_max':max(v['clipped_pixels'] for v in frames),'gains':sorted(set(v['photometric_gain'] for v in frames))})
assert passes[0]['frames']==61 and passes[0]['every_frame_full_canvas_covered'] and passes[0]['every_frame_original_footprint_unclipped']
out={'schema':'strehl.independent-hdr-mapped-rois.v1','freeze_sha256':sha(freeze),'status':'Mapped from the previously frozen centers and saved canvas before HDR image viewing','canvas_plane':canvas,'dimensions_native':[2*canvas[2],2*canvas[3]],'warpmap_sha256':f['inputs']['new_warpmap_sha256'],'render_report_sha256':sha(p/'render-report.json'),'invalid_output_pixels':r['invalid_output_pixels'],'support_receipts':passes,'support_qualification':'Every actual2.5s source has unclipped original-footprint support across the entire delivered canvas. This establishes availability, not which source/band contributed to each final pixel. Long clipping witnesses remain bound to independent original-u16 block counts.','size':384,'rois':rows}
(HERE/'hdr-roi-mapped-frozen.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'receipt_sha256':sha(HERE/'hdr-roi-mapped-frozen.json'),'origins':{v['name']:v['origins']['shared-hdr-gauge'] for v in rows},'support':passes},indent=2))
