"""Preserve a successful Rust build while binding a corrected Python-only driver."""
from pathlib import Path
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('driver_binding', HERE/'run.py')
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)
c = runner.common
parent = HERE/'build-3'
out = HERE/'build-3-driver-fixed'
process = json.loads((parent/'process.json').read_text())
assert process['exit_code'] == 0 and process['error'] is None
assert process['terminal_job_accounting'] and not process['cleanup_errors']
log = (parent/'process.log').read_text(encoding='utf-8')
assert 'Compiling strehl-cli' in log and 'Compiling strehl-native-gpu-gather' in log
old = json.loads((parent/'sources.json').read_text())
allowed = str((HERE/'full-run.py').resolve())
changed = [row for row in old if c.ref(Path(row['path'])) != row]
assert len(changed) == 1 and changed[0]['path'] == allowed
assert Path(allowed).suffix == '.py'
new = [c.ref(Path(row['path'])) for row in old]
artifacts = {}
for line in log.splitlines():
    try:
        row = json.loads(line)
    except ValueError:
        continue
    if (row.get('reason') == 'compiler-artifact' and row.get('executable')
            and row.get('target', {}).get('name') == 'strehl'):
        name = 'cli-tests' if row['profile']['test'] else 'strehl'
        assert name not in artifacts
        artifacts[name] = row['executable']
assert set(artifacts) == {'cli-tests', 'strehl'}
out.mkdir(exist_ok=False)
executables = {}
for name, built_path in artifacts.items():
    preserved = parent/(name+'.exe')
    assert preserved.exists() and c.ref(preserved)['sha256'] == c.ref(Path(built_path))['sha256']
    destination = out/(name+'.exe')
    shutil.copyfile(preserved, destination)
    executables[name] = c.ref(destination)
c.save(out/'sources.json', new)
c.save(out/'executables.json', executables)
c.save(out/'driver-binding.json', dict(
    compiled_parent=c.ref(parent/'process.json'), compiler_log=c.ref(parent/'process.log'),
    original_bindings=c.ref(parent/'sources.json'), changed_before=changed,
    changed_after=[c.ref(Path(allowed))], compiled_sources_unchanged=True,
    executable_bytes_unchanged=True, binder=c.ref(Path(__file__)),
    reason='ICC-preserving PNG views and corrected master reference; Python is not compiled into Rust. '
           'The parent wrapper caught the driver change after successful compilation. '
           'No generated or photographic execution used the old driver.'))
print(json.dumps({'derived_build': str(out), 'compiled_sources_unchanged': True}))
