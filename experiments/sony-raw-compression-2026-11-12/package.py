"""Package original experiment code, builds and receipts; never RAWs or secrets."""
import hashlib
import json
from pathlib import Path
import zipfile

SRC = Path(__file__).resolve().parent
ROOT = SRC.parents[1]
OUT = ROOT/'outputs'/SRC.name


def main():
    files = [p for p in SRC.rglob('*') if p.is_file() and p.suffix in {'.py', '.rs', '.md', '.txt', '.json', '.jsonl'} and '__pycache__' not in p.parts]
    files += [ROOT/'LICENSE-MIT', ROOT/'LICENSE-APACHE']
    files += [OUT/name for name in ['predict-v3.dll', 'libpredict.so', 'public-files-4.json',
                                    'public-files-16.json', 'input-manifest.json', 'measured-build.json']]
    for folder in ['measured-source', 'v1']:
        files += [p for p in (OUT/folder).glob('*') if p.is_file() and p.suffix in {'.py', '.rs', '.md', '.dll', '.json'}]
    files = sorted(set(files))
    assert all(p.is_relative_to(ROOT) and p.suffix.lower() not in {'.arw', '.jpg', '.png'} and 'private' not in p.relative_to(ROOT).parts for p in files)
    manifest = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
                 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    dest = OUT/'strehl-raw-compression-prototype-2026-11-12.zip'
    with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
        z.writestr('package-manifest.json', json.dumps(manifest, indent=2)+'\n')
        z.writestr('START-HERE.txt', 'Read experiments/sony-raw-compression-2026-11-12/README.md and results.md.\nResearch prototype; running capture app is unchanged. No RAWs or credentials included.\n')
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None
        for row in manifest:
            b = z.read(row['path'])
            assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
    receipt = {'file': str(dest), 'bytes': dest.stat().st_size,
               'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(), 'verified_members': len(files),
               'includes_raws_or_credentials': False}
    (OUT/'package-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
