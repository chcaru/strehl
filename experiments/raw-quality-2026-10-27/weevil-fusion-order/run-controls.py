"""Root-owned unchanged predecessor controls under current CPU/direct-off flags."""
from pathlib import Path
import copy
import importlib.util
import json
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
spec = importlib.util.spec_from_file_location('fusion_order_control_helpers', AREA.parent / 'insect-blur-phase/full/run.py')
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
h = r.h


def main():
    out = r.CAMPAIGN / 'weevil-fusion-order-controls-1'
    out.mkdir(parents=True, exist_ok=False)
    build = r.folder('build', 3)
    exe = json.loads((build / 'executable.json').read_text(encoding='utf-8'))
    build_sources = json.loads((build / 'rust-sources.json').read_text(encoding='utf-8'))
    h.check_refs(build_sources + [exe])
    old = ROOT / 'experiments/phase-packed-rgb/screen-2/output/screen.json'
    bindings = [h.ref(__file__), h.ref(AREA / 'brief.md'), h.ref(AREA / 'independent-plan.md'),
                h.ref(old), h.ref(build / 'executable.json'), h.ref(build / 'rust-sources.json')]
    h.save(out / 'bindings.json', dict(sources=bindings, build_sources=build_sources, executable=exe))
    (out / 'run-controls-executed.py').write_bytes(Path(__file__).read_bytes())
    fields, env, removed = r.standard_environment()
    fields.update(STREHL_PHASE_PACKED_OUT=str(out / 'output'), STREHL_FULLRES_GATHER='1',
                  STREHL_DIRECT_PLANES='off', STREHL_PROBE_GATHER='green', STREHL_GPU_GATHER='off',
                  STREHL_DEFECT='off', STREHL_WARP_WRITEBACK='parallel', STREHL_FIX_CA='off',
                  STREHL_GPU_GATHER_LOG='off', STREHL_WARPMAP=str(out / 'unused-isolated-warp.txt'))
    env.update(fields)
    command = [exe['path'], 'merge_cmd::phase_packed_rgb::independent_controls::', '--nocapture', '--test-threads=1']
    bounds = dict(wall_seconds=120, cpu_seconds=480, committed_bytes=6 << 30, log_bytes=32 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
           removed_environment=removed, executable=exe,
           scope='Unchanged four predecessor controls using current CPU/direct-off flags. Not a photographic gain.'))
    h.observed_run(command, env, out, bounds)
    assert '4 passed; 0 failed' in (out / 'process.log').read_text(encoding='utf-8')
    current = json.loads((out / 'output/screen.json').read_text(encoding='utf-8'))
    previous = json.loads(old.read_text(encoding='utf-8'))
    assert len(current['cases']) == 28
    a, b = copy.deepcopy(previous), copy.deepcopy(current)
    a['actual_writer'].pop('tiff')
    b['actual_writer'].pop('tiff')
    h.check_refs(build_sources + bindings + [exe])
    h.save(out / 'comparison.json', dict(unchanged_cases=current['cases'] == previous['cases'],
           unchanged_full_screen_except_writer_path=a == b,
           previous_screen=h.ref(old), current_screen=h.ref(out / 'output/screen.json'),
           historical_flat_chroma_ratio=1.078951, strict_1_05_claim=False,
           co_located_near_fine_far_coarse_commissioned=False,
           photographic_improvement_claimed=False))
    h.save(out / 'completion.json', dict(status='FOUR_UNCHANGED_PREDECESSOR_CONTROLS_COMPLETE',
           passed=4, sources_unchanged=True,
           reports=[h.ref(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'completion.json'],
           photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
