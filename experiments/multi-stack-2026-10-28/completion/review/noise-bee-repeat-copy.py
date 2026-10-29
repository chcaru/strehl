"""Materialize only the frozen32 originals into two disjoint ABBA groups."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'outputs/multi-stack/completion/noise-bee-repeat-01'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4<<20),b''):h.update(block)
    return h.hexdigest()

def main():
    identities=json.loads((OUT/'inputs/source-identities32.json').read_text(encoding='utf-8'))
    protocol=json.loads((OUT/'inputs/protocol.json').read_text(encoding='utf-8'))
    expected='f2fc47d451314ef0bf4a188cdf52d147d17de4fd72b947f58069017f631fcae4'
    assert sha(OUT/'inputs/protocol.json')==expected
    destination=OUT/'original-copies';destination.mkdir(exist_ok=False)
    rows=[];passes=[]
    for name,indices in protocol['full_photo_passes'].items():
        folder=destination/name;folder.mkdir()
        for index in indices:
            identity=identities[index];source=Path(identity['path']);target=folder/source.name
            before=source.stat()
            assert (before.st_size,before.st_mtime_ns)==(identity['bytes'],identity['modified_unix_nanos'])
            shutil.copyfile(source,target)
            assert sha(target)==identity['sha256'] and sha(source)==identity['sha256']
            after=source.stat();assert(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
            rows.append({'pass':name,'ordinal':index,'source':identity,'copy':str(target),
                         'copy_sha256':identity['sha256']})
        passes.append({'name':f'Fixed-focus balanced acquisition {name}','directories':[str(folder)]})
    (OUT/'inputs/copy-receipt.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    (OUT/'inputs/manifest.json').write_text(json.dumps({'version':1,'mode':'repeat','primary_pass':None,'passes':passes},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'copies':len(rows),'manifest_sha256':sha(OUT/'inputs/manifest.json'),'protocol_sha256':expected}))

if __name__=='__main__':main()
