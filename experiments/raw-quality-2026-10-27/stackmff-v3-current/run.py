"""Root-owned bounded current StackMFF comparator execution."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
UPSTREAM = CAMPAIGN / 'stackmff-v3-upstream-2'
HELPERS = AREA.parent / 'insect-placement-observer/run.py'
spec = importlib.util.spec_from_file_location('stackmff_root_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('controls', 'cost', 'full', 'views'))
    p.add_argument('--iteration', type=int, default=1)
    p.add_argument('--controls-iteration', type=int, default=1)
    p.add_argument('--cost-iteration', type=int, default=1)
    p.add_argument('--full-iteration', type=int, default=1)
    a = p.parse_args()
    assert min(a.iteration, a.controls_iteration, a.cost_iteration, a.full_iteration) > 0
    out = CAMPAIGN / f'stackmff-v3-{a.stage}-{a.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    source_paths = sorted(AREA.glob('*.py')) + [AREA / 'upstream-manifest.json', AREA / 'brief.md',
                                             AREA / 'comparison-protocol.md']
    source_paths += [HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    sources = [h.ref(path) for path in source_paths]
    upstream = json.loads((UPSTREAM / 'download-receipt.json').read_text())
    assert upstream['status'] == 'COMPLETE_PINNED_DOWNLOAD'
    upstream_bindings = []
    for row in upstream['artifacts']:
        bound = h.ref(UPSTREAM / row['path'])
        assert bound['bytes'] == row['bytes'] and bound['sha256'] == row['sha256']
        upstream_bindings.append(bound)
    h.save(out / 'source-bindings.json', sources)
    h.save(out / 'upstream-bindings.json', upstream_bindings)
    dependencies = []
    for stage, iteration in [('controls', a.controls_iteration), ('cost', a.cost_iteration)]:
        if a.stage == 'controls' or (a.stage == 'cost' and stage == 'cost') or a.stage == 'views':
            continue
        job = CAMPAIGN / f'stackmff-v3-{stage}-{iteration}'
        c = json.loads((job / 'completion.json').read_text())
        h.check_refs(c['reports'])
        h.check_refs(json.loads((job / 'source-bindings.json').read_text()))
        assert c['mechanical_pass'] is True
        dependencies.append(h.ref(job / 'completion.json'))
    script = 'controls.py' if a.stage == 'controls' else 'worker.py'
    cmd = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / script),
           '--upstream', str(UPSTREAM), '--out', str(out / 'output')]
    if a.stage != 'controls':
        cmd += ['--stage', a.stage]
    if a.stage == 'views':
        full = CAMPAIGN / f'stackmff-v3-full-{a.full_iteration}'
        c = json.loads((full / 'completion.json').read_text())
        h.check_refs(c['reports'])
        assert c['mechanical_pass'] is True
        cmd += ['--full', str(full / 'output')]
        dependencies.append(h.ref(full / 'completion.json'))
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  CUBLAS_WORKSPACE_CONFIG=':4096:8', MS_SCALES='1,0.75')
    env, removed = h.b.clean_environment(fields.items())
    wall = dict(controls=300, cost=600, full=3600, views=180)[a.stage]
    bounds = dict(wall_seconds=wall, cpu_seconds=wall*4, committed_bytes=24 << 30,
                  log_bytes=32 << 20)
    h.save(out / 'invocation.json', dict(command=cmd, bounds=bounds, environment=fields,
        removed_environment=removed, dependencies=dependencies, python=h.ref(sys.executable),
        scope='External RGB comparator with held Strehl geometry; no native reconstruction or photographic claim.'))
    h.observed_run(cmd, env, out, bounds)
    h.check_refs(sources + upstream_bindings + dependencies)
    receipt_path = out / 'output/receipt.json'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['complete'] is True and receipt['mechanical_pass'] is True
    assert receipt['quality_claim'] is False
    reports = [h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()]
    h.save(out / 'completion.json', dict(reports=reports, mechanical_pass=True,
        source_bindings_unchanged=True, photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
