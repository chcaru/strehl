"""Bounded RGB16 strip reads; adapted from owned independent-derivative-tiff.py.
No TIFF/numerical package imports, full-frame buffers or image work on import.
"""
import hashlib,math,os,stat,struct
from contextlib import contextmanager
from pathlib import Path

DESCRIPTION=('Linear camera-native RGB (sensor primaries), NO colour matrix, no transfer curve. '
 'THIS IS NOT sRGB -- do not treat it as such. This is the measurement output. '
 'White balance: as-shot per-channel gains, green = 1, applied AFTER black subtraction '
 'and normalisation by (white - black), and AFTER the noise model, which is calibrated '
 'in raw DN before any gain.')
SOFTWARE='strehl 0.0.0';MAX_FILE=216*1024*1024;ROOT=Path(__file__).resolve().parents[2]

def need(ok,msg):
    if not ok:raise ValueError(msg)
def identity(st):
    return [int(getattr(st,k,0)) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_file_attributes','st_nlink')]
def ordinary(st):
    need(stat.S_ISREG(st.st_mode) and not getattr(st,'st_file_attributes',0)&1024 and st.st_nlink==1,'owned regular non-reparse single-link image')
def exact(stream,at,size,extent):
    need(type(at) is type(size) is int and 0<=at<=extent-size and 0<=size<=1024*1024,'bounded exact file range')
    stream.seek(at);raw=stream.read(size);need(len(raw)==size,'complete exact read');return raw
def layout(stream,extent,expected):
    need(8<=extent<=MAX_FILE,'finite TIFF extent');head=exact(stream,0,8,extent)
    need(head[:2] in (b'II',b'MM'),'TIFF byte order');endian='<' if head[:2]==b'II' else '>'
    def unpack(fmt,at):return struct.unpack(endian+fmt,exact(stream,at,struct.calcsize(endian+fmt),extent))
    need(unpack('H',2)[0]==42,'classic TIFF');ifd=unpack('I',4)[0];need(ifd>=8,'IFD header separation')
    n=unpack('H',ifd)[0];need(1<=n<=64,'bounded IFD');end=ifd+2+12*n+4;need(unpack('I',end-4)[0]==0,'one IFD only')
    occupied=[(0,8),(ifd,end)];tags={};allowed={256,257,258,259,262,270,273,274,277,278,279,282,283,284,296,305,317,339}
    for i in range(n):
        at=ifd+2+12*i;tag,typ,count=unpack('HHI',at)
        need(tag in allowed and tag not in tags and typ in (2,3,4,5) and 1<=count<=4096,'closed unique TIFF tags')
        need((typ==2)==(tag in (270,305)) and (typ==5)==(tag in (282,283)),'ASCII/rational tag typing')
        if tag in (258,259,262,274,277,284,296,317,339):need(typ==3,'SHORT tag type')
        size={2:1,3:2,4:4,5:8}[typ]*count;offset=at+8 if size<=4 else unpack('I',at+8)[0]
        if size>4:occupied.append((offset,offset+size))
        raw=exact(stream,offset,size,extent)
        if typ==2:
            need(raw.endswith(b'\0') and b'\0' not in raw[:-1],'ASCII termination');value=raw[:-1].decode('ascii')
        elif typ==5:
            need(count==1,'resolution count');value=struct.unpack(endian+'II',raw)
        else:value=struct.unpack(endian+('H' if typ==3 else 'I')*count,raw)
        tags[tag]=value
    def values(tag,default=None):
        value=tags.get(tag,default);need(type(value) is tuple,'integer tag values');return value
    def scalar(tag,default=None):
        value=values(tag,None if default is None else (default,));need(len(value)==1,'scalar tag');return value[0]
    width,height=scalar(256),scalar(257);need((height,width,3)==tuple(expected) and 1<=height<=8192 and 1<=width<=8192 and width*height<=36000000,'expected bounded RGB dimensions')
    need(scalar(277,1)==3 and values(258)==(16,16,16) and values(339,(1,1,1))==(1,1,1),'unsigned RGB16')
    need(scalar(259)==1 and scalar(262)==2,'uncompressed RGB')
    need(all(scalar(t,1)==1 for t in (274,284,317,296)),'orientation/planar/predictor/resolution unit')
    need(all(tags.get(t,(1,1))==(1,1) for t in (282,283)),'measurement resolution')
    need(tags.get(270)==DESCRIPTION and tags.get(305)==SOFTWARE,'native CameraLinear convention')
    rows=scalar(278);need(rows>0,'positive rows per strip');offsets,counts=values(273),values(279)
    need(len(offsets)==len(counts)==math.ceil(height/rows),'complete strip counts')
    for i,(offset,count) in enumerate(zip(offsets,counts)):
        need(count==min(rows,height-i*rows)*width*6 and 8<=offset<=extent-count,'exact strip extent');occupied.append((offset,offset+count))
    occupied.sort();need(all(a[1]<=b[0] for a,b in zip(occupied,occupied[1:])) and occupied[-1][1]==extent,'nonoverlapping referenced ranges/exact final extent')
    return dict(shape=list(expected),endian=endian,rows_per_strip=rows,strip_offsets=list(offsets),strip_bytes=list(counts))
def patch(stream,info,extent,rect):
    y,x,height,width=rect;h,w,_=info['shape']
    need(all(type(v) is int for v in rect) and 1<=height<=129 and 1<=width<=129 and 0<=y<=h-height and 0<=x<=w-width,'bounded in-image native rectangle')
    result=bytearray()
    for row in range(y,y+height):
        i,within=divmod(row,info['rows_per_strip']);at=info['strip_offsets'][i]+(within*w+x)*6
        result.extend(exact(stream,at,width*6,extent))
    need(len(result)==height*width*6,'patch rows complete');return bytes(result)
def hash_stream(stream,check,extent):
    stream.seek(0);h=hashlib.sha256();n=0
    while raw:=stream.read(min(1024*1024,extent-n+1)):
        n+=len(raw);need(n<=extent,'declared stream extent');check();h.update(raw)
    return dict(bytes=n,sha256=h.hexdigest())
@contextmanager
def opened(path,ref,expected,check,receipt):
    path=Path(path).resolve();need(path==(ROOT/ref['path']).resolve(),'exact native FileRef path');before=path.lstat();ordinary(before)
    with path.open('rb') as stream:
        first=os.fstat(stream.fileno());ordinary(first);need(identity(first)==identity(before),'same opened native file')
        need(type(ref['bytes']) is int and first.st_size==ref['bytes'] and 8<=ref['bytes']<=MAX_FILE,'declared bounded image extent before hashing')
        need(hash_stream(stream,check,first.st_size)=={k:ref[k] for k in ('bytes','sha256')},'native full-file initial hash')
        info=layout(stream,first.st_size,expected);receipt.update(initial_identity=identity(first),layout=info,initial_hash_verified=True,final_hash_verified=False)
        try:yield stream,info,first.st_size
        finally:
            need(hash_stream(stream,check,first.st_size)=={k:ref[k] for k in ('bytes','sha256')},'native full-file final hash')
            after=os.fstat(stream.fileno());named=path.lstat();ordinary(after);ordinary(named)
            need(identity(first)==identity(after)==identity(named),'native file identity unchanged');receipt['final_hash_verified']=True

def fixture_bytes(endian):
    # Independent literal RGB ramp, intentionally crossing many short strips.
    need(endian in ('<','>'),'private endian');w,h,rows=137,139,17
    pack=lambda fmt,*v:struct.pack(endian+fmt,*v)
    entries=[(256,4,(w,)),(257,4,(h,)),(258,3,(16,16,16)),(259,3,(1,)),(262,3,(2,)),(270,2,DESCRIPTION+'\0'),(273,4,tuple(0 for _ in range(math.ceil(h/rows)))),(277,3,(3,)),(278,4,(rows,)),(279,4,tuple(min(rows,h-i*rows)*w*6 for i in range(math.ceil(h/rows)))),(305,2,SOFTWARE+'\0')]
    count=len(entries);base=8+2+12*count+4;payload=bytearray();table=[];offset_patch=None
    for tag,typ,val in entries:
        data=val.encode('ascii') if typ==2 else pack(('H' if typ==3 else 'I')*len(val),*val);num=len(val)
        if len(data)<=4:field=data.ljust(4,b'\0')
        else:
            offset=base+len(payload);field=pack('I',offset)
            if tag==273:offset_patch=len(payload)
            payload.extend(data)
        table.append(pack('HHI',tag,typ,num)+field)
    image_start=base+len(payload);counts=next(v for t,_,v in entries if t==279);offsets=[];position=image_start
    for size in counts:offsets.append(position);position+=size
    encoded=pack('I'*len(offsets),*offsets);payload[offset_patch:offset_patch+len(encoded)]=encoded
    header=(b'II' if endian=='<' else b'MM')+pack('HI',42,8)+pack('H',count)+b''.join(table)+pack('I',0)+payload
    pixels=b''.join(pack('HHH',100+y*3+x,200+y+x*2,300+y*2+x*3) for y in range(h) for x in range(w))
    return bytes(header)+pixels
