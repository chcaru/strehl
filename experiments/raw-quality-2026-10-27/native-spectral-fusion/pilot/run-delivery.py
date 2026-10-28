"""Root-owned saved-array audit and complete native spectral presentation."""
from pathlib import Path
import argparse
import importlib.util
import sys

AREA = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('spectral_delivery_root',AREA / 'run.py')
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
h = r.h


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('stage-audit','full-views'))
    p.add_argument('--iteration',type=int,default=1)
    p.add_argument('--full-iteration',type=int,default=1)
    a = p.parse_args()
    out = r.folder(a.stage,a.iteration)
    out.mkdir(parents=True,exist_ok=False)
    fields,env,removed = r.r.standard_environment()
    paths = [Path(__file__),AREA / 'run.py',r.HELPER,Path(r.r.__file__),r.r.HELPERS,h.PRIOR,h.prior.HELPER,h.b.HARNESS]
    if a.stage == 'stage-audit':
        script = AREA / 'analysis/stage-audit.py'
        source = r.folder('controls',5)
        r.f.terminal_clean(source / 'process.json')
        h.check_refs(r.read(source / 'completion.json')['reports'])
        paths += [script,source / 'completion.json',source / 'output/receipt.json']
        command = [sys.executable,'-B','-X','faulthandler',str(script),'--out',str(out / 'output')]
        bounds = dict(wall_seconds=60,cpu_seconds=240,committed_bytes=4 << 30,log_bytes=16 << 20)
        expected = 'COMPLETE_NATIVE_SPECTRAL_STAGE_AUDIT'
    else:
        full = r.folder('full299',a.full_iteration)
        r.f.terminal_clean(full / 'process.json')
        fc = r.read(full / 'completion.json')
        h.check_refs(fc['reports'])
        report = r.read(full / 'output/receipt.json')
        assert report['complete'] and report['status'] == 'COMPLETE_NATIVE_SPECTRAL_FULL299'
        assert report['source_count'] == 299 and report['source_ids'] == list(range(299))
        assert report['complete_coverage'] and report['whole_output']
        null = r.folder('null',1)
        r.f.terminal_clean(null / 'process.json')
        h.check_refs(r.read(null / 'completion.json')['reports'])
        script = AREA / 'views.py'
        paths += [script,full / 'completion.json',full / 'output/receipt.json',null / 'completion.json']
        command = [sys.executable,'-B','-X','faulthandler',str(script),
            '--candidate-receipt',str(full / 'output/candidate/native/receipt.json'),
            '--uniform-receipt',str(full / 'output/uniform/native/receipt.json'),
            '--null-receipt',str(null / 'output/receipt.json'),'--out',str(out / 'output')]
        bounds = dict(wall_seconds=300,cpu_seconds=1200,committed_bytes=6 << 30,log_bytes=16 << 20)
        expected = None
    bindings = [h.ref(v) for v in paths]
    h.save(out / 'source-bindings.json',bindings)
    for v in (Path(__file__),script):
        (out / (v.stem + '-executed' + v.suffix)).write_bytes(v.read_bytes())
    h.save(out / 'invocation.json',dict(command=command,bounds=bounds,environment=fields,
        removed_environment=removed,concurrent_work='No other root numerical, GPU or build job.',
        scope='Saved artifacts only; no reconstruction or new photographic-quality claim.'))
    h.observed_run(command,env,out,bounds)
    report_path = out / 'output' / ('receipt.json' if a.stage == 'stage-audit' else 'views.json')
    report = r.read(report_path)
    assert report['complete'] and not report['quality_claim'] and not report['photographic_admission']
    if expected:
        assert report['status'] == expected
    h.check_refs(bindings)
    h.save(out / 'completion.json',dict(status=report['status'],sources_unchanged=True,
        reports=[h.ref(q) for q in sorted((out / 'output').rglob('*')) if q.is_file()],
        photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
