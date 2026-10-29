"""One-worker geometry support census using sealed focus fields only.
No candidate pixels, registration residuals, source images or RAW reads.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import argparse,json,hashlib,collections
from pathlib import Path
import numpy as np
P=argparse.ArgumentParser();P.add_argument('--census',type=Path,required=True);P.add_argument('--seal',type=Path,required=True);P.add_argument('--out',type=Path,required=True);A=P.parse_args()
assert not A.out.exists()
seal=json.loads(A.seal.read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
def checked(name):
 b=(A.census/name).read_bytes();assert sha(b)==seal['files'][name],name;return b
report=json.loads(checked('report.json'));roi=report['rois'][0];fx,fy,w,h=roi['focus_domain_quad'];fields=[]
for pass_index in range(2):
 fields.append(tuple(np.frombuffer(checked(f'roi-0/focus-pass-{pass_index}-{name}.{ext}'),dtype).reshape(h,w) for name,ext,dtype in [('flags','u8',np.uint8),('ordinal','f32',np.float32),('width','f32',np.float32)]))
def admitted(index):
 p=0 if index<299 else 1;flags,peak,width=fields[p];ordinal=index-299*p
 return (flags==0)&np.isfinite(peak)&np.isfinite(width)&(width>0)&(np.abs(ordinal-peak)<=width)
def components(mask):
 unseen=set(map(tuple,np.argwhere(mask)));out=[]
 while unseen:
  start=unseen.pop();todo=[start];seen=[start]
  while todo:
   y,x=todo.pop()
   for q in [(y-1,x),(y+1,x),(y,x-1),(y,x+1)]:
    if q in unseen:unseen.remove(q);todo.append(q);seen.append(q)
  if len(seen)>=4:
   a=np.array(seen);lo=a.min(0);hi=a.max(0)+1
   out.append({'pixels_quad':len(seen),'bbox_anchor_sensor':[int(2*(fx+lo[1])),int(2*(fy+lo[0])),int(2*(hi[1]-lo[1])),int(2*(hi[0]-lo[0]))]})
 return sorted(out,key=lambda v:-v['pixels_quad'])[:4]
def full_squares(mask,side):
 a=np.pad(mask.astype(np.int32),((1,0),(1,0))).cumsum(0).cumsum(1)
 sums=a[side:,side:]-a[:-side,side:]-a[side:,:-side]+a[:-side,:-side]
 return int((sums==side*side).sum())
targets=list(range(107,114))+list(range(397,404));pairs=sorted({tuple(sorted((110,i))) for i in targets if i!=110}|{(a,b) for a,b in zip(targets,targets[1:])});out=[]
for a,b in pairs:
 m=admitted(a)&admitted(b)
 out.append({'acquisitions':[a,b],'common_focus_quad_pixels':int(m.sum()),'components':components(m),'complete_qualified_square_counts_by_side_quad':{str(side):full_squares(m,side) for side in [4,8,12,18,24]}})
result={'schema':'strehl.sr-focus-registration-preselection.v1','command':__import__('sys').argv,'source_sha256':sha(Path(__file__).read_bytes()),'seal_sha256':sha(A.seal.read_bytes()),'census_report_sha256':seal['census_report_sha256'],'focus_domain_quad':[fx,fy,w,h],'selection_basis':'Only sealed full-track focus flags and one-width membership, before local residuals or candidate pixels. Complete-square counts include no extra NCC search or filter halo; those stricter requirements can only reduce support.','pairs':out}
A.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
