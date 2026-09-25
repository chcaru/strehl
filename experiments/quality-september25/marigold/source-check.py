"""Bounded read-only RAW witnesses, never an argmax or an aligned-frame volume."""
from pathlib import Path
import os
os.environ['OMP_NUM_THREADS']='4'
import json, hashlib, struct, argparse
import numpy as np
import rawpy, cv2, tifffile
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--indices',default='0,64,128,192,244,320,400,487')
parser.add_argument('--tag',default='broad')
args=parser.parse_args()
assert args.tag.replace('-','').isalnum()
OUT=OUT/args.tag
OUT.mkdir(exist_ok=True)
STACK=4
INDICES=[int(x) for x in args.indices.split(',')]
assert 0<len(INDICES)<=12 and len(set(INDICES))==len(INDICES) and all(0<=x<488 for x in INDICES)
REGIONS={'throat':(2350,2310,700,500),'rim':(1170,1380,650,600),'fan':(3230,3000,600,600)}
base=ROOT/f'outputs/flower-marigold-cpl/stack-{STACK}'
manifest=json.loads((base/'input-order.json').read_text())
maps={}
for line in (base/'alignment.txt').read_text().splitlines():
 s=line.split()
 if s and s[0].isdigit(): maps[int(s[0])]=[struct.unpack('>d',bytes.fromhex(z))[0] for z in s[2:6]]
record={'command':f'python -I -B -X faulthandler experiments/quality-september25/marigold/source-check.py --indices {args.indices} --tag {args.tag}',
 'stack':STACK,'indices':INDICES,'selection':'predetermined temporal subsample, not focus argmax',
 'reference':244,'quad_crop_origin':[191,128],'plane_center':[1758,1172],
 'regions_native_output':REGIONS,'map_sha256':hashlib.sha256((base/'alignment.txt').read_bytes()).hexdigest(),
 'display':'direct Gr plane; sqrt((DN-512)/(15360-512)/0.4), clipped only for display; RGB repeated grayscale; native quad samples, linear interpolation of bounded ROIs only',
 'limitations':'One green CFA phase at two-native-pixel sampling, not production full-resolution gather; phase convention and interpolation can shift apparent edges by approximately a native pixel. Intensity is not matched to rendered sRGB. Active u16 hashes permit independent decoder checking; no decoder agreement asserted.',
 'sources':[]}
tiles={name:[] for name in REGIONS}
for idx in INDICES:
 p=Path(manifest[idx]['source'])
 assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest[idx]['sha256']
 with rawpy.imread(str(p)) as raw:
  visible_shape=list(raw.raw_image_visible.shape)
  active=raw.raw_image[:4688,:7032].copy()
  pattern=raw.raw_pattern.copy()
  black=list(raw.black_level_per_channel); white=raw.white_level
 assert active.shape==(4688,7032) and pattern[0,1]==1
 record['sources'].append({'index':idx,'path':str(p),'sha256':manifest[idx]['sha256'],
  'active_u16_le_sha256':hashlib.sha256(active.astype('<u2').tobytes()).hexdigest(),
  'pattern':pattern.tolist(),'black':black,'white':white,'libraw_visible_shape':visible_shape,
  'copied_domain':[0,0,7032,4688],'domain_note':'Explicit renderer active domain; LibRaw declares four fewer visible columns. All sampled ROIs are well inside the common domain.'})
 plane=active[::2,1::2].astype(np.float32)
 ar,ai,bx,by=maps[idx]
 for name,(x,y,w,h) in REGIONS.items():
  yy,xx=np.mgrid[:h//2,:w//2].astype(np.float64)
  xx+=x/2+191; yy+=y/2+128
  sx=(ar*(xx-1758)-ai*(yy-1172)+bx+1758).astype(np.float32)
  sy=(ai*(xx-1758)+ar*(yy-1172)+by+1172).astype(np.float32)
  z=cv2.remap(plane,sx,sy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=0)
  np.save(OUT/f'source-{idx:03}-{name}-gr.npy',z)
  gray=np.uint8(np.clip(np.sqrt(np.maximum(z-512,0)/(15360-512)/0.4),0,1)*255+0.5)
  tile=Image.fromarray(gray).convert('RGB'); canvas=Image.new('RGB',(tile.width,tile.height+24)); canvas.paste(tile,(0,24));ImageDraw.Draw(canvas).text((5,5),f'original index {idx}',fill='white')
  tiles[name].append(canvas)
 print(f'decoded {idx}',flush=True)
for name,ts in tiles.items():
 w=max(t.width for t in ts);h=max(t.height for t in ts)
 im=Image.new('RGB',(w*4,h*((len(ts)+3)//4)))
 for j,t in enumerate(ts):im.paste(t,((j%4)*w,(j//4)*h))
 im.save(OUT/f'source-ladder-{name}.png')
(OUT/'source-check.json').write_text(json.dumps(record,indent=2)+'\n')
