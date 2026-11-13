"""Experimental bounded, chunked RAW transport; restores the exact original ARW.

Independent chunks and frames: no temporal dependency or Bayer resampling.
No change to the production capture service. The native predictor is Rust.
"""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse, ctypes as C, ctypes.util, hashlib, io, json, os, struct, sys, time

MAX_RAW=256*1024*1024
MAX_CHUNK=8*1024*1024
MAGIC=b'STRHCMP1'
if os.name=='nt':
    import imagecodecs as ic
    root=Path(__file__).resolve().parents[2]/'outputs/sony-raw-compression-2026-11-12'
    lib=C.CDLL(os.environ.get('STREHL_PREDICT_LIBRARY', str(root/'predict-v3.dll')))
    def compress(data):return ic.zstd_encode(data,level=1)
    def decompress(data,n):
        # Preallocate the declared bounded output; refuse a larger expansion.
        out=bytearray(n);value=ic.zstd_decode(data,out=out)
        assert len(value)==n
        return bytes(value)
else:
    lib=C.CDLL(os.environ.get('STREHL_PREDICT_LIBRARY', '/home/strehl/strehl-compression-probe/libpredict.so'))
    z=C.CDLL(ctypes.util.find_library('zstd'))
    z.ZSTD_compressBound.argtypes=[C.c_size_t];z.ZSTD_compressBound.restype=C.c_size_t
    z.ZSTD_compress.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.c_int];z.ZSTD_compress.restype=C.c_size_t
    z.ZSTD_decompress.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t];z.ZSTD_decompress.restype=C.c_size_t
    z.ZSTD_isError.argtypes=[C.c_size_t];z.ZSTD_isError.restype=C.c_uint
    def compress(data):
        out=C.create_string_buffer(z.ZSTD_compressBound(len(data)))
        n=z.ZSTD_compress(out,len(out),data,len(data),1)
        assert not z.ZSTD_isError(n)
        return out.raw[:n]
    def decompress(data,n):
        out=C.create_string_buffer(n)
        got=z.ZSTD_decompress(out,n,data,len(data))
        assert got==n
        return out.raw
lib.strehl_predict.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_size_t,C.c_uint,C.c_bool]
lib.strehl_predict.restype=C.c_int

def predict(data,width,mode,inverse=False):
    assert len(data)%(2*width)==0
    height=len(data)//(2*width)
    assert height>=2
    out=C.create_string_buffer(len(data))
    assert lib.strehl_predict(data,None,out,width,height,mode,inverse)==0
    return out.raw

def layout(data):
    """Read only standard TIFF tags; unsupported layout uses generic bytes."""
    if data[:4]!=b'II*\0':return None
    def u16(at):return struct.unpack_from('<H',data,at)[0]
    def u32(at):return struct.unpack_from('<I',data,at)[0]
    todo=[u32(4)];seen=set();matches=[]
    try:
        while todo:
            at=todo.pop()
            if at==0 or at in seen:continue
            seen.add(at);assert len(seen)<=16
            count=u16(at);assert count<=512 and at+2+12*count+4<=len(data)
            tags={}
            for i in range(count):
                p=at+2+12*i;tag,typ,n=struct.unpack_from('<HHI',data,p)
                if typ in [3,4] and n==1:tags[tag]=u16(p+8) if typ==3 else u32(p+8)
            todo.extend([tags.get(330,0),u32(at+2+12*count)])
            if tags.get(262)==32803 and tags.get(259)==1 and tags.get(277,1)==1:
                w,h=tags[256],tags[257];off,length=tags[273],tags[279]
                assert tags.get(258) in [14,16] and w%2==0 and h%2==0
                assert w>=2 and h>=2 and w*h*2==length and off+length<=len(data)
                matches.append({'width':w,'height':h,'offset':off,'body_bytes':length})
        return matches[0] if len(matches)==1 else None
    except (AssertionError,KeyError,struct.error):return None

