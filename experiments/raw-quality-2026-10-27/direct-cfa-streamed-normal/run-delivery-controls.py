"""Root-only final RGB integration and actual native development commissioning."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
HELPERS = AREA.parent / 'insect-placement-observer/run.py'
spec = importlib.util.spec_from_file_location('delivery_controls_root_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=int, default=1)
    args = parser.parse_args()
    build = CAMPAIGN / 'direct-cfa-streamed-delivery-build-3'
    completion = json.loads((build / 'completion.json').read_text())
    assert completion['compiled_new_renderer']
    h.check_refs(completion['reports'])
    h.check_refs(json.loads((build / 'source-bindings.json').read_text()))
    out = CAMPAIGN / f'direct-cfa-streamed-delivery-controls-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    paths = [AREA / name for name in ('run-delivery-controls.py', 'delivery-controls.py',
             'delivery-controls-plan.md', 'delivery.py')]
    paths += [AREA.parent / name for name in
              ('direct-cfa-forward-gpu/measurement-gpu.py',
               'joint-cfa-local-fit/band-residual/sensor-operator.py')]
    paths += [ROOT / 'crates/strehl-cli/examples/direct-rgb-develop.rs',
              build / 'executable.json', HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    sources = [h.ref(path) for path in paths]
    h.save(out / 'source-bindings.json', sources)
    command = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / 'delivery-controls.py'),
               '--out', str(out / 'output'), '--renderer-binding', str(build / 'executable.json')]
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  RAYON_NUM_THREADS='4', CUBLAS_WORKSPACE_CONFIG=':4096:8')
    env, removed = h.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=8 << 30, log_bytes=16 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds,
         environment=fields, removed_environment=removed, python=h.ref(sys.executable),
         scope='Final RGB consumer controls; no photograph reconstruction or quality admission.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    receipt = json.loads((out / 'output/receipt.json').read_text())
    assert receipt['status'] == 'COMPLETE_DIRECT_CFA_DELIVERY_CONTROLS'
    assert receipt['all_cases_completed'] and receipt['mechanical_pass']
    assert receipt['quality_claim'] is False and receipt['photographic_admission'] is False
    reports = [h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()]
    h.save(out / 'completion.json', dict(reports=reports, delivery_mechanics_pass=True,
         source_bindings_unchanged=True, photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
