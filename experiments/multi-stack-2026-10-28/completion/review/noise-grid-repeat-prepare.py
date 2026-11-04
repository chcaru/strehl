"""Read all50 headers and bounded embedded JPEGs; never decode/mutate captures."""
from pathlib import Path
import hashlib
import io
import json
import os
import subprocess
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'outputs/multi-stack/completion/noise-grid-repeat-01'
EXIF = r'C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe'
TAGS = ['Model','ISO','ExposureTime','FNumber','DateTimeOriginal','SubSecTimeOriginal',
        'ImageWidth','ImageHeight','FocusPosition2','FocusDistance','FocusDistance2',
        'FocusMode','FocusMode2','SequenceNumber','ShutterCount','LensModel','DriveMode',
        'WhiteBalance','ImageStabilization','BrightnessValue','ExposureCompensation']

def run(args):
    env = dict(os.environ, LC_ALL='C', LC_CTYPE='C', LANG='C')
    result = subprocess.run([EXIF, *args], capture_output=True, env=env, check=True)
    return result.stdout

def main():
    inspection = json.loads((OUT/'inputs/inspection.json').read_text(encoding='utf-8'))
    sources = inspection['source_identities']
    paths = [s['path'].removeprefix('\\\\?\\') for s in sources]
    metadata = json.loads(run(['-j','-n','-fast2', *['-'+t for t in TAGS], *paths]))
    (OUT/'inputs/exiftool-all50.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    previews = []
    sheet = Image.new('RGB',(3*600,2*440),(18,18,18))
    for cell,index in enumerate([0,11,22,23,36,49]):
        payload = run(['-b','-PreviewImage',paths[index]])
        if not payload:
            payload = run(['-b','-JpgFromRaw',paths[index]])
        original = Image.open(io.BytesIO(payload)).convert('RGB')
        output = OUT/f'orientation/global-{index:02}.jpg'
        output.write_bytes(payload)
        previews.append({'global_index':index,'source':sources[index],
                         'path':str(output.relative_to(ROOT)),
                         'dimensions':list(original.size),
                         'sha256':hashlib.sha256(payload).hexdigest()})
        original.thumbnail((600,400),Image.Resampling.LANCZOS)
        x,y=(cell%3)*600,(cell//3)*440
        sheet.paste(original,(x+(600-original.width)//2,y))
        ImageDraw.Draw(sheet).text((x+8,y+405),f'pass {int(index>=23)} global {index} {Path(paths[index]).name}',fill='white')
    sheet.save(OUT/'orientation/contact.jpg',quality=95)
    summary={'schema':'strehl.noise-grid-nomination.v1','method':'All50 complete RAW SHA256 via native session inspect; all50 ExifTool metadata; six embedded previews, no CFA decode.',
             'source_count':len(sources),'unique_source_sha256':len({s['sha256'] for s in sources}),
             'total_source_bytes':sum(s['bytes'] for s in sources),'previews':previews,
             'metadata_ranges':{}}
    for key in TAGS:
        values = {json.dumps(m.get(key),sort_keys=True) for m in metadata}
        summary['metadata_ranges'][key] = sorted(values)
    (OUT/'inputs/nomination.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='previews'},indent=2))

if __name__=='__main__':
    main()
