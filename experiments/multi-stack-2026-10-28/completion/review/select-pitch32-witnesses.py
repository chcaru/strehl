"""Preselect focus-gap witnesses from existing dense-half maps; no photograph/RAW read."""
import os
for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):os.environ[k]="1"
from pathlib import Path
import hashlib,json,sys
import numpy as np
from scipy import ndimage
import tifffile
R=Path(__file__).resolve().parents[4]; F=R/"outputs/multi-stack/completion/interleave-02/focus"
O=R/"experiments/multi-stack-2026-10-28/completion/review/pitch32-focus-witnesses.json"
def sha(p):
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def nearest(v,positions):
    result=np.full(v.shape,np.inf,dtype=np.float32)
    for p in positions:np.minimum(result,np.abs(v-p),out=result)
    return result
A=np.arange(0,182,32);B=np.arange(16,182,32)
def selection(a,b,wa,wb,valid):
    base=valid & np.isfinite(a)&np.isfinite(b)&np.isfinite(wa)&np.isfinite(wb)&(wa>0)&(wb>0)&(np.abs(a-b)<=np.maximum(wa,wb))
    da,db=nearest(a,A),nearest(b,A);ea,eb=nearest(a,B),nearest(b,B)
    return (base&(da<.5*wa)&(db<.5*wb)&(ea>2*wa)&(eb>2*wb),
            base&(ea<.5*wa)&(eb<.5*wb)&(da>2*wa)&(db>2*wb),base)
# Failing inputs exercised before applying the selector to real maps.
x=np.array([32.,48.,32.,32.,32.],dtype='f4');y=np.array([33.,49.,42.,33.,33.],dtype='f4')
w=np.array([4.,4.,4.,20.,4.],dtype='f4');v=np.array([1,1,1,1,0],dtype=bool)
a,b,_=selection(x,y,w,w,v)
assert a.tolist()==[True,False,False,False,False] and b.tolist()==[False,True,False,False,False]
bindings=[];maps=[];geometries=[]
for i in (1,2):
    d=F/f"pass-{i:02}"; gp=d/"geometry.json";g=json.loads(gp.read_text());geometries.append(g)
    receipt={v['file']:v for v in g['files']}; row={}
    for name in ('mode-1-ordinal','width-frames','usable'):
        p=d/f"{name}.tiff"; r=receipt[p.name]
        assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
        data=tifffile.memmap(p,mode='r');assert list(data.shape[::-1])==g['dimensions']
        row[name]=data;bindings.append({'path':str(p),'sha256':r['sha256']})
    maps.append(row)
assert all(geometries[0][k]==geometries[1][k] for k in ('dimensions','origin_quad','step_quad'))
assert geometries[0]['step_quad']==[1,1]
ma=2*maps[0]['mode-1-ordinal'];mb=2*maps[1]['mode-1-ordinal']+1
wa=2*maps[0]['width-frames'];wb=2*maps[1]['width-frames']
valid=(maps[0]['usable']>0)&(maps[1]['usable']>0)
even,offset,base=selection(ma,mb,wa,wb,valid)
widths=[]
for m,w in zip(maps,(wa,wb)):
    q=(m['usable']>0)&np.isfinite(w)&(w>0)
    widths.append({'count':int(q.sum()),'original_frame_shape_width_quantiles':np.quantile(w[q],[.1,.5,.9]).tolist()})
witnesses=[];census={}
for direction,mask in [('even32-good',even),('offset16-good',offset)]:
    labels,n=ndimage.label(mask,np.ones((3,3),dtype='i1'))
    sizes=np.bincount(labels.ravel());sizes[0]=0
    density=ndimage.uniform_filter(mask.astype('f4'),size=192,mode='constant')
    ids=np.argsort(sizes)[::-1]
    selected=[]
    for component in ids[:100]:
        if component==0 or sizes[component]==0:continue
        inds=np.flatnonzero(labels.ravel()==component)
        best=inds[np.argmax(density.ravel()[inds])];y,x=np.unravel_index(best,mask.shape)
        center=np.array([2*int(x),2*int(y)])
        if any(np.max(np.abs(center-np.array(z['center_sensor_in_dense_control'])))<384 for z in selected):continue
        x0=max(0,min(mask.shape[1]-192,int(x)-96));y0=max(0,min(mask.shape[0]-192,int(y)-96))
        q=(slice(y0,y0+192),slice(x0,x0+192));local=mask[q]
        row={'direction':direction,'component':int(component),'component_pixels':int(sizes[component]),
             'center_sensor_in_dense_control':center.tolist(),'origin_sensor_in_dense_control':[2*x0,2*y0],'native_size':384,
             'qualifying_quad_pixels_in_witness':int(local.sum()),'qualifying_fraction':float(local.mean()),
             'center_modes_original_ordinals':[float(ma[y,x]),float(mb[y,x])],
             'center_widths_original_frames':[float(wa[y,x]),float(wb[y,x])],
             'geometry_origin_quad':geometries[0]['origin_quad']}
        selected.append(row)
        if len(selected)==3:break
    witnesses+=selected
    census[direction]={'qualifying_pixels':int(mask.sum()),'components':int(n),'largest_component_pixels':int(sizes.max()),'witnesses':len(selected)}
result={'schema':'strehl.pitch32-focus-witnesses.v1','argv':sys.argv,'workers':1,'no_photograph_pixels_read':True,
 'protocol':'Both usable; primary modes in original acquisition ordinals agree within max shape width. Each half independently requires distance to good sample <0.5 own width and distance to bad sample >2 own width. Eight-connected components ranked by area; witness center is maximum192quad density within each component, deterministic tie-first. Up to3 nonoverlapping384sensor witnesses per direction.',
 'shape_not_confidence':'Local width is a shape descriptor, not calibrated uncertainty. Selection predicts an adverse gap; does not prove detail or unbiased geometry.',
 'controls':{'even_positive':True,'offset_positive':True,'inconsistent_modes_refused':True,'broad_width_refused':True,'unusable_refused':True},
 'sampling':{'even32':A.tolist(),'offset16':B.tolist()},'widths':widths,'both_usable':int(valid.sum()),'consistent_usable':int(base.sum()),'census':census,
 'gauge_policy':'Coordinates are in existing dense-half output gauge6800x4534. Before candidate viewing, map these physical regions into NEW first-half control gauge and freeze rounded native384 origins there; no cross-gauge pixel differences.',
 'map_bindings':bindings,'geometry_receipt_sha256':[sha(F/f"pass-{i:02}/geometry.json") for i in (1,2)],'witnesses':witnesses}
with O.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps({'widths':widths,'census':census,'output':str(O),'sha256':sha(O)},indent=2))
