"""Root-owned bounded build, controls and matched complete observer-on/off pair."""
from pathlib import Path
import argparse, importlib.util, json, re, shutil, sys
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('real_source_retained',ROOT/'experiments/garnet-spatial-trace/run.py')
r=importlib.util.module_from_spec(spec);sys.modules[spec.name]=r;spec.loader.exec_module(r)
f,g,c=r.f,r.g,r.c
FILTER='merge_cmd::real_source_contributions::'
RECIPE=ROOT/'experiments/full-stack-source-prior/recipes/marigold-4.json'
HISTORY=ROOT/'experiments/full-stack-source-prior/marigold4-full-1/output/receipt.json'
CORRECTED=ROOT/'experiments/garnet-spatial-trace/marigold4-fixed-1/output/receipt.json'
SCOPE='Read-only actual complete488-source attribution, no quality treatment or SOTA claim.'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sources():
    paths={Path(v['path']) for v in r.sources()}
    paths.update(HERE/n for n in ('core-bridge.rs','observer.rs','independent-controls.rs',
        'analyze.py','run.py','design.md','integration.md','independent-plan.json',
        'independent-plan.md','independent-controls.py'))
    paths.update(ROOT/'experiments/opal-headroom'/n for n in ('run.py','design.md','targets.json','integration.md',
        'stage-observer.rs','stage-run.py','stage-design.md','independent-stage-controls.rs'))
    return [c.ref(p.resolve()) for p in sorted(paths)]

def build(out):
    out.mkdir();bound=sources();c.save(out/'sources.json',bound)
    for name in ('crates/strehl-core/src/pyramid.rs','crates/strehl-cli/src/merge_cmd.rs'):(ROOT/name).touch()
    features=','.join('strehl-cli/'+x for x in g.FEATURES.split(','))
    command=['cargo','test','-p','strehl-core','-p','strehl-cli','--lib','--bin','strehl','--test','byte-freeze',
        '--no-run','--release','--features',features,'--jobs','2','--target-dir',str(ROOT/'target/native-pyramid-profile'),
        '--message-format=json-render-diagnostics','--locked','--offline']
    g.job(command,dict(RAYON_NUM_THREADS='8',CARGO_INCREMENTAL='0'),out,wall=900,cpu=4000,gib=20)
    log=(out/'process.log').read_text(errors='replace')
    assert 'Compiling strehl-core' in log and 'Compiling strehl-cli' in log
    artifacts={}
    for line in log.splitlines():
        try:v=json.loads(line)
        except ValueError:continue
        if v.get('reason')!='compiler-artifact' or not v.get('executable'):continue
        name=v.get('target',{}).get('name');test=v['profile']['test']
        key=('cli-tests' if test else 'strehl') if name=='strehl' else ('core-tests' if name=='strehl_core' and test else None)
        if key is None:continue
        assert key not in artifacts
        dest=out/(key+'.exe');shutil.copyfile(v['executable'],dest);artifacts[key]=c.ref(dest)
    assert set(artifacts)=={'core-tests','cli-tests','strehl'}
    g.unchanged(bound);c.save(out/'executables.json',artifacts)

def controls(out,build,bound):
    out.mkdir();exe=build/'cli-tests.exe';c.save(out/'bindings.json',dict(sources=bound,executable=c.ref(exe)))
    py=out/'python';py.mkdir()
    g.job([sys.executable,'-I','-B','-X','faulthandler',str(HERE/'independent-controls.py'),
        '--out',str(py/'commission.json'),'--analysis-dir',str(py/'analysis')],{},py,wall=60,cpu=120,gib=2)
    commission=read(py/'commission.json')
    assert commission['passed'] and commission['analysis']['actual_analysis_path_passed']
    rust=out/'rust';rust.mkdir()
    env=f.fields();env['STREHL_REAL_SOURCE_TRACE']='off'
    g.job([str(exe),FILTER,'--nocapture','--test-threads=1'],env,rust,wall=180,cpu=900,gib=4)
    log=(rust/'process.log').read_text(errors='replace')
    match=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',log)
    assert match==[('5','0','0')]
    g.unchanged(bound)
    c.save(out/'completion.json',dict(python_commission=True,rust_controls_passed=int(match[0][0]),
        source_bindings_unchanged=True,scope=SCOPE))

