"""Registered highlight support only; this is not an HDR reconstruction."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import hashlib,importlib.util,json,sys,time
from pathlib import Path
import numpy as np
import psutil
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('photometry',HERE/'hdr-photometry.py');lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
OUT=lib.OUT
start=time.perf_counter()
stage=json.loads((OUT/'stage-a.json').read_text()); records=stage['records'];base=records[1]
binding,poses,identities,center=lib.parse_map();ab,bb=poses[identities[base['whole_sha256']]]
ref=np.load(OUT/base['active_file'],mmap_mode='r',allow_pickle=False)
results=[];peak=0
for source in records[6:]:
    raw=np.load(OUT/source['active_file'],mmap_mode='r',allow_pickle=False)
    aj,bj=poses[identities[source['whole_sha256']]];aa=ab/aj;brel=bb-aa*bj
    sites=[]
    for dy in range(2):
        for dx in range(2):
            plane=raw[dy::2,dx::2];c=source['rawpy_indices'][dy][dx];white=source['white_per_color'][c]
            total=0;covered=0;support=0;values=[]
            for y in range(0,plane.shape[0],128):
                yy,xx=np.nonzero(plane[y:y+128]>=white);total+=len(xx)
                if not len(xx):continue
                sensor=(2*xx+dx)+1j*(2*(yy+y)+dy)
                guide=(sensor-(.5+.5j))/2
                pulled=2*(aa*(guide-center)+brel+center)+(.5+.5j)
                px=(pulled.real-dx)/2;py=(pulled.imag-dy)/2
                inside=(px>=0)&(py>=0)&(px<ref[dy::2,dx::2].shape[1]-1)&(py<ref[dy::2,dx::2].shape[0]-1)
                pulled=pulled[inside];covered+=len(pulled)
                v,clip=lib.sample_site(ref,pulled,(dx,dy),base['white_per_color'][base['rawpy_indices'][dy][dx]])
                v-=base['black_per_color'][base['rawpy_indices'][dy][dx]]
                eligible=(~clip)&(v>=64);support+=int(eligible.sum());values.append(v[eligible])
            flat=np.concatenate(values) if values else np.array([],dtype=np.float64)
            sites.append({'site':dy*2+dx,'color':source['active']['pattern'][dy][dx],'long_original_clipped':total,'registered_short_covered':covered,'short_unclipped_and_ge64dn':support,'short_signal_min':float(flat.min()) if len(flat) else None,'short_signal_median':float(np.median(flat)) if len(flat) else None,'short_signal_max':float(flat.max()) if len(flat) else None})
            peak=max(peak,psutil.Process().memory_info().rss)
        
    r={'source':source['source'],'sites':sites};results.append(r);print(json.dumps({'bracket':source['source']['bracket'],'index':source['source']['index'],'sites':sites}),flush=True)
    del raw,plane
lib.save('registered-highlight-opportunity.json',{'status':'MEASURED_COVERAGE_OPPORTUNITY_NOT_RECOVERY','reference':base['source'],'geometry_sha256':lib.sha(lib.MAP),'domain':'shared7028x4688active;original-long-clipped-sites mapped into independent1smiddle copy','threshold':'short black-subtracted signal>=64DN is a fixed engineering floor, not a fitted noise estimate','focus':'compatibility not established by matching broad coverage; no reconstructed detail claim','results':results})
# Post-hoc diagnostic: rank triples were not the predeclared matched-focus arm.
p=json.loads((OUT/'photometry.json').read_text());post=[]
for i in range(3):
    refp=p['reports'][i];refs={(x['patch'],x['site']):x for x in refp['details']}
    for j in [3+i,6+i]:
        r=p['reports'][j];ratio=r['summary']['fitted_normalized_ratio']/refp['summary']['fitted_normalized_ratio'];res=[]
        for d in r['details']:
            rr=refs[(d['patch'],d['site'])]
            if d['eligible'] and rr['eligible'] and d['role']=='validation':res.append(d['normalized_ratio']/rr['normalized_ratio']/ratio-1)
        aj,_=poses[identities[records[j]['whole_sha256']]];ai,_=poses[identities[records[i]['whole_sha256']]]
        post.append({'source':r['source'],'reference':refp['source'],'normalized_ratio_quotient':ratio,'correction_ev':float(-np.log2(ratio)),'relative_scale_minus_one':abs(aj/ai)-1,'validation_median_abs':float(np.median(np.abs(res))),'validation_p95_abs':float(np.percentile(np.abs(res),95))})
lib.save('rank-paired-posthoc-diagnostic.json',{'status':'POST_HOC_NOT_FOCUS_CERTIFICATION','reason':'compare first/middle/last to corresponding1sstratum after observing same-pass dark-patch tail; no revised pass/fail claim','results':post})
lib.save('opportunity-receipt.json',{'command':[sys.executable,'-X','faulthandler','-I',*sys.argv],'script_sha256':lib.sha(__file__),'library_sha256':lib.sha(HERE/'hdr-photometry.py'),'numpy':np.__version__,'python':sys.version,'compute_workers':1,'raw_decodes':0,'wall_seconds':time.perf_counter()-start,'sampled_between_chunks_peak_rss':peak,'exit_code':0})
print('PASS; no new RAW decode; elapsed',time.perf_counter()-start,flush=True)
