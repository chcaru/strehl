"""CCSDS adaptive entropy coding vs Zstd on exact CFA prediction residuals."""
import json,time
import numpy as np
import imagecodecs as ic
from bench import OUT,load,transform,controls
from advanced import shifted_reference

def aec_pack(a,block=32):
    n=((a.size+block*128-1)//(block*128))*block*128
    padded=np.zeros(n,dtype='u2');padded[:a.size]=a
    return ic.aec_encode(padded,bitspersample=16,flags=0,blocksize=block,rsi=128)

def aec_unpack(p,size,block=32):
    n=((size+block*128-1)//(block*128))*block*128
    b=ic.aec_decode(p,bitspersample=16,flags=0,blocksize=block,rsi=128,out=np.empty(n,dtype='u2'))
    assert not np.any(b[size:])
    return b[:size]

def run():
    controls()
    # Negative: arbitrary 16-bit noise, odd block boundary. Positive: constants.
    rng=np.random.default_rng(728)
    for a in [np.zeros(1031,dtype='u2'),rng.integers(0,65536,1031,dtype='u2')]:
        for block in [16,32,64]:
            p=aec_pack(a,block)
            b=aec_unpack(p,a.size,block)
            assert np.array_equal(a,b)
    print(json.dumps({'aec_controls':6}),flush=True)
    for group in ['4','16']:
        files=sorted((OUT/'inputs'/('pixel-shift-'+group)).glob('*.ARW'))
        previous=None
        for idx,path in enumerate(files):
            data,a,off=load(path);side=data[:off]+data[off+a.nbytes:]
            methods=[('spatial',8,None)]
            if previous is not None:methods+=[('filtered-temporal',4,shifted_reference(previous,0,0,True))]
            for kind,mode,reference in methods:
                start=time.perf_counter();delta=transform(a,mode,reference)
                residual=delta.reshape(2,-1).T.copy().view('<u2').ravel()
                # CFA phase order improves per-block adaptation to different
                # colour-channel noise levels. Descriptor records the layout.
                residual=residual.reshape(a.shape).reshape(a.shape[0]//2,2,a.shape[1]//2,2).transpose(1,3,0,2).copy().ravel()
                payload=aec_pack(residual)
                extra=ic.zstd_encode(side,level=1);enc=time.perf_counter()-start
                start=time.perf_counter()
                decoded=aec_unpack(payload,residual.size)
                decoded=decoded.reshape(2,2,a.shape[0]//2,a.shape[1]//2).transpose(2,0,3,1).copy().ravel()
                decoded=decoded.view('u1').reshape(-1,2).T.copy().ravel()
                b=transform(decoded,mode,reference,True,a.shape)
                assert np.array_equal(a,b) and ic.zstd_decode(extra)==side
                print(json.dumps({'group':group,'file':path.name,'index':idx,'kind':kind,
                                  'bytes':len(payload)+len(extra)+512,'encode_s':enc,
                                  'decode_s':time.perf_counter()-start,'exact':True}),flush=True)
            previous=a

if __name__=='__main__':run()
