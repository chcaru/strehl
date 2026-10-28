"""Root-owned bounded native developer build and exact held-CFA replay."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
HELPER = AREA.parents[1] / 'weevil-fusion-order/run.py'
spec = importlib.util.spec_from_file_location('spectral_root_helpers', HELPER)
f = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = f
spec.loader.exec_module(f)
h, r = f.h, f.r
CAMPAIGN = r.CAMPAIGN
DEVELOPMENT = CAMPAIGN / 'direct-cfa-streamed-delivery-controls-2/output/held-development.json'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def folder(stage, iteration):
    return CAMPAIGN / f'native-spectral-{stage}-{iteration}'


def build_artifact(log):
    rows = []
    for line in log.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    assert any(v.get('reason') == 'build-finished' and v.get('success') for v in rows)
    rows = [v for v in rows if v.get('reason') == 'compiler-artifact' and v.get('executable')
            and v.get('target', {}).get('name') == 'native-cfa-develop']
    assert len(rows) == 1
    return rows[0]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('build', 'null'))
    p.add_argument('--iteration', type=int, default=1)
    p.add_argument('--build-iteration', type=int, default=1)
    a = p.parse_args()
    assert min(a.iteration, a.build_iteration) > 0
    out = folder(a.stage, a.iteration)
    out.mkdir(parents=True, exist_ok=False)
    fields, env, removed = r.standard_environment()
    paths = [Path(__file__), AREA / 'native-cfa-develop.rs', AREA / 'delivery-notes.md',
             HELPER, Path(r.__file__), r.HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    bindings = [h.ref(v) for v in paths]
    h.save(out / 'source-bindings.json', bindings)
    for path in paths:
        if path.parent == AREA:
            (out / (path.stem + '-executed' + path.suffix)).write_bytes(path.read_bytes())
    if a.stage == 'build':
        rust = r.rust_bindings()
        h.save(out / 'rust-sources.json', rust)
        command = ['cargo', 'build', '--locked', '--offline', '--release', '-p', 'strehl-cli',
                   '--example', 'native-cfa-develop', '--features', r.FEATURES, '--jobs', '4',
                   '--message-format=json-render-diagnostics']
        env.update(CARGO_INCREMENTAL='0', CARGO_BUILD_JOBS='4')
        bounds = dict(wall_seconds=420, cpu_seconds=1680, committed_bytes=24 << 30, log_bytes=64 << 20)
        h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
            removed_environment=removed, build_environment={'CARGO_INCREMENTAL':'0','CARGO_BUILD_JOBS':'4'},
            scope='Fresh standalone final-CFA developer; no source fusion or quality claim.'))
        recovered = False
        try:
            h.observed_run(command, env, out, bounds)
        except AssertionError:
            result = read(out / 'process.json')
            assert result['exit_code'] == 0 and result['error'] == "ValueError('child wall bound')"
            assert result['direct_exit_observed'] and result['pipe_eof_observed']
            assert result['terminal_job_accounting'] and not result['cleanup_errors']
            log = (out / 'process.log').read_text(encoding='utf-8')
            artifact = build_artifact(log)
            assert 'Compiling strehl-cli' in log and artifact['fresh'] is False
            h.check_refs(rust + bindings)
            before = h.ref(artifact['executable'])
            recovery = out / 'cached-recovery'
            recovery.mkdir()
            h.save(recovery / 'input-artifact.json', before)
            h.observed_run(command, env, recovery, dict(bounds, wall_seconds=120, cpu_seconds=480))
            after = build_artifact((recovery / 'process.log').read_text(encoding='utf-8'))
            assert after['fresh'] is True and h.ref(after['executable']) == before
            recovered = True
        artifact = build_artifact((out / 'process.log').read_text(encoding='utf-8'))
        assert artifact['fresh'] is False
        h.check_refs(rust + bindings)
        original = h.ref(artifact['executable'])
        exe = out / 'native-cfa-develop.exe'
        shutil.copyfile(original['path'], exe)
        copied = h.ref(exe)
        assert (copied['sha256'], copied['bytes']) == (original['sha256'], original['bytes'])
        h.save(out / 'executable.json', copied)
        h.save(out / 'completion.json', dict(status='NATIVE_CFA_DEVELOPER_BUILD_BOUND',
            sources_unchanged=True, compilation_job_clean=not recovered, cached_recovery_used=recovered,
            original_artifact=original, executable=copied, photographic_improvement_claimed=False))
        return
    build = folder('build', a.build_iteration)
    bc = read(build / 'completion.json')
    f.terminal_clean(build / ('cached-recovery/process.json' if bc['cached_recovery_used'] else 'process.json'))
    exe = read(build / 'executable.json')
    rust = read(build / 'rust-sources.json')
    h.check_refs(rust + [exe])
    h.check_refs(read(DEVELOPMENT)['source_bindings'])
    full = CAMPAIGN / 'weevil-fusion-order-full-1'
    f.terminal_clean(full / 'process.json')
    complete = read(full / 'completion.json')
    h.check_refs(complete['reports'])
    receipt = read(full / 'output/receipt.json')
    assert receipt['status'] == 'COMPLETE299_WEEVIL_FUSION_ORDER_PAIR'
    cfa = full / 'output/baseline-cfa-dn.f32le'
    assert h.ref(cfa)['sha256'] == '1a442c1638eb8f1b68d31dd502acc670eedf0f35463e864dd5f21ee26d4112b0'
    baseline = ROOT / 'outputs/raw-quality-2026-10-26/weevil-107-ca-off'
    config = dict(schema=1, cfa=h.ref(cfa), width=6896, height=4596, active_origin_xy=[68,46],
        physical_pattern='RGGB', units='black-subtracted-DN', development_receipt=h.ref(DEVELOPMENT),
        expected_executable_sha256=exe['sha256'], out_dir=str(out / 'output'),
        parity_reference=dict(rgb16=h.ref(baseline / 'stack-master.tiff'),
                              linear_rgb32=h.ref(baseline / 'linear-master.tiff')))
    h.save(out / 'config.json', config)
    command = [exe['path'], str(out / 'config.json')]
    bounds = dict(wall_seconds=180, cpu_seconds=720, committed_bytes=8 << 30, log_bytes=16 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
        removed_environment=removed, config=h.ref(out / 'config.json'), executable=exe, workers=4,
        concurrent_work='No other root numerical or GPU job.', scope='Exact held signed-CFA development null.'))
    h.observed_run(command, env, out, bounds)
    report = read(out / 'output/receipt.json')
    assert report['complete'] and report['status'] == 'COMPLETE_NATIVE_CFA_DEVELOPMENT'
    assert report['demosaic_stages'] == 1 and report['source_demosaic_calls'] == report['remosaic_calls'] == 0
    assert all(report['parity'][k] for k in ('rgb16_pixel_exact','linear_pixel_exact','rgb16_material_exact','linear_material_exact'))
    h.check_refs(rust + bindings + [exe])
    h.save(out / 'completion.json', dict(status='COMPLETE_HELD_CFA_DEVELOPMENT_NULL',
        reports=[h.ref(q) for q in sorted((out / 'output').rglob('*')) if q.is_file()],
        sources_unchanged=True, photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
