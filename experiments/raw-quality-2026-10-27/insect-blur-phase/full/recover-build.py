"""Root-only clean cached Cargo confirmation after build2 descendant timeout."""
from pathlib import Path
import importlib.util
import json
import shutil
import sys

AREA = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('phase_build_recovery_helpers', AREA / 'run.py')
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
h = r.h


def artifacts(log):
    rows = []
    for line in log.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    assert any(v.get('reason') == 'build-finished' and v.get('success') for v in rows)
    matches = [v for v in rows if v.get('reason') == 'compiler-artifact'
               and v.get('executable') and v.get('target', {}).get('name') == 'strehl_cli'
               and v.get('profile', {}).get('test')]
    assert len(matches) == 1
    return matches[0]


def main():
    failed = r.folder('build', 2)
    out = r.folder('build', 3)
    out.mkdir(parents=True, exist_ok=False)
    old_process = json.loads((failed / 'process.json').read_text(encoding='utf-8'))
    assert old_process['exit_code'] == 0 and old_process['error'] == "ValueError('child wall bound')"
    assert old_process['terminal_job_accounting'] and old_process['job_accounting']['active_processes'] == 0
    old_log = (failed / 'process.log').read_text(encoding='utf-8')
    assert 'Compiling strehl-cli' in old_log
    old_artifact = artifacts(old_log)
    assert old_artifact['fresh'] is False
    sources = json.loads((failed / 'rust-sources.json').read_text(encoding='utf-8'))
    h.check_refs(sources)
    old_exe = h.ref(old_artifact['executable'])
    bindings = [h.ref(__file__), h.ref(AREA / 'run.py'), h.ref(failed / 'process.json'),
                h.ref(failed / 'process.log'), h.ref(failed / 'rust-sources.json'), old_exe]
    h.save(out / 'recovery-inputs.json', bindings)
    h.save(out / 'rust-sources.json', sources)
    (out / 'recover-build-executed.py').write_bytes(Path(__file__).read_bytes())
    fields, env, removed = r.standard_environment()
    env.update(CARGO_INCREMENTAL='0', CARGO_BUILD_JOBS='4')
    command = json.loads((failed / 'invocation.json').read_text(encoding='utf-8'))['command']
    bounds = dict(wall_seconds=120, cpu_seconds=480, committed_bytes=24 << 30, log_bytes=64 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
           build_environment={'CARGO_INCREMENTAL':'0','CARGO_BUILD_JOBS':'4'}, removed_environment=removed,
           scope='Cached artifact confirmation; fresh compilation occurred in build2, whose owned descendant timed out. No timing or quality claim.'))
    h.observed_run(command, env, out, bounds)
    new_artifact = artifacts((out / 'process.log').read_text(encoding='utf-8'))
    assert new_artifact['fresh'] is True
    assert h.ref(new_artifact['executable']) == old_exe
    h.check_refs(sources + bindings)
    exe = out / 'strehl-cli-tests.exe'
    shutil.copyfile(old_exe['path'], exe)
    recovered = h.ref(exe)
    assert (recovered['sha256'], recovered['bytes']) == (old_exe['sha256'], old_exe['bytes'])
    h.save(out / 'executable.json', recovered)
    h.save(out / 'completion.json', dict(status='CLEAN_CACHED_BUILD_RECOVERY',
           failed_fresh_build_preserved=True, sources_unchanged=True, executable_matches_fresh_artifact=True,
           fresh_compile_run_claimed_clean=False, photographic_improvement_claimed=False,
           reports=[h.ref(out / name) for name in ('process.json','rust-sources.json','executable.json')]))


if __name__ == '__main__':
    main()
