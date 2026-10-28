"""Root-only bounded saved-result diagnostic; never reconstructs a new image."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
HELPERS = AREA.parent / 'insect-placement-observer/run.py'
spec = importlib.util.spec_from_file_location('band_budget_root_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=int, default=1)
    args = parser.parse_args()
    photograph = CAMPAIGN / 'direct-cfa-streamed-full-photograph-1'
    completion = json.loads((photograph / 'completion.json').read_text())
    assert completion['complete_photograph'] and completion['numerical_convergence'] is False
    h.check_refs(completion['reports'])
    h.check_refs(json.loads((photograph / 'source-bindings.json').read_text()))
    out = CAMPAIGN / f'direct-cfa-streamed-band-budget-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    paths = [AREA / name for name in ('run-band-budget.py', 'band-budget.py', 'band-budget-notes.md',
             'band-budget-brief.md', 'bands-gpu.py', 'normal-operator.py', 'measurement-paired.py',
             'full-photograph.py')]
    paths += [AREA.parent / name for name in
              ('direct-cfa-forward-gpu/measurement-gpu.py',
               'joint-cfa-local-fit/band-residual/sensor-operator.py')]
    paths += [photograph / 'completion.json', photograph / 'output/receipt.json',
              photograph / 'output/fit/result.json', photograph / 'output/constructor.json',
              CAMPAIGN / 'direct-cfa-streamed-originals-1/output/receipt.json',
              CAMPAIGN / 'direct-cfa-forward-cost-precise-1/output/geometry.json',
              HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    sources = [h.ref(path) for path in paths]
    h.save(out / 'source-bindings.json', sources)
    command = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / 'band-budget.py'),
               '--out', str(out / 'output')]
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  CUBLAS_WORKSPACE_CONFIG=':4096:8')
    env, removed = h.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=16 << 30, log_bytes=16 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
         removed_environment=removed, python=h.ref(sys.executable), workers=4, cuda_budget_bytes=8 << 30,
         scope='No-fit actual-source diagnostic of the rejected full image. No RAW decode, extra solve, retune or quality admission.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    receipt = json.loads((out / 'output/receipt.json').read_text())
    assert receipt['status'] == 'COMPLETE_FULL299_BAND_BUDGET'
    assert receipt['complete'] and receipt['source_count'] == 299 and receipt['controls_pass']
    assert receipt['quality_claim'] is False and receipt['photographic_admission'] is False
    reports = [h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()]
    h.save(out / 'completion.json', dict(reports=reports, complete_diagnostic=True,
         source_bindings_unchanged=True, photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
