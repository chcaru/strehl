"""Paste the released twelve frozen HDR crops; no resampling, RAW, or rendering."""
from pathlib import Path
from PIL import Image, ImageDraw
import hashlib
import json
r = Path(__file__).resolve().parents[4]
p = r / 'outputs/multi-stack/completion/independent-photographs'
old = r / 'experiments/multi-stack-2026-10-28/review/hdr-displays-complete/physical-reference'
arms = [('Equal HDR', old/'slide-hdr-pair-6'), ('Precision01 delivered focus', p/'hdr-precision'),
        ('Precision03 equal focus', p/'hdr-precision03'), ('Short2.5s', old/'hdr-short-7'), ('Long6s', old/'hdr-long-7')]
out = p/'hdr-precision03'/'native-comparisons'
out.mkdir(exist_ok=True)
receipt = []
for f in sorted((p/'hdr-precision03').glob('native-*.png')):
    board = Image.new('RGB', (1184, 820), (30, 30, 30))
    draw = ImageDraw.Draw(board)
    items = []
    for i, (label, d) in enumerate(arms):
        src = d/f.name
        im = Image.open(src).convert('RGB')
        assert im.size == (384, 384)
        x, y = 8+(i%3)*392, 26+(i//3)*410
        board.paste(im, (x,y))
        draw.text((x,y-18), label, fill='white')
        assert board.crop((x,y,x+384,y+384)).tobytes() == im.tobytes()
        items.append({'label':label,'path':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
                      'origin':[x,y],'size':[384,384]})
    dest = out/f.name
    board.save(dest)
    receipt.append({'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'images':items})
assert len(receipt) == 12
(out/'layout.json').write_text(json.dumps({'schema':'strehl.native-paste-board.v1','resampling':False,
                                        'boards':receipt},indent=2)+'\n')
print(json.dumps({'boards':len(receipt),'output':str(out)}))
