"""Root-executed complete photographic observations; old qualification stays false."""
from pathlib import Path
import argparse, importlib.util, json, math, re, shutil, sys, hashlib
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('full_prior_retained_runner',ROOT/'experiments/cross-scale-source-prior/run.py')
g=importlib.util.module_from_spec(spec);sys.modules[spec.name]=g;spec.loader.exec_module(g)
c=g.c
TEST='merge_cmd::full_stack_source_prior::complete_pair'
CONSTRUCTOR='merge_cmd::full_stack_source_prior::bounded_constructor_preserves_retained_arithmetic'
CORRECTED='merge_cmd::full_stack_source_prior::corrected_current'
OLD_SCREEN=ROOT/'experiments/cross-scale-source-prior/controls-1/output/screen.json'
OLD_SCREEN_HASH='a63516111176f8b68a2f3d433ca596f672ea0a02823f71e298c92be546ee9144'
SCOPE='Separate complete photographic observation of unchanged known-risk prior. General quality qualification remains false; no default or SOTA claim.'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def bindings():
    paths={Path(r['path']) for r in g.bindings()}
    paths.update(HERE/n for n in ('adapter.rs','runner.py','design.md'))
    paths.update(ROOT/'experiments/highlight-rendering'/n for n in
        ('image-out-bridge.rs','merge-replay.rs','independent-controls.rs'))
    paths.add(OLD_SCREEN)
    return [c.ref(p.resolve()) for p in sorted(paths)]
def fields():
    return dict(RAYON_NUM_THREADS='8',STREHL_PYRAMID_WORKERS='8',STREHL_ALIGN='1',STREHL_FULLRES_GATHER='1',
        STREHL_DIRECT_PLANES='rounded',STREHL_PROBE_GATHER='green',STREHL_WARP_WRITEBACK='parallel',
        STREHL_GPU_GATHER='on',STREHL_GPU_SCHEDULE='device',STREHL_GPU_GATHER_LOG='on',
        STREHL_DEFECT='off',STREHL_FINE_SUPPORT='off',STREHL_CA_BEFORE_MHC='off')
def job(command,env,out,**limits):
    return g.job(command,env,out,**limits)
def build(out):
    out.mkdir(exist_ok=False)
    for f in ('crates/strehl-cli/src/merge_cmd.rs','crates/strehl-core/src/pyramid.rs'):(ROOT/f).touch()
    sources=bindings();c.save(out/'sources.json',sources)
    cmd=['cargo','test','-p','strehl-cli','--bin','strehl','--test','byte-freeze','--no-run','--release',
        '--features',g.FEATURES,'--jobs','2','--target-dir',str(ROOT/'target/native-pyramid-profile'),
        '--message-format=json-render-diagnostics','--locked','--offline']
    job(cmd,dict(RAYON_NUM_THREADS='8',CARGO_INCREMENTAL='0'),out,wall=600,cpu=2400,gib=16)
    log=(out/'process.log').read_text(encoding='utf-8',errors='replace')
    assert 'Compiling strehl-cli' in log and 'Compiling strehl-core' in log
    artifacts={}
    for line in log.splitlines():
        try:r=json.loads(line)
        except ValueError:continue
        if r.get('reason')=='compiler-artifact' and r.get('executable') and r.get('target',{}).get('name')=='strehl':
            key='cli-tests' if r['profile']['test'] else 'strehl';assert key not in artifacts
            dest=out/(key+'.exe');shutil.copyfile(r['executable'],dest);artifacts[key]=c.ref(dest)
    assert set(artifacts)=={'cli-tests','strehl'};g.unchanged(sources);c.save(out/'executables.json',artifacts)
def controls(out,exe,sources):
    assert c.ref(OLD_SCREEN)['sha256']==OLD_SCREEN_HASH
    out.mkdir(exist_ok=False);c.save(out/'bindings.json',dict(sources=sources,executable=c.ref(exe)))
    retained=out/'retained';retained.mkdir();env=fields();env['STREHL_CROSS_SCALE_SOURCE_PRIOR_OUT']=str(retained/'output')
    job([str(exe),g.FILTER,'--nocapture','--test-threads=1'],env,retained,wall=180,cpu=900,gib=4)
    assert re.findall(r'test result: ok\. (\d+) passed;',(retained/'process.log').read_text())==['2']
    old,new=read(OLD_SCREEN),read(retained/'output/screen.json')
    assert new==old and new['photographic_replay_admitted'] is False
    constructor=out/'constructor';constructor.mkdir()
    job([str(exe),CONSTRUCTOR,'--exact','--nocapture','--test-threads=1'],fields(),constructor,wall=60,cpu=180,gib=2)
    assert re.findall(r'test result: ok\. (\d+) passed;',(constructor/'process.log').read_text())==['1']
    g.unchanged(sources);c.save(out/'completion.json',dict(retained_screen_exact=True,photographic_replay_admitted=False,
        retained_screen=c.ref(retained/'output/screen.json'),constructor_completed=True,sources_unchanged=True,scope=SCOPE))
