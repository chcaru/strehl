"""Root-only fixed64 solver commissioning; no full photograph."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
HELPERS = AREA.parent / 'insect-placement-observer/run.py'
spec = importlib.util.spec_from_file_location('solver_controls_root_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=int, default=1)
    args = parser.parse_args()
    control = CAMPAIGN / 'direct-cfa-streamed-controls-2'
    completed = json.loads((control / 'completion.json').read_text())
    assert completed['mechanical_pass']
    h.check_refs(completed['reports'])
    h.check_refs(json.loads((control / 'source-bindings.json').read_text()))
    out = CAMPAIGN / f'direct-cfa-streamed-solver-controls-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    paths = [AREA / name for name in
             ('run-solver-controls.py', 'solver-controls.py', 'solver-controls-plan.md',
              'controls.py', 'bands-gpu.py', 'normal-operator.py', 'solver.py', 'measurement-paired.py')]
    paths += [AREA.parent / name for name in
              ('direct-cfa-forward-gpu/measurement-gpu.py', 'direct-cfa-forward-gpu/controls.py',
               'joint-cfa-local-fit/band-residual/sensor-operator.py',
               'joint-cfa-local-fit/constant-deflation/sensor-operator.py')]
    paths += [HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    sources = [h.ref(path) for path in paths]
    h.save(out / 'source-bindings.json', sources)
    command = [sys.executable, '-B', '-X', 'faulthandler',
               str(AREA / 'solver-controls.py'), '--out', str(out / 'output')]
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  CUBLAS_WORKSPACE_CONFIG=':4096:8')
    env, removed = h.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=8 << 30,
                  log_bytes=16 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds,
         environment=fields, removed_environment=removed, python=h.ref(sys.executable),
         scope='Fixed64 actual small solver and numerical refusal controls; no RAW or photographic admission.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    receipt = json.loads((out / 'output/receipt.json').read_text())
    assert receipt['status'] == 'COMPLETE_DIRECT_CFA_SOLVER_CONTROLS'
    assert receipt['all_cases_completed'] and receipt['mechanical_pass']
    assert receipt['quality_claim'] is False and receipt['photographic_admission'] is False
    reports = [h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()]
    h.save(out / 'completion.json', dict(reports=reports, solver_mechanics_pass=True,
         source_bindings_unchanged=True, photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
