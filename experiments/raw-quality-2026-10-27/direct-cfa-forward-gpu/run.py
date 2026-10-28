"""Root-owned bounded original-CFA GPU measurement commissioning."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
HELPERS = AREA.parent / 'insect-placement-observer/run.py'
CPU = AREA.parent / 'joint-cfa-local-fit/band-residual/sensor-operator.py'
LOADER = AREA.parent / 'dual-tree-cfa-gpu/ordered-fir.py'
CPU_SHA = '536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac'
spec = importlib.util.spec_from_file_location('direct_cfa_gpu_root_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('controls',))
    parser.add_argument('--iteration', type=int, default=1)
    args = parser.parse_args()
    assert args.iteration > 0
    assert h.ref(CPU)['sha256'] == CPU_SHA, 'frozen CPU measurement source changed'
    out = CAMPAIGN / f'direct-cfa-forward-{args.stage}-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    source_paths = [AREA / name for name in ('run.py', 'controls.py', 'measurement-gpu.py',
                    'brief.md', 'independent-plan.md')] + [CPU]
    source_paths += [LOADER, HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    sources = [h.ref(path) for path in source_paths]
    h.save(out / 'source-bindings.json', sources)
    command = [sys.executable, '-B', '-X', 'faulthandler',
               str(AREA / 'controls.py'), '--out', str(out / 'output')]
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  CUBLAS_WORKSPACE_CONFIG=':4096:8')
    env, removed = h.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=8 << 30,
                  log_bytes=16 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds,
         environment=fields, removed_environment=removed, python=h.ref(sys.executable),
         scope='Original-CFA measurement mechanics only; no reconstruction, RAW decode or photographic claim.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    receipt = json.loads((out / 'output/receipt.json').read_text())
    assert receipt['status'] == 'COMPLETE_DIRECT_CFA_FORWARD_CONTROLS'
    assert receipt['all_cases_completed'] is True
    assert receipt['mechanical_pass'] is True
    assert receipt['photographic_admission'] is False and receipt['quality_claim'] is False
    reports = [h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()]
    h.save(out / 'completion.json', dict(reports=reports, mechanical_pass=True,
         source_bindings_unchanged=True, photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
