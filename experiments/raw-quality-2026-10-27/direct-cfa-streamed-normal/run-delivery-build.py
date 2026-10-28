"""Root-only pinned native final-RGB renderer build and targeted checks."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
HELPERS = AREA.parent / 'insect-placement-observer/run.py'
spec = importlib.util.spec_from_file_location('delivery_build_root_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iteration', type=int, default=1)
    args = parser.parse_args()
    out = CAMPAIGN / f'direct-cfa-streamed-delivery-build-{args.iteration}'
    out.mkdir(parents=True, exist_ok=False)
    example = ROOT / 'crates/strehl-cli/examples/direct-rgb-develop.rs'
    sources = h.prior.source_bindings() + [h.ref(example), h.ref(__file__)]
    h.save(out / 'source-bindings.json', sources)
    env, removed = h.b.clean_environment()
    env.update(CARGO_BUILD_JOBS='4', RAYON_NUM_THREADS='4')
    command = ['cargo', 'build', '--locked', '--offline', '--release', '-p', 'strehl-cli',
               '--example', 'direct-rgb-develop', '--jobs', '4', '--message-format=json-render-diagnostics']
    bounds = dict(wall_seconds=600, cpu_seconds=2400, committed_bytes=16 << 30, log_bytes=16 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds,
         removed_environment=removed, workers=4,
         concurrent_work='Root-owned serial original-CFA export may overlap; not a performance benchmark.'))
    h.observed_run(command, env, out, bounds)
    h.check_refs(sources)
    log = (out / 'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'Compiling strehl-cli' in log, 'new renderer was not compiled'
    records = [json.loads(line) for line in log.splitlines() if line.startswith('{')]
    matches = [r for r in records if r.get('reason') == 'compiler-artifact'
               and r.get('target', {}).get('name') == 'direct-rgb-develop' and r.get('executable')]
    assert len(matches) == 1
    binary = out / 'direct-rgb-develop.exe'
    shutil.copyfile(matches[0]['executable'], binary)
    assert h.ref(binary)['sha256'] == h.ref(matches[0]['executable'])['sha256']
    h.save(out / 'executable.json', h.ref(binary))
    h.save(out / 'completion.json', dict(executable=h.ref(binary), source_bindings_unchanged=True,
         compiled_new_renderer=True, renderer_exercised=False, photographic_improvement_claimed=False,
         reports=[h.ref(out / 'executable.json'), h.ref(out / 'source-bindings.json')]))


if __name__ == '__main__':
    main()
