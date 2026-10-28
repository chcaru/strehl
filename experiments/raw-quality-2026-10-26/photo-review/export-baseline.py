"""Freeze baseline-only native witnesses before any candidate viewing."""
from pathlib import Path
import hashlib,json
import numpy as np
import tifffile
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
BASE=ROOT/'outputs/raw-quality-2026-10-26/weevil-107-baseline'
WITNESSES=[
 ('background-black',3800,500,'Visually dark background; clipping/faint speck guard, not a certified flat-noise measurement.'),
 ('dark-elytron',2750,2120,'Weak dark material texture and faint specks; smoothing must not be mistaken for detail recovery.'),
 ('turquoise-scales',2120,1340,'Individual bright scale shapes and gaps, not aggregate high-frequency energy.'),
 ('elytron-seam',2950,1960,'Long diagonal seam and nearby scales at distinct depths; continuity and double rims.'),
 ('bright-wing-rim',4050,1810,'Bright glints and pale scale texture near the body edge; color and highlight structure.'),
 ('thorax-texture',4520,2560,'Dense fine scale/texture pattern on curved thorax.'),
 ('upper-leg-hairs',1820,640,'Slender hairs, leg surface marks and dark edge surround.'),
 ('blue-joint',2680,850,'Saturated blue/cyan transition and small dark/bright marks.'),
 ('upper-occlusion',3850,1300,'Overlap between raised blue limb, elytron edge and dark cavity; edge multiplicity and shading.'),
 ('eye-and-antenna',5350,2920,'Eye outline, adjacent head texture and hair/antenna strands; cross-depth preservation.'),
]

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}

def main():
 manifest=OUT/'baseline-witnesses.json'
 assert not manifest.exists(),'frozen witness manifest already exists'
 completion=json.loads((BASE/'completion.json').read_text())
 master=BASE/'stack-master.tiff'
 assert digest(master)==completion['master']['sha256']
 with tifffile.TiffFile(master) as f:
  rgb=f.asarray();icc=bytes(f.pages[0].tags[34675].value)
 assert rgb.dtype==np.uint16 and rgb.shape==(4596,6896,3)
 dest=OUT/'baseline-native';dest.mkdir(exist_ok=False)
 rows=[]
 for name,x,y,role in WITNESSES:
  crop=rgb[y:y+384,x:x+384].copy();assert crop.shape==(384,384,3)
  tp=dest/f'{name}.tiff';pp=dest/f'{name}.png'
  tifffile.imwrite(tp,crop,photometric='rgb',metadata=None,extratags=[(34675,'B',len(icc),icc,False)])
  eight=((crop.astype(np.uint32)+128)//257).astype(np.uint8)
  Image.fromarray(eight).save(pp,icc_profile=icc)
  with tifffile.TiffFile(tp) as check:
   assert np.array_equal(check.asarray(),crop) and bytes(check.pages[0].tags[34675].value)==icc
  with Image.open(pp) as check:
   assert check.size==(384,384) and np.array_equal(np.asarray(check),eight) and check.info['icc_profile']==icc
  rows.append({'name':name,'rect_xywh':[x,y,384,384],'gauge':'delivered native RGB pixels; origin at cropped master top-left','role':role,'resized':False,'rgb16':ref(tp),'png8':ref(pp),'rgb16_pixel_sha256':hashlib.sha256(crop.astype('<u2').tobytes()).hexdigest()})
 result={'schema':1,'state':'BASELINE_ONLY_WITNESSES_FROZEN_BEFORE_CANDIDATE','master':ref(master),'complete_rgb16_dimensions':[6896,4596],'frames':299,'map':completion['warp_map'],'source_crop_quad_xywh':completion['crop_quad_xywh'],'icc_sha256':hashlib.sha256(icc).hexdigest(),'display':{'png8':'round RGB16/257 via (value+128)//257; original ICC retained; no exposure/tone/contrast changes','rgb16':'exact source subarray copied losslessly; original ICC retained','viewer':'view_image detail original at384x384; whole image view is resized orientation only'},'producer':ref(Path(__file__).resolve()),'witnesses':rows,'candidate_seen':False,'raw_decodes':0}
 manifest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(f'Frozen {len(rows)} witnesses; TIFF and PNG pixel/ICC round trips exact; master {result["master"]["sha256"]}')
if __name__=='__main__':main()