def encode_iter(data,mode='cfa',workers=4,rows=128):
    assert 0<len(data)<=MAX_RAW and workers in [1,2,4] and rows>=2 and rows%2==0
    info=layout(data) if mode=='cfa' else None
    meta={'version':1,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'layout':info}
    header=json.dumps(meta,separators=(',',':')).encode()
    yield MAGIC+struct.pack('<I',len(header))+header
    parts=[]
    if info:
        off=info['offset'];end=off+info['body_bytes'];width=info['width']
        if off:parts.append((0,off,0,0))
        stride=2*width*rows
        assert stride<=MAX_CHUNK
        parts.extend((i,min(stride,end-i),8,width) for i in range(off,end,stride))
        if end<len(data):parts.append((end,len(data)-end,0,0))
    else:parts=[(i,min(4*1024*1024,len(data)-i),0,0) for i in range(0,len(data),4*1024*1024)]
    assert all(0<n<=MAX_CHUNK for _,n,_,_ in parts)
    def encode(part):
        at,n,pred,width=part;raw=data[at:at+n]
        if mode=='identity':packed=raw;pred=255
        else:
            transformed=predict(raw,width,pred) if pred else raw
            packed=compress(transformed)
            if len(packed)>=len(raw):packed=raw;pred=255
        return struct.pack('<IIBI',n,len(packed),pred,width)+packed
    # Bound the work queue; do not submit an entire stack or materialize all chunks.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending=deque();next_part=iter(parts)
        for _ in range(workers):
            p=next(next_part,None)
            if p is not None:pending.append(pool.submit(encode,p))
        while pending:
            packet=pending.popleft().result()
            yield packet
            p=next(next_part,None)
            if p is not None:pending.append(pool.submit(encode,p))

def read_exact(stream,n):
    assert 0<=n<=MAX_CHUNK
    b=bytearray()
    while len(b)<n:
        part=stream.read(n-len(b))
        if not part:raise ValueError('Truncated transport')
        b.extend(part)
    return bytes(b)

def receive(stream,destination):
    assert read_exact(stream,8)==MAGIC
    hsize=struct.unpack('<I',read_exact(stream,4))[0];assert hsize<=2048
    meta=json.loads(read_exact(stream,hsize));size=meta['bytes']
    assert meta['version']==1 and isinstance(size,int) and 0<size<=MAX_RAW
    assert isinstance(meta['sha256'],str) and len(meta['sha256'])==64
    total=0;wire=12+hsize;digest=hashlib.sha256();chunks=0
    while total<size:
        n,packed_size,mode,width=struct.unpack('<IIBI',read_exact(stream,13))
        assert 0<n<=MAX_CHUNK and 0<packed_size<=MAX_CHUNK and total+n<=size
        assert mode in [0,8,255]
        packed=read_exact(stream,packed_size);wire+=13+packed_size
        if mode==255:assert packed_size==n;raw=packed
        else:
            raw=decompress(packed,n)
            if mode:
                assert 2<=width<=32768 and width%2==0 and n%(2*width)==0 and n//(2*width)>=2
                raw=predict(raw,width,mode,True)
        digest.update(raw);destination.write(raw);total+=len(raw);chunks+=1
    assert stream.read(1)==b'', 'Trailing transport bytes'
    assert total==size and digest.hexdigest()==meta['sha256'], 'Original-byte SHA-256 mismatch'
    return {'bytes':total,'wire_bytes':wire,'sha256':digest.hexdigest(),'chunks':chunks,'exact':True}

def controls():
    data=bytes(range(256))*127
    for mode in ['identity','zstd','cfa']:
        packet=b''.join(encode_iter(data,mode,workers=2));out=io.BytesIO()
        assert receive(io.BytesIO(packet),out)['exact'] and out.getvalue()==data
        for bad in [packet[:-3],packet+b'!',packet[:8]+struct.pack('<I',999999)+packet[12:],packet[:-5]+bytes([packet[-5]^1])+packet[-4:]]:
            try:receive(io.BytesIO(bad),io.BytesIO())
            except (AssertionError,ValueError,RuntimeError):pass
            else:raise AssertionError('Invalid transport accepted')
    print(json.dumps({'wire_roundtrips':3,'malformed_refusals':12}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('op',choices=['send','controls']);p.add_argument('--file');p.add_argument('--mode',default='cfa',choices=['identity','zstd','cfa']);p.add_argument('--workers',default=4,type=int);p.add_argument('--stats',action='store_true');args=p.parse_args()
    if args.op=='controls':controls()
    else:
        start=time.perf_counter();source=Path(args.file).read_bytes()
        for chunk in encode_iter(source,args.mode,args.workers):sys.stdout.buffer.write(chunk);sys.stdout.buffer.flush()
        if args.stats:
            import resource
            r=resource.getrusage(resource.RUSAGE_SELF)
            print(json.dumps({'sender_seconds':time.perf_counter()-start,'max_rss_KiB':r.ru_maxrss,
                              'user_cpu_s':r.ru_utime,'system_cpu_s':r.ru_stime,
                              'load':os.getloadavg(),'workers':args.workers}),file=sys.stderr)
