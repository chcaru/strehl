"""Full-file exactness and codec comparisons. All original inputs are read-only."""
from pathlib import Path
import argparse, ctypes, hashlib, json, os, platform, time
import imagecodecs as ic
import numpy as np
import rawpy
import tifffile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/sony-raw-compression-2026-11-12'
LIB = ctypes.CDLL(str(OUT / ('predict-v3.dll' if os.name == 'nt' else 'libpredict.so')))
LIB.strehl_predict.argtypes = [ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,
                               ctypes.c_size_t,ctypes.c_size_t,ctypes.c_uint,ctypes.c_bool]
LIB.strehl_predict.restype = ctypes.c_int


def transform(a, mode, ref=None, inverse=False, shape=None):
    a = np.ascontiguousarray(a)
    if ref is not None: ref = np.ascontiguousarray(ref,dtype='<u2')
    h,w = shape or a.shape
    assert ref is None or ref.shape==(h,w)
    dest = np.empty((h,w),dtype='<u2') if inverse else np.empty(h*w*2,dtype='u1')
    assert LIB.strehl_predict(a.ctypes.data,ref.ctypes.data if ref is not None else None,
                             dest.ctypes.data,w,h,mode,inverse) == 0
    return dest


def load(path):
    data = path.read_bytes()
    found=[]
    with tifffile.TiffFile(path) as t:
        for pg in t.pages:
            for q in [pg]+list(pg.pages or []):
                if int(q.photometric)==32803 and int(q.compression)==1:
                    offsets=q.tags[273].value;counts=q.tags[279].value
                    assert len(offsets)==len(counts)==1
                    h,w=q.shape;off=offsets[0]
                    assert counts[0]==h*w*2 and off+counts[0]<=len(data)
                    found.append((off,h,w))
    assert len(found)==1
    off,h,w=found[0]
    a=np.frombuffer(data,dtype='<u2',offset=off,count=h*w).reshape(h,w).copy()
    with rawpy.imread(str(path)) as raw:
        independent=raw.raw_image.copy()
        assert np.array_equal(a,independent), 'Independent full sensor decode mismatch'
    return data,a,off


