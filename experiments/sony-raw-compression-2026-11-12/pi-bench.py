"""No NumPy needed. RAM-only native Rust prediction and system Zstd on Pi."""
from pathlib import Path
import ctypes as C, ctypes.util, hashlib, json, os, resource, time
from concurrent.futures import ThreadPoolExecutor

ROOT=Path('/run/strehl-compression-20261112')
LIB_PATH=Path('/home/strehl/strehl-compression-probe/libpredict.so')
lib=C.CDLL(str(LIB_PATH))
lib.strehl_predict.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_size_t,C.c_uint,C.c_bool]
lib.strehl_predict.restype=C.c_int
z=C.CDLL(ctypes.util.find_library('zstd'))
z.ZSTD_compressBound.argtypes=[C.c_size_t];z.ZSTD_compressBound.restype=C.c_size_t
z.ZSTD_compress.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.c_int];z.ZSTD_compress.restype=C.c_size_t
z.ZSTD_decompress.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t];z.ZSTD_decompress.restype=C.c_size_t
z.ZSTD_isError.argtypes=[C.c_size_t];z.ZSTD_isError.restype=C.c_uint
z.ZSTD_versionString.restype=C.c_char_p

def code(src,level=1):
    dst=C.create_string_buffer(z.ZSTD_compressBound(len(src)))
    count=z.ZSTD_compress(dst,len(dst),src,len(src),level)
    assert not z.ZSTD_isError(count)
    return dst.raw[:count]

def decode(src,n):
    dst=C.create_string_buffer(n)
    count=z.ZSTD_decompress(dst,n,src,len(src))
    assert count==n
    return dst

def state():
    return {'load':Path('/proc/loadavg').read_text().strip(),
            'temperature_mC':int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()),
            'max_rss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}

def one(src,mode,reference=None):
    if mode<0:return code(src),None
    assert mode not in range(4,8) or (reference is not None and len(reference)==len(src))
    target=C.create_string_buffer(len(src))
    count=len(src)//2;w=9600;h=count//w
    assert h*w==count
    assert lib.strehl_predict(src,reference,target,w,h,mode,False)==0
    return code(target),h

def check(src,packet,mode,reference=None):
    packed,h=packet
    delta=decode(packed,len(src))
    if mode<0:result=delta.raw
    else:
        final=C.create_string_buffer(len(src))
        assert lib.strehl_predict(delta,reference,final,9600,h,mode,True)==0
        result=final.raw
    assert result==src

if __name__=='__main__':
    path=ROOT/'DSC01472.ARW';data=path.read_bytes()
    offset=548864;size=122419200
    assert len(data)==122968064
    body=data[offset:offset+size];side=data[:offset]+data[offset+size:]
    ref_data=(ROOT/'DSC01473.ARW').read_bytes()
    ref_offset=544768
    assert len(ref_data)==122963968 and ref_offset+size<=len(ref_data)
    ref=ref_data[ref_offset:ref_offset+size]
    assert len(ref)==len(body)
    print(json.dumps({'environment':state(),'zstd':z.ZSTD_versionString().decode(),
                      'rust_library_sha256':hashlib.sha256(LIB_PATH.read_bytes()).hexdigest(),
                      'input_sha256':hashlib.sha256(data).hexdigest()}),flush=True)
    for workers in [1,4]:
        for mode in [-1,2,3,8,9,4,6]:
            for repeat in range(3):
                before=state();start=time.perf_counter()
                source=data if mode<0 else body
                if workers==1:
                    packets=[one(source,mode,ref)];chunks=[source];references=[ref]
                else:
                    chunk_size=9600*2*256 if mode>=0 else 4*1024*1024
                    chunks=[source[i:i+chunk_size] for i in range(0,len(source),chunk_size)]
                    references=[ref[i:i+chunk_size] for i in range(0,len(source),chunk_size)] if mode>=0 else [None]*len(chunks)
                    with ThreadPoolExecutor(max_workers=workers) as pool:
                        packets=list(pool.map(lambda p:one(p[0],mode,p[1]),zip(chunks,references)))
                extra=code(side) if mode>=0 else b''
                encoded=sum(len(x[0]) for x in packets)+len(extra)+128+24*len(packets)
                encode_s=time.perf_counter()-start
                start=time.perf_counter()
                for chunk,pkt,reference in zip(chunks,packets,references):check(chunk,pkt,mode,reference)
                assert mode<0 or decode(extra,len(side)).raw==side
                decode_s=time.perf_counter()-start
                print(json.dumps({'workers':workers,'mode':mode,'repeat':repeat,'input_bytes':len(data),
                                  'encoded_bytes':encoded,'encode_s':encode_s,'decode_s_serial':decode_s,
                                  'roundtrip_exact':True,'before':before,'after':state()}),flush=True)