def screen_binding(screen,exe,sources):
    assert read(screen/'bindings.json')==dict(sources=sources,executable=c.ref(exe))
    r=read(screen/'completion.json');assert r['retained_screen_exact'] and r['constructor_completed'] and r['sources_unchanged']
    assert r['photographic_replay_admitted'] is False and r['retained_screen']==c.ref(screen/'retained/output/screen.json')
    assert read(screen/'retained/output/screen.json')==read(OLD_SCREEN)
    for part in ('retained','constructor'):
        process=read(screen/part/'process.json');assert process['exit_code']==0 and process['error'] is None
        assert process['terminal_job_accounting'] and not process['cleanup_errors']
    return c.ref(screen/'completion.json')
def recipe(path):
    r=read(path)
    assert set(r)==set(('schema','mode','stack_name','inputs','warp_map','warp_map_sha256','expected_reference',
        'expected_full_geometry','expected_crop','expected_baseline','expected_baseline_sha256','expected_baseline_pixels_sha256',
        'expected_camera','expected_iso','exposure_stops','tone_policy'))
    assert r['schema']==1 and r['mode'] in ('current','prior') and 3<=len(r['inputs'])<=1024
    assert r['expected_full_geometry']==[3516,2344] and r['tone_policy']=='automatic-per-arm-current-writer'
    assert [i['index'] for i in r['inputs']]==list(range(len(r['inputs'])))
    assert len({i['path'] for i in r['inputs']})==len(r['inputs'])
    assert all(Path(i['path']).is_absolute() for i in r['inputs'])
    assert c.ref(Path(r['warp_map']))['sha256']==r['warp_map_sha256']
    assert c.ref(Path(r['expected_baseline']))['sha256']==r['expected_baseline_sha256']
    return r
def validate(run,r,phase):
    data=read(run/'output/receipt.json');assert data['phase']==phase and data['mode']==r['mode']
    n=len(r['inputs']);ref=r['expected_reference'];indices=[ref-1,ref,ref+1] if phase=='cost' else list(range(n))
    assert data['source_count']==len(indices) and data['probe_source_count']==n and [f['index'] for f in data['frames']]==indices
    assert data['crop']==r['expected_crop'] and data['native_dimensions']==[r['expected_crop'][2]*2,r['expected_crop'][3]*2]
    assert data['map_sha256']==r['warp_map_sha256'] and data['threads']==8 and data['original_metadata_unchanged']
    assert data['generated_photographic_replay_admitted'] is False
    names=('baseline','candidate') if r['mode']=='prior' else ('baseline',)
    for name in names:
        assert c.ref(run/'output'/(name+'.tiff'))['sha256']==data[name+'_sha256']
        cache=read(run/'output'/(name+'-cache.json'))
        assert cache['phase']==phase and cache['frames']==n and cache['reference']==ref
        assert cache['plane_sha256']==data[name+'_planes_sha256']
        assert c.ref(run/'output'/cache['binary'])['sha256']==cache['binary_sha256']
    if r['mode']=='prior':
        assert data['held_state_bit_exact'] and data['replay_exact']
        assert all(f['replay_exact'] and f['held_state_bit_exact'] and f['source_unchanged']
            and f['canonical_weight_sha256'][0]==f['candidate_weight_sha256'][0] for f in data['frames'])
    if phase=='full':assert data['baseline_rgb16_le_sha256']==r['expected_baseline_pixels_sha256']
    return data

def corrected_config(r,out,historical_receipt):
    assert r['mode'] in ('current','prior')
    old=read(historical_receipt);assert old['phase']=='full' and old['mode'] in ('current','prior')
    assert old['baseline_rgb16_le_sha256']==r['expected_baseline_pixels_sha256'] and old['source_count']==len(r['inputs'])
    return dict(r,mode='current',phase='full',out_dir=str(out/'output'),historical=dict(receipt=str(historical_receipt.resolve()),sha256=c.ref(historical_receipt)['sha256']))

