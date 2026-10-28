"""Root-owned, bounded, single fixed BIPC control screen; no real RAW access."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
HELPERS = AREA.parent / 'insect-placement-observer/run.py'
spec = importlib.util.spec_from_file_location('insect_blur_phase_root_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=int, default=1)
    args = parser.parse_args()
    assert args.iteration > 0
    paths = [AREA / name for name in ('run-controls.py', 'phase.py', 'controls.py',
             'implementation-notes.md', 'controls-protocol.md', 'brief.md')]
    paths += [HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    paths += [ROOT / 'outputs/raw-quality-2026-10-26/weevil-107-baseline/alignment.txt']
    sources = [h.ref(path) for path in paths]
    out = CAMPAIGN / f'insect-blur-phase-controls-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    h.save(out / 'source-bindings.json', sources)
    for path in paths:
        if path.parent == AREA:
            (out / (path.stem + '-executed' + path.suffix)).write_bytes(path.read_bytes())
    command = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / 'controls.py'),
               '--out', str(out / 'output')]
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  CUBLAS_WORKSPACE_CONFIG=':4096:8', RAYON_NUM_THREADS='4')
    env, removed = h.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=8 << 30,
                  log_bytes=32 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds,
         environment=fields, removed_environment=removed, python=h.ref(sys.executable),
         workers=4, cuda_budget_bytes=4 << 30,
         concurrent_work='No other root-scheduled GPU or numerical job.',
         scope='Single fixed independent phase control screen; no photographic claim.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    receipt = json.loads((out / 'output/receipt.json').read_text(encoding='utf-8'))
    assert receipt['complete'] is True
    assert receipt['quality_claim'] is False and receipt['photographic_admission'] is False
    reports = [h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()]
    h.save(out / 'completion.json', dict(reports=reports,
         source_bindings_unchanged=True, photographic_improvement_claimed=False,
         controls_pass=receipt['controls_pass']))
    print(json.dumps(dict(controls_pass=receipt['controls_pass'],
                         photographic_improvement_claimed=False)))


if __name__ == '__main__':
    main()
