"""Read-only scan of previously developed TIFFs; geometry locates crops only."""
from pathlib import Path
import hashlib, json, struct, time
import numpy as np
import tifffile
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SOURCE=ROOT/'vitamin-c-comparator-2/developed'
MAP=ROOT/'vitamin-c-baseline-1/vitamin-c.warpmap.txt'
FROZEN=ROOT/'vitamin-c-review-1/regions.json'
OUT=HERE/'scan-1'
TARGETS={'facet-edges':(128,222),'dark-inclusion':(46,326)}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def score(g):
    g=np.asarray(g,dtype=np.float64)
    smooth=sum(g[dy:dy+g.shape[0]-2,dx:dx+g.shape[1]-2] for dy in range(3) for dx in range(3))/9
    return float(np.mean(np.diff(smooth,axis=1)**2)+np.mean(np.diff(smooth,axis=0)**2))
def controls():
    constant=np.full((80,80),0.3)
    y,x=np.mgrid[:80,:80]
    wave=constant+0.003*np.sin(2*np.pi*x/12)
    noisy=constant+np.random.default_rng(1971).normal(0,0.1,constant.shape)
    values={'constant':score(constant),'known_low_contrast_wave':score(wave),'noisy_flat':score(noisy)}
    assert values['constant']==0 and values['noisy_flat']>values['known_low_contrast_wave']>0
    return values
def map_point(bits,x,y):
    ar,ai,br,bi=[struct.unpack('>d',bytes.fromhex(v))[0] for v in bits]
    u=x/2-1758;v=y/2-1172
    return [2*(1758+ar*u-ai*v+br),2*(1172+ai*u+ar*v+bi)]
def open_image(path):
    arr=tifffile.memmap(path,mode='r')
    assert arr.shape==(4688,7032,3) and arr.dtype==np.uint16
    return arr
def cut(arr,xy):
    x,y=xy
    assert x>=0 and y>=0 and x+384<=7032 and y+384<=4688
    return np.asarray(arr[y:y+384,x:x+384]).copy()
def save_cut(path,arr):
    tifffile.imwrite(path.with_suffix('.tiff'),arr,photometric='rgb')
    Image.fromarray(((arr.astype(np.uint32)+128)//257).astype(np.uint8)).save(path.with_suffix('.png'))

started=time.perf_counter()
nulls=controls() # Before any real frame statistic.
assert not OUT.exists()
OUT.mkdir()
maps={}
for line in MAP.read_text().splitlines():
    p=line.split()
    if len(p)>5 and p[0].isdigit():
        assert p[1]=='placed';maps[int(p[0])]=p[2:6]
assert sorted(maps)==list(range(70))
regions={r['name']:r['xywh'] for r in json.loads(FROZEN.read_text())['regions'] if r['name'] in TARGETS}
source_receipt=json.loads((SOURCE/'receipt.json').read_text())
assert source_receipt['status']=='70_UNALIGNED_NATIVE_RGB16_DEVELOPED'
records=[]
for index in range(70):
    path=SOURCE/f'DSC{index+94:05}.tiff'
    before=path.stat()
    arr=open_image(path)
    for name,(x,y,w,h) in regions.items():
        assert w==h==384
        reference_center=[x+56+191.5,y+38+191.5]
        mapped=map_point(maps[index],*reference_center)
        origin=[int(np.floor(v-191.5+0.5)) for v in mapped]
        view=cut(arr,origin)
        lx,ly=TARGETS[name]
        locator=view[ly-40:ly+40,lx-40:lx+40,1].astype(np.float64)/65535
        assert locator.shape==(80,80)
        records.append({'region':name,'index0':index,'original_raw_name':f'DSC{index+94:05}.ARW',
            'source_tiff':str(path.resolve()),'source_bytes':before.st_size,'source_mtime_ns':before.st_mtime_ns,
            'pull_bits':maps[index],'reference_native_center':reference_center,'mapped_native_center':mapped,
            'source_native_xywh':origin+[384,384],'green_locator':score(locator),
            'crop_rgb16_sha256':hashlib.sha256(view.tobytes()).hexdigest()})
    del arr
    after=path.stat()
    assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
nominations=[]
for name in TARGETS:
    scan=[r for r in records if r['region']==name]
    peak=max(scan,key=lambda r:r['green_locator'])
    indices=sorted({max(0,min(69,peak['index0']+offset)) for offset in [-3,0,3]})
    for index in indices:
        record=scan[index]
        arr=open_image(Path(record['source_tiff']))
        view=cut(arr,record['source_native_xywh'][:2]);del arr
        stem=f'{name}-source-{index:02}-DSC{index+94:05}'
        save_cut(OUT/stem,view)
        record['display_png']=str((OUT/stem).with_suffix('.png').resolve())
    # Reuse the frozen baseline pixels exactly, not a new render.
    baseline=Image.open(ROOT/f'vitamin-c-review-1/{name}.png')
    baseline.save(OUT/f'{name}-baseline.png')
    nominations.append({'region':name,'locator_peak_index0':peak['index0'],
        'endpoint':peak['index0'] in [0,69],'inspection_indices0':indices,
        'top_five_locator_only':[{'index0':r['index0'],'value':r['green_locator']} for r in sorted(scan,key=lambda r:r['green_locator'],reverse=True)[:5]]})
receipt={'scope':'source localization, not a quality or sensor-clipping measurement','command':
    'python -I -B experiments/quality-september19/vitamin-c-source-highlights/scan.py',
    'helper_sha256':sha(Path(__file__)),'plan_sha256':sha(HERE/'plan.md'),'warpmap_sha256':sha(MAP),
    'source_receipt_sha256':sha(SOURCE/'receipt.json'),'frozen_regions_sha256':sha(FROZEN),
    'source_tone_bits':source_receipt['tone_bits'],'source_wb_bits':source_receipt['wb_bits'],
    'locator_failure_controls':nulls,'nominations':nominations,'frames':records,
    'display':'native384, integer crop only, rounded divide257, no colour adjustment',
    'seconds':time.perf_counter()-started}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'seconds':receipt['seconds'],'controls':nulls,'nominations':nominations},indent=2))
