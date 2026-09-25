"""Read-only cache attribution; no RAW, no candidate operator, no image writes."""
from pathlib import Path
import hashlib,json
import numpy as np
import tifffile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def read(path):return json.loads(path.read_text())
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def floats(bits):return np.asarray(bits,dtype='<u4').view('<f4')
def cache(path):
    m=read(path);p=path.parent/m['binary'];assert sha(p)==m['binary_sha256']
    v=np.memmap(p,dtype='<f4',mode='r',shape=(4,m['crop'][3],m['crop'][2]))
    assert np.isfinite(v).all();return m,v

old_path=HERE/'garnet-off-1/output/baseline-cache.json'
new_path=HERE/'garnet-fixed-1/output/candidate-cache.json'
om,old=cache(old_path);nm,new=cache(new_path)
for key in ('crop','levels_bits','wb_gains_bits','xyz_to_cam_bits','exposure_stops_bits'):
    assert om[key]==nm[key]
record=read(ROOT/'experiments/highlight-rendering/replay-garnet104-1/output/baseline-verified.json')
dev=record['resolved_development'];matrix=floats(dev['matrix_bits']);ceil=floats(dev['ceiling_bits'])
top=floats(dev['sensor_top_bits']);eg=floats(dev['exposure_gain_bits'])
gains=floats(om['wb_gains_bits']);levels=floats(om['levels_bits']);span=levels[1]-levels[0]
weights=np.array([.2126,.7152,.0722],np.float32)
def apply_matrix(v):
    # Separate f32 operations match color::apply (no BLAS/FMA reordering).
    return np.stack([matrix[r,0]*v[0]+matrix[r,1]*v[1]+matrix[r,2]*v[2] for r in range(3)])
def luma(v):return weights[0]*v[0]+weights[1]*v[1]+weights[2]*v[2]
def anchors(planes):
    p=planes[:,::7,::7]
    values=[np.maximum(p[c],np.float32(0))*gains[g]*eg/span for c,g in ((0,0),(1,1),(2,1),(3,2))]
    v=np.stack([values[0],np.float32(.5)*(values[1]+values[2]),values[3]])
    pinned=np.any(v>=ceil[:,None,None],axis=0)
    v=np.where(pinned[None],np.minimum(v,ceil.min()),v)
    u=np.maximum(np.float32(0),np.max(v/ceil[:,None,None],axis=0))
    x=np.clip((u-np.float32(.6))/(top-np.float32(.6)),np.float32(0),np.float32(1))
    t=x*x*(np.float32(3)-np.float32(2)*x)
    n=np.zeros_like(u)
    for r in range(3):n+=weights[r]*(matrix[r,0]*v[0]+matrix[r,1]*v[1]+matrix[r,2]*v[2])
    v=np.where((t>0)[None],v+t[None]*(n[None]-v),v)
    lum=luma(apply_matrix(v)).ravel();assert np.isfinite(lum).all()
    ordered=np.sort(lum)
    at=lambda pct:ordered[int(np.floor((pct/100)*(len(lum)-1)+.5))]
    black=at(.1)*np.float32(.85)
    white=black+np.maximum(at(99.9)-black,np.float32(1e-4))/np.float32(.9)
    triple=np.array([black,white,.55],np.float32)
    return dict(bits=triple.view('u4').tolist(),values=triple.tolist(),sample_count=len(lum),
                sampled_white_luminance=float(at(99.9))),lum

old_tone,old_lum=anchors(old);new_tone,new_lum=anchors(new)
assert old_tone['bits']==dev['tone_bits'],(old_tone,dev['tone_bits'])
old_census=read(HERE/'garnet-on-1/census.json')
rows=[]
for c in range(4):
    r=next(r for r in old_census if r['stage']=='resolved' and r.get('plane')==c and r.get('band')==2)
    assert len(r['scan']['first_nonfinite_xy_bits'])==r['scan']['negative_infinity']<64
    bad=np.zeros(old.shape[1:],bool)
    for x,y,_ in r['scan']['first_nonfinite_xy_bits']:bad[4*y-6:4*y+7,4*x-6:4*x+7]=True
    diff=np.abs(new[c]-old[c]);changed=old[c].view('u4')!=new[c].view('u4');off=changed&~bad
    rows.append(dict(plane=c,old_bad_sites=int(bad.sum()),old_bad_changed=int((bad&changed).sum()),
        old_bad_max_abs_dn=float(diff[bad].max()),outside_bad_changed=int(off.sum()),outside_max_abs_dn=float(diff[~bad].max()),
        outside_changed_quantiles=np.quantile(diff[off],[0,.5,.9,.99,1]).tolist(),
        outside_exceed_0_001_dn=int((diff[~bad]>.001).sum())))
with tifffile.TiffFile(HERE/'garnet-off-1/output/baseline.tiff') as f:rgb_old=f.asarray();icc_old=bytes(f.pages[0].tags[34675].value)
with tifffile.TiffFile(HERE/'garnet-fixed-1/output/candidate.tiff') as f:rgb_new=f.asarray();assert bytes(f.pages[0].tags[34675].value)==icc_old
delta=np.abs(rgb_new.astype(np.int32)-rgb_old.astype(np.int32));changes=np.any(delta!=0,axis=2)
rois={}
for name,(x,y,w,h) in dict(red_control=(3068,1908,384,384),dark_control=(256,256,384,384),white_facet=(4668,1858,384,384)).items():
    d=delta[y:y+h,x:x+w];a=rgb_old[y:y+h,x:x+w];b=rgb_new[y:y+h,x:x+w]
    rois[name]=dict(native_xywh=[x,y,w,h],changed_pixels=int(np.any(d!=0,axis=2).sum()),max_code_delta=int(d.max()),
        median_abs_code_delta=float(np.median(d)),mean_abs_code_delta=float(d.mean()),
        mean_code_change=float(np.mean(b.astype(np.int32)-a.astype(np.int32))))
result=dict(scope='Numerical attribution only; neither pixel-change count nor dimming is a quality score.',
    old_cache_sha256=sha(old_path),new_cache_sha256=sha(new_path),
    old_tone_reproduces_actual_writer_bits=True,old_tone=old_tone,new_tone_reconstructed=new_tone,
    new_tone_direct_writer_capture=False,
    nominal_placement_gain_ratio=(old_tone['values'][1]-old_tone['values'][0])/(new_tone['values'][1]-new_tone['values'][0]),
    tone_sample_luminances_changed=int(np.count_nonzero(old_lum.view('u4')!=new_lum.view('u4'))),
    cfa=rows,rgb_changed_pixels=int(changes.sum()),rgb_channel_abs_delta_quantiles=np.quantile(delta,[0,.5,.9,.99,.999,1]).tolist(),rois=rois)
out=HERE/'garnet-finite-and-tone-attribution.json'
assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
