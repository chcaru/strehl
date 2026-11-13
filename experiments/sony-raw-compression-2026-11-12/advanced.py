"""Stronger spatial coding and causal temporal prediction on genuine RAWs."""
import argparse, ctypes, hashlib, json, time
from pathlib import Path
import numpy as np
import imagecodecs as ic
from scipy.ndimage import uniform_filter, shift
from scipy.signal import fftconvolve
from bench import OUT, LIB, controls, load, transform, benchmark

LIB.strehl_splitbits.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_bool]
LIB.strehl_splitbits.restype=ctypes.c_size_t

def splitbits(a,bits,inverse=False,n=None):
    a=np.ascontiguousarray(a,dtype='u1');n=n or a.size//2
    total=(n*bits+7)//8+2*n
    dest=np.empty(n*2 if inverse else total,dtype='u1')
    assert LIB.strehl_splitbits(a.ctypes.data,dest.ctypes.data,n,bits,inverse)==total
    return dest

def controls_extra():
    rng=np.random.default_rng(9912)
    for n in [1,7,8,17,32768]:
        a=rng.integers(0,256,2*n,dtype='u1')
        for bits in range(1,9):
            assert np.array_equal(a,splitbits(splitbits(a,bits),bits,True,n))
    print(json.dumps({'splitbit_controls':40}),flush=True)

def shifted_reference(a,dy,dx,filtered=False):
    # Predict each CFA phase separately. Never interpolate the signal being coded.
    r=np.empty_like(a)
    for py in range(2):
        for px in range(2):
            plane=a[py::2,px::2].astype('f4')
            if filtered:plane=uniform_filter(plane,size=3,mode='nearest')
            q=shift(plane,(dy/2,dx/2),order=1,mode='nearest',prefilter=False)
            r[py::2,px::2]=np.clip(np.rint(q),0,65535).astype('u2')
    return r

def probe(path,a,side,method,reference=None,bits=None):
    start=time.perf_counter();delta=transform(a,method,reference)
    if bits is not None:delta=splitbits(delta,bits)
    packet=ic.zstd_encode(delta,level=1);other=ic.zstd_encode(side,level=1)
    enc_s=time.perf_counter()-start
    start=time.perf_counter();decoded=np.frombuffer(ic.zstd_decode(packet),dtype='u1')
    if bits is not None:decoded=splitbits(decoded,bits,True,a.size)
    b=transform(decoded,method,reference,True,a.shape)
    assert np.array_equal(a,b) and ic.zstd_decode(other)==side
    dec_s=time.perf_counter()-start
    # The wrapper has not yet been frozen; 512 bytes includes its descriptors.
    return {'file':path.name,'method':method,'bits':bits,'encoded_bytes':len(packet)+len(other)+512,
            'encode_s':enc_s,'decode_s':dec_s,'exact_sensor_and_side':True}

def spatial():
    for group in ['4','16']:
        path=sorted((OUT/'inputs'/('pixel-shift-'+group)).glob('*.ARW'))[0]
        benchmark(path,['ljpeg-phase','jpegls-phase'],label=group)
        data,a,off=load(path);side=data[:off]+data[off+a.nbytes:]
        for mode in [2,3,8,9]:
            for bits in [None,4,5,6,7,8]:
                r=probe(path,a,side,mode,bits=bits);r['group']=group
                print(json.dumps(r),flush=True)

def temporal():
    for group in ['4','16']:
        files=sorted((OUT/'inputs'/('pixel-shift-'+group)).glob('*.ARW'))
        prev=None;running=None;count=0
        for index,path in enumerate(files):
            data,a,off=load(path);side=data[:off]+data[off+a.nbytes:]
            benchmark(path,['jpegls-phase'],label=group)
            if prev is not None:
                # Fit low-resolution same-color shift from a fixed central ROI.
                # Search a deliberately small +/-2 sensor pixel range. This is
                # compression side information, not a geometric-quality claim.
                sy=slice(2000,3024);sx=slice(3000,4024)
                target=a[sy,sx].astype('f4')
                costs=[]
                for dy,dx in [(y,x) for y in [-2,-1,0,1,2] for x in [-2,-1,0,1,2]]:
                    ref=shifted_reference(prev[sy,sx],dy,dx)
                    costs.append((float(np.mean(np.abs(target[8:-8,8:-8]-ref[8:-8,8:-8]))),dy,dx))
                _,dy,dx=min(costs)
                for kind in ['spatial','raw-reference','aligned-reference','filtered-reference','running-reference']:
                    start=time.perf_counter()
                    if kind=='spatial':ref=None
                    elif kind=='raw-reference':ref=prev
                    elif kind=='aligned-reference':ref=shifted_reference(prev,dy,dx)
                    elif kind=='filtered-reference':ref=shifted_reference(prev,dy,dx,True)
                    else:ref=np.rint(running/count).astype('u2')
                    prep=time.perf_counter()-start
                    r=probe(path,a,side,8 if ref is None else 4,ref,None)
                    r.update(group=group,index=index,reference_kind=kind,shift=[dy,dx],reference_prepare_s=prep)
                    print(json.dumps(r),flush=True)
            else:
                r=probe(path,a,side,8);r.update(group=group,index=0,reference_kind='spatial-keyframe')
                print(json.dumps(r),flush=True)
            if running is None:running=a.astype('f4')
            else:running+=a
            count+=1;prev=a

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('suite',choices=['spatial','temporal','controls']);args=p.parse_args()
    controls();controls_extra()
    if args.suite=='spatial':spatial()
    if args.suite=='temporal':temporal()
