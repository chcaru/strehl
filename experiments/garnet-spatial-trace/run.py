"""Root-executed finite-range regressions and actual full-stack on/off census."""
from pathlib import Path
import argparse, importlib.util, json, re, shutil, sys
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('garnet_trace_full',ROOT/'experiments/full-stack-source-prior/runner.py')
f=importlib.util.module_from_spec(spec);sys.modules[spec.name]=f;spec.loader.exec_module(f)
g,c=f.g,f.c
FILTER='pyramid::accumulator_range_independent::independent_'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sources():
    paths={Path(r['path']) for r in f.bindings()}
    paths.update([HERE/'core-observer.rs',HERE/'run.py',
        ROOT/'experiments/pyramid-accumulator-range/independent-controls.rs',
        ROOT/'experiments/pyramid-accumulator-range/range-bound-controls.rs',
        ROOT/'experiments/pyramid-accumulator-range/plan.md'])
    paths.update(ROOT/'experiments/marigold-source-pure'/n for n in ('oracle.rs','run.py','design.md'))
    return [c.ref(p.resolve()) for p in sorted(paths)]

def build(out):
    out.mkdir();bound=sources();c.save(out/'sources.json',bound)
    for p in ('crates/strehl-core/src/pyramid.rs','crates/strehl-cli/src/merge_cmd.rs'):(ROOT/p).touch()
    features=','.join('strehl-cli/'+x for x in g.FEATURES.split(','))
    cmd=['cargo','test','-p','strehl-core','-p','strehl-cli','--lib','--bin','strehl','--test','byte-freeze',
        '--no-run','--release','--features',features,'--jobs','2','--target-dir',str(ROOT/'target/native-pyramid-profile'),
        '--message-format=json-render-diagnostics','--locked','--offline']
    g.job(cmd,dict(RAYON_NUM_THREADS='8',CARGO_INCREMENTAL='0'),out,wall=900,cpu=4000,gib=20)
    log=(out/'process.log').read_text(errors='replace')
    assert 'Compiling strehl-core' in log and 'Compiling strehl-cli' in log
    artifacts={}
    for line in log.splitlines():
        try:r=json.loads(line)
        except ValueError:continue
        if r.get('reason')!='compiler-artifact' or not r.get('executable'):continue
        name=r.get('target',{}).get('name');test=r['profile']['test']
        key=('cli-tests' if test else 'strehl') if name=='strehl' else ('core-tests' if name=='strehl_core' and test else None)
        if key is None:continue
        assert key not in artifacts
        dest=out/(key+'.exe');shutil.copyfile(r['executable'],dest);artifacts[key]=c.ref(dest)
    assert set(artifacts)=={'core-tests','cli-tests','strehl'}
    g.unchanged(bound);c.save(out/'executables.json',artifacts)

def regressions(out,build,bound):
    out.mkdir();exe=build/'core-tests.exe'
    c.save(out/'bindings.json',dict(sources=bound,executable=c.ref(exe)))
    try:g.job([str(exe),FILTER,'--nocapture','--test-threads=1'],dict(RAYON_NUM_THREADS='8'),out,wall=120,cpu=600,gib=4)
    except AssertionError:
        process=read(out/'process.json')
        assert process['exit_code']==101 and process['error'] is None and process['terminal_job_accounting']
    log=(out/'process.log').read_text(errors='replace')
    rows=[json.loads(line.split('PYRAMID_ACCUMULATOR_RANGE ',1)[1]) for line in log.splitlines() if 'PYRAMID_ACCUMULATOR_RANGE ' in line]
    assert re.findall(r'test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;',log) in ([('4','0','0')],[('1','3','0')],[('2','2','0')],[('3','1','0')],[('0','4','0')])
    assert [r['case'] for r in rows]==['flat','midtone','camera-range-low-variance-pair','identical-high-dn-pair','camera-range-profile-variance-pair']
    process=read(out/'process.json');g.unchanged(bound)
    c.save(out/'results.json',dict(exit_code=process['exit_code'],all_tests_passed=process['exit_code']==0,observations=rows,
        scope='Arithmetic range tests; actual photographic cause requires the separate full-stack census.'))
    print(json.dumps(dict(exit_code=process['exit_code'],all_tests_passed=process['exit_code']==0,observations=len(rows))))

