"""Freeze HDR witnesses from existing geometry/clipping reports; no RAW/image reads."""
import hashlib,json,math,struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
PRE=ROOT/'outputs/multi-stack/hdr-preflight'; NEW=ROOT/'outputs/multi-stack/slide-hdr-pair-6'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def parse(t):
 rows={}
 for line in t.splitlines():
  s=line.split()
  if len(s)>=6 and s[0].isdigit() and s[1]=='placed': rows[int(s[0])]=[struct.unpack('>d',bytes.fromhex(v))[0] for v in s[2:6]]
 return rows
old_path=ROOT/'outputs/multi-stack/hdr-geometry-2/alignment.json'
old=load(old_path); new=load(NEW/'alignment.json')
assert old['report']['reference_frame']==153 and new['report']['reference_frame']==93
ow=parse(old['warpmap']); nw=parse(new['warpmap']); C=complex(1758,1172)
ids=load(NEW/'source-identities.json'); original=load(PRE/'b12-0032.json')
assert ids[93]['sha256']==original['whole_sha256']
assert new['report']['reference_pass']==1
photometry=load(NEW/'photometry.json'); assert photometry['anchor_pass']==1
assert photometry['calibrated_gains'] is not None

def apply(t,z):return complex(*t[:2])*(z-C)+complex(*t[2:])+C
def inv(t,z):return (z-C-complex(*t[2:]))/complex(*t[:2])+C
def map_center(xy,from_one_second):
 z=(complex(*xy)-complex(.5,.5))/2
 if from_one_second: z=apply(ow[153],inv(ow[30],z))
 z=inv(nw[93],z)
 z=z*2+complex(.5,.5)
 return [z.real,z.imag]
manual=[('gray-ramp-middle',[1200,650],'Gray field and low-frequency radiometry'),('adverse-flare-p12',[4400,1800],'Keep known focus-dependent flare witness; do not censor failure'),('qr-white-black-grid',[4200,650],'Clipped grid edges, false contrast and chromatic fringes'),('qr-corner-boundary',[4900,1400],'High-contrast corner continuity and halos'),('large-radial-star',[6100,850],'Radial spoke continuity, false detail and aliasing'),('fine-resolution-bars',[5400,2050],'Fine bars and colored moire; not gradient-energy sharpness'),('bright-dot-field',[800,2250],'Bright dot shape and halo/background'),('low-contrast-dot-field',[4200,3350],'Faint dots and smoothing/noise trade'),('lower-radial-spokes',[1500,4350],'Field-dependent spoke/color behavior')]
entries=[{'name':name,'selection':'Existing1s-middle locator only; selected before fused HDR view','selection_center_sensor':xy,'full_candidate_native_center':map_center(xy,True),'purpose':why,'size':384} for name,xy,why in manual]
block_path=PRE/'b12-0032-blocks.npz'
with np.load(block_path,allow_pickle=False) as b:
 clips=np.stack([b[f'site{i}_clipped'] for i in range(4)]).astype(np.int64)
 counts=np.stack([b[f'site{i}_count'] for i in range(4)]).astype(np.int64)
 total=clips.sum(axis=0); available=counts.sum(axis=0); blue=clips[3];green=clips[1]+clips[2]
 selected=[]
 for name,kind in [('clipped-core','total'),('blue-clipped-core','blue'),('clipped-boundary','mixed')]:
  candidates=[]
  for y in range(total.shape[0]):
   for x in range(total.shape[1]):
    cx,cy=x*64+31.5,y*64+31.5
    if not(256<=cx<=7028-256 and 256<=cy<=4688-256):continue
    if any((cx-px)**2+(cy-py)**2<512**2 for px,py in selected):continue
    if kind=='total':score=int(total[y,x])
    elif kind=='blue':score=int(blue[y,x])
    else:
     if not(0<total[y,x]<.5*available[y,x]):continue
     score=int(green[y,x])
    if score>0:candidates.append((-score,y,x))
  assert candidates
  _,y,x=min(candidates);xy=[x*64+31.5,y*64+31.5];selected.append(xy)
  entries.append({'name':name,'selection':'Derived clipping-count report only; maximal count, raster-order tie break,384square fits,512px separation between selected clipping witnesses','selection_center_sensor':xy,'full_candidate_native_center':map_center(xy,False),'size':384,'purpose':'Original6s clipping support witness; requires actual2.5s admitted support evidence before recovery claim','block_sensor_origin':[x*64,y*64],'block_sensor_size':[64,64],'original6s_clipped_sites_rg1g2b':clips[:,y,x].tolist(),'original6s_site_counts_rg1g2b':counts[:,y,x].tolist()})
record={'schema':'strehl.independent-hdr-review-freeze.v1','status':'FROZEN before viewing fused HDR or either output control; source locator only was inspected','helper_sha256':sha(Path(__file__)),'inputs':{'one_second_locator_sha256':sha(PRE/'photometry-patches-locator.png'),'old_geometry_sha256':sha(old_path),'new_geometry_sha256':sha(NEW/'alignment.json'),'new_warpmap_sha256':hashlib.sha256(new['warpmap'].encode()).hexdigest(),'clipping_count_report_sha256':sha(block_path),'photometry_report_sha256':sha(NEW/'photometry.json')},'common_anchor':{'new_global_index':93,'old_global_index':153,'path':ids[93]['path'],'sha256':ids[93]['sha256'],'exposure_seconds':6,'pass_index':32},'calibrated_gains_recorded_not_refit':photometry['calibrated_gains'],'rounding_rule':'When final saved canvas is available, origin[d]=floor(full_candidate_native_center[d]-2*canvas_origin_plane[d]-191.5+0.5); fixed384square, no resampling. Refuse out-of-bounds; no content-driven reposition.','geometry_limits':'Legacy1s locator centers use the old globally measured map only to transfer broad landmarks into the same physical6s-middle frame; this is not placement truth or pixelwise registration. Clipping-count witnesses already name that actual6s-middle sensor.','controls_required':['Full2.5sonly and6sonly on the exact126map/canvas with same calibrated gains,WB,color matrix,noise/transfer config and frozen display','Keep full3pass refusal evidence; two-pass success does not validate rejected1spass','Local original long clipping plus actual contributing short coverage/uncensored support before highlight-recovery language'],'display_views':[{'name':'physical-reference','black':0.,'white':4.,'contrast':.55,'exposure_gain':1.},{'name':'highlight-headroom','black':0.,'white':4.,'contrast':.55,'exposure_gain':.25}],'rois':entries}
(HERE/'hdr-photographic-freeze.json').write_text(json.dumps(record,indent=2)+'\n')
for item in record['display_views']:
 transform={'schema':'strehl.independent-review-transform.v1','parameter_source':'Predeclared6s sensor-reference physical scale; no output histogram or image fitted','display_baseline':{k:item[k] for k in ['black','white','contrast','exposure_gain']},'display_icc_file':'display-srgb.icc','display_icc_sha256':'238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b','policy':'Apply both predeclared views identically to fullHDR and both controls. No per-image fit.'}
 (HERE/('hdr-'+item['name']+'-transform.json')).write_text(json.dumps(transform,indent=2)+'\n')
print(json.dumps({'freeze_sha256':sha(HERE/'hdr-photographic-freeze.json'),'witnesses':[(e['name'],e['full_candidate_native_center']) for e in entries],'clip_blocks':[e for e in entries if 'original6s_clipped_sites_rg1g2b' in e]},indent=2))
