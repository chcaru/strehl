"""Root-only four-iteration full299 level-balanced photographic pilot."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import time

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
HELPERS = AREA.parent / 'insect-placement-observer/run.py'
spec = importlib.util.spec_from_file_location('level_balanced_photo_root_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=int, default=1)
    parser.add_argument('--controls-iteration', type=int, default=1)
    args = parser.parse_args()
    assert args.iteration > 0 and args.controls_iteration > 0
    control = CAMPAIGN / f'direct-cfa-level-balanced-controls-{args.controls_iteration}'
    completed = json.loads((control / 'completion.json').read_text())
    assert completed['controls_pass'] and completed['source_bindings_unchanged']
    h.check_refs(completed['reports'])
    h.check_refs(json.loads((control / 'source-bindings.json').read_text()))
    build = CAMPAIGN / 'direct-cfa-streamed-delivery-build-4'
    delivery_controls = CAMPAIGN / 'direct-cfa-streamed-delivery-controls-2'
    development = delivery_controls / 'output/held-development.json'
    for directory, key in ((build, 'compiled_new_renderer'),
                           (delivery_controls, 'delivery_mechanics_pass')):
        completion = json.loads((directory / 'completion.json').read_text())
        assert completion[key]
        h.check_refs(completion['reports'])
        h.check_refs(json.loads((directory / 'source-bindings.json').read_text()))
    assert shutil.disk_usage(CAMPAIGN).free >= 12 << 30
    paths = [AREA / name for name in ('run-photograph.py', 'photograph.py', 'views.py',
             'brief.md', 'implementation-notes.md', 'bands-gpu.py', 'normal-operator.py', 'solver.py')]
    paths += [AREA.parent / name for name in (
        'direct-cfa-streamed-normal/bands-gpu.py',
        'direct-cfa-streamed-normal/normal-operator.py',
        'direct-cfa-streamed-normal/solver.py',
        'direct-cfa-streamed-normal/measurement-paired.py',
        'direct-cfa-streamed-normal/delivery.py',
        'direct-cfa-streamed-normal/full-photograph.py',
        'direct-cfa-streamed-normal/full-photograph-views.py',
        'weevil-fine-comparator/photo-review/mapped-witnesses.json',
        'weevil-fine-comparator/photo-review/crop-export-receipt.json',
        'direct-cfa-forward-gpu/measurement-gpu.py',
        'joint-cfa-local-fit/band-residual/sensor-operator.py')]
    paths += [CAMPAIGN / 'direct-cfa-streamed-originals-1/output/receipt.json',
              CAMPAIGN / 'direct-cfa-forward-cost-precise-1/output/geometry.json',
              ROOT / 'outputs/raw-quality-2026-10-26/weevil-107-baseline/input-order.json',
              ROOT / 'outputs/raw-quality-2026-10-26/weevil-107-baseline/alignment.txt',
              ROOT / 'crates/strehl-cli/examples/direct-rgb-develop.rs',
              ROOT / 'experiments/raw-quality-2026-10-26/photo-review/baseline-witnesses.json',
              CAMPAIGN / 'direct-cfa-streamed-full-views-2/output/receipt.json',
              build / 'executable.json', development,
              control / 'completion.json', control / 'output/receipt.json',
              HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    sources = [h.ref(path) for path in paths]
    out = CAMPAIGN / f'direct-cfa-level-balanced-photograph-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    h.save(out / 'source-bindings.json', sources)
    for path in paths:
        if path.parent == AREA:
            (out / (path.stem + '-executed' + path.suffix)).write_bytes(path.read_bytes())
    command = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / 'photograph.py'),
               '--out', str(out / 'output'), '--renderer-binding', str(build / 'executable.json'),
               '--development-receipt', str(development)]
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  RAYON_NUM_THREADS='4', CUBLAS_WORKSPACE_CONFIG=':4096:8')
    env, removed = h.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=1500, cpu_seconds=6000, committed_bytes=16 << 30,
                  log_bytes=32 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds,
         environment=fields, removed_environment=removed, python=h.ref(sys.executable),
         clock=vars(time.get_clock_info('perf_counter')), workers=4, cuda_budget_bytes=8 << 30,
         concurrent_work='No competing root-scheduled GPU or numerical job; source/research review only.',
         scope='One changed objective; all299 originals; complete checkpoints1/2/4; no automatic extension.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    receipt = json.loads((out / 'output/receipt.json').read_text())
    assert receipt['status'] == 'COMPLETE_LEVEL_BALANCED_FULL299_PILOT'
    assert receipt['complete'] and receipt['source_count'] == 299
    assert receipt['quality_claim'] is False and receipt['photographic_admission'] is False
    assert receipt['maximum_iterations'] == receipt['iterations'] == 4
    assert receipt['scheduled_checkpoints'] == [1, 2, 4] and receipt['no_automatic_extension']
    assert receipt['source_bindings_unchanged'] and receipt['all_sources_consumed']
    assert receipt['cache_bytes_and_metadata_unchanged'] and receipt['original_RAW_metadata_unchanged']
    assert receipt['final_checkpoint_latent_exact']
    assert [c['iteration'] for c in receipt['checkpoints']] == [1, 2, 4]
    for checkpoint in receipt['checkpoints']:
        saved_checkpoint = out / 'output/checkpoints' / f"iteration-{checkpoint['iteration']:02d}" / 'receipt.json'
        assert json.loads(saved_checkpoint.read_text()) == checkpoint
        assert checkpoint['status'] == 'COMPLETE_LEVEL_BALANCED_CHECKPOINT' and checkpoint['complete']
        assert checkpoint['source_count'] == 299 and checkpoint['entire_output']
        assert checkpoint['quality_claim'] is False and checkpoint['photographic_admission'] is False
        h.check_refs([checkpoint[k] for k in ('latent', 'latent_metadata', 'camera_rgb',
                     'delivery', 'rgb16', 'native_development', 'views')])
    reports = [h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()]
    h.save(out / 'completion.json', dict(reports=reports, complete_photograph=True,
         source_bindings_unchanged=True, photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
