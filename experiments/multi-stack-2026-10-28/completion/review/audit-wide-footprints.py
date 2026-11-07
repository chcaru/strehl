from pathlib import Path
import re, struct, math, json, hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[4]
SR=ROOT/'experiments/multi-stack-2026-10-28/completion/sr'
OUT=Path(__file__).with_suffix('.json')
S=192; T=46; R=3; H=4
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
spots=[(x,y) for y in (10,73,136) for x in (10,73,136)]
def dilate(m):
    p=np.pad(m,H); out=np.zeros_like(m)
    for y in range(2*H+1):
        for x in range(2*H+1):out |= p[y:y+S,x:x+S]
    return out
def footprint(a,b,spot,mask=False):
    x,y=spot; m=np.zeros((S,S),bool)
    if mask:
        corners=[a*complex(u-96,v-96)+b+complex(96,96) for u in (x-R-1,x+T+R+1) for v in (y-R-1,y+T+R+1)]
        x0=math.floor(min(z.real for z in corners)); x1=math.ceil(max(z.real for z in corners))
        y0=math.floor(min(z.imag for z in corners)); y1=math.ceil(max(z.imag for z in corners))
        if min(x0,y0)<0 or max(x1,y1)>=S:return None
        m[y0:y1+1,x0:x1+1]=True
    else:
        q=a*complex(x+T/2-96,y+T/2-96)+b+complex(96,96)
        cx=x+T/2+f32(q.real-x-T/2); cy=y+T/2+f32(q.imag-y-T/2)
        v=np.arange(T+2*R,dtype=np.float64)-R-T/2
        sx=cx+a.real*v[None,:]-a.imag*v[:,None]
        sy=cy+a.imag*v[None,:]+a.real*v[:,None]
        ix=np.floor(sx).astype(int); iy=np.floor(sy).astype(int)
        if min(ix.min(),iy.min())<0 or max(ix.max(),iy.max())+1>=S:return None
        for dy in (0,1):
            for dx in (0,1):m[iy+dy,ix+dx]=True
    return dilate(m)
def census(a,b,mask=False):
    roles=[np.zeros((S,S),bool),np.zeros((S,S),bool)]
    oob=0
    for i,spot in enumerate(spots):
        f=footprint(a,b,spot,mask)
        if f is None:oob+=1
        else:roles[(i%3+i//3)%2] |= f
    yy,xx=np.nonzero(roles[0]&roles[1])
    return {'overlap_plane_sites':int(len(xx)),'first_overlap_xy':None if len(xx)==0 else [int(xx[0]),int(yy[0])],'train_union_sites':int(roles[0].sum()),'held_union_sites':int(roles[1].sum()),'out_of_bounds_tiles':oob}
def trajectory(path):
    words=re.findall(r'0x([0-9a-f]+)',path.read_text())
    vals=[struct.unpack('>d',bytes.fromhex(w.zfill(16)))[0] for w in words]
    return [(complex(*vals[i:i+2]),complex(*vals[i+2:i+4])) for i in range(0,len(vals),4)]
def plane(t,off):
    a,b=t; site=complex(off*.5-.25,off*.5-.25)
    return a,b+a*site-site
def origin(t,off):
    a,b=t; target=(256.5-off)*.5
    p=a*complex(target-128,target-128)+b+complex(128,128)
    return complex(math.floor(p.real-96),math.floor(p.imag-96))
def crop_pair(t0,t1,off):
    t0=plane(t0,off);t1=plane(t1,off)
    o0=origin(t0,off);o1=origin(t1,off)
    a=t1[0]/t0[0];b=t1[1]-a*t0[1]
    return a,a*(o0+complex(-32,-32))+b-(o1+complex(-32,-32))
result={'schema':'strehl.review.registration-initial-footprints.v1','scope':'Independent geometric enumeration only: initial measured seed, no RAW/NCC/refinement execution. The numerical sets include all bilinear reads (including zero-coefficient taps) and finite Gaussian support; mask sets additionally include supported() rectangle. Later runtime train iterations and final held transform are unobserved.','command':'python -X utf8 experiments/multi-stack-2026-10-28/completion/review/audit-wide-footprints.py','counterexample':{},'initial_seeds':[],'sources':{}}
for scale in (1.,.85,.75):
    result['counterexample'][str(scale)]={'numeric':census(complex(scale,0),0j),'mask_dependencies':census(complex(scale,0),0j,True)}
for name in ('measured-trajectory-01.rs','chart-measured-trajectory-01.rs'):
    p=SR/name; ts=trajectory(p);result['sources'][name]=hashlib.sha256(p.read_bytes()).hexdigest()
    for i,j in ((3,4),(9,10),(3,10)):
        for color,off in (('R',0),('G',.5),('B',1)):
            a,b=crop_pair(ts[i],ts[j],off)
            result['initial_seeds'].append({'trajectory':name,'pair_indices':[i,j],'color':color,'relative_scale':abs(a),'relative_rotation_radians':math.atan2(a.imag,a.real),'crop_transform':[a.real,a.imag,b.real,b.imag],'numeric':census(a,b),'mask_dependencies':census(a,b,True)})
result['sources'][Path(__file__).name]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({'counterexample':result['counterexample'],'initial_cases':len(result['initial_seeds']),'initial_numeric_overlap_cases':sum(x['numeric']['overlap_plane_sites']>0 for x in result['initial_seeds']),'initial_mask_overlap_cases':sum(x['mask_dependencies']['overlap_plane_sites']>0 for x in result['initial_seeds']),'relative_scale_range':[min(x['relative_scale'] for x in result['initial_seeds']),max(x['relative_scale'] for x in result['initial_seeds'])],'report':str(OUT)},indent=2))
