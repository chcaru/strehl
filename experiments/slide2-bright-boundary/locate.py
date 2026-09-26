"""Frozen slide2 locator adapted only to the three current gray-fan sites.

Retains at most six structured region/frame pairs and the fixed pale149 patch.
Original u16 is copied inside RawPy lifetime. No full RGB postprocess or merge.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import math
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRIOR_LOCATOR = ROOT / 'experiments/slide2-focus-witness/locate.py'
PRIOR_SHA = 'f282e6d1b83e14ac3b44c18d0d73b3b2bb742d8151e67a34553c771f9cbb30bc'
PRIOR_CONFIG = ROOT / 'experiments/quality-september20/slide2-source-config.json'
COORDINATES = ROOT / 'experiments/slide2-focus-witness/render-1/broad-artifact-inspection/coordinates.json'
OLD = ROOT / 'experiments/quality-september14/focus-locator.py'
OLD_SHA = '8c75f1a14fd0024774954a31423f4bf5bcf6bedc9dc5b4840cb0e22d450edb03'
PARSER = ROOT / 'experiments/M-PHASE0-PHASE/src/clib.py'
PARSER_SHA = '95d557d38855d720322d96edd57c2b654f6b8ea1af49fabb66df08ad5d93e0d2'
CONFIG = HERE / 'config.json'
CONFIG_SHA = '9607ee4a966cbea5266cd519a9a7399ef8238c8277300f480915d1c5e60f300b'
BASE = ROOT / 'experiments/quality-september20/slide2-baseline-1'
GOLDEN = ROOT / 'experiments/quality-september20/slide2-source-1/on/output'
SECONDARY = ROOT / 'experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe'
BOUNDED = ROOT / 'experiments/m193c-output-grid/bounded-process.py'
HARNESS = ROOT / 'experiments/m12-scorecard/m12-harness.py'
MAP_SHA = '7712a5eb7f74001485bc69b9d9721fe1bde4c0aa8099e28ddf703ede8069c14a'
STRUCTURED = ('qr-upper', 'qr-lower', 'siemens-contact')
FIXED = [('qr-upper',3700,490),('qr-lower',3900,900),
         ('siemens-contact',5260,750),('pale-control',792,600)]
CONTENT_SCOPE = ('Retained baseline all299 original-content audit plus current metadata/order; '
                 'no fresh all299 original-content hash. Selected copied sensels independently decoded.')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def ref(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def inventory(source):
    # Python directory enumeration includes hidden/system names; no shell glob.
    return [dict(path=str(p.resolve()), bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns)
            for p in sorted(source.iterdir()) if p.is_file()]


def score_control(out):
    import numpy as np
    from scipy.ndimage import gaussian_filter
    assert ref(OLD)['sha256'] == OLD_SHA
    tree = ast.parse(OLD.read_text(encoding='utf-8'))
    child = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == 'child')
    definition = next(n for n in child.body if isinstance(n,ast.FunctionDef) and n.name == 'score')
    scope = dict(np=np, gaussian_filter=gaussian_filter)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[definition],type_ignores=[])),str(OLD),'exec'),scope)
    score = scope['score']
    rng = np.random.default_rng(14092026)
    yy,xx = np.mgrid[:150,:150]
    flat = np.full((150,150),1000,dtype=np.float32)
    texture = flat+100*np.cos((xx+.3*yy)*2*np.pi/12)
    values = dict(flat=score(flat), flat_noise_sigma10=score(flat+rng.normal(0,10,flat.shape)),
                  flat_noise_sigma100=score(flat+rng.normal(0,100,flat.shape)),
                  sharp_texture=score(texture), blurred_texture=score(gaussian_filter(texture,5)))
    assert values['flat'] == 0 and values['flat_noise_sigma100'] > values['flat_noise_sigma10'] > 0
    assert values['sharp_texture'] > values['blurred_texture']
    assert values['flat_noise_sigma100'] > values['blurred_texture']
    save(out/'controls.json',dict(passed=True, values=values, old_locator_sha256=OLD_SHA,
        failure_input='A noisy flat must outrank blurred texture on this same score path.',
        interpretation='Nomination only: noise, contrast, defocus and scale can change the score.'))
    return score


def locations(index, warp, clib, regions):
    a,b = warp['placements'][index]
    rows = []
    for region in regions:
        x,y,w,h = (region[k] for k in ('x','y','width','height'))
        # Same plane-domain expression and positive Rust .round()/even origin
        # as matched-source-tests.rs. Do not round the whole map to identity.
        mx,my = clib.apply_at(a,b,(x+w/2)/2+139,(y+h/2)/2+93,1758,1172)
        sx = int(math.floor(2*mx-w/2+.5)) & ~1
        sy = int(math.floor(2*my-h/2+.5)) & ~1
        rows.append(dict(name=region['name'], reference_output_xywh=[x,y,w,h],
                         source_xywh=[sx-4,sy-4,w+8,h+8], trim=4))
    return rows


def copied_patches(path, rows):
    import numpy as np
    import rawpy
    result = {}
    with rawpy.imread(str(path)) as raw:
        assert raw.raw_pattern.tolist() == [[0,1],[3,2]]
        assert raw.raw_image_visible.shape == (4688,7028)
        assert list(raw.black_level_per_channel) == [512]*4 and raw.white_level == 16383
        for row in rows:
            x,y,w,h = row['source_xywh']
            assert x%2 == y%2 == 0 and 0 <= x < x+w <= 7028 and 0 <= y < y+h <= 4688
            result[row['name']] = raw.raw_image_visible[y:y+h,x:x+w].copy()
            assert result[row['name']].dtype == np.uint16 and result[row['name']].shape == (h,w)
    return result


def child(out):
    import numpy as np
    import rawpy
    from scipy.ndimage import gaussian_filter1d
    from PIL import Image
    score = score_control(out)  # FIRST, before any source pixel read.
    assert ref(CONFIG)['sha256'] == CONFIG_SHA and ref(PARSER)['sha256'] == PARSER_SHA
    assert ref(PRIOR_LOCATOR)['sha256'] == PRIOR_SHA
    cfg = read(CONFIG)
    prior_cfg = read(PRIOR_CONFIG)
    assert {k:v for k,v in cfg.items() if k!='regions'} == {k:v for k,v in prior_cfg.items() if k!='regions'}
    assert read(COORDINATES) == {name:[x,y,384,384] for name,x,y in FIXED[:3]}
    assert cfg['regions'][-1] == prior_cfg['regions'][-1]
    assert cfg['frames'] == 299
    assert [(r['name'],r['x'],r['y']) for r in cfg['regions']] == FIXED
    assert all(r['width'] == r['height'] == 384 and r['frame'] == 149 for r in cfg['regions'])
    source = Path(cfg['dir']); map_path = Path(cfg['map'])
    assert ref(map_path)['sha256'] == MAP_SHA
    clib = load('slide2_locator_map',PARSER)
    warp = clib.parse_warpmap(str(map_path))
    assert warp['frames'] == warp['placed_count'] == 299 and warp['reference_index'] == 149
    assert warp['plane'] == (3516,2344) and not warp['refusals']
    before = inventory(source)
    assert before == read(BASE/'inputs.json')['inventory']
    assert [Path(r['path']).name for r in before] == [f'DSC{i:05d}.ARW' for i in range(1,300)]
    save(out/'originals-before.json',before)
    receipt = read(GOLDEN/'receipt.json')
    assert receipt['source_frame_count'] == 299 and receipt['crop_quad_xywh'] == [139,93,3238,2158]
    wb = np.asarray(receipt['wb_bits'],dtype='<u4').view('<f4')
    black,white = np.asarray(receipt['levels'],dtype=np.float32)
    assert [float(black),float(white)] == [512.0,15360.0]
    scores = np.zeros((299,4),dtype=np.float64)
    records = []; first_pass_hashes = []; cached149 = None; golden_checks = []
    for index,info in enumerate(before):
        path = Path(info['path']); st = path.stat()
        assert (st.st_size,st.st_mtime_ns) == (info['bytes'],info['mtime_ns'])
        rows = locations(index,warp,clib,cfg['regions'])
        patches = copied_patches(path,rows)
        hashes = {}
        for k,row in enumerate(rows):
            patch = patches[row['name']]
            core = patch[4:-4,4:-4]
            # G1 only nominates. G2 is never silently averaged or used to rerank.
            scores[index,k] = score(core[0::2,1::2])
            hashes[row['name']] = hashlib.sha256(patch.tobytes()).hexdigest()
            # Only pale-control is unchanged. Old bar goldens cannot validate
            # the new QR/Siemens positions; their selected patches get the
            # same independent rawler comparison below.
            if index == 149 and row['name'] == 'pale-control':
                old = next(p for p in receipt['patches'] if p['stage']=='raw' and p['name']==row['name'])
                assert old['padded_origin_xy'] == row['source_xywh'][:2]
                assert [old['width'],old['height']] == row['source_xywh'][2:]
                yy,xx = np.indices(patch.shape)
                channel = np.where((xx+yy)%2,1,np.where(yy%2,2,0))
                normalized = np.maximum(patch.astype(np.float32)-black,np.float32(0))*wb[channel]/(white-black)
                expected = np.fromfile(GOLDEN/(old['stem']+'-cfa.f32'),dtype='<f4').reshape(patch.shape)
                differing = int(np.count_nonzero(normalized.view('<u4') != expected.view('<u4')))
                assert differing == 0, 'Actual source149 coordinate/normalization golden differs'
                golden_checks.append(dict(region=row['name'],different_cfa_f32_bits=differing))
        if index == 149:
            cached149 = patches  # Four small u16 patches, not a full frame.
        a,b = warp['placements'][index]
        records.append(dict(frame_index=index,source=str(path),rois=rows,
                            a=[a.real,a.imag],b_plane=[b.real,b.imag],scale=abs(a)))
        first_pass_hashes.append(hashes)
        if index%25 == 0 or index == 298:
            print(json.dumps(dict(stage='locate',frame=index)),flush=True)
    assert np.isfinite(scores).all() and cached149 is not None
    # Explicit temporal smoothing of scalar curves only, no frame-axis image filter.
    smooth = gaussian_filter1d(scores,sigma=2,axis=0,mode='nearest')
    nominations = {}
    chosen = []
    for k,name in enumerate(STRUCTURED):
        peak = int(np.argmax(smooth[:,k]))
        neighbor = peak+2 if peak+2 < 299 else peak-2
        nominations[name] = [peak,neighbor]
        for index in (peak,neighbor):
            chosen.append((index,k))
    assert len(chosen) == 6 and len(set(chosen)) == 6
    chosen.append((149,3))
    fixed_control = dict(name='pale-control',frame=149)
    save(out/'locator.json',dict(schema=1,reference_index=149,crop_quad_xywh=[139,93,3238,2158],
        map_sha256=MAP_SHA,config=ref(CONFIG),regions=cfg['regions'],nominations=nominations,
        fixed_control=fixed_control,records=records,score_curves=scores.tolist(),
        smoothed_score_curves=smooth.tolist(),first_pass_patch_sha256=first_pass_hashes,
        nomination='G1 pooled scalar, fixed sigma2 temporal smoothing; first argmax then +2, or -2 at endpoint',
        support='Complete384 native core; G1 original pitch2, old score interior trim4 green samples',
        source_rounding='Actual observer: floor(native_origin+.5), then clear low bit; padded4 native',
        interpretation='Nominations only; pale curve is diagnostic, not a calibrated flat/noise test; G2 does not nominate.'))
    checks = []; saved = []; redecodes = 0
    for index in sorted({i for i,_ in chosen}):
        selected = [k for i,k in chosen if i == index]
        rows = [records[index]['rois'][k] for k in selected]
        path = Path(before[index]['path'])
        if index == 149:
            patches = {r['name']:cached149[r['name']] for r in rows}
        else:
            patches = copied_patches(path,rows); redecodes += 1
        assert redecodes <= 6
        x0 = min(r['source_xywh'][0] for r in rows); y0 = min(r['source_xywh'][1] for r in rows)
        x1 = max(r['source_xywh'][0]+r['source_xywh'][2] for r in rows)
        y1 = max(r['source_xywh'][1]+r['source_xywh'][3] for r in rows)
        command = [str(SECONDARY),str(path),str(out),str(index),str(y0),str(x0),str(y1-y0),str(x1-x0)]
        result = subprocess.run(command,capture_output=True,text=True,check=True,timeout=30)
        (out/f'selected-{index}-secondary.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        blob = (out/f'rawler-{index}.bin').read_bytes()
        assert struct.unpack('<4I',blob[:16]) == (y0,x0,y1-y0,x1-x0)
        other = np.frombuffer(blob,dtype='<u2',offset=16).reshape(y1-y0,x1-x0)
        for row in rows:
            name = row['name']; patch = patches[name]; x,y,w,h = row['source_xywh']
            assert hashlib.sha256(patch.tobytes()).hexdigest() == first_pass_hashes[index][name]
            different = int(np.count_nonzero(patch != other[y-y0:y-y0+h,x-x0:x-x0+w]))
            assert different == 0, 'Independent nominated RAW decode differs'
            filename = out/f'frame-{index}-{name}-cfa.npy'
            np.save(filename,patch,allow_pickle=False)
            core = patch[4:-4,4:-4]
            panels = []
            for label,dx,dy in [('g1',1,0),('g2',0,1)]:
                plane = core[dy::2,dx::2].astype(np.float32)
                normalized = (plane-np.float32(512))/np.float32(16383-512)
                display = np.rint(255*np.clip(normalized*np.float32(2.809),0,1)**(1/2.2)).astype(np.uint8)
                assert display.shape == (192,192)
                png = out/f'frame-{index}-{name}-{label}.png'
                Image.fromarray(display).save(png)
                assert np.array_equal(np.asarray(Image.open(png)),display)
                panels.append(ref(png))
            checks.append(dict(frame_index=index,region=name,different_sensels=different,command=command))
            saved.append(dict(frame_index=index,region=name,source_xywh=row['source_xywh'],
                              cfa=ref(filename),green_panels=panels))
        print(json.dumps(dict(stage='selected_ready',frame=index,regions=[r['name'] for r in rows])),flush=True)
    after = inventory(source)
    save(out/'originals-after.json',after)
    assert before == after
    assert len(checks) == 7 and len(golden_checks) == 1
    save(out/'locator-result.json',dict(status='FOCUS_NEIGHBOURHOODS_READY',passed=True,
        controls_passed=True,original_metadata_unchanged=True,independent_decode_exact=True,
        config=ref(CONFIG),locator=ref(out/'locator.json'),nominations=nominations,fixed_control=fixed_control,
        source_inventory=ref(out/'originals-before.json'),original_content_scope=CONTENT_SCOPE,
        independent_decode_checks=checks,source149_golden_checks=golden_checks,saved=saved,
        original_pass_decodes=299,selected_redecodes=redecodes,full_rgb_postprocesses=0,
        rawpy_version=rawpy.__version__,libraw_version=list(rawpy.libraw_version),
        adaptation=dict(prior_locator=ref(PRIOR_LOCATOR),current_only_sites=ref(COORDINATES),
            changes='Three fixed site coordinates/names and config binding; old source149 golden only at unchanged pale-control; nomination/decoder/display unchanged'),
        display='G1/G2 separately192x192 original same-colour samples at native pitch2; fixed gain2.809 gamma1/2.2; no resize',
        limitation='Source-centred, unaligned, CA-off, fixed monochrome display; actual product matched-source render still required.'))
    assert sum(p.stat().st_size for p in out.iterdir() if p.is_file()) < 64<<20


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--child',action='store_true')
    args = parser.parse_args(); out = args.out.resolve()
    assert out.is_relative_to(HERE)
    if args.child:
        assert out.is_dir(); child(out); return
    out.mkdir(exist_ok=False)
    b = load('slide2_locator_bounded',BOUNDED)
    paths = [Path(__file__),PRIOR_LOCATOR,PRIOR_CONFIG,COORDINATES,HERE/'plan.md',OLD,PARSER,CONFIG,BOUNDED,HARNESS,SECONDARY,
             BASE/'inputs.json',BASE/'completion.json',GOLDEN/'receipt.json',Path(read(CONFIG)['map'])]
    paths += [GOLDEN/'pale-control-frame149-raw-cfa.f32']
    sources = [ref(p) for p in paths]
    save(out/'bindings.json',sources)
    env,removed = b.clean_environment(dict(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
        MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',RAYON_NUM_THREADS='1').items())
    api = b.load_job_api(b.binding(HARNESS))
    command = [sys.executable,'-I','-B','-X','faulthandler',str(Path(__file__).resolve()),'--out',str(out),'--child']
    save(out/'invocation.json',dict(command=command,removed_environment=removed,
        configured_environment={k:env[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','RAYON_NUM_THREADS')},
        limits=dict(wall_seconds=240,cpu_seconds=1200,committed_bytes=2<<30,log_bytes=4<<20)))
    result = b.run(command,env,ROOT,out/'process.log',api=api,wall_seconds=240,cpu_seconds=1200,
                   log_bytes=4<<20,committed_bytes=2<<30)
    save(out/'process.json',result)
    unchanged = all(ref(Path(row['path'])) == row for row in sources)
    save(out/'source-check.json',dict(unchanged=unchanged))
    assert result['exit_code'] == 0 and result['error'] is None and result['terminal_job_accounting'] and unchanged
    completion = read(out/'locator-result.json')
    completion.update(process=ref(out/'process.json'),sources=ref(out/'bindings.json'),sources_unchanged=True)
    save(out/'completion.json',completion)
    print(json.dumps(dict(status=completion['status'],nominations=completion['nominations'],accounting=result['job_accounting'])))


if __name__ == '__main__':
    main()
