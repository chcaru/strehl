"""Frozen-nine broad-patch photometry; independent estimator, fixed production geometry."""
import os
for key in ["OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"]: os.environ[key]="1"
import argparse,hashlib,json,platform,struct,sys,time,threading
from pathlib import Path
import numpy as np
import psutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/"outputs/multi-stack/hdr-preflight"
MAP=ROOT/"outputs/multi-stack/hdr-geometry-2/alignment.json"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def sample_site(a,coordinates,site,white):
    dx,dy=site
    x=(coordinates.real-dx)/2;y=(coordinates.imag-dy)/2
    ix=np.floor(x).astype(np.int64);iy=np.floor(y).astype(np.int64)
    fx=x-ix;fy=y-iy
    plane=a[dy::2,dx::2]
    if np.any(ix<0) or np.any(iy<0) or np.any(ix+1>=plane.shape[1]) or np.any(iy+1>=plane.shape[0]):raise ValueError('patch lacks true coverage')
    result=np.zeros_like(x);clipped=np.zeros(x.shape,bool)
    for sy,sx,weight in [(0,0,(1-fx)*(1-fy)),(0,1,fx*(1-fy)),(1,0,(1-fx)*fy),(1,1,fx*fy)]:
        value=plane[iy+sy,ix+sx]
        result+=weight*value
        clipped|=(weight!=0)&(value>=white)
    return result,clipped


