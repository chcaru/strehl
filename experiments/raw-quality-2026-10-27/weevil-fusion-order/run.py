"""Root-only bounded source149 and complete paired fusion-order observation."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
spec = importlib.util.spec_from_file_location('weevil_fusion_root_helpers', AREA.parent / 'insect-blur-phase/full/run.py')
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
h = r.h
CAMPAIGN = r.CAMPAIGN
TEST = 'merge_cmd::weevil_fusion_order::'


def folder(stage, iteration):
    return CAMPAIGN / f'weevil-fusion-order-{stage}-{iteration}'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_artifact(log):
    rows = []
    for line in log.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    assert any(v.get('reason') == 'build-finished' and v.get('success') for v in rows)
    rows = [v for v in rows if v.get('reason') == 'compiler-artifact' and v.get('executable')
            and v.get('target', {}).get('name') == 'strehl_cli' and v.get('profile', {}).get('test')]
    assert len(rows) == 1
    return rows[0]


def sources(out):
    paths = [Path(__file__), AREA / 'implementation.rs', AREA / 'brief.md', AREA / 'adapter-notes.md',
             AREA / 'independent-plan.md', AREA.parent / 'insect-blur-phase/full/run.py',
             r.HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    records = [h.ref(p) for p in paths]
    h.save(out / 'source-bindings.json', records)
    for p in paths:
        if p.parent == AREA:
            (out / (p.stem + '-executed' + p.suffix)).write_bytes(p.read_bytes())
    return records


def terminal_clean(path):
    process = read(path)
    assert process['exit_code'] == 0 and process['error'] is None
    assert process['terminal_job_accounting'] and not process['cleanup_errors']
    assert process['job_accounting']['active_processes'] == 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('build','cost','full','views'))
    p.add_argument('--iteration', type=int, default=1)
    p.add_argument('--build-iteration', type=int, default=1)
    p.add_argument('--cost-iteration', type=int, default=1)
    p.add_argument('--full-iteration', type=int, default=1)
    a = p.parse_args()
    assert min(a.iteration,a.build_iteration,a.cost_iteration,a.full_iteration) > 0
    out = folder(a.stage,a.iteration)
    out.mkdir(parents=True, exist_ok=False)
    fields, env, removed = r.standard_environment()
    bindings = sources(out)
    if a.stage == 'build':
        rust = r.rust_bindings()
        h.save(out / 'rust-sources.json', rust)
        command = ['cargo','test','--locked','--offline','--release','-p','strehl-cli','--lib','--no-run',
                   '--features',r.FEATURES,'--jobs','4','--message-format=json-render-diagnostics']
        env.update(CARGO_INCREMENTAL='0', CARGO_BUILD_JOBS='4')
        bounds = dict(wall_seconds=420,cpu_seconds=2400,committed_bytes=24 << 30,log_bytes=64 << 20)
        h.save(out / 'invocation.json',dict(command=command,bounds=bounds,environment=fields,
               build_environment={'CARGO_INCREMENTAL':'0','CARGO_BUILD_JOBS':'4'},removed_environment=removed,
               scope='Fresh test-only adapter build; clean cached recovery conditional on successful Cargo exit plus owned descendant timeout. No performance claim.'))
        recovered = False
        try:
            h.observed_run(command,env,out,bounds)
        except AssertionError:
            result = read(out / 'process.json')
            # The preceding phase build commissioned this narrow recovery.
            # Do not recover compiler failures or kill-interrupted compilation.
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
            h.save(recovery / 'input-artifact.json',before)
            h.observed_run(command,env,recovery,dict(bounds,wall_seconds=120,cpu_seconds=480))
            after = build_artifact((recovery / 'process.log').read_text(encoding='utf-8'))
            assert after['fresh'] is True and h.ref(after['executable']) == before
            recovered = True
        log = (out / 'process.log').read_text(encoding='utf-8')
        artifact = build_artifact(log)
        assert 'Compiling strehl-cli' in log and artifact['fresh'] is False
        h.check_refs(rust + bindings)
        exe = out / 'strehl-cli-tests.exe'
        original = h.ref(artifact['executable'])
        shutil.copyfile(original['path'],exe)
        copied = h.ref(exe)
        assert (copied['sha256'],copied['bytes']) == (original['sha256'],original['bytes'])
        h.save(out / 'executable.json',copied)
        h.save(out / 'completion.json',dict(status='TEST_BUILD_BOUND',sources_unchanged=True,
               compilation_job_clean=not recovered,cached_recovery_used=recovered,
               original_artifact=original,executable=copied,photographic_improvement_claimed=False))
        return
    if a.stage == 'views':
        full = folder('full',a.full_iteration)
        terminal_clean(full / 'process.json')
        completion = read(full / 'completion.json')
        h.check_refs(completion['reports'])
        view_bindings = bindings + [h.ref(AREA / 'views.py'), h.ref(full / 'completion.json')]
        h.save(out / 'views-bindings.json',view_bindings)
        command = [sys.executable,'-B','-X','faulthandler',str(AREA / 'views.py'),
                   '--render',str(full / 'output'),'--out',str(out / 'output')]
        bounds = dict(wall_seconds=300,cpu_seconds=1200,committed_bytes=6 << 30,log_bytes=16 << 20)
        h.save(out / 'invocation.json',dict(command=command,bounds=bounds,environment=fields,removed_environment=removed))
        h.observed_run(command,env,out,bounds)
        h.check_refs(view_bindings)
        view = read(out / 'output/views.json')
        assert view['complete'] and not view['quality_claim'] and not view['photographic_admission']
        h.save(out / 'completion.json',dict(status=view['status'],reports=[h.ref(q) for q in sorted((out / 'output').rglob('*')) if q.is_file()],photographic_improvement_claimed=False))
        return
    build = folder('build',a.build_iteration)
    build_complete = read(build / 'completion.json')
    terminal_clean(build / ('cached-recovery/process.json' if build_complete['cached_recovery_used'] else 'process.json'))
    exe = read(build / 'executable.json')
    rust = read(build / 'rust-sources.json')
    h.check_refs(rust + [exe])
    controls = CAMPAIGN / 'weevil-fusion-order-controls-1'
    terminal_clean(controls / 'process.json')
    controls_complete = read(controls / 'completion.json')
    h.check_refs(controls_complete['reports'])
    comparison = read(controls / 'comparison.json')
    assert comparison['unchanged_full_screen_except_writer_path']
    h.check_refs([comparison['previous_screen'], comparison['current_screen']])
    prerequisites = [h.ref(controls / name) for name in ('process.json','completion.json','comparison.json')]
    if a.stage == 'full':
        cost = folder('cost',a.cost_iteration)
        terminal_clean(cost / 'process.json')
        complete = read(cost / 'completion.json')
        h.check_refs(complete['reports'])
        cost_receipt = read(cost / 'output/receipt.json')
        assert cost_receipt['status'] == 'COMPLETE_WEEVIL_FUSION_ORDER_SOURCE149_CHECKPOINT'
        assert cost_receipt['test_executable']['sha256'] == exe['sha256']
        assert cost_receipt['configuration']['expected_test_executable_sha256'] == exe['sha256']
        prerequisites.extend(h.ref(cost / name) for name in ('process.json','completion.json','output/receipt.json'))
    h.save(out / 'prerequisite-bindings.json', prerequisites)
    baseline = ROOT / 'outputs/raw-quality-2026-10-26'
    config = dict(schema=1,phase=a.stage,out_dir=str(out / 'output'),expected_test_executable_sha256=exe['sha256'],
                  input_order=h.ref(r.ORDER),warp_map=h.ref(r.MAP),
                  held_rgb16=h.ref(baseline / 'weevil-107-ca-off/stack-master.tiff'),
                  held_linear=h.ref(baseline / 'weevil-107-ca-off/linear-master.tiff'),
                  held_sensor=h.ref(baseline / 'weevil-107-sensor-ca-off/sensor-master.tiff'),
                  held_sensor_sidecar=h.ref(baseline / 'weevil-107-sensor-ca-off/sensor-master.tiff.json'))
    h.save(out / 'config.json',config)
    fields.update(STREHL_WEEVIL_FUSION_ORDER_CONFIG=str(out / 'config.json'),STREHL_WARPMAP=str(r.MAP),
                  STREHL_ALIGN='1',STREHL_FIX_CA='off',STREHL_DEFECT='off',STREHL_FINE_SUPPORT='off',
                  STREHL_TEMPORAL_ENERGY='off',STREHL_SPATIAL_NOISE_FLOOR='off',STREHL_PYRAMID_WORKERS='4',
                  STREHL_PROBE_GATHER='green',STREHL_GPU_GATHER='off',STREHL_DIRECT_PLANES='off',
                  STREHL_FULLRES_GATHER='1',STREHL_GPU_GATHER_LOG='off',STREHL_WARP_WRITEBACK='parallel')
    env.update(fields)
    command = [exe['path'],TEST + ('source149_checkpoint' if a.stage == 'cost' else 'complete299_pair'),
               '--ignored','--exact','--nocapture','--test-threads=1']
    bounds = dict(wall_seconds=300 if a.stage == 'cost' else 2400,cpu_seconds=1200 if a.stage == 'cost' else 9600,
                  committed_bytes=(12 if a.stage == 'cost' else 24) << 30,log_bytes=32 << 20)
    h.save(out / 'invocation.json',dict(command=command,bounds=bounds,environment=fields,removed_environment=removed,
           executable=exe,config=h.ref(out / 'config.json'),workers=4,concurrent_work='No other root numeric/RAW/GPU job.',
           scope='Unchanged non-native twelve-plane diagnostic; geometry/focus/development held. No quality claim.'))
    h.observed_run(command,env,out,bounds)
    receipt = read(out / 'output/receipt.json')
    expected = 'COMPLETE_WEEVIL_FUSION_ORDER_SOURCE149_CHECKPOINT' if a.stage == 'cost' else 'COMPLETE299_WEEVIL_FUSION_ORDER_PAIR'
    assert receipt['status'] == expected and not receipt['quality_claim'] and not receipt['photographic_admission']
    assert receipt['complete'] and receipt['source_count'] == receipt['native_decode_count'] == (1 if a.stage == 'cost' else 299)
    assert receipt['indices'] == ([149] if a.stage == 'cost' else list(range(299)))
    assert receipt['known4_after_finish_exact'] and receipt['admission_exact'] and receipt['writer_camera_path_parity_exact']
    assert receipt['all299_original_bytes_and_metadata_unchanged'] and receipt['all_bound_inputs_unchanged']
    h.check_refs(rust + bindings + prerequisites + [exe])
    h.save(out / 'completion.json',dict(status=expected,sources_unchanged=True,
           reports=[h.ref(q) for q in sorted((out / 'output').rglob('*')) if q.is_file()],photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
