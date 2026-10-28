"""Root-only complete photographic presentation after the full run terminates."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
spec = importlib.util.spec_from_file_location('full_views_root_helpers', AREA.parent / 'insect-placement-observer/run.py')
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=int, default=1)
    parser.add_argument('--photograph-iteration', type=int, default=1)
    args = parser.parse_args()
    photograph = CAMPAIGN / f'direct-cfa-streamed-full-photograph-{args.photograph_iteration}'
    assert json.loads((photograph / 'completion.json').read_text())['complete_photograph']
    process = json.loads((photograph / 'process.json').read_text())
    assert process['exit_code'] == 0 and process['error'] is None and process['terminal_job_accounting']
    out = CAMPAIGN / f'direct-cfa-streamed-full-views-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    paths = [Path(__file__), AREA / 'full-photograph-views.py', AREA / 'full-photograph-view-protocol.md',
             photograph / 'completion.json', photograph / 'process.json', photograph / 'output/receipt.json']
    sources = [h.ref(path) for path in paths]
    h.save(out / 'source-bindings.json', sources)
    command = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / 'full-photograph-views.py'),
               '--input-receipt', str(photograph / 'output/receipt.json'), '--out', str(out / 'output')]
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    env, removed = h.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=8 << 30, log_bytes=16 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
         removed_environment=removed, python=h.ref(sys.executable),
         scope='Full photograph presentation and exact native witnesses; no retone or quality verdict.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    receipt = json.loads((out / 'output/receipt.json').read_text())
    assert receipt['status'] == 'COMPLETE_ORIGINAL_CFA_PHOTOGRAPH_VIEWS_READY_NO_VERDICT'
    h.save(out / 'completion.json', dict(reports=[h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()],
         source_bindings_unchanged=True, photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
