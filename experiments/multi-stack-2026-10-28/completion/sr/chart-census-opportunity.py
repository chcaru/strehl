"""Read completed focus census, select focus neighborhoods, evaluate exact-taper
phase opportunities on all four native output parities. No original samples/RAW.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import argparse,collections,hashlib,json,struct,time
import numpy as np
import tifffile
P=argparse.ArgumentParser();P.add_argument('census',type=Path);P.add_argument('--out',type=Path,required=True);P.add_argument('--seal',type=Path,required=True);A=P.parse_args()
ROOT=Path(__file__).resolve().parents[4];base=A.census.resolve();report=json.loads((base/'report.json').read_text())
assert report['schema']=='strehl.sr-focus-census.v1';assert not A.out.exists()
seal=json.loads(A.seal.read_text())
for relative,digest in seal['files'].items():
    path=(base/relative).resolve();assert path.is_relative_to(base);assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
render=ROOT/report['input_render'];alignment=json.loads((render/'alignment.json').read_text());cal=json.loads((render/'calibration.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(render/'alignment.json')==report['alignment_sha256']
# Exposure-aware opportunity only: native inversion is a dependent frozen
# brightness predictor for ranking, never a calibration or candidate truth.
noise=lambda p:{k:v for k,v in p.items() if k!='plane'}
assert all(noise(c['noise_planes'][1])==noise(c['noise_planes'][3]) for c in cal)
assert all('translation: (0.0, 0.0)' in c['optical_profile']['applied_record'] for c in cal)
render_report=json.loads((render/'render-report.json').read_text())
ranges=[p['global_range'] for p in report['rois'][0]['passes']]
assert len(ranges)==2 and all([p['global_range'] for p in r['passes']]==ranges for r in report['rois'])
gains={r['frame']:np.float32(r['photometric_gain']).item() for r in render_report['frames']}
assert len(gains)==ranges[-1][1] and all(np.isfinite(v) and v>0 for v in gains.values())
ref=cal[render_report['development_reference_pass']]
xyz=np.array([[.4124564,.3575761,.1804375],[.2126729,.7151522,.0721750],[.0193339,.1191920,.9503041]])
# camera_to_srgb inverse is the row-normalized camera_from_srgb matrix.
inv=np.array(ref['color_matrix'][0],dtype=np.float32).astype(float)@xyz
inv=inv/inv.sum(axis=1)[:,None]
wb=np.array(ref['white_balance']);sensor_range=ref['white']-ref['black']
def source_pass(i):
    return next(p for p,(lo,hi) in enumerate(ranges) if lo<=i<hi)
center=np.array(report['full_guide_geometry'],float)+.5;center=complex(*center)
maps={}
for line in alignment['warpmap'].splitlines():
    q=line.split()
    if len(q)>=6 and q[0].isdigit() and q[1]=='placed':
        f=[struct.unpack('>d',bytes.fromhex(v))[0] for v in q[2:6]];maps[int(q[0])]=(complex(f[0],f[1]),complex(f[2],f[3]))
freq=np.array([[0,0],[0,1],[1,0],[1,1]])
def measure(points,fields,sources,color,expected):
    count=len(points);gram=np.zeros((count,4,4),complex);total=np.zeros(count);acquisitions=np.zeros(count,int)
    for i in sources:
        pass_index=source_pass(i);flag,peak,width=fields[pass_index];delta=(i-ranges[pass_index][0]-peak)/width
        active=(flag==0)&np.isfinite(delta)&(np.abs(delta)<=1);idx=np.flatnonzero(active)
        if len(idx)==0:continue
        z=points[idx];fw=np.exp(-.5*delta[idx]**2);aa,b=maps[i]
        pn=cal[pass_index]['noise_planes'][[0,1,2][color]];gain=gains[i]
        variance=(pn['gain_dn_per_e']*np.maximum(expected[idx,color]/gain,0)+(pn['gain_dn_per_e']*pn['read_noise_e'])**2)*gain**2
        fw=fw/np.maximum(variance,1e-6)
        eps=[cal[pass_index]['optical_profile']['eps_r'],0,cal[pass_index]['optical_profile']['eps_b']][color]
        aa*=1+eps;b*=1+eps
        source=aa*(z-center)+2*b+center;floorx=np.floor(source.real).astype(int);floory=np.floor(source.imag).astype(int)
        radius=int(np.ceil(2*abs(aa)))+1;used=np.zeros(len(idx),bool)
        for dy in range(-radius,radius+1):
            for dx in range(-radius,radius+1):
                sx=floorx+dx;sy=floory+dy
                plane=np.where((sx%2==0)&(sy%2==0),0,np.where((sx%2==1)&(sy%2==1),2,1))
                d=(sx+1j*sy-center-2*b)/aa+center-z;squared=d.real*d.real+d.imag*d.imag
                valid=(plane==color)&(squared<=4)&(sx>=0)&(sy>=0)&(sx<report['full_guide_geometry'][0]*2)&(sy<report['full_guide_geometry'][1]*2)
                if not np.any(valid):continue
                selected=idx[valid];dd=np.column_stack([d.real[valid],d.imag[valid]])
                w=fw[valid]*np.exp(-.5*squared[valid]/(.35**2));v=np.exp(1j*np.pi*(dd@freq.T))
                gram[selected]+=np.einsum('n,ni,nj->nij',w,v.conj(),v);total[selected]+=w;used|=valid
        acquisitions[idx]+=used
    eig=np.linalg.eigvalsh(gram/np.maximum(total[:,None,None],1e-300));cond=np.full(count,np.inf)
    okay=(eig[:,0]>1e-6)&(acquisitions>=(2 if color==1 else 4))
    cond[okay]=np.sqrt(eig[okay,-1]/eig[okay,0]);return cond,acquisitions
start=time.perf_counter();results=[]
for roi in report['rois']:
    index=roi['index'];folder=base/f'roi-{index}';ox,oy,n,_=roi['roi_sensor'];fx,fy,w,h=roi['focus_domain_quad']
    eligible=np.fromfile(folder/'native-linear-eligible.u8',np.uint8).reshape(n,n)>0
    native=tifffile.imread(folder/'native.tiff');assert native.shape==(n,n,3)
    predicted=(native@inv.T)*sensor_range/wb
    assert np.all(np.isfinite(predicted[eligible]))
    yy,xx=np.mgrid[:n,:n];qy=np.floor((oy+yy-.5)/2-fy+.5).astype(int);qx=np.floor((ox+xx-.5)/2-fx+.5).astype(int)
    fullfields=[]
    for pass_index in range(2):
        fullfields.append(tuple(np.fromfile(folder/f'focus-pass-{pass_index}-{name}.{ext}',dtype).reshape(h,w)[qy,qx]
            for name,ext,dtype in [('flags','u8',np.uint8),('ordinal','f32',np.float32),('width','f32',np.float32)]))
    both=eligible&(fullfields[0][0]==0)&(fullfields[1][0]==0)
    pairs=collections.Counter(zip(np.rint(fullfields[0][1][both]).astype(int),np.rint(fullfields[1][1][both]).astype(int)))
    choices=[]
    for (a,b),occurrences in pairs.most_common():
        if 4<=a<=ranges[0][1]-ranges[0][0]-5 and 4<=b<=ranges[1][1]-ranges[1][0]-5 and all(abs(a-x)+abs(b-y)>=3 for x,y,_ in choices):choices.append((int(a),int(b),occurrences))
        if len(choices)==4:break
    # Same bounded 2304 locations at192 square, now equally covering all four
    # anchor output parities instead of only even/even.
    mask=eligible&(xx%8<2)&(yy%8<2);px=xx[mask];py=yy[mask];points=ox+px+1j*(oy+py)
    fields=[tuple(v[mask] for v in f) for f in fullfields];summaries=[]
    for c0,c1,occurrences in choices:
        sources=list(range(ranges[0][0]+c0-3,ranges[0][0]+c0+4))+list(range(ranges[1][0]+c1-3,ranges[1][0]+c1+4))
        assert all(i in maps for i in sources)
        measured=[measure(points,fields,sources,c,predicted[mask]) for c in range(3)];conditions=np.column_stack([v[0] for v in measured]);counts=np.column_stack([v[1] for v in measured]);passed=np.all(conditions<=20,axis=1)
        best=np.argsort(np.max(conditions,axis=1))[:12]
        summaries.append({'mode_centers_ordinal':[c0,c1],'native_pixels_with_this_pair':occurrences,'sources':sources,'independent_guide_candidates':[ranges[0][0]+c0-4,ranges[0][0]+c0+4,ranges[1][0]+c1-4,ranges[1][0]+c1+4],
            'tested_points':len(points),'passed_rgb':np.sum(conditions<=20,axis=0).tolist(),'passed_all_rgb':int(passed.sum()),
            'parity_counts':[{'parity':[x,y],'tested':int(((px%2==x)&(py%2==y)).sum()),'passed_all_rgb':int((passed&(px%2==x)&(py%2==y)).sum())} for y in range(2) for x in range(2)],
            'best_all_rgb':[{'local_sensor':[int(px[k]),int(py[k])],'conditions':conditions[k].tolist(),'acquisitions':counts[k].tolist()} for k in best if passed[k]]})
    results.append({'index':index,'roi_sensor':roi['roi_sensor'],'eligible_native_pixels':int(eligible.sum()),'nonlinear_native_pixels':int((~eligible).sum()),'dependent_native_camera_dn_percentiles_rgb':np.percentile(predicted[eligible],[5,50,95],axis=0).tolist() if eligible.any() else [],'dependent_native_camera_dn_mean_rgb':predicted[eligible].mean(axis=0).tolist() if eligible.any() else [],'usable_pixels_per_pass':[int(np.sum(eligible&(f[0]==0))) for f in fullfields],'both_passes_usable_pixels':int(both.sum()),
        'top_focus_mode_pairs':[[int(a),int(b),int(count)] for (a,b),count in pairs.most_common(12)],'summaries':summaries})
result={'schema':'strehl.sr-exposure-aware-opportunity.v1','command':__import__('sys').argv,'workers':1,'elapsed_seconds':time.perf_counter()-start,
    'scope':'DERIVED opportunity from measured complete-track focus and saved placements. Exact positive isotropic Gaussian.35sensor taper and hard one-width mode membership. Recorded source gains and calibrated variance weight the design. Expected signal is a dependent native-master linear inverse used only for ranking; actual core uses withheld original guide photons. Float64 analytic opportunity is not a bitwise core replay. All four output CFA parities sampled. No source-clipping, motion, local geometry certificate, anisotropic guide or measured photographic quality.',
    'inputs':{'seal':sha(A.seal),'script':sha(Path(__file__)),'render_report':sha(render/'render-report.json'),'census':sha(base/'report.json'),'alignment':sha(render/'alignment.json'),'calibration':sha(render/'calibration.json')},'pass_ranges':ranges,'source_gains':gains,'rois':results}
A.out.parent.mkdir(parents=True,exist_ok=True)
with A.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'output':str(A.out),'seconds':result['elapsed_seconds'],'rois':[{'index':r['index'],'both_usable':r['both_passes_usable_pixels'],'cases':[{'centers':v['mode_centers_ordinal'],'all_rgb':v['passed_all_rgb'],'tested':v['tested_points']} for v in r['summaries']]} for r in results]},indent=2))