def observe(out,build,bound,controls,on):
    exe=build/'cli-tests.exe'
    assert read(controls/'bindings.json')==dict(sources=bound,executable=c.ref(exe))
    assert read(controls/'completion.json')['source_bindings_unchanged']
    for part in ('rust','python'):
        process=read(controls/part/'process.json')
        assert process['exit_code']==0 and process['error'] is None and process['terminal_job_accounting'] and not process['cleanup_errors']
    recipe=f.recipe(RECIPE);assert len(recipe['inputs'])==488
    out.mkdir();config=f.corrected_config(recipe,out,HISTORY)
    c.save(out/'config.json',config)
    bindings=dict(sources=bound,executable=c.ref(exe),recipe=c.ref(RECIPE),historical=c.ref(HISTORY),
        corrected_reference=c.ref(CORRECTED),controls=c.ref(controls/'completion.json'),observer=on,scope=SCOPE)
    c.save(out/'bindings.json',bindings)
    env=f.fields();env.update(STREHL_REAL_SOURCE_TRACE='on' if on else 'off',STREHL_WARPMAP=recipe['warp_map'],
        STREHL_FULL_STACK_SOURCE_PRIOR_CONFIG=str(out/'config.json'))
    g.job([str(exe),f.CORRECTED,'--exact','--ignored','--nocapture','--test-threads=1'],env,out,wall=900,cpu=6000,gib=12)
    receipt=f.validate_corrected(out,recipe,config);old=read(CORRECTED)
    for key in ('candidate_sha256','candidate_rgb16_le_sha256','candidate_planes_sha256','plan','threads','crop','source_count'):
        assert receipt[key]==old[key],f'corrected full reference differs: {key}'
    trace=out/'output/source-trace'
    if on:
        t=read(trace/'receipt.json');assert t['sources']==488
        assert all(t[k] for k in ('all_sampled_chunk_accumulators_bit_exact','all_final_accumulators_bit_exact','all_sampled_final_cfa_bit_exact'))
        layout=read(trace/'layout.json')
        assert (trace/'sources.f32').stat().st_size==488*layout['source_record_floats']*4
    else:assert not trace.exists()
    g.unchanged(bound)
    assert c.ref(CORRECTED)==bindings['corrected_reference'] and c.ref(HISTORY)==bindings['historical']
    c.save(out/'completion.json',dict(observer=on,corrected_reference_exact=True,
        master=c.ref(out/'output/candidate.tiff'),planes=receipt['candidate_planes_sha256'],
        pixels=receipt['candidate_rgb16_le_sha256'],trace=c.ref(trace/'receipt.json') if on else None,scope=SCOPE))

def compare(out,on,off):
    a,b=read(on/'completion.json'),read(off/'completion.json')
    assert a['observer'] and not b['observer'] and a['corrected_reference_exact'] and b['corrected_reference_exact']
    ab,bb=read(on/'bindings.json'),read(off/'bindings.json')
    for key in ('sources','executable','recipe','historical','corrected_reference','controls'):assert ab[key]==bb[key]
    assert c.ref(Path(a['master']['path']))==a['master'] and c.ref(Path(b['master']['path']))==b['master']
    assert a['master']['sha256']==b['master']['sha256'] and a['planes']==b['planes'] and a['pixels']==b['pixels']
    g.unchanged(ab['sources']);out.mkdir()
    c.save(out/'comparison.json',dict(observer_full_tiff_byte_exact=True,all_complete_planes_exact=True,
        source_bindings_unchanged=True,on=c.ref(on/'completion.json'),off=c.ref(off/'completion.json'),scope=SCOPE))

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('build','controls','on','off','compare'))
    p.add_argument('--out',type=Path,required=True)
    for n in ('build','controls','on','off'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();out=a.out.resolve()
    assert out.is_relative_to(HERE) and out!=HERE and not out.exists()
    if a.phase=='build':build(out);return
    if a.phase=='compare':compare(out,a.on.resolve(),a.off.resolve());return
    directory=a.build.resolve();bound=read(directory/'sources.json');g.unchanged(bound)
    for k,v in read(directory/'executables.json').items():assert c.ref(directory/(k+'.exe'))==v
    if a.phase=='controls':controls(out,directory,bound)
    else:observe(out,directory,bound,a.controls.resolve(),a.phase=='on')

if __name__=='__main__':main()
