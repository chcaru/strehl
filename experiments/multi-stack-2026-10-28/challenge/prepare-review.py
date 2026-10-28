"""Fixed-baseline complete-photo review; never reads RAW capture inputs.

Run prepare-baselines first. render requires that frozen transform and never fits
anything from the candidate. Crop locations are a separately frozen JSON file.
"""
from __future__ import annotations
import argparse, hashlib, json, platform, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import tifffile

F = np.float32
BASE = Path('outputs/multi-stack/baseline')
OUT = Path('outputs/multi-stack/independent-review')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def luma(rgb):
    return F(.2126) * rgb[..., 0] + F(.7152) * rgb[..., 1] + F(.0722) * rgb[..., 2]


def display(rgb, baseline):
    """Strehl's recorded baseline placement/gamut/sRGB/S-curve, fixed parameters.

    This independent NumPy expression is commissioned against baseline106's
    encoded TIFF. It does not refit black/white or locally enhance an image.
    """
    rgb = np.asarray(rgb, dtype=np.float32)
    lum = np.maximum(luma(rgb), F(0))
    scale = F(1) / (F(baseline['white']) - F(baseline['black']))
    y = (lum - F(baseline['black'])) * scale
    soft = F(.5) * (y + np.sqrt(y * y + F(.004) * F(.004)))
    gain = np.zeros_like(lum)
    np.divide(soft, lum, out=gain, where=lum > 0)
    gain = np.minimum(gain, scale) * F(baseline['exposure_gain'])
    v = rgb * gain[..., None]
    grey = np.clip(luma(v), 0, 1)
    blend = np.zeros_like(grey)
    for c in range(3):
        channel = v[..., c]
        d = grey - channel
        a = np.zeros_like(grey)
        np.divide(-channel, d, out=a, where=(channel < 0) & (d > F(1e-6)))
        blend = np.maximum(blend, a)
        d = channel - grey
        a.fill(0)
        np.divide(channel - F(1), d, out=a, where=(channel > 1) & (d > F(1e-6)))
        blend = np.maximum(blend, a)
    v = np.clip(v + (grey[..., None] - v) * np.clip(blend, 0, 1)[..., None], 0, 1)
    encoded = np.where(v <= F(.0031308), v * F(12.92), F(1.055) * np.power(v, F(1) / F(2.4)) - F(.055))
    encoded = encoded + (encoded * encoded * (F(3) - F(2) * encoded) - encoded) * F(baseline['contrast'])
    return np.floor(np.clip(encoded, 0, 1) * F(65535) + F(.5)).astype(np.uint16)