def census(out,build,bound,recipe,on):
    r=f.recipe(recipe);assert r['mode']=='current' and len(r['inputs'])==183
    out.mkdir();exe=build/'cli-tests.exe'
    c.save(out/'bindings.json',dict(sources=bound,executable=c.ref(exe),recipe=c.ref(recipe),observer=on,
        scope='Same complete183-source current merge; read-only finish census on/off. Prior baseline run measured113.468s; no new speed claim.'))
    config=dict(r,phase='full',out_dir=str(out/'output'));c.save(out/'config.json',config)
    env=f.fields();env.update(STREHL_WARPMAP=r['warp_map'],STREHL_FULL_STACK_SOURCE_PRIOR_CONFIG=str(out/'config.json'))
    if on:env['STREHL_GARNET_NUMERATOR_CENSUS']='1'
    g.job([str(exe),f.TEST,'--exact','--ignored','--nocapture','--test-threads=1'],env,out,wall=900,cpu=6000,gib=12)
    receipt=f.validate(out,r,'full');log=(out/'process.log').read_text(errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed;',log)==['1']
    records=[json.loads(line.split('GARNET_NUMERATOR_CENSUS ',1)[1]) for line in log.splitlines() if 'GARNET_NUMERATOR_CENSUS ' in line]
    if on:
        assert records[0]['stage']=='begin' and records[0]['frames']==183
        assert records[-1]['stage']=='end' and records[-1]['complete'] and records[-1]['completed_planes']==4
        assert len([x for x in records if x['stage']=='pre_hull'])==4
    else:assert not records
    g.unchanged(bound);c.save(out/'census.json',records)
    c.save(out/'completion.json',dict(observer=on,actual_historical_pixels_exact=True,
        baseline_tiff=c.ref(out/'output/baseline.tiff'),baseline_pixel_hash=receipt['baseline_rgb16_le_sha256'],
        merged_plane_hashes=receipt['baseline_planes_sha256'],census=c.ref(out/'census.json')))

def compare(out,on,off):
    a,b=read(on/'completion.json'),read(off/'completion.json')
    assert a['observer'] and not b['observer'] and a['actual_historical_pixels_exact'] and b['actual_historical_pixels_exact']
    assert a['baseline_tiff']['sha256']==b['baseline_tiff']['sha256']
    assert a['baseline_pixel_hash']==b['baseline_pixel_hash'] and a['merged_plane_hashes']==b['merged_plane_hashes']
    ab,bb=read(on/'bindings.json'),read(off/'bindings.json')
    assert all(ab[k]==bb[k] for k in ('executable','recipe','sources'))
    out.mkdir();c.save(out/'comparison.json',dict(observer_output_file_exact=True,merged_planes_exact=True,
        on=c.ref(on/'completion.json'),off=c.ref(off/'completion.json'),census=a['census']))
    print('OBSERVER_ON_OFF_EXACT')

def candidate(out,build,bound,recipe,historical):
    r=f.recipe(recipe);out.mkdir();exe=build/'cli-tests.exe'
    config=f.corrected_config(r,out,historical)
    c.save(out/'bindings.json',dict(sources=bound,executable=c.ref(exe),recipe=c.ref(recipe),
        historical=c.ref(historical),scope='Complete current merge with numerical fix; held source weights and gather compared exactly with history.'))
    c.save(out/'config.json',config)
    env=f.fields();env.update(STREHL_WARPMAP=r['warp_map'],STREHL_FULL_STACK_SOURCE_PRIOR_CONFIG=str(out/'config.json'),STREHL_GARNET_NUMERATOR_CENSUS='1')
    g.job([str(exe),f.CORRECTED,'--exact','--ignored','--nocapture','--test-threads=1'],env,out,wall=1200,cpu=9000,gib=12)
    receipt=f.validate_corrected(out,r,config);log=(out/'process.log').read_text(errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed;',log)==['1']
    records=[json.loads(line.split('GARNET_NUMERATOR_CENSUS ',1)[1]) for line in log.splitlines() if 'GARNET_NUMERATOR_CENSUS ' in line]
    assert records[0]['stage']=='begin' and records[0]['frames']==len(r['inputs'])
    assert records[-1]['stage']=='end' and records[-1]['complete'] and records[-1]['completed_planes']==4
    assert len([x for x in records if x['stage']=='pre_hull'])==4
    assert all(not any(x['scan'][k] for k in ('nan','positive_infinity','negative_infinity')) for x in records if 'scan' in x)
    g.unchanged(bound);c.save(out/'census.json',records)
    c.save(out/'completion.json',dict(all_finish_values_finite=True,held_source_evidence_exact=True,
        historical_cache_replay_exact=True,changed=receipt['corrected_output_changed'],
        candidate_tiff=c.ref(out/'output/candidate.tiff'),receipt=c.ref(out/'output/receipt.json')))

def bounds(out,build,bound):
    out.mkdir();exe=build/'core-tests.exe'
    c.save(out/'bindings.json',dict(sources=bound,executable=c.ref(exe)))
    g.job([str(exe),'pyramid::accumulator_range_bounds::','--nocapture','--test-threads=1'],dict(RAYON_NUM_THREADS='8'),out,wall=180,cpu=900,gib=4)
    log=(out/'process.log').read_text(errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',log)==[('5','0','0')]
    g.unchanged(bound);c.save(out/'completion.json',dict(all_five_passed=True))

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('build','regressions','bounds','candidate','census-on','census-off','compare'))
    p.add_argument('--out',type=Path,required=True)
    for name in ('build','recipe','historical','on','off'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();out=a.out.resolve();assert out.is_relative_to(HERE) and out!=HERE and not out.exists()
    if a.phase=='build':build(out);return
    if a.phase=='compare':compare(out,a.on.resolve(),a.off.resolve());return
    directory=a.build.resolve();bound=read(directory/'sources.json');g.unchanged(bound)
    for key,row in read(directory/'executables.json').items():assert c.ref(directory/(key+'.exe'))==row
    if a.phase=='regressions':regressions(out,directory,bound)
    elif a.phase=='bounds':bounds(out,directory,bound)
    elif a.phase=='candidate':candidate(out,directory,bound,a.recipe.resolve(),a.historical.resolve())
    else:census(out,directory,bound,a.recipe.resolve(),a.phase=='census-on')

if __name__=='__main__':main()
