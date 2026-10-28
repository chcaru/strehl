"""Root-only bounded complete original-sensor weighted-normal cost."""
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
spec = importlib.util.spec_from_file_location('weighted_cost_root_helpers', HELPERS)
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
    control = CAMPAIGN / 'direct-cfa-streamed-controls-2'
    completion = json.loads((control / 'completion.json').read_text())
    assert completion['mechanical_pass']
    h.check_refs(completion['reports'])
    h.check_refs(json.loads((control / 'source-bindings.json').read_text()))
    out = CAMPAIGN / f'direct-cfa-streamed-full-cost-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    paths = [AREA / name for name in
             ('run-full-cost.py', 'full-cost.py', 'full-cost-notes.md', 'cost-brief.md',
              'bands-gpu.py', 'normal-operator.py', 'measurement-paired.py')]
    paths += [AREA.parent / name for name in
              ('direct-cfa-forward-gpu/measurement-gpu.py',
               'joint-cfa-local-fit/band-residual/sensor-operator.py')]
    paths += [HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS,
              control / 'completion.json', control / 'source-bindings.json']
    sources = [h.ref(path) for path in paths]
    h.save(out / 'source-bindings.json', sources)
    command = [sys.executable, '-B', '-X', 'faulthandler',
               str(AREA / 'full-cost.py'), '--out', str(out / 'output')]
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  CUBLAS_WORKSPACE_CONFIG=':4096:8')
    env, removed = h.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=8 << 30,
                  log_bytes=16 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds,
         environment=fields, removed_environment=removed, python=h.ref(sys.executable),
         authoritative_wall_clock=vars(clock),
         scope='Complete generated original-u16 source149/0 workload and global weighted normal; no RAW read or fit.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    receipt = json.loads((out / 'output/receipt.json').read_text())
    assert receipt['status'] == 'COMPLETE_DIRECT_CFA_WEIGHTED_NORMAL_COST'
    assert receipt['all_passes_completed'] and receipt['mechanical_pass']
    assert receipt['quality_claim'] is False and receipt['photographic_admission'] is False
    reports = [h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()]
    h.save(out / 'completion.json', dict(reports=reports, full_cost_complete=True,
         scenario=receipt['scenario'], source_bindings_unchanged=True,
         photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