def encoded8(u16):
    return ((u16.astype(np.uint32) + 128) // 257).astype(np.uint8)


def metadata(path):
    with tifffile.TiffFile(path) as tf:
        assert len(tf.pages) == 1, 'review expects one complete RGB image'
        p = tf.pages[0]
        return {'path': str(Path(path).resolve()), 'shape': list(p.shape), 'dtype': str(p.dtype),
                'description': p.description, 'icc_bytes': len(p.tags[34675].value) if 34675 in p.tags else 0,
                'file_sha256': digest(path)}


def render(master, destination, transform_path, label, compare=None, rois=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    transform = json.loads(Path(transform_path).read_text())
    baseline = transform['display_baseline']
    meta = metadata(master)
    assert meta['dtype'] == 'float32' and meta['shape'][2] == 3
    assert 'BT.709 primaries; D65; linear transfer' in meta['description']
    array = tifffile.memmap(master, mode='r')
    h, w, _ = array.shape
    full = np.empty((h, w, 3), dtype=np.uint8)
    comparison = tifffile.memmap(compare, mode='r') if compare else None
    max_delta = 0
    differing = 0
    sum_delta = 0
    below0 = 0
    above1 = 0
    for start in range(0, h, 128):
        strip = array[start:start+128]
        assert np.isfinite(strip).all(), f'nonfinite source strip {start}'
        below0 += int(np.count_nonzero(strip < 0))
        above1 += int(np.count_nonzero(strip > 1))
        encoded = display(strip, baseline)
        full[start:start+128] = encoded8(encoded)
        if comparison is not None:
            delta = np.abs(encoded.astype(np.int32) - comparison[start:start+128].astype(np.int32))
            max_delta = max(max_delta, int(delta.max()))
            differing += int(np.count_nonzero(delta))
            sum_delta += int(delta.sum(dtype=np.int64))
    icc_path = Path(transform_path).parent / transform['display_icc_file']
    assert digest(icc_path) == transform['display_icc_sha256']
    icc = icc_path.read_bytes()
    complete = destination/'complete-fixed-display.png'
    Image.fromarray(full).save(complete, icc_profile=icc)
    overview = Image.fromarray(full)
    overview.thumbnail((1400, 1000), Image.Resampling.LANCZOS)
    overview_path = destination/'overview-fixed-display.png'
    overview.save(overview_path, icc_profile=icc)
    # Coordinate-grid overview is only a locator; it is never a native witness.
    locator = overview.copy()
    draw = ImageDraw.Draw(locator)
    for x in range(0, w, 1000):
        sx = round(x*locator.width/w)
        draw.line((sx, 0, sx, locator.height), fill=(150, 150, 150), width=1)
        draw.text((sx+2, 2), str(x), fill=(255,255,255), stroke_fill=(0,0,0), stroke_width=1)
    for y in range(500, h, 500):
        sy = round(y*locator.height/h)
        draw.line((0, sy, locator.width, sy), fill=(100,100,100), width=1)
        draw.text((2, sy+2), str(y), fill=(255,255,255), stroke_fill=(0,0,0), stroke_width=1)
    locator.save(destination/'locator.png', icc_profile=icc)
    report = {'label': label, 'master': meta, 'shape_verified': list(full.shape),
              'transform_file_sha256': digest(transform_path), 'transform': baseline,
              'complete_display_sha256': digest(complete), 'overview_sha256': digest(overview_path),
              'overview_size': list(overview.size), 'overview_use': 'orientation only; resized',
              'source_negative_channels': below0, 'source_above1_channels': above1,
              'numpy': np.__version__, 'python': platform.python_version(), 'argv': sys.argv,
              'script_sha256': digest(__file__)}
    if comparison is not None:
        report['display_commission'] = {'photograph_sha256': digest(compare), 'max_u16_delta': max_delta,
                'differing_channels': differing, 'mean_abs_u16_delta': sum_delta/full.size,
                'pass': max_delta <= 3, 'bar': 'max3/65535, accounts for independent float math'}
        assert max_delta <= 3, report['display_commission']
    if rois:
        report['rois'] = emit_crops(array, destination, baseline, icc, rois, label)
    write_json(destination/'readback.json', report)
    print(json.dumps({'label':label, 'destination':str(destination), 'display_commission':report.get('display_commission')}))


def emit_crops(array, destination, baseline, icc, rois, label):
    entries = []
    for roi in rois:
        x, y = roi['origins'][label]
        size = roi.get('size', 384)
        assert x >= 0 and y >= 0 and x+size <= array.shape[1] and y+size <= array.shape[0]
        crop = np.array(array[y:y+size,x:x+size], copy=True)
        encoded = encoded8(display(crop, baseline))
        path = destination/f"native-{roi['name']}.png"
        Image.fromarray(encoded).save(path, icc_profile=icc)
        read = np.array(Image.open(path))
        assert read.shape == (size,size,3) and np.array_equal(read,encoded)
        entries.append({'name':roi['name'],'origin':[x,y],'size':[size,size], 'file_sha256':digest(path),
                        'linear_pixel_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),
                        'encoded_pixel_sha256':hashlib.sha256(encoded.tobytes()).hexdigest(),
                        'sampling':'native pixel slice; no spatial resampling'})
    return entries


def commission_viewer(destination):
    destination=Path(destination)
    yy,xx=np.indices((384,384))
    a=np.zeros((384,384,3),np.uint8)
    a[:128]=np.where((xx[:128]%2)[...,None],255,0)
    a[128:256]=np.where(((xx[128:256]+yy[128:256])%2)[...,None],255,0)
    a[256:]=np.where(((xx[256:]//4)%2)[...,None],255,0)
    a[:,192]=[255,0,0]
    a[0,:]=[0,255,0]
    a[-1,:]=[0,0,255]
    p=destination/'viewer-commission-384.png'
    Image.fromarray(a).save(p)
    b=np.array(Image.open(p))
    assert np.array_equal(a,b)
    write_json(destination/'viewer-commission.json',{'shape':list(a.shape),'file_sha256':digest(p),
        'pixel_sha256':hashlib.sha256(a.tobytes()).hexdigest(),
        'expected':'top1px vertical stripes; middle1px checker; bottom4px stripes; redcolumn192; greenrow0; bluerow383',
        'roundtrip_exact':True, 'viewer_observation':'pending original-detail view_image inspection'})


def prepare():
    OUT.mkdir(parents=True,exist_ok=False)
    master=BASE/'bug-3-106/master.tiff'
    with tifffile.TiffFile(master) as tf:
        desc=tf.pages[0].description
        baseline=json.loads(desc.split('DisplayBaseline: ',1)[1])
    with tifffile.TiffFile(BASE/'bug-3-106/photograph.tiff') as tf:
        icc=tf.pages[0].tags[34675].value
    (OUT/'display-srgb.icc').write_bytes(icc)
    write_json(OUT/'fixed-transform.json',{'schema':'strehl.independent-review-transform.v1',
        'parameter_source':str(master.resolve()),'parameter_source_sha256':digest(master),
        'display_baseline':baseline,'display_icc_file':'display-srgb.icc',
        'display_icc_sha256':digest(OUT/'display-srgb.icc'),
        'policy':'Freeze106 embedded baseline; identical placement/gamut/sRGB/contrast all arms; no per-arm fit.'})
    commission_viewer(OUT)
    for label in ['bug-3-106','bug-3-107']:
        render(BASE/label/'master.tiff',OUT/label,OUT/'fixed-transform.json',label,
               compare=BASE/label/'photograph.tiff' if label=='bug-3-106' else None)


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='mode',required=True)
    sub.add_parser('prepare-baselines')
    r=sub.add_parser('render')
    r.add_argument('--master',type=Path,required=True)
    r.add_argument('--destination',type=Path,required=True)
    r.add_argument('--label',required=True)
    r.add_argument('--transform',type=Path,default=OUT/'fixed-transform.json')
    r.add_argument('--rois',type=Path)
    c=sub.add_parser('crops')
    c.add_argument('--rois',type=Path,required=True)
    args=parser.parse_args()
    if args.mode=='prepare-baselines': prepare()
    elif args.mode=='render':
        rois=json.loads(args.rois.read_text())['rois'] if args.rois else None
        render(args.master,args.destination,args.transform,args.label,rois=rois)
    else:
        transform=json.loads((OUT/'fixed-transform.json').read_text())
        rois=json.loads(args.rois.read_text())['rois']
        for label in ['bug-3-106','bug-3-107']:
            a=tifffile.memmap(BASE/label/'master.tiff',mode='r')
            entries=emit_crops(a,OUT/label,transform['display_baseline'],(OUT/'display-srgb.icc').read_bytes(),rois,label)
            write_json(OUT/label/'crop-readback.json',{'rois_file_sha256':digest(args.rois),'rois':entries,'script_sha256':digest(__file__),'argv':sys.argv})

if __name__=='__main__': main()
