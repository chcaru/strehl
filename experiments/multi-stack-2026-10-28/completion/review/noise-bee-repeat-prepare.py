"""Exactly32 prior first-light ISO100 originals: headers/hash/embedded previews only."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[4]
SOURCE=Path(r'D:\personal\macro\requests\12-bee-iso-var-no-bracket-32-repeat-diff-light')
OUT=ROOT/'outputs/multi-stack/completion/noise-bee-repeat-01'
EXIF=r'C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe'
TAGS=['Model','ISO','ExposureTime','FNumber','FocalLength','DateTimeOriginal','SubSecTimeOriginal',
      'SubSecDateTimeOriginal','ImageWidth','ImageHeight','FocusPosition2','FocusDistance2',
      'FocusMode','SequenceNumber','ShutterCount','LensModel','WhiteBalance','ImageStabilization',
      'BrightnessValue','ExposureCompensation','BitsPerSample']

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4<<20),b''):h.update(block)
    return h.hexdigest()

def exif(args):
    return subprocess.run([EXIF,*args],capture_output=True,check=True,
        env=dict(os.environ,LC_ALL='C',LC_CTYPE='C',LANG='C')).stdout

def main():
    (OUT/'inputs').mkdir(parents=True,exist_ok=False)
    (OUT/'orientation').mkdir()
    paths=[SOURCE/f'DSC{i:05}.ARW' for i in range(328,360)]
    metadata=json.loads(exif(['-j','-n',*['-'+x for x in TAGS],*[str(x) for x in paths]]))
    (OUT/'inputs/metadata32.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    identities=[]
    for i,path in enumerate(paths):
        before=path.stat();digest=sha(path);after=path.stat()
        assert(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        identities.append({'ordinal':i,'path':str(path),'bytes':before.st_size,
                           'modified_unix_nanos':before.st_mtime_ns,'sha256':digest})
    (OUT/'inputs/source-identities32.json').write_text(json.dumps(identities,indent=2)+'\n',encoding='utf-8')
    previews=[];sheet=Image.new('RGB',(1800,440),(18,18,18))
    for cell,index in enumerate([0,15,31]):
        payload=exif(['-b','-PreviewImage',str(paths[index])])
        if not payload:payload=exif(['-b','-JpgFromRaw',str(paths[index])])
        image=Image.open(io.BytesIO(payload)).convert('RGB')
        target=OUT/f'orientation/ordinal-{index:02}.jpg';target.write_bytes(payload)
        previews.append({'ordinal':index,'path':str(target.relative_to(ROOT)),
                         'dimensions':list(image.size),'sha256':hashlib.sha256(payload).hexdigest()})
        image.thumbnail((600,400),Image.Resampling.LANCZOS);sheet.paste(image,(cell*600,0))
        ImageDraw.Draw(sheet).text((cell*600+8,405),f'ordinal{index} {paths[index].name}',fill='white')
    sheet.save(OUT/'orientation/contact.jpg',quality=95)
    summary={'schema':'strehl.noise-bee-repeat-nomination.v1','count':32,
             'source_directory':str(SOURCE),'files':[p.name for p in paths],
             'unique_sha256':len({s['sha256'] for s in identities}),
             'total_bytes':sum(s['bytes'] for s in identities),'previews':previews,
             'metadata_ranges':{tag:sorted({json.dumps(m.get(tag),sort_keys=True) for m in metadata}) for tag in TAGS},
             'scope':'First-light ISO100 only; no other originals opened; no CFA decode; existing development corpus separate from requested grid/fabric407.'}
    (OUT/'inputs/nomination.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
