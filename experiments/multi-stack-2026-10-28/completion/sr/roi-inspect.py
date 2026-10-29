"""Inspect a completed bounded SR ROI at native pixel size, common fixed display."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import tifffile
from PIL import Image, ImageDraw
p=argparse.ArgumentParser();p.add_argument('pilot',type=Path);a=p.parse_args();root=a.pilot.resolve()
r=json.loads((root/'report.json').read_text());assert r['schema']=='strehl.sr-roi-pilot.v1'
w,h=r['roi_sensor'][2:];assert 0<w<=512 and 0<h<=512
planes={};baselines={}
keys=['native','candidate']
if (root/'matched-cfa-mhc.tiff').is_file(): keys.append('matched-cfa-mhc')
for key in keys:
    with tifffile.TiffFile(root/f'{key}.tiff') as f:
        assert f.pages[0].shape==(h,w,3)
        planes[key]=f.asarray()
        line=next(x for x in f.pages[0].description.splitlines() if x.startswith('DisplayBaseline: '))
        baselines[key]=json.loads(line.split(': ',1)[1])
    assert planes[key].dtype==np.float32 and np.isfinite(planes[key]).all()
assert all(b==baselines['native'] for b in baselines.values())
eligible=np.fromfile(root/'native-linear-eligible.u8',np.uint8).reshape(h,w).astype(bool)
reason=np.fromfile(root/'reason.u8',np.uint8).reshape(h,w,3)
variance_valid=np.fromfile(root/'variance-valid.u8',np.uint8).reshape(h,w,3).astype(bool)
phase=np.fromfile(root/'phase-condition.f32',np.float32).reshape(h,w,3)
native_bits=planes['native'].view(np.uint32);candidate_bits=planes['candidate'].view(np.uint32)
assert np.array_equal(native_bits[~eligible],candidate_bits[~eligible]),'nonlinear native bits changed'
coherent_file=root/'coherent-rgb-mask.u8'
coherent=np.fromfile(coherent_file,np.uint8).reshape(h,w).astype(bool) if coherent_file.exists() else None
whole_fallback=~coherent if coherent is not None else np.all(reason!=0,axis=2)
assert np.array_equal(native_bits[whole_fallback],candidate_bits[whole_fallback]),'all-native fallback bits changed'
matched_support=None
if 'matched-cfa-mhc' in planes:
    matched_support=np.fromfile(root/'matched-cfa-mhc-support.u8',np.uint8).reshape(h,w).astype(bool)
    assert coherent is not None and np.all(~matched_support|coherent),'matched comparator escaped candidate support'
    assert np.array_equal(native_bits[~matched_support],planes['matched-cfa-mhc'].view(np.uint32)[~matched_support]),'matched fallback bits changed'
def display(v):
    # Direct port of unchanged DisplayBaseline::place, gamut_map and default
    # display_sample. Common fixed transform; no per-arm auto stretch or resize.
    b=baselines['native'];v=v.copy();lum=np.maximum(v@np.array([.2126,.7152,.0722],np.float32),0.)
    scale=np.float32(1/(b['white']-b['black']));y=(lum-b['black'])*scale
    soft=.5*(y+np.sqrt(y*y+.004*.004))
    gain=np.where(lum>0,np.minimum(soft/np.maximum(lum,1e-30),scale)*b['exposure_gain'],0.)
    v*=gain[...,None];y=np.clip(v@np.array([.2126,.7152,.0722],np.float32),0,1)
    t=np.zeros((h,w),np.float32)
    for c in range(3):
        q=v[...,c];low=(q<0)&(y-q>1e-6);high=(q>1)&(q-y>1e-6)
        t=np.maximum(t,np.where(low,-q/np.maximum(y-q,1e-30),0.))
        t=np.maximum(t,np.where(high,(q-1)/np.maximum(q-y,1e-30),0.))
    v=np.clip(v+(y[...,None]-v)*np.clip(t,0,1)[...,None],0,1)
    x=np.where(v<=.0031308,v*12.92,1.055*np.power(v,1/2.4)-.055)
    x=x+(x*x*(3-2*x)-x)*b['contrast']
    return np.floor(np.clip(x,0,1)*255+.5).astype(np.uint8)
out=root/'inspection';out.mkdir(exist_ok=False)
canvas=Image.new('RGB',(len(keys)*w+12*(len(keys)-1),h+22),(32,32,32));draw=ImageDraw.Draw(canvas)
for i,key in enumerate(keys):
    image=Image.fromarray(display(planes[key]));image.save(out/f'{key}.png');canvas.paste(image,(i*(w+12),22));draw.text((i*(w+12),4),key,fill=(240,240,240))
canvas.save(out/'comparison-native-pixels.png')
mask=np.where(reason==0,255,0).astype(np.uint8);Image.fromarray(mask).save(out/'reconstructed-rgb-mask.png')
if coherent is not None:
    Image.fromarray(np.where(coherent,255,0).astype(np.uint8)).save(out/'coherent-rgb-mask.png')
    assert np.all(~variance_valid[~coherent]),'native fallback incorrectly reports known variance'
result={'status':'ROI consistency and display inspection; not photographic truth or full-scene validation','roi_sensor':r['roi_sensor'],'same_baseline':baselines['native'],'native_pixel_display':True,'nonlinear_native_exact_bits':True,'whole_native_fallback_exact_bits':True,'reconstructed_pixels_rgb':np.sum(reason==0,axis=(0,1)).tolist(),'coherent_delivered_pixels':int(coherent.sum()) if coherent is not None else None,'unknown_variance_pixels_rgb':np.sum(~variance_valid,axis=(0,1)).tolist(),'reconstructed_condition_percentiles_rgb':[np.percentile(phase[...,c][reason[...,c]==0],[0,50,95,100]).tolist() if np.any(reason[...,c]==0) else None for c in range(3)],'difference_to_native_rgb_rmse':np.sqrt(np.mean((planes['candidate']-planes['native'])**2,axis=(0,1))).tolist(),'difference_is_not_quality':True,'input_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['report.json','native.tiff','candidate.tiff']}}
if matched_support is not None:
    result['matched_comparator_pixels']=int(matched_support.sum())
    result['matched_native_fallback_exact_bits']=True
    result['input_sha256']['matched-cfa-mhc.tiff']=hashlib.sha256((root/'matched-cfa-mhc.tiff').read_bytes()).hexdigest()
    result['input_sha256']['matched-cfa-mhc-support.u8']=hashlib.sha256((root/'matched-cfa-mhc-support.u8').read_bytes()).hexdigest()
(out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
