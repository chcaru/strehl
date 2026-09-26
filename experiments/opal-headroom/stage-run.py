"""Root-owned bounded current-cache writer attribution; no RAW reads or treatment."""
from pathlib import Path
import argparse, importlib.util, json, re, sys
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('opal_stage_highlight_runner',ROOT/'experiments/highlight-rendering/run.py')
h=importlib.util.module_from_spec(spec);sys.modules[spec.name]=h;spec.loader.exec_module(h)
g,c=h.g,h.c
FILTER='image_out::opal_stage_observer::'
TEST='image_out::opal_stage_observer::opal_cached_stage_trace'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def bound_build(path):
    exe,sources=h.shared_build(path)
    required=[HERE/n for n in ('stage-observer.rs','stage-run.py','stage-design.md','independent-stage-controls.rs')]
    assert {str(p.resolve()) for p in required}<={r['path'] for r in sources},'new observer sources absent from fresh build'
    return exe,sources
def controls(out,exe,sources):
    c.save(out/'bindings.json',dict(executable=c.ref(exe),sources=sources))
    g.job([str(exe),FILTER,'--nocapture','--test-threads=1'],dict(RAYON_NUM_THREADS='8'),out,wall=90,cpu=240,gib=3)
    log=(out/'process.log').read_text(encoding='utf-8',errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',log)==[('3','0','1')]
    g.unchanged(sources)
    c.save(out/'completion.json',dict(controls_executed=3,sources_unchanged=True,photographic_verdict=None))
def run(args,out,exe,sources):
    control=args.controls.resolve();assert read(control/'bindings.json')==dict(executable=c.ref(exe),sources=sources)
    done=read(control/'completion.json');assert done['controls_executed']==3 and done['sources_unchanged']
    process=read(control/'process.json');assert process['exit_code']==0 and process['error'] is None and process['terminal_job_accounting'] and not process['cleanup_errors']
    assert read(control/'invocation.json')['command']==[str(exe),FILTER,'--nocapture','--test-threads=1']
    cache_run=args.cache_run.resolve();factorial=args.factorial.resolve()
    cache=cache_run/'output/baseline-cache.json';cache_done=read(cache_run/'completion.json')
    assert cache_done['current_production_rgb16_icc_exact'] and cache_done['sources_and_production_unchanged']
    assert cache_done['receipt']==c.ref(cache_run/'output/receipt.json')
    meta=read(cache);assert meta['phase']=='full' and meta['frames']==155 and meta['reference']==77 and meta['crop']==[60,40,3396,2264]
    factorial_done=read(factorial/'completion.json');receipt=read(factorial/'output/receipt.json')
    assert factorial_done['receipt']==c.ref(factorial/'output/receipt.json')
    assert receipt['status']=='COMPLETE_CACHED_FACTORIAL' and receipt['raw_reads']==0 and receipt['observer_on_off_file_exact']
    assert receipt['retained_current_pixels_and_icc_exact'] and receipt['merged_planes_unchanged']
    assert receipt['cache_metadata_sha256']==c.ref(cache)['sha256'] and receipt['planes_sha256']==meta['plane_sha256']
    assert [a['arm'] for a in receipt['arms']]==list(h.ARMS)
    assert all(a['resolved_development']==receipt['arms'][0]['resolved_development'] for a in receipt['arms'])
    current=factorial/'output/current.tiff';shoulder=factorial/'output/shoulder.tiff'
    refs=[c.ref(p) for p in (cache,cache.parent/meta['binary'],current,shoulder,
        cache_run/'completion.json',cache_run/'output/receipt.json',factorial/'completion.json',factorial/'output/receipt.json')]
    assert refs[1]['sha256']==meta['binary_sha256']
    for arm,p in [('current',current),('shoulder',shoulder)]:
        row=next(r for r in receipt['arms'] if r['arm']==arm);assert row['file_sha256']==c.ref(p)['sha256']
    config=dict(schema=1,cache=str(cache),cache_sha256=refs[0]['sha256'],expected_current_tiff=str(current),
        expected_current_file_sha256=refs[2]['sha256'],expected_shoulder_tiff=str(shoulder),
        expected_shoulder_file_sha256=refs[3]['sha256'],out_dir=str(out/'output'))
    c.save(out/'config.json',config);c.save(out/'bindings.json',dict(executable=c.ref(exe),sources=sources,inputs=refs,
        controls=c.ref(control/'completion.json')))
    g.job([str(exe),TEST,'--exact','--ignored','--nocapture','--test-threads=1'],
        dict(RAYON_NUM_THREADS='8',STREHL_OPAL_STAGE_CONFIG=str(out/'config.json')),out,wall=300,cpu=1500,gib=8)
    log=(out/'process.log').read_text(encoding='utf-8',errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed;',log)==['1'] and 'OPAL_STAGE_TRACE_COMPLETE ' in log
    observed=read(out/'output/receipt.json')
    assert observed['status']=='OPAL_STAGE_TRACE_COMPLETE' and observed['raw_reads']==0
    assert observed['whole_current_and_shoulder_pixels_exact'] and observed['observer_on_off_file_exact']
    assert observed['retained_current_pixels_and_icc_exact'] and observed['merged_planes_unchanged']
    assert observed['resolved_development']==receipt['arms'][0]['resolved_development']
    assert observed['whole_counts']['pixels']==6792*4528 and len(observed['regions'])==2
    for region in observed['regions']:
        assert region['counts']['pixels']==384*384
        for artifact in region['artifacts']:
            assert c.ref(out/'output'/region['name']/artifact['file'])['sha256']==artifact['sha256']
    g.unchanged(sources+refs)
    c.save(out/'completion.json',dict(receipt=c.ref(out/'output/receipt.json'),raw_reads=0,
        actual_stage_scan_matches_whole_current_and_shoulder=True,observer_on_off_file_exact=True,
        sources_and_inputs_unchanged=True,causal_verdict=None))
def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('controls','run'));p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    for name in ('controls','cache-run','factorial'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();out=a.out.resolve();assert out.is_relative_to(HERE) and out!=HERE and not out.exists()
    exe,sources=bound_build(a.build.resolve());out.mkdir()
    if a.phase=='controls':controls(out,exe,sources)
    else:
        assert a.controls and a.cache_run and a.factorial
        run(a,out,exe,sources)
if __name__=='__main__':main()