def validate_corrected(run,r,config):
    import numpy as np,tifffile
    data=read(run/'output/receipt.json');h=config['historical'];old=read(Path(h['receipt']))
    assert c.ref(Path(h['receipt']))['sha256']==h['sha256'] and data['historical']==h
    assert data['phase']=='full' and data['mode']=='numerical-candidate' and data['photographic_replay_admitted'] is False
    assert data['historical_cache_replay_exact'] and data['held_source_evidence_exact'] and data['original_metadata_unchanged']
    assert data['source_count']==data['probe_source_count']==len(r['inputs']) and data['threads']==8
    assert data['plan']==old['plan'] and data['threads']==old['threads']
    assert data['crop']==r['expected_crop'] and data['map_sha256']==r['warp_map_sha256']
    keys=('index','active_u16_sha256','known4_sha256','guide_sha256','variance_sha256','beta','energy_sha256','floor_sha256','canonical_weight_sha256','source_unchanged')
    assert len(data['frames'])==len(old['frames'])==len(r['inputs'])
    assert all(all(a[k]==b[k] for k in keys) for a,b in zip(data['frames'],old['frames']))
    with tifffile.TiffFile(r['expected_baseline']) as f: baseline=f.asarray();icc=bytes(f.pages[0].tags[34675].value)
    for name in ('historical-baseline-replay','candidate'):
        with tifffile.TiffFile(run/'output'/(name+'.tiff')) as f: pixels=f.asarray();profile=bytes(f.pages[0].tags[34675].value)
        assert pixels.dtype==baseline.dtype==np.uint16 and pixels.shape==baseline.shape and profile==icc
        if name=='historical-baseline-replay':assert np.array_equal(pixels,baseline)
        else:assert hashlib.sha256(pixels.astype('<u2',copy=False).tobytes()).hexdigest()==data['candidate_rgb16_le_sha256']
    assert c.ref(run/'output/candidate.tiff')['sha256']==data['candidate_sha256']
    assert data['expected_historical_pixels_sha256']==r['expected_baseline_pixels_sha256']
    assert data['corrected_output_changed']==(data['candidate_rgb16_le_sha256']!=r['expected_baseline_pixels_sha256'])
    cache=read(run/'output/candidate-cache.json')
    assert cache['arm']=='candidate' and cache['phase']=='full' and cache['frames']==len(r['inputs'])
    assert cache['plane_sha256']==data['candidate_planes_sha256'] and c.ref(run/'output'/cache['binary'])['sha256']==cache['binary_sha256']
    return data
def observe(args,out,exe,sources,screen):
    assert args.recipe is not None;r=recipe(args.recipe.resolve());recipe_ref=c.ref(args.recipe.resolve())
    cost_binding=None
    if args.phase=='full':
        assert args.cost is not None;prior=args.cost.resolve();b=read(prior/'bindings.json')
        assert b['sources']==sources and b['executable']==c.ref(exe) and b['recipe']==recipe_ref and b['screen']==screen
        decision=read(prior/'cost-decision.json');assert decision['resource_feasible']
        assert decision['receipt']==c.ref(prior/'output/receipt.json') and decision['process']==c.ref(prior/'process.json')
        validate(prior,r,'cost');cost_binding=c.ref(prior/'cost-decision.json')
    out.mkdir(exist_ok=False);c.save(out/'bindings.json',dict(sources=sources,executable=c.ref(exe),recipe=recipe_ref,screen=screen,prior_cost=cost_binding,scope=SCOPE))
    config=dict(r,phase=args.phase,out_dir=str(out/'output'));c.save(out/'config.json',config)
    env=fields();env.update(STREHL_WARPMAP=r['warp_map'],STREHL_FULL_STACK_SOURCE_PRIOR_CONFIG=str(out/'config.json'))
    cost=args.phase=='cost'
    process=job([str(exe),TEST,'--exact','--ignored','--nocapture','--test-threads=1'],env,out,
        wall=300 if cost else 1800,cpu=1200 if cost else 12000,gib=24)
    assert re.findall(r'test result: ok\. (\d+) passed;',(out/'process.log').read_text())==['1']
    g.unchanged(sources);assert c.ref(args.recipe.resolve())==recipe_ref;data=validate(out,r,args.phase)
    if cost:
        variable=data['variable_source_seconds'];fixed=max(0,data['total_seconds']-variable)
        assert math.isfinite(variable) and variable>0 and math.isfinite(fixed)
        estimate=1.25*len(r['inputs'])/3*variable+fixed+120
        peak=process['job_memory']['peak_job_memory_used_bytes']
        c.save(out/'cost-decision.json',dict(resource_feasible=estimate<=1500 and peak<(18<<30),
            estimated_full_seconds=estimate,maximum_estimate_seconds=1500,variable_source_seconds=variable,
            cost_source_count=3,full_source_count=len(r['inputs']),source_multiplier=1.25,
            observed_fixed_seconds=fixed,additional_allowance_seconds=120,cost_peak_bytes=peak,maximum_cost_peak_bytes=18<<30,
            full_limits=dict(wall_seconds=1800,cpu_seconds=12000,committed_bytes=24<<30),
            receipt=c.ref(out/'output/receipt.json'),process=c.ref(out/'process.json'),photographic_replay_admitted=False,
            limitation='Three predetermined original indices, whole-count probe, subset prior only. Resource extrapolation is not runtime guarantee, quality evidence, or a complete stack.'))
    else:
        import numpy as np,tifffile
        a=tifffile.imread(out/'output/baseline.tiff');b=tifffile.imread(r['expected_baseline'])
        assert a.dtype==b.dtype==np.uint16 and a.shape==b.shape and np.array_equal(a,b)
    c.save(out/'completion.json',dict(phase=args.phase,mode=r['mode'],sources_unchanged=True,
        historical_full_baseline_exact=not cost,receipt=c.ref(out/'output/receipt.json'),photographic_replay_admitted=False,scope=SCOPE))
