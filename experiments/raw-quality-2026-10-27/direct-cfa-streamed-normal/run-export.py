"""Root-only serial complete original-u16 export for a later RAW observation."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import time

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
HELPERS = AREA.parent / 'insect-placement-observer/run.py'
spec = importlib.util.spec_from_file_location('native_export_root_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=int, default=1)
    args = parser.parse_args()
    assert args.iteration > 0
    started = time.perf_counter()
    for name in ('direct-cfa-streamed-controls-2', 'direct-cfa-streamed-full-cost-1'):
        previous = CAMPAIGN / name
        completed = json.loads((previous / 'completion.json').read_text())
        h.check_refs(completed['reports'])
        h.check_refs(json.loads((previous / 'source-bindings.json').read_text()))
    cost = json.loads((CAMPAIGN / 'direct-cfa-streamed-full-cost-1/output/receipt.json').read_text())
    assert cost['scenario']['within_research_observation_ceiling']
    disk = shutil.disk_usage(ROOT)
    assert disk.free >= 50 << 30, 'insufficient original-cache disk allowance'
    out = CAMPAIGN / f'direct-cfa-streamed-originals-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    paths = [AREA / name for name in
             ('run-export.py', 'export-originals.py', 'export-notes.md', 'export-brief.md',
              'brief.md', 'export-source-review.md')]
    paths += [HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS,
              CAMPAIGN / 'direct-cfa-streamed-controls-2/completion.json',
              CAMPAIGN / 'direct-cfa-streamed-full-cost-1/completion.json']
    sources = [h.ref(path) for path in paths]
    h.save(out / 'source-bindings.json', sources)
    command = [sys.executable, '-B', '-X', 'faulthandler',
               str(AREA / 'export-originals.py'), '--out', str(out / 'output')]
    fields = dict(RAYON_NUM_THREADS='4', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4',
                  OPENBLAS_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1',
                  PYTHONDONTWRITEBYTECODE='1')
    env, removed = h.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=600, cpu_seconds=2400, committed_bytes=8 << 30,
                  log_bytes=16 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds,
         environment=fields, removed_environment=removed, python=h.ref(sys.executable),
         free_disk_before_bytes=disk.free,
         scope='299 original native-u16 exports only; capture files read-only, no fit or photographic claim.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    receipt = json.loads((out / 'output/receipt.json').read_text())
    assert receipt['status'] == 'COMPLETE299_ORIGINAL_NATIVE_CFA_EXPORT'
    assert receipt['complete'] and receipt['source_count'] == 299
    assert receipt['original_bytes_and_metadata_unchanged'] and receipt['source_bindings_unchanged']
    assert receipt['quality_claim'] is False
    reports = [h.ref(path) for path in sorted((out / 'output').rglob('*')) if path.is_file()]
    h.save(out / 'completion.json', dict(reports=reports, original_cache_complete=True,
         source_bindings_unchanged=True, photographic_improvement_claimed=False,
         wrapper_wall_seconds_including_postflight_hashes=time.perf_counter()-started))


if __name__ == '__main__':
    main()
