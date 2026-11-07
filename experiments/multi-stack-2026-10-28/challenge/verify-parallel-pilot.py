"""Independent read-only candidate2/candidate3 optimization audit."""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
import tifffile
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'outputs/multi-stack'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k not in ['build','renderer_source_sha256','elapsed_before_output_seconds','accumulate_seconds','gather_seconds','prepare_seconds','probe_seconds']}
    if isinstance(value,list):return [clean(x) for x in value]
    return value
start=time.perf_counter();report={'status':'VERIFIED_MECHANICS_NOT_PHOTOGRAPHIC_GAIN','outputs':{}}
for name in ['master.tiff','photograph.tiff']:
    paths=[BASE/f'pilot-{i}'/name for i in [2,3]]
    hashes=[sha(p) for p in paths]
    a=tifffile.memmap(paths[0]);b=tifffile.memmap(paths[1]);assert a.shape==b.shape and a.dtype==b.dtype
    dtype=np.uint32 if a.dtype==np.float32 else np.uint16
    mismatches=0
    for y in range(0,a.shape[0],128):mismatches+=int(np.count_nonzero(a[y:y+128].view(dtype)!=b[y:y+128].view(dtype)))
    with tifffile.TiffFile(paths[0]) as ta,tifffile.TiffFile(paths[1]) as tb:
        da={t.code:t.value for t in ta.pages[0].tags.values()};db={t.code:t.value for t in tb.pages[0].tags.values()}
        changed=[str(k) for k in set(da)|set(db) if da.get(k)!=db.get(k)]
    report['outputs'][name]={'shape':list(a.shape),'dtype':str(a.dtype),'float_or_integer_bit_mismatches':mismatches,'whole_file_sha256':hashes,'changed_tiff_tag_codes':changed}
    assert mismatches==0
    assert changed in [[],['305']]
    del a,b
reports=[json.loads((BASE/f'pilot-{i}'/'render-report.json').read_text()) for i in [2,3]]
assert clean(reports[0])==clean(reports[1])
report['all_non_build_non_timing_render_fields_equal']=True
report['excluded_fields']=['build','renderer_source_sha256','elapsed_before_output_seconds','accumulate_seconds','gather_seconds','prepare_seconds','probe_seconds']
for name in ['source-identities.json','calibration.json']:
    h=[sha(BASE/f'pilot-{i}'/name) for i in [2,3]];assert h[0]==h[1];report[name]={'whole_file_sha256':h,'equal':True}
geometry=[json.loads((BASE/f'pilot-{i}'/'alignment.json').read_text()) for i in [2,3]]
assert geometry[0]['warpmap']==geometry[1]['warpmap'];report['exact_geometry_warpmap']=True
report['group_counts']={k:reports[0][k] for k in ['groups','proposed_groups','sources']}
report['qualification']='Only10sources,incompletefocus,andnoacceptedrepeatgroups;validatesordinary/singletonoptimizationmechanicsnotrepeatphotographicgain.'
report['command']=[sys.executable,'-X','faulthandler','-I',*sys.argv];report['script_sha256']=sha(Path(__file__));report['numpy']=np.__version__;report['tifffile']=tifffile.__version__;report['elapsed_seconds']=time.perf_counter()-start;report['exit_code']=0
out=BASE/'pilot-3'/'independent-optimization-equality.json'
with out.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(report,indent=2))
