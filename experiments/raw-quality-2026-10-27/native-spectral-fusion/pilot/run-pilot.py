"""Root-only bounded spectral controls and prospective real-source cost stages."""
from pathlib import Path
import argparse
import importlib.util
import sys

AREA = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('spectral_pilot_root', AREA / 'run.py')
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
h = r.h


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('controls','cost16','source149','full299'))
    p.add_argument('--iteration', type=int, default=1)
    p.add_argument('--build-iteration', type=int, default=1)
    p.add_argument('--null-iteration', type=int, default=1)
    p.add_argument('--controls-iteration', type=int, default=1)
    p.add_argument('--cost-iteration', type=int, default=1)
    p.add_argument('--source-iteration', type=int, default=1)
    a = p.parse_args()
    assert min(a.iteration,a.build_iteration,a.null_iteration,a.controls_iteration,a.cost_iteration,a.source_iteration) > 0
    out = r.folder(a.stage,a.iteration)
    out.mkdir(parents=True,exist_ok=False)
    numerical_paths = [v for v in AREA.glob('*.py') if not v.name.startswith('run') and v.name != 'views.py']
    numerical_paths += [AREA / name for name in ('controls-protocol.md','api.md','implementation-notes.md','brief.md')]
    numerical_paths += [AREA.parent / 'design.md',AREA.parent / 'challenge.md',
                        AREA.parents[1] / 'dual-tree-cfa-gpu/ordered-fir.py']
    numerical = [h.ref(v) for v in sorted(set(numerical_paths))]
    h.save(out / 'numerical-dependencies.json',numerical)
    fields,env,removed = r.r.standard_environment()
    build = r.folder('build',a.build_iteration)
    bc = r.read(build / 'completion.json')
    r.f.terminal_clean(build / ('cached-recovery/process.json' if bc['cached_recovery_used'] else 'process.json'))
    exe = r.read(build / 'executable.json')
    rust = r.read(build / 'rust-sources.json')
    h.check_refs(rust + [exe])
    null = r.folder('null',a.null_iteration)
    r.f.terminal_clean(null / 'process.json')
    nc = r.read(null / 'completion.json')
    assert nc['status'] == 'COMPLETE_HELD_CFA_DEVELOPMENT_NULL'
    h.check_refs(nc['reports'])
    prerequisites = [h.ref(build / 'completion.json'),h.ref(null / 'completion.json')]
    if a.stage != 'controls':
        controls = r.folder('controls',a.controls_iteration)
        r.f.terminal_clean(controls / 'process.json')
        cc = r.read(controls / 'completion.json')
        h.check_refs(cc['reports'])
        cr = r.read(controls / 'output/receipt.json')
        assert cr['complete'] and cr['controls_pass']
        controls_sources = r.read(controls / 'numerical-dependencies.json')
        h.check_refs(controls_sources)
        assert controls_sources == numerical, 'current numerical recipe differs from passing controls'
        prerequisites += [h.ref(controls / name) for name in ('completion.json','output/receipt.json')]
        prerequisites.append(h.ref(controls / 'numerical-dependencies.json'))
    if a.stage in ('source149','full299'):
        cost = r.folder('cost16',a.cost_iteration)
        r.f.terminal_clean(cost / 'process.json')
        cc = r.read(cost / 'completion.json')
        h.check_refs(cc['reports'])
        cr = r.read(cost / 'output/receipt.json')
        assert cr['status'] == 'COMPLETE_NATIVE_SPECTRAL_COST16' and cr['complete']
        cost_sources = r.read(cost / 'numerical-dependencies.json')
        h.check_refs(cost_sources)
        assert cost_sources == numerical, 'current numerical recipe differs from measured cost'
        # Conservative practical screen only; root still explicitly releases this stage.
        assert cr['measured_batch_seconds_qpc'] * (7957/16) + cr['finish_seconds_qpc'] < 240
        prerequisites += [h.ref(cost / name) for name in ('completion.json','output/receipt.json')]
        prerequisites.append(h.ref(cost / 'numerical-dependencies.json'))
    if a.stage == 'full299':
        source = r.folder('source149',a.source_iteration)
        r.f.terminal_clean(source / 'process.json')
        sc = r.read(source / 'completion.json')
        h.check_refs(sc['reports'])
        sr = r.read(source / 'output/receipt.json')
        assert sr['status'] == 'COMPLETE_NATIVE_SPECTRAL_SOURCE149' and sr['complete']
        assert sr['source_ids'] == [149] and sr['patch_count'] == 7957 and sr['complete_coverage']
        source_dependencies = r.read(source / 'numerical-dependencies.json')
        h.check_refs(source_dependencies)
        assert source_dependencies == numerical, 'recipe changed since full-source cost'
        prerequisites += [h.ref(source / name) for name in ('completion.json','output/receipt.json','numerical-dependencies.json')]
        prerequisites.append(h.ref(AREA / 'full-release.md'))
    paths = [Path(__file__),AREA / 'run.py',r.HELPER,Path(r.r.__file__),r.r.HELPERS,h.PRIOR,
             h.prior.HELPER,h.b.HARNESS,AREA / 'spectral-operator.py',AREA / 'stream.py',
             AREA / 'controls.py',AREA / 'controls-protocol.md',AREA / 'api.md',
             AREA / 'implementation-notes.md',AREA / 'brief.md',AREA.parent / 'design.md',
             AREA.parent / 'challenge.md',r.DEVELOPMENT]
    bindings = [h.ref(v) for v in paths]
    h.save(out / 'source-bindings.json',bindings)
    h.save(out / 'prerequisite-bindings.json',prerequisites)
    for path in paths:
        if path.parent == AREA:
            (out / (path.stem + '-executed' + path.suffix)).write_bytes(path.read_bytes())
    command = [sys.executable,'-B','-X','faulthandler',str(AREA / ('controls.py' if a.stage == 'controls' else 'stream.py'))]
    if a.stage != 'controls':
        command += ['--mode',a.stage]
    command += ['--out',str(out / 'output')]
    if a.stage != 'cost16':
        command += ['--renderer-binding',str(build / 'executable.json'),'--development-receipt',str(r.DEVELOPMENT)]
    limits = {'controls':(300,1200,12,10),'cost16':(180,720,12,10),
              'source149':(300,1200,16,12),'full299':(9000,36000,24,12)}
    wall,cpu,host,gpu = limits[a.stage]
    bounds = dict(wall_seconds=wall,cpu_seconds=cpu,committed_bytes=host << 30,log_bytes=32 << 20)
    h.save(out / 'invocation.json',dict(command=command,bounds=bounds,environment=fields,
        removed_environment=removed,python=h.ref(sys.executable),workers=4,interop_workers=1,
        gpu_budget_bytes=gpu << 30,concurrent_work='No other root numeric, build or GPU job.',
        scope='Fixed native spectral pilot; independent quality failures retained; no photographic gain claim.'))
    h.observed_run(command,env,out,bounds)
    receipt = r.read(out / 'output/receipt.json')
    expected = 'COMPLETE_NATIVE_SPECTRAL_' + a.stage.upper()
    assert receipt['status'] == expected and receipt['complete']
    assert not receipt['quality_claim'] and not receipt['photographic_admission']
    if a.stage != 'controls':
        assert receipt['source_count'] == (299 if a.stage == 'full299' else 1)
        assert receipt['source_ids'] == (list(range(299)) if a.stage == 'full299' else [149])
        assert receipt['patch_count'] == (16 if a.stage == 'cost16' else 7957)
        assert receipt['cache_bytes_and_metadata_unchanged'] and receipt['original_RAW_metadata_unchanged']
        assert receipt['original_noise_draws_per_source_patch'] == 16
        assert not receipt['per_source_rgb'] and not receipt['aligned_frame_volume']
        if a.stage != 'cost16':
            assert receipt['complete_coverage'] and receipt['whole_output']
            assert receipt['final_demosaic_calls'] == 2
    h.check_refs(rust + bindings + numerical + prerequisites + [exe])
    h.save(out / 'completion.json',dict(status=expected,sources_unchanged=True,
        mechanical_controls_pass=receipt.get('controls_pass'),quality_controls_pass=receipt.get('quality_pass'),
        reports=[h.ref(q) for q in sorted((out / 'output').rglob('*')) if q.is_file()],
        photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
