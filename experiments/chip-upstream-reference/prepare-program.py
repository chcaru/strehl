"""Copy a complete existing upstream runtime; change no installed program."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
SOURCE = Path(r'C:\dev\macro\tools\focus-stack\focus-stack')
OLD = Path(r'C:\dev\strehl-out\V-LINEAR2\fs15\focus-stack')
OUT = HERE/'program-1'
EXE_SHA = 'e256176d70bec54bb51a448b2adc452e7f49d21bc5042b40689a3257bbfdee9e'


def ref(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=digest)


files = sorted(p for p in SOURCE.iterdir() if p.suffix.lower() in ('.exe', '.dll') and p.is_file())
assert [p.name for p in files if p.suffix.lower() == '.exe'] == ['focus-stack.exe']
assert ref(SOURCE/'focus-stack.exe')['sha256'] == EXE_SHA
before = [ref(p) for p in files]
common = []
for p in sorted(OLD.iterdir()):
    if p.suffix.lower() not in ('.exe', '.dll'):
        continue
    a, b = ref(p), ref(SOURCE/p.name)
    assert (a['bytes'], a['sha256']) == (b['bytes'], b['sha256']), p.name
    common.append(dict(original=a, complete_cached=b))
assert ref(SOURCE/'libprotobuf.dll')['sha256'] == '36e7e36b191edf2ef74eb9063146b8b91c47b0c37dcdeb100b2562fb075657b1'
assert not (OLD/'libprotobuf.dll').exists()
OUT.mkdir(exist_ok=False)
(OUT/'.gitignore').write_text('*\n', encoding='ascii')
for p in files:
    shutil.copyfile(p, OUT/p.name)
copied = [ref(OUT/p.name) for p in files]
assert [(r['bytes'], r['sha256']) for r in copied] == [(r['bytes'], r['sha256']) for r in before]
inventory = []
for argument in ('--version', '--help'):
    process = subprocess.run([str(OUT/'focus-stack.exe'), argument], capture_output=True,
                             timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    inventory.append(dict(argument=argument, returncode=process.returncode,
                          stdout=process.stdout.decode(errors='replace'), stderr=process.stderr.decode(errors='replace')))
assert before == [ref(p) for p in files]
manifest = dict(schema=1, files=copied, original_files=before, all_original_common_binaries_exact=common,
                additional_dependency='libprotobuf.dll', source_bundle_unchanged=True,
                no_installation=True, inventory=inventory)
(HERE/'program-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(executable_sha256=EXE_SHA, files=len(files), inventory=inventory), indent=2))
assert inventory[0]['returncode'] == 0 and '1.3-42-g0cd289e' in (inventory[0]['stdout']+inventory[0]['stderr'])
assert inventory[1]['returncode'] == 1 and '--no-whitebalance' in (inventory[1]['stdout']+inventory[1]['stderr'])
