"""Reuse the September 14 orientation: ExifTool binary metadata/JPEG only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from PIL import Image

HERE = Path(__file__).resolve().parent
EXIF = Path(r'C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe')
inputs = json.loads((HERE / 'inputs.json').read_text(encoding='utf-8-sig'))
env = os.environ.copy()
env.update(LC_ALL='C', LC_CTYPE='C', LANG='C')
tags = ['Model', 'LensModel', 'LensID', 'FocalLength', 'FNumber', 'ExposureTime',
        'ISO', 'WhiteBalance', 'ColorTemperature', 'ImageStabilization',
        'ElectronicFrontCurtainShutter', 'ShutterType', 'DateTimeOriginal']
commands = []

def run(args):
    command = [str(EXIF), *args]
    commands.append(command)
    result = subprocess.run(command, env=env, check=True, capture_output=True, timeout=60)
    if result.stderr:
        with (HERE / 'exiftool-stderr.log').open('ab') as handle:
            handle.write(result.stderr)
    return result.stdout

paths = [item['path'] for item in inputs]
for suffix, numeric in [('', []), ('-numeric', ['-n'])]:
    data = run(['-j', *numeric, *['-' + tag for tag in tags], *paths])
    # Parse before saving so errors cannot masquerade as metadata.
    parsed = json.loads(data)
    assert len(parsed) == len(inputs)
    (HERE / ('metadata' + suffix + '.json')).write_text(json.dumps(parsed, indent=2) + '\n', encoding='utf-8')

preview_records = []
for item in inputs:
    filename = f"{item['stack']}-{item['index']:03d}-embedded.jpg"
    target = HERE / filename
    jpeg = run(['-b', '-PreviewImage', item['path']])
    assert jpeg[:2] == b'\xff\xd8', f'No embedded JPEG: {item["path"]}'
    target.write_bytes(jpeg)
    with Image.open(target) as preview:
        preview.load()
        size = list(preview.size)
    preview_records.append(dict(**item, preview=filename, preview_tag='PreviewImage',
                                dimensions=size, sha256=hashlib.sha256(jpeg).hexdigest(),
                                purpose='Camera-rendered embedded JPEG; orientation only, not RAW quality evidence'))
(HERE / 'previews.json').write_text(json.dumps(preview_records, indent=2) + '\n', encoding='utf-8')
(HERE / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(previews=len(preview_records), dimensions=[p['dimensions'] for p in preview_records])))