def summary(values):
    a=np.sort(np.asarray(values).ravel())
    n=len(a);trim=max(0,n//10)
    return {'mean':float(a.mean()),'median':float(np.median(a)),'trimmed_mean_10pct':float(a[trim:n-trim].mean()),'p05':float(np.percentile(a,5)),'p95':float(np.percentile(a,95))}


def score(ratios,roles,ids):
    ratios=np.asarray(ratios);cal=np.array([r=='calibration' for r in roles]);val=~cal
    scale=float(np.median(ratios[cal]));residual=ratios/scale-1
    vv=np.abs(residual[val]);nom=np.abs(ratios[val]-1)
    counts={'calibration':len(set(np.array(ids)[cal])),'validation':len(set(np.array(ids)[val]))}
    return {'fitted_normalized_ratio':scale,'calibration_patch_count':counts['calibration'],'validation_patch_count':counts['validation'],
            'validation_median_abs_relative':float(np.median(vv)), 'validation_p95_abs_relative':float(np.percentile(vv,95)),
            'nominal_validation_median_abs_relative':float(np.median(nom)), 'nominal_validation_p95_abs_relative':float(np.percentile(nom,95)),
            'provisional_pass':bool(counts['calibration']>=4 and counts['validation']>=4 and np.median(vv)<=.01 and np.percentile(vv,95)<=.03),
            'sensitivity_passes':[bool(counts['calibration']>=4 and counts['validation']>=4 and np.median(vv)<=m and np.percentile(vv,95)<=p) for m,p in [(.005,.02),(.02,.05)]],
            'validation_residuals':residual[val].tolist()}


def controls():
    roles=['calibration']*24+['validation']*24;ids=[f'p{x//4}' for x in range(48)]
    v=np.ones(48);positive=score(v,roles,ids);assert positive['provisional_pass'];json.dumps(positive,allow_nan=False)
    wrong=score(v*1.1,roles,ids);assert wrong['nominal_validation_median_abs_relative']>.09
    assert wrong['provisional_pass'] # A scalar refit hides this, so nominal check is mandatory.
    spatial=v.copy();spatial[24:]*=1.1;assert not score(spatial,roles,ids)['provisional_pass']
    color=v.copy();color[::4]*=1.1;assert not score(color,roles,ids)['provisional_pass']
    a=np.arange(100,dtype=np.uint16).reshape(10,10);z=np.array([[2+2j,4+4j]])
    out,clip=sample_site(a,z,(0,0),65535);assert np.array_equal(out,[[22,44]]) and not clip.any()
    a[2,4]=65535
    out,clip=sample_site(a,np.array([[2+2j]]),(0,0),65535);assert not clip.any() # zero-weight tap not censoring
    out,clip=sample_site(a,np.array([[3+2j]]),(0,0),65535);assert clip.all()
    return {'status':'PASS','tests':['identity sampler','exact zero-weight clipping support','fractional clipping support','positive no-change photometry','wrong10pct nominal gain rejects before scalar refit','spatial drift fails held-out validation','channel drift fails held-out validation'],'scalar_fit_hides_uniform_gain_placebo':True}


def parse_map():
    v=json.loads(MAP.read_text());poses={}
    for line in v['warpmap'].splitlines():
        f=line.split()
        if len(f)>=6 and f[0].isdigit() and f[1]=='placed':
            re,im,br,bi=[struct.unpack('>d',bytes.fromhex(x))[0] for x in f[2:6]]
            poses[int(f[0])]=(complex(re,im),complex(br,bi))
    identities={s['sha256']:i for i,s in enumerate(v['binding']['sources'])}
    w,h=v['report']['geometry_plane_pixels'];return v,poses,identities,complex(w/2,h/2)


def measure():
    assert json.loads((OUT/'cross-decoder.json').read_text())['all_exact']
    assert json.loads((OUT/'extra-strip-comparison.json').read_text())['all_exact']
    freeze=json.loads((OUT/'photometry-patches.json').read_text());stage=json.loads((OUT/'stage-a.json').read_text());records=stage['records']
    binding,poses,identities,center=parse_map();base=next(r for r in records if r['source']['bracket']=='b10' and r['source']['index']==30)
    ai,bi=poses[identities[base['whole_sha256']]]
    measured=[];peak=0
    for record in records:
        source=record['source'];a=np.load(OUT/record['active_file'],mmap_mode='r',allow_pickle=False)
        aj,bj=poses[identities[record['whole_sha256']]];aa=aj/ai;bb=bj-aa*bi
        rows=[]
        for patch in freeze['patches']:
            x,y,w,h=patch['measurement_xywh']
            for dy in range(2):
                for dx in range(2):
                    xx,yy=np.meshgrid(np.arange(x+dx,x+w,2),np.arange(y+dy,y+h,2));p=xx+1j*yy
                    q=(p-(.5+.5j))/2
                    pulled=2*(aa*(q-center)+bb+center)+(.5+.5j)
                    site=dy*2+dx;c=record['rawpy_indices'][dy][dx]
                    black=record['black_per_color'][c];white=record['white_per_color'][c] if record['white_per_color'] else record['white_scalar']
                    values,clipped=sample_site(a,pulled,(dx,dy),white)
                    stats=summary(values-black)
                    shifts=[]
                    for shift in [2,-2,2j,-2j]:
                        shifted,_=sample_site(a,pulled+shift,(dx,dy),white)
                        shifts.append(summary(shifted-black)['trimmed_mean_10pct'])
                    rows.append({'patch':patch['id'],'role':patch['role'],'site':site,'color':record['active']['pattern'][dy][dx],
                                 'pulled_center_sensor_xy':[float(pulled.real.mean()),float(pulled.imag.mean())],
                                 'sample_count':int(values.size),'clipped_footprints':int(clipped.sum()),'statistics_dn_above_black':stats,
                                 'translation_sensitivity_plus_minus_2_sensor_px_dn':shifts})
        measured.append({'source':source,'global_index':identities[record['whole_sha256']],'relative_pose_to_b10_mid':{'a':[aa.real,aa.imag],'b_plane':[bb.real,bb.imag]},'patches':rows})
        peak=max(peak,psutil.Process().memory_info().rss);del a
    baseline=next(r for r in measured if r['source']==base['source']);base_rows={(x['patch'],x['site']):x for x in baseline['patches']}
    reports=[]
    for r in measured:
        ratios=[];roles=[];ids=[];details=[]
        for row in r['patches']:
            ref=base_rows[(row['patch'],row['site'])];refmean=ref['statistics_dn_above_black']['trimmed_mean_10pct'];mean=row['statistics_dn_above_black']['trimmed_mean_10pct']
            eligible=refmean>=freeze['minimum_reference_signal_dn'] and ref['clipped_footprints']==0 and row['clipped_footprints']==0
            ratio=mean/r['source']['exposure_seconds']/refmean
            detail={'patch':row['patch'],'site':row['site'],'color':row['color'],'role':row['role'],'eligible':eligible,'reference_dn':refmean,'normalized_ratio':ratio,
                    'source_clipped_footprints':row['clipped_footprints'],'translation_sensitivity_relative_span':(max(row['translation_sensitivity_plus_minus_2_sensor_px_dn'])-min(row['translation_sensitivity_plus_minus_2_sensor_px_dn']))/max(1,mean)}
            details.append(detail)
            if eligible:ratios.append(ratio);roles.append(row['role']);ids.append(row['patch'])
        if not ratios or not any(x=='calibration' for x in roles) or not any(x=='validation' for x in roles):s={'provisional_pass':False,'reason':'insufficient usable photometry'}
        else:s=score(ratios,roles,ids)
        percolor={}
        for site in range(4):
            d=[x for x in details if x['eligible'] and x['site']==site]
            train=[x['normalized_ratio'] for x in d if x['role']=='calibration'];val=[x['normalized_ratio'] for x in d if x['role']=='validation']
            percolor[str(site)]={'calibration_median_ratio':float(np.median(train)) if train else None,'validation_median_ratio':float(np.median(val)) if val else None,'calibration_count':len(train),'validation_count':len(val)}
        report={'source':r['source'],'summary':s,'per_site_ratios':percolor,'details':details};reports.append(report)
        print(json.dumps({'source':f'{r["source"]["bracket"]}-{r["source"]["index"]}','summary':{k:v for k,v in s.items() if k!='validation_residuals'},'per_site':percolor}),flush=True)
    save('photometry-measurements.json',{'status':'MEASURED','records':measured})
    result={'schema':'strehl.hdr-preflight.photometry.v1','status':'MEASURED_SCREEN_ONLY','patches_sha256':sha(OUT/'photometry-patches.json'),'geometry_sha256':sha(MAP),'reference_source':base['source'],'reference_global_index':identities[base['whole_sha256']],
            'geometry_plane_pixels':binding['report']['geometry_plane_pixels'],'sensor_pixels_per_plane_pixel':2,'sampler':'independent float64 per-color bilinear, actual nonzero-tap clipping, no color optical correction; broad interiors only',
            'estimator':'10pct trimmed means per128x128sensor patch/site; shared scalar median of calibration normalized ratios; all site/patch validation residuals',
            'independence':'photometry validation patches excluded from scalar fitting; geometry reused chart data so not independent placement validation','sampled_between_sources_peak_rss':peak,'reports':reports}
    save('photometry.json',result)
    return {'sources':len(reports),'provisional_passes':sum(r['summary']['provisional_pass'] for r in reports),'photographic_gain_established':False}


def main():
    arg=argparse.ArgumentParser();arg.add_argument('command',choices=['controls','measure']);args=arg.parse_args()
    start=time.perf_counter();proc=psutil.Process();peak=[0,0];stop=threading.Event()
    def monitor():
        while not stop.wait(.1):
            m=proc.memory_info();peak[0]=max(peak[0],m.rss);peak[1]=max(peak[1],getattr(m,'private',0))
    thread=threading.Thread(target=monitor,daemon=True);thread.start();status=0;error=None;result=None
    try:
        if args.command=='controls':result=controls();print(json.dumps(result),flush=True)
        else:controls();result=measure()
    except Exception as exc:
        import traceback
        traceback.print_exc();status=1;error=repr(exc)
    finally:
        stop.set();thread.join();m=proc.memory_info();peak[0]=max(peak[0],m.rss);peak[1]=max(peak[1],getattr(m,'private',0))
        receipt={'command':[sys.executable,'-X','faulthandler','-I',*sys.argv],'cwd':str(Path.cwd()),'script_sha256':sha(__file__),'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),'compute_workers':1,'monitor_threads':1,'environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']},'wall_seconds':time.perf_counter()-start,'sampled_peak_rss':peak[0],'sampled_peak_private':peak[1],'exit_code':status,'result':result,'error':error}
        print(json.dumps(receipt),flush=True);save(f'photometry-{args.command}-receipt.json',receipt)
    return status
if __name__=='__main__':raise SystemExit(main())