def controls():
    rng=np.random.default_rng(732891)
    cases=[np.zeros((32,48),dtype='u2'),np.full((32,48),65535,dtype='u2'),
           np.arange(32*48,dtype='u2').reshape(32,48),rng.integers(0,65536,(32,48),dtype='u2')]
    checked=0
    for a in cases:
        ref=rng.integers(0,65536,a.shape,dtype='u2')
        for mode in range(10):
            coded=transform(a,mode,ref)
            packed=ic.zstd_encode(coded,level=1)
            unpacked=np.frombuffer(ic.zstd_decode(packed),dtype='u1')
            b=transform(unpacked,mode,ref,True,a.shape)
            assert np.array_equal(a,b)
            checked+=1
    a=cases[-1];ref=cases[2];packed=transform(a,4,ref)
    wrong=transform(packed,4,np.zeros_like(ref),True,a.shape)
    assert not np.array_equal(a,wrong)
    corrupted=packed.copy();corrupted[413]^=1
    assert hashlib.sha256(transform(corrupted,4,ref,True,a.shape).tobytes()).digest()!=hashlib.sha256(a.tobytes()).digest()
    data=ic.zstd_encode(a)
    try: ic.zstd_decode(data[:len(data)//2])
    except Exception: pass
    else: raise AssertionError('Truncated frame accepted')
    print(json.dumps({'controls':checked,'wrong_reference_rejected':True,'corruption_rejected':True,'truncation_rejected':True}),flush=True)


def benchmark(path, methods, ref=None, label=None):
    data,a,offset=load(path)
    side=data[:offset]+data[offset+a.nbytes:]
    original_hash=hashlib.sha256(data).hexdigest()
    for method in methods:
        before=time.perf_counter()
        mode=None;layout='cfa'
        if method.startswith('zstd'):
            encoded=ic.zstd_encode(data,level=int(method[-1]));payload=encoded;extra=b''
        else:
            if method.startswith('pred'):
                mode=int(method.split('-')[0][4:]);v=transform(a,mode,ref)
                payload=ic.zstd_encode(v,level=int(method[-1]))
            elif method.startswith('shuffle'):
                v=a.view('u1').reshape(-1,2).T.copy();payload=ic.zstd_encode(v,level=int(method[-1]))
            elif method.startswith('bitshuffle'):
                v=ic.bitshuffle_encode(a);payload=ic.zstd_encode(v,level=int(method[-1]))
            elif method in ('ljpeg','jpegls','ljpeg-phase','jpegls-phase'):
                v=a
                if method.endswith('phase'):
                    v=a.reshape(a.shape[0]//2,2,a.shape[1]//2,2).transpose(1,3,0,2).reshape(2*a.shape[0],a.shape[1]//2).copy();layout='phase'
                payload=ic.ljpeg_encode(v,bitspersample=14) if method.startswith('ljpeg') else ic.jpegls_encode(v,level=0)
            elif method.startswith('jxl'):
                # Pack four CFA phases as independent channels, no demosaicing.
                if 'rgba' in method:
                    v=a.reshape(a.shape[0]//2,2,a.shape[1]//2,2).transpose(0,2,1,3).reshape(a.shape[0]//2,a.shape[1]//2,4).copy();layout='rgba'
                else:v=a
                payload=ic.jpegxl_encode(v,lossless=True,effort=int(method[-1]),bitspersample=14,numthreads=1)
            else: raise ValueError(method)
            extra=ic.zstd_encode(side,level=1)
            # Account for a fixed 256-byte file descriptor/reference hash budget.
            encoded=payload+extra+bytes(256)
        encode_s=time.perf_counter()-before
        before=time.perf_counter()
        if method.startswith('zstd'):reconstructed=ic.zstd_decode(encoded)
        else:
            if mode is not None:
                decoded=np.frombuffer(ic.zstd_decode(payload),dtype='u1')
                b=transform(decoded,mode,ref,True,a.shape)
            elif method.startswith('shuffle'):
                b=np.frombuffer(ic.zstd_decode(payload),dtype='u1').reshape(2,-1).T.copy().view('<u2').reshape(a.shape)
            elif method.startswith('bitshuffle'):
                b=ic.bitshuffle_decode(np.frombuffer(ic.zstd_decode(payload),dtype='<u2').reshape(a.shape))
            elif method.startswith('ljpeg') or method.startswith('jpegls'):
                b=ic.ljpeg_decode(payload) if method.startswith('ljpeg') else ic.jpegls_decode(payload)
                if layout=='phase':b=b.reshape(2,2,a.shape[0]//2,a.shape[1]//2).transpose(2,0,3,1).reshape(a.shape)
            else:
                b=ic.jpegxl_decode(payload,numthreads=1)
                if layout=='rgba':b=b.reshape(a.shape[0]//2,a.shape[1]//2,2,2).transpose(0,2,1,3).reshape(a.shape)
            assert np.array_equal(a,b),(path,method)
            s=ic.zstd_decode(extra)
            reconstructed=s[:offset]+np.ascontiguousarray(b,dtype='<u2').tobytes()+s[offset:]
        decode_s=time.perf_counter()-before
        assert reconstructed==data
        assert hashlib.sha256(reconstructed).hexdigest()==original_hash
        row={'file':str(path),'label':label,'method':method,'input_bytes':len(data),'encoded_bytes':len(encoded),
             'ratio':len(encoded)/len(data),'encode_s':encode_s,'decode_s':decode_s,'shape':list(a.shape),
             'sha256':original_hash,'full_file_exact':True,'worker_count':1,'platform':platform.platform()}
        print(json.dumps(row),flush=True)
    return a


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--suite',choices=['controls','spatial','temporal'],required=True)
    args=parser.parse_args();controls()
    if args.suite=='spatial':
        for group in ['4','16']:
            path=sorted((OUT/'inputs'/('pixel-shift-'+group)).glob('*.ARW'))[0]
            benchmark(path,['zstd1','zstd3','shuffle1','bitshuffle1','pred1-z1','pred2-z1','pred2-z3','pred3-z1','ljpeg','jpegls','jxl-cfa3','jxl-rgba3','jxl-rgba7'],label=group)
    if args.suite=='temporal':
        for group in ['4','16']:
            previous=None
            for path in sorted((OUT/'inputs'/('pixel-shift-'+group)).glob('*.ARW')):
                methods=['pred2-z1','pred2-z3']
                if previous is not None:methods+=['pred4-z1','pred5-z1','pred6-z1','pred7-z1']
                previous=benchmark(path,methods,previous,label=group)
