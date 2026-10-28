"""Root-only QPC timing repair; identical complete source149/0 measurements."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
import time

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
HELPERS = AREA.parent / 'insect-placement-observer/run.py'
spec = importlib.util.spec_from_file_location('direct_cfa_precise_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=int, default=1)
    args = parser.parse_args()
    assert args.iteration > 0
    clock = time.get_clock_info('perf_counter')
    assert clock.monotonic and not clock.adjustable and clock.resolution <= 1e-6
    control = CAMPAIGN / 'direct-cfa-forward-controls-2'
    old_cost = CAMPAIGN / 'direct-cfa-forward-cost-1'
    for previous in (control, old_cost):
        completion = json.loads((previous / 'completion.json').read_text())
        h.check_refs(completion['reports'])
        h.check_refs(json.loads((previous / 'source-bindings.json').read_text()))
    out = CAMPAIGN / f'direct-cfa-forward-cost-precise-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    sources = [h.ref(AREA / name) for name in
               ('run-cost-precise.py', 'cost-precise.py', 'cost-precise-notes.md',
                'cost.py', 'cost-notes.md', 'cost-brief.md', 'measurement-gpu.py')]
    sources += [h.ref(path) for path in
                (AREA.parent / 'joint-cfa-local-fit/band-residual/sensor-operator.py',
                 AREA.parent / 'dual-tree-cfa-gpu/ordered-fir.py', HELPERS,
                 h.PRIOR, h.prior.HELPER, h.b.HARNESS,
                 control / 'completion.json', control / 'source-bindings.json',
                 old_cost / 'completion.json', old_cost / 'source-bindings.json',
                 old_cost / 'output/receipt.json',
                 ROOT / 'outputs/raw-quality-2026-10-26/weevil-107-baseline/alignment.txt',
                 ROOT / 'outputs/raw-quality-2026-10-26/weevil-107-baseline/input-order.json')]
    h.save(out / 'source-bindings.json', sources)
    command = [sys.executable, '-B', '-X', 'faulthandler',
               str(AREA / 'cost-precise.py'), '--out', str(out / 'output')]
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  CUBLAS_WORKSPACE_CONFIG=':4096:8')
    env, removed = h.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=8 << 30,
                  log_bytes=16 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds,
         environment=fields, removed_environment=removed, python=h.ref(sys.executable),
         authoritative_wall_clock=vars(clock),
         scope='QPC timing-only repair; exact preceding complete geometry calls. No RAW decode, fit or quality claim.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    receipt = json.loads((out / 'output/receipt.json').read_text())
    assert receipt['status'] == 'COMPLETE_DIRECT_CFA_FORWARD_COST'
    assert receipt['all_passes_completed'] and receipt['mechanical_pass']
    assert receipt['quality_claim'] is False
    reports = [h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()]
    h.save(out / 'completion.json', dict(reports=reports, cost_passes_complete=True,
         authoritative_wall_clock=vars(clock), source_bindings_unchanged=True,
         photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
