"""Root-owned bounded pixel-free coordinate/combiner checks."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

AREA = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('insect_phase_full_runner_helpers', AREA / 'run.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=int, default=1)
    args = parser.parse_args()
    assert args.iteration > 0
    out = m.folder('actual-controls', args.iteration)
    out.mkdir(parents=True, exist_ok=False)
    paths = [Path(__file__), AREA / 'run.py', AREA / 'actual-controls.py', AREA / 'actual.py',
             AREA / 'full-control-plan.md', m.HELPERS, m.h.PRIOR, m.h.prior.HELPER, m.h.b.HARNESS]
    sources = m.bind_local(out, paths)
    fields, env, removed = m.standard_environment()
    command = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / 'actual-controls.py'),
               '--out', str(out / 'output')]
    bounds = dict(wall_seconds=120, cpu_seconds=120, committed_bytes=2 << 30, log_bytes=8 << 20)
    m.h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
             removed_environment=removed, python=m.h.ref(sys.executable),
             concurrent_work='Native build2 may still be linking; this tiny pixel-free job is not a speed benchmark.'))
    m.h.observed_run(command, env, out, bounds)
    receipt = json.loads((out / 'output/receipt.json').read_text(encoding='utf-8'))
    assert receipt['status'] == 'COMPLETE_INSECT_PHASE_ACTUAL_CONTROLS'
    m.finish(out, receipt, sources)
    assert receipt['controls_pass'], 'fixed geometry controls failed; do not release actual pixels'


if __name__ == '__main__':
    main()
