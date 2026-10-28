"""Root-only complete all299 original-CFA photographic observation."""
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
spec = importlib.util.spec_from_file_location('full_photograph_root_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=int, default=1)
    args = parser.parse_args()
    assert args.iteration > 0
    cost_dir = CAMPAIGN / 'direct-cfa-streamed-full-cost-1'
    h.check_refs(json.loads((cost_dir / 'completion.json').read_text())['reports'])
    cost = json.loads((cost_dir / 'output/receipt.json').read_text())
    assert cost['status'] == 'COMPLETE_DIRECT_CFA_WEIGHTED_NORMAL_COST'
    assert cost['all_passes_completed'] and cost['mechanical_pass']
    assert cost['scenario']['within_research_observation_ceiling']
    assert cost['scenario']['total_seconds'] <= cost['scenario']['research_observation_ceiling_seconds'] == 7200
    assert cost['quality_claim'] is False and cost['photographic_admission'] is False
    for name, key in [('direct-cfa-streamed-controls-2', 'mechanical_pass'),
                      ('direct-cfa-streamed-solver-controls-1', 'solver_mechanics_pass'),
                      ('direct-cfa-streamed-delivery-controls-2', 'delivery_mechanics_pass')]:
        previous = CAMPAIGN / name
        completed = json.loads((previous / 'completion.json').read_text())
        assert completed[key]
        h.check_refs(completed['reports'])
        h.check_refs(json.loads((previous / 'source-bindings.json').read_text()))
    build = CAMPAIGN / 'direct-cfa-streamed-delivery-build-4'
    development = CAMPAIGN / 'direct-cfa-streamed-delivery-controls-2/output/held-development.json'
    built = json.loads((build / 'completion.json').read_text())
    assert built['compiled_new_renderer']
    h.check_refs(built['reports'])
    h.check_refs(json.loads((build / 'source-bindings.json').read_text()))
    assert shutil.disk_usage(CAMPAIGN).free >= 20 << 30
    out = CAMPAIGN / f'direct-cfa-streamed-full-photograph-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    paths = [AREA / name for name in ('run-full-photograph.py', 'full-photograph.py',
             'full-photograph-notes.md', 'full-photograph-brief.md', 'bands-gpu.py',
             'normal-operator.py', 'solver.py', 'measurement-paired.py', 'delivery.py')]
    paths += [AREA.parent / name for name in
              ('direct-cfa-forward-gpu/measurement-gpu.py',
               'joint-cfa-local-fit/band-residual/sensor-operator.py')]
    paths += [CAMPAIGN / 'direct-cfa-streamed-originals-1/output/receipt.json',
              CAMPAIGN / 'direct-cfa-streamed-full-cost-1/output/receipt.json',
              CAMPAIGN / 'direct-cfa-forward-cost-precise-1/output/geometry.json',
              ROOT / 'crates/strehl-cli/examples/direct-rgb-develop.rs',
              build / 'executable.json', development, HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    sources = [h.ref(path) for path in paths]
    h.save(out / 'source-bindings.json', sources)
    command = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / 'full-photograph.py'),
               '--out', str(out / 'output'), '--renderer-binding', str(build / 'executable.json'),
               '--development-receipt', str(development)]
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  RAYON_NUM_THREADS='4', CUBLAS_WORKSPACE_CONFIG=':4096:8')
    env, removed = h.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=7200, cpu_seconds=28800, committed_bytes=16 << 30, log_bytes=32 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds,
         environment=fields, removed_environment=removed, python=h.ref(sys.executable),
         clock=vars(time.get_clock_info('perf_counter')), workers=4, cuda_budget_bytes=8 << 30,
         concurrent_work='No competing root-scheduled GPU or numerical job; independent source/research reviews only.',
         scope='Complete all299 original-CFA weevil observation; retain numeric refusal and require separate photographic review.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    receipt = json.loads((out / 'output/receipt.json').read_text())
    assert receipt['status'] == 'COMPLETE_DIRECT_CFA_FULL_PHOTOGRAPH'
    assert receipt['complete'] and receipt['source_count'] == 299
    assert receipt['quality_claim'] is False and receipt['photographic_admission'] is False
    reports = [h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()]
    h.save(out / 'completion.json', dict(reports=reports, complete_photograph=True,
         source_bindings_unchanged=True, numerical_convergence=receipt['numeric_converged'],
         photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
