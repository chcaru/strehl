"""Read-only mineral diagnosis; complete ICC-preserving views, bounded RAW samples."""
from pathlib import Path
import hashlib, json, re, struct, sys
import numpy as np
import tifffile
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
PY='C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe'
ITEMS=[
 ('100','peacock-ore',31,237,'peacock-ore'),
 ('102','peacock-ore',41,256,'peacock-ore'),
 ('103','rainbow-opal-cabochon',46,200,'minerals-september24'),
 ('104','etched-spessartine-garnet',27,209,'minerals-september24'),
 ('105','rutile-star-on-hematite',27,254,'minerals-september24'),
]
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(name,v): (HERE/name).write_text(json.dumps(v,indent=2)+'\n')
def views():
 records=[]
 for code,label,first,last,group in ITEMS:
  out=ROOT/'outputs'/group
  master=out/'final'/f'{label}-{code}msdcf-master.tiff'
  comp=json.loads((out/f'{code}msdcf'/'completion.json').read_text())
  with tifffile.TiffFile(master) as tf:
   rgb=tf.asarray();icc=bytes(tf.pages[0].tags[34675].value)
  assert rgb.dtype==np.uint16 and rgb.shape==(comp['height'],comp['width'],3)
  image=Image.fromarray(((rgb.astype(np.uint32)+128)//257).astype(np.uint8))
  image.thumbnail((1617,1617),Image.Resampling.LANCZOS)
  image.save(HERE/f'{code}-whole.png',icc_profile=icc)
  native=Path('D:/personal/macro/minerals')/label/f'{code}MSDCF'
  files=sorted(native.glob('*.ARW'))
  assert [f.name for f in files]==[f'DSC{i:05d}.ARW' for i in range(first,last+1)]
  rec=dict(code=code,label=label,frames=len(files),master=str(master),sha256=sha(master),
     active_native_shape=[4688,7032],output_shape=list(rgb.shape),crop_quad_xywh=comp['crop_quad_xywh'],
     source_folder=str(native),overview=str(HERE/f'{code}-whole.png'),icc_sha256=hashlib.sha256(icc).hexdigest(),
     displayed_one_channel_at_65535=int(np.count_nonzero(np.any(rgb==65535,axis=2))),
     displayed_three_channels_at_65535=int(np.count_nonzero(np.all(rgb==65535,axis=2))),
     output_pixels=int(rgb.shape[0]*rgb.shape[1]))
  records.append(rec)
  print(json.dumps(rec),flush=True)
 save('inventory.json',records)
if __name__=='__main__':views()
