"""Root-only scoped Cargo build; Cargo exit, not research-job tree accounting."""
from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import time

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
spec = importlib.util.spec_from_file_location('direct_build_helpers', AREA / 'run-delivery-build.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def main():
    out = h.CAMPAIGN / 'direct-cfa-streamed-delivery-build-3'
    out.mkdir(parents=True, exist_ok=False)
    example = ROOT / 'crates/strehl-cli/examples/direct-rgb-develop.rs'
    sources = h.h.prior.source_bindings() + [h.h.ref(example), h.h.ref(__file__)]
    h.h.save(out / 'source-bindings.json', sources)
    # Force this example to rebuild after the previous owned-job timeout.
    # Content remains unchanged and is checked after the fresh compilation.
    example.touch()
    env, removed = h.h.b.clean_environment()
    env.update(CARGO_BUILD_JOBS='4', RAYON_NUM_THREADS='4')
    command = ['cargo', 'build', '--locked', '--offline', '--release', '-p', 'strehl-cli',
               '--example', 'direct-rgb-develop', '--jobs', '4', '--message-format=json-render-diagnostics']
    h.h.save(out / 'invocation.json', dict(command=command, workers=4, removed_environment=removed,
         scope='Normal scoped Cargo compilation, not a numerical measurement. Cargo timeout600s; no claim of bounded descendant accounting.',
         reason='Prior build completed Cargo successfully but its Job retained one child until600s. Preserve failed supervisor evidence.'))
    started = time.perf_counter()
    with (out / 'artifacts.jsonl').open('xb') as stdout, (out / 'build.log').open('xb') as stderr:
        process = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                 check=False, timeout=600)
    h.h.save(out / 'process.json', dict(exit_code=process.returncode, wall_seconds=time.perf_counter()-started))
    log = (out / 'build.log').read_text(encoding='utf-8', errors='replace')
    print(log, flush=True)
    assert process.returncode == 0 and 'Compiling strehl-cli' in log
    h.h.check_refs(sources)
    records = [json.loads(line) for line in (out / 'artifacts.jsonl').read_text().splitlines() if line.startswith('{')]
    matches = [r for r in records if r.get('reason') == 'compiler-artifact'
               and r.get('target', {}).get('name') == 'direct-rgb-develop' and r.get('executable')]
    assert len(matches) == 1 and not matches[0]['fresh']
    assert any(r.get('reason') == 'build-finished' and r.get('success') for r in records)
    binary = out / 'direct-rgb-develop.exe'
    shutil.copyfile(matches[0]['executable'], binary)
    assert h.h.ref(binary)['sha256'] == h.h.ref(matches[0]['executable'])['sha256']
    h.h.save(out / 'executable.json', h.h.ref(binary))
    h.h.save(out / 'completion.json', dict(executable=h.h.ref(binary), source_bindings_unchanged=True,
         compiled_new_renderer=True, renderer_exercised=False, photographic_improvement_claimed=False,
         reports=[h.h.ref(out / 'executable.json'), h.h.ref(out / 'source-bindings.json')]))


if __name__ == '__main__':
    main()