def views(args,out,exe,sources,screen):
    import numpy as np,tifffile
    from PIL import Image
    assert args.run is not None;run=args.run.resolve();bound=read(run/'bindings.json')
    assert bound['sources']==sources and bound['executable']==c.ref(exe) and bound['screen']==screen
    completion=read(run/'completion.json');assert completion['phase']=='full' and completion['historical_full_baseline_exact']
    r=recipe(Path(bound['recipe']['path']));assert c.ref(Path(bound['recipe']['path']))==bound['recipe']
    data=validate(run,r,'full');out.mkdir(exist_ok=False);records=[]
    for name in (('baseline','candidate') if r['mode']=='prior' else ('baseline',)):
        path=run/'output'/(name+'.tiff')
        with tifffile.TiffFile(path) as f:a=f.asarray();icc=bytes(f.pages[0].tags[34675].value)
        assert hashlib.sha256(a.astype('<u2',copy=False).tobytes()).hexdigest()==data[name+'_rgb16_le_sha256']
        image=Image.fromarray(((a.astype(np.uint32)+128)//257).astype(np.uint8));image.thumbnail((1617,1617),Image.Resampling.LANCZOS)
        dest=out/(name+'-overview.png');image.save(dest,icc_profile=icc)
        records.append(dict(name=name,master=c.ref(path),overview=c.ref(dest),icc_sha256=hashlib.sha256(icc).hexdigest(),native_dimensions=data['native_dimensions']))
    assert len({r['icc_sha256'] for r in records})==1;g.unchanged(sources)
    c.save(out/'completion.json',dict(complete_images=records,view='whole-image orientation only; source masters remain full resolution',
        receipt=c.ref(run/'output/receipt.json'),scope=SCOPE,visual_verdict=None))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('build','controls','cost','full','views'))
    parser.add_argument('--out',type=Path,required=True)
    for n in ('build','screen','recipe','cost','run'):parser.add_argument('--'+n,type=Path)
    args=parser.parse_args();out=args.out.resolve();assert out.is_relative_to(HERE) and out!=HERE and not out.exists()
    if args.phase=='build':build(out);return
    assert args.build is not None;b=args.build.resolve();sources=read(b/'sources.json');g.unchanged(sources)
    exe=b/'cli-tests.exe';assert c.ref(exe)==read(b/'executables.json')['cli-tests']
    assert {str((HERE/n).resolve()) for n in ('adapter.rs','runner.py','design.md')}<={r['path'] for r in sources}
    if args.phase=='controls':controls(out,exe,sources);return
    assert args.screen is not None;screen=screen_binding(args.screen.resolve(),exe,sources)
    if args.phase=='views':views(args,out,exe,sources,screen)
    else:observe(args,out,exe,sources,screen)
if __name__=='__main__':main()
