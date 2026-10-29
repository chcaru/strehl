"""Geometry/focus census for existing ROI; no RAW decode or image samples."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import json,hashlib,struct,time
import numpy as np
ROOT=Path(__file__).resolve().parents[4];p=ROOT/'outputs/multi-stack/completion/sr-roi-03'
r=json.loads((p/'report.json').read_text());a=json.loads((ROOT/'outputs/multi-stack/insect-repeat-7/alignment.json').read_text());cal=json.loads((ROOT/'outputs/multi-stack/insect-repeat-7/calibration.json').read_text())
x,y,w,h=r['focus_domain_quad'];ox,oy,n,_=r['roi_sensor'];full=np.array(r['full_guide_geometry'],float);center=full+.5
maps={}
for line in a['warpmap'].splitlines():
    q=line.split()
    if len(q)>=6 and q[0].isdigit() and q[1]=='placed':
        f=[struct.unpack('>d',bytes.fromhex(v))[0] for v in q[2:6]];maps[int(q[0])]=(complex(f[0],f[1]),complex(f[2],f[3]))
fields=[]
for k in range(2):
    fields.append((np.fromfile(p/f'focus-pass-{k}-flags.u8',np.uint8).reshape(h,w),np.fromfile(p/f'focus-pass-{k}-ordinal.f32',np.float32).reshape(h,w),np.fromfile(p/f'focus-pass-{k}-width.f32',np.float32).reshape(h,w)))
eligible=np.fromfile(p/'native-linear-eligible.u8',np.uint8).reshape(n,n)>0
freq=np.array([[0,0],[0,1],[1,0],[1,1]])
def condition(point,sources,color):
    gram=np.zeros((4,4),complex);weight=0;count=0;qx=int(np.floor((point[0]-.5)/2-x+.5));qy=int(np.floor((point[1]-.5)/2-y+.5));z=complex(*(point-center))
    eps=[cal[0]['optical_profile']['eps_r'],0,cal[0]['optical_profile']['eps_b']][color]
    for i in sources:
        f,peak,width=fields[i//299];ordinal=i%299
        if f[qy,qx]!=0 or not np.isfinite(width[qy,qx]) or width[qy,qx]<=0:continue
        delta=(ordinal-peak[qy,qx])/width[qy,qx]
        if abs(delta)>1:continue
        focus=np.exp(-.5*delta*delta);aa,b=maps[i];aa*=1+eps;b*=1+eps
        source=aa*z+2*b+complex(*center);rad=2*abs(aa);used=False
        for sy in range(int(np.ceil(source.imag-rad)),int(np.floor(source.imag+rad))+1):
            for sx in range(int(np.ceil(source.real-rad)),int(np.floor(source.real+rad))+1):
                plane=0 if sx%2==sy%2==0 else 2 if sx%2==sy%2==1 else 1
                if plane!=color:continue
                original=(complex(sx,sy)-complex(*center)-2*b)/aa+complex(*center);d=np.array([original.real-point[0],original.imag-point[1]])
                if d@d>4:continue
                ww=focus*np.exp(-.5*(d@d)/(.35*.35));v=np.exp(1j*np.pi*(freq@d));gram+=ww*np.outer(v.conj(),v);weight+=ww;used=True
        count+=used
    if count<(2 if color==1 else 4) or weight==0:return None,count
    e=np.linalg.eigvalsh(gram/weight);return (float(np.sqrt(e[-1]/e[0])) if e[0]>1e-6 else None),count
started=time.perf_counter();summaries=[];examples=[]
for c0,c1 in [(74,66),(75,68),(76,69),(77,69)]:
    sources=list(range(c0-3,c0+4))+list(range(299+c1-3,299+c1+4));counts=[0,0,0];all_rgb=0;best=[];tested=0
    for yy in range(0,n,4):
        for xx in range(0,n,4):
            if not eligible[yy,xx]:continue
            point=np.array([ox+xx,oy+yy],float);q=[condition(point,sources,c) for c in range(3)];tested+=1
            okay=[v is not None and v<=20 for v,_ in q];counts=[v+int(ok) for v,ok in zip(counts,okay)]
            if all(okay):all_rgb+=1;best.append((max(v for v,_ in q),xx,yy,[v for v,_ in q],[count for _,count in q]))
    summaries.append({'centers_ordinal':[c0,c1],'sources':sources,'tested_every_four_sensor_pixels':tested,'passed_rgb':counts,'passed_all_rgb':all_rgb,'best_all_rgb':sorted(best)[:12]})
result={'schema':'strehl.sr-roi-source-opportunity.v1','workers':1,'elapsed_seconds':time.perf_counter()-started,'scope':'DERIVED from saved geometry+measured full-track focus; actual Gaussian .35 sensor kernel, one-width focus membership; excludes nonlinear native sites. Isotropic kernel, no motion witness, no independently measured local registration; not measured output quality. Calibrated variance is common to sources here and cancels from the phase Gram.','inputs':{'roi_report':hashlib.sha256((p/'report.json').read_bytes()).hexdigest(),'alignment':hashlib.sha256((ROOT/'outputs/multi-stack/insect-repeat-7/alignment.json').read_bytes()).hexdigest()},'summaries':summaries}
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
