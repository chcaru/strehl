"""Root-owned bounded build, native null, controls and saved final-field jobs.

Source prepared while native spectral full299 is running. Execution is forbidden
until that job reaches a clean terminal state and root releases these stages.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

AREA = Path(__file__).resolve().parent
SPECTRAL = AREA.parents[1] / 'native-spectral-fusion/pilot'
spec = importlib.util.spec_from_file_location('final_color_root_helpers', SPECTRAL / 'run.py')
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
h = r.h
CAMPAIGN = r.CAMPAIGN
EXAMPLE = 'normalized-camera-develop'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def folder(stage, iteration):
    return CAMPAIGN / f'final-cfa-color-{stage}-{iteration}'


def artifact(log):
    rows = []
    for line in log.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    assert any(v.get('reason') == 'build-finished' and v.get('success') for v in rows)
    found = [v for v in rows if v.get('reason') == 'compiler-artifact'
             and v.get('executable') and v.get('target', {}).get('name') == EXAMPLE]
    assert len(found) == 1
    return found[0]


def common_bindings():
    paths = [Path(__file__), SPECTRAL / 'run.py', r.HELPER, Path(r.r.__file__),
             r.r.HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    return [h.ref(v) for v in paths]


def numerical_bindings():
    names = ('spectral-completion.py', 'controls.py', 'saved-field.py',
             'normalized-camera-develop.rs', 'api.md', 'implementation-notes.md',
             'controls-protocol.md', 'delivery-notes.md', 'brief.md')
    paths = [AREA / v for v in names]
    paths += [AREA.parent / v for v in ('design.md', 'challenge.md', 'prior-photo-constraints.md')]
    paths.append(AREA.parents[1] / 'dual-tree-cfa-gpu/ordered-fir.py')
    return [h.ref(v) for v in sorted(paths)]


def finished_spectral_full(iteration):
    full = r.folder('full299', iteration)
    r.f.terminal_clean(full / 'process.json')
    completion = read(full / 'completion.json')
    assert completion['status'] == 'COMPLETE_NATIVE_SPECTRAL_FULL299'
    assert completion['sources_unchanged']
    report = read(full / 'output/receipt.json')
    assert report['complete'] and report['whole_output'] and report['complete_coverage']
    assert report['source_count'] == 299 and report['source_ids'] == list(range(299))
    assert report['cache_bytes_and_metadata_unchanged'] and report['original_RAW_metadata_unchanged']
    # Full output hashes are checked again before an actual saved-field job.
    return full, completion


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('build', 'null', 'controls', 'cost', 'candidate', 'uniform'))
    p.add_argument('--iteration', type=int, default=1)
    p.add_argument('--build-iteration', type=int, default=1)
    p.add_argument('--null-iteration', type=int, default=1)
    p.add_argument('--controls-iteration', type=int, default=1)
    p.add_argument('--cost-iteration', type=int, default=1)
    p.add_argument('--full-iteration', type=int, default=1)
    a = p.parse_args()
    assert min(a.iteration, a.build_iteration, a.null_iteration, a.controls_iteration,
               a.cost_iteration, a.full_iteration) > 0
    # Prevent accidental source-preparation execution during the frozen job.
    full, full_completion = finished_spectral_full(a.full_iteration)
    out = folder(a.stage, a.iteration)
    out.mkdir(parents=True, exist_ok=False)
    fields, env, removed = r.r.standard_environment()
    bindings = common_bindings()
    h.save(out / 'source-bindings.json', bindings)
    (out / 'run-executed.py').write_bytes(Path(__file__).read_bytes())
    prerequisites = [h.ref(full / name) for name in ('process.json', 'completion.json', 'output/receipt.json')]

    if a.stage == 'build':
        rust = r.r.rust_bindings()
        h.save(out / 'rust-sources.json', rust)
        source = h.ref(AREA / 'normalized-camera-develop.rs')
        bindings += [source]
        h.save(out / 'writer-source.json', source)
        command = ['cargo', 'build', '--locked', '--offline', '--release', '-p', 'strehl-cli',
                   '--example', EXAMPLE, '--features', r.r.FEATURES, '--jobs', '4',
                   '--message-format=json-render-diagnostics']
        env.update(CARGO_INCREMENTAL='0', CARGO_BUILD_JOBS='4')
        bounds = dict(wall_seconds=420, cpu_seconds=1680, committed_bytes=24 << 30, log_bytes=64 << 20)
        h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
            removed_environment=removed, build_environment={'CARGO_INCREMENTAL':'0', 'CARGO_BUILD_JOBS':'4'},
            scope='Fresh normalized-camera writer; no completion or photographic claim.'))
        recovered = False
        try:
            h.observed_run(command, env, out, bounds)
        except AssertionError:
            result = read(out / 'process.json')
            assert result['exit_code'] == 0 and result['error'] == "ValueError('child wall bound')"
            assert result['direct_exit_observed'] and result['pipe_eof_observed']
            assert result['terminal_job_accounting'] and not result['cleanup_errors']
            log = (out / 'process.log').read_text(encoding='utf-8')
            built = artifact(log)
            assert 'Compiling strehl-cli' in log and built['fresh'] is False
            h.check_refs(rust + bindings)
            before = h.ref(built['executable'])
            recovery = out / 'cached-recovery'
            recovery.mkdir()
            h.save(recovery / 'input-artifact.json', before)
            h.observed_run(command, env, recovery, dict(bounds, wall_seconds=120, cpu_seconds=480))
            cached = artifact((recovery / 'process.log').read_text(encoding='utf-8'))
            assert cached['fresh'] is True and h.ref(cached['executable']) == before
            recovered = True
        log = (out / 'process.log').read_text(encoding='utf-8')
        built = artifact(log)
        assert 'Compiling strehl-cli' in log and built['fresh'] is False
        h.check_refs(rust + bindings + prerequisites)
        original = h.ref(built['executable'])
        exe = out / (EXAMPLE + '.exe')
        shutil.copyfile(original['path'], exe)
        copied = h.ref(exe)
        assert (copied['sha256'], copied['bytes']) == (original['sha256'], original['bytes'])
        h.save(out / 'executable.json', copied)
        h.save(out / 'completion.json', dict(status='NORMALIZED_CAMERA_DEVELOPER_BUILD_BOUND',
            sources_unchanged=True, compilation_job_clean=not recovered, cached_recovery_used=recovered,
            original_artifact=original, executable=copied, photographic_improvement_claimed=False))
        return

    build = folder('build', a.build_iteration)
    bc = read(build / 'completion.json')
    assert bc['status'] == 'NORMALIZED_CAMERA_DEVELOPER_BUILD_BOUND'
    r.f.terminal_clean(build / ('cached-recovery/process.json' if bc['cached_recovery_used'] else 'process.json'))
    rust = read(build / 'rust-sources.json')
    exe = read(build / 'executable.json')
    h.check_refs(rust + [exe])
    prerequisites += [h.ref(build / name) for name in ('completion.json', 'executable.json', 'rust-sources.json')]
    if a.stage == 'null':
        source = r.folder('null', 1)
        r.f.terminal_clean(source / 'process.json')
        h.check_refs(read(source / 'completion.json')['reports'])
        receipt = read(source / 'output/receipt.json')
        assert receipt['status'] == 'COMPLETE_NATIVE_CFA_DEVELOPMENT' and receipt['complete']
        assert receipt['demosaic_stages'] == 1
        camera = receipt['camera_rgb']
        assert camera['sha256'] == '42429be10904e1c81a95e83fc0d1fed22a1ced1eb211c9d449a20cb0cef2a7cf'
        baseline = r.ROOT / 'outputs/raw-quality-2026-10-26/weevil-107-ca-off'
        config = dict(schema=1, camera_rgb=camera, source_receipt=h.ref(source / 'output/receipt.json'),
            width=6896, height=4596, active_origin_xy=[68,46], units='normalized-camera-RGB',
            development_receipt=h.ref(r.DEVELOPMENT), expected_executable_sha256=exe['sha256'],
            out_dir=str(out / 'output'), parity_reference=dict(rgb16=h.ref(baseline / 'stack-master.tiff'),
                linear_rgb32=h.ref(baseline / 'linear-master.tiff')))
        h.save(out / 'config.json', config)
        prerequisites += [h.ref(source / 'completion.json'), config['source_receipt'], camera,
                          config['development_receipt'], *config['parity_reference'].values()]
        command = [exe['path'], str(out / 'config.json')]
        bounds = dict(wall_seconds=180, cpu_seconds=720, committed_bytes=8 << 30, log_bytes=16 << 20)
    else:
        numerical = numerical_bindings()
        h.save(out / 'numerical-dependencies.json', numerical)
        bindings += numerical
        for path in AREA.glob('*.py'):
            if not path.name.startswith('run'):
                (out / (path.stem + '-executed.py')).write_bytes(path.read_bytes())
        null = folder('null', a.null_iteration)
        r.f.terminal_clean(null / 'process.json')
        nc = read(null / 'completion.json')
        assert nc['status'] == 'COMPLETE_HELD_NORMALIZED_CAMERA_NULL'
        h.check_refs(nc['reports'])
        prerequisites += [h.ref(null / name) for name in ('completion.json', 'output/receipt.json')]
        if a.stage == 'controls':
            command = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / 'controls.py'),
                '--out', str(out / 'output'), '--renderer-binding', str(build / 'executable.json'),
                '--development-receipt', str(r.DEVELOPMENT)]
            bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=12 << 30, log_bytes=16 << 20)
        else:
            controls = folder('controls', a.controls_iteration)
            r.f.terminal_clean(controls / 'process.json')
            cc = read(controls / 'completion.json')
            h.check_refs(cc['reports'])
            cr = read(controls / 'output/receipt.json')
            assert cr['complete'] and cr['controls_pass']
            assert read(controls / 'numerical-dependencies.json') == numerical
            prerequisites += [h.ref(controls / name) for name in ('completion.json', 'output/receipt.json', 'numerical-dependencies.json')]
            if a.stage in ('candidate', 'uniform'):
                cost = folder('cost', a.cost_iteration)
                r.f.terminal_clean(cost / 'process.json')
                cost_complete = read(cost / 'completion.json')
                assert cost_complete['status'] == 'COMPLETE_SAVED_FINAL_CFA_COLOR'
                h.check_refs(cost_complete['reports'])
                assert read(cost / 'numerical-dependencies.json') == numerical
                prerequisites += [h.ref(cost / name) for name in ('completion.json', 'output/receipt.json', 'numerical-dependencies.json')]
                h.check_refs(full_completion['reports'])
            # Cost uses the exact held native field at the same complete dimensions.
            # Candidate/uniform use their actual full299 MHC receipts and CFA fields.
            source = (r.folder('null', 1) / 'output/receipt.json' if a.stage == 'cost'
                      else full / ('output/' + a.stage + '/native/receipt.json'))
            prerequisites.append(h.ref(source))
            command = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / 'saved-field.py'),
                '--input-receipt', str(source), '--renderer-binding', str(build / 'executable.json'),
                '--null-receipt', str(null / 'output/receipt.json'), '--expected-completion-sha',
                h.ref(AREA / 'spectral-completion.py')['sha256'], '--out', str(out / 'output')]
            bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=16 << 30, log_bytes=16 << 20)

    h.save(out / 'prerequisite-bindings.json', prerequisites)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
        removed_environment=removed, workers=4, interop_workers=1, gpu_budget_bytes=8 << 30,
        concurrent_work='No other root numerical, RAW, GPU or build job.',
        scope='Saved final fields and exact held development; no photographic gain claim.'))
    h.observed_run(command, env, out, bounds)
    report = read(out / 'output/receipt.json')
    assert report['complete'] and not report['quality_claim'] and not report['photographic_admission']
    if a.stage == 'null':
        assert report['status'] == 'COMPLETE_NORMALIZED_CAMERA_NATIVE_DEVELOPMENT'
        assert report['writer_completion_stages'] == report['writer_demosaic_calls'] == 0
        assert report['signed_camera_copy_bit_exact'] and not report['normalization_applied']
        assert all(report['parity'][k] for k in ('rgb16_pixel_exact', 'linear_pixel_exact',
                                               'rgb16_material_exact', 'linear_material_exact'))
        status = 'COMPLETE_HELD_NORMALIZED_CAMERA_NULL'
    elif a.stage == 'controls':
        assert report['status'] == 'COMPLETE_FINAL_CFA_COLOR_CONTROLS'
        assert report['saved_case_count'] == 10 and report['delivered_arm_count'] == 20
        assert report['inputs_unchanged'] and report['original_RAW_reads'] == 0
        status = report['status']
    else:
        assert report['status'] == 'COMPLETE_SAVED_FINAL_CFA_COLOR'
        assert report['native_dimensions'] == [6896,4596] and report['active_origin_xy'] == [68,46]
        assert report['inputs_unchanged'] and report['entire_output'] and report['development_unchanged']
        assert report['final_completion_stages'] == 1 and report['writer_completion_stages'] == report['RAW_reads'] == 0
        status = report['status']
    h.check_refs(rust + bindings + prerequisites + [exe])
    h.save(out / 'completion.json', dict(status=status, sources_unchanged=True,
        mechanical_controls_pass=report.get('controls_pass'), quality_controls_pass=report.get('quality_pass'),
        reports=[h.ref(q) for q in sorted((out / 'output').rglob('*')) if q.is_file()],
        photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
