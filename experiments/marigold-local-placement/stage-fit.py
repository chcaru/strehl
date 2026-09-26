"""Fixed nine-source patch extraction and unchanged green registrar; root executes."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RECIPE = ROOT/'experiments/full-stack-source-prior/recipes/marigold-4.json'
REGISTRAR = ROOT/'experiments/quality-september14/local-green-translation.py'
REGISTRAR_SHA = '5b64f7e612fd94cd8a22515bffb67addcee71021f6338f10a249c63864420196'
DECODER = ROOT/'experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe'
INDICES, ANCHOR, SUPPORT = list(range(108, 117)), 112, [3608, 3252, 392, 392]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def ref(path):
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=sha(path))


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def plan():
    import numpy as np
    recipe = read(RECIPE); warp = Path(recipe['warp_map'])
    assert sha(REGISTRAR) == REGISTRAR_SHA and sha(warp) == recipe['warp_map_sha256']
    assert len(recipe['inputs']) == 488 and recipe['expected_reference'] == 244
    assert recipe['expected_crop'] == [191, 128, 3134, 2088]
    assert recipe['expected_full_geometry'] == [3516, 2344]
    lines = warp.read_text().splitlines()
    assert 'reference 244' in lines and 'plane 3516x2344' in lines
    bits = {int(p[0]):p[2:6] for line in lines
            if len(p := line.split()) > 5 and p[0].isdigit() and p[1] == 'placed'}
    assert set(bits) == set(range(488))
    x, y, w, h = SUPPORT; centre = complex(3516, 2344)
    corners = np.array([complex(x,y), complex(x+w-1,y), complex(x,y+h-1), complex(x+w-1,y+h-1)])
    frames = []
    for index in INDICES:
        source = recipe['inputs'][index]; assert source['index'] == index
        values = [struct.unpack('>d', bytes.fromhex(v))[0] for v in bits[index]]
        a, b = complex(*values[:2]), complex(*values[2:])
        points = centre+a*(corners-centre)+2*b
        x0, y0 = (2*int(np.floor((v.min()-8)/2)) for v in (points.real, points.imag))
        x1, y1 = (2*int(np.ceil((v.max()+9)/2)) for v in (points.real, points.imag))
        assert 0 <= x0 < x1 <= 7028 and 0 <= y0 < y1 <= 4688
        frames.append(dict(index=index, source=source['path'], identity_name=source['identity_name'],
            source_bytes=source['bytes'], source_sha256=source['sha256'], source_xywh=[x0,y0,x1-x0,y1-y0],
            transform_bits=bits[index], a=values[:2], b_plane=values[2:]))
    return dict(schema=1, status='FIXED_PLAN_NO_RAW_DECODE', anchor=ANCHOR, global_reference=244,
        indices=INDICES, source_count=488, support_native=SUPPORT, taper_native=32,
        output_support_native=[3226,2996,392,392], native_sensor_shape=[4688,7032],
        libraw_visible_shape=[4688,7028], levels=[512,15360], frames=frames,
        recipe=ref(RECIPE), map=ref(warp), registrar=ref(REGISTRAR), decoder=ref(DECODER),
        choice='All eight non-anchor fits pass unchanged bars or stop; no subsets or altered interval.',
        limitation='Guide prediction is not geometric truth; a complete photograph decides practical utility.')


def extract(out):
    import numpy as np
    import rawpy
    design = read(out/'plan.json'); assert design == plan()
    folder = out/'patches'; folder.mkdir()
    records = []
    for expected in design['frames']:
        path = Path(expected['source']); before = (path.stat().st_size, path.stat().st_mtime_ns)
        assert before[0] == expected['source_bytes'] and sha(path) == expected['source_sha256']
        x,y,w,h = expected['source_xywh']
        with rawpy.imread(str(path)) as raw:
            assert raw.raw_image_visible.shape == (4688,7028)
            assert raw.raw_pattern.tolist() == [[0,1],[3,2]]
            assert list(raw.black_level_per_channel) == [512]*4 and raw.white_level == 16383
            patch = raw.raw_image_visible[y:y+h,x:x+w].copy()
        assert patch.dtype == np.uint16 and patch.shape == (h,w)
        file = folder/f"frame-{expected['index']}-cfa.npy"
        np.save(file, patch, allow_pickle=False)
        different = None
        if expected['index'] == ANCHOR:
            command = [str(DECODER),str(path),str(folder),str(ANCHOR),str(y),str(x),str(h),str(w)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=True)
            (folder/'secondary-decoder.log').write_text(result.stdout+result.stderr, encoding='utf-8')
            blob = (folder/f'rawler-{ANCHOR}.bin').read_bytes()
            assert struct.unpack('<4I', blob[:16]) == (y,x,h,w)
            other = np.frombuffer(blob, dtype='<u2', offset=16).reshape(patch.shape)
            different = int(np.count_nonzero(patch != other))
            save(folder/'secondary-decoder.json', dict(command=command, executable=ref(DECODER), different_sensels=different))
            assert different == 0, 'Independent original-u16 anchor decode disagrees.'
        assert (path.stat().st_size,path.stat().st_mtime_ns) == before
        records.append(dict(**expected, mtime_ns=before[1], patch=ref(file),
            raw_u16_sha256=hashlib.sha256(patch.astype('<u2',copy=False).tobytes()).hexdigest(),
            independently_decoded_different_sensels=different, exact_16383=int(np.count_nonzero(patch == 16383))))
        print(f"Saved original u16 source {expected['index']}; independent differences {different}", flush=True)
    save(out/'receipt.json', dict(schema=1, plan=ref(out/'plan.json'), frames=records,
        rawpy=rawpy.__version__, libraw=list(rawpy.libraw_version), original_metadata_unchanged=True,
        independent_decode_scope='Anchor112 patch only; other eight originals not independently decoded.'))


def fit(out, staged):
    import numpy as np
    design = read(staged/'plan.json'); assert design == plan()
    receipt = read(staged/'receipt.json'); assert receipt['plan'] == ref(staged/'plan.json')
    assert [r['index'] for r in receipt['frames']] == INDICES
    reg = load('marigold_fixed_green_registrar', REGISTRAR)
    save(out/'controls.json', reg.controls())  # Before reading photographic samples.
    grids = reg.grids(); guides, positions, shape = {}, {}, {}
    radius = reg.RADIUS+reg.MAX_SHIFT+reg.FD_STEP+1
    for record, expected in zip(receipt['frames'], design['frames']):
        assert all(record[key] == value for key,value in expected.items())
        file = Path(record['patch']['path']); assert ref(file) == record['patch']
        raw = np.load(file, allow_pickle=False); index = record['index']
        assert raw.dtype == np.uint16 and raw.shape == tuple(reversed(record['source_xywh'][2:]))
        assert hashlib.sha256(raw.astype('<u2',copy=False).tobytes()).hexdigest() == record['raw_u16_sha256']
        assert record['independently_decoded_different_sensels'] == (0 if index == ANCHOR else None)
        origin = record['source_xywh'][:2]
        guides[index] = reg.guide((raw.astype(np.float32)-np.float32(512))/np.float32(15360-512),origin,raw<16383)
        positions[index] = [reg.mapped(p,SUPPORT[:2],complex(3516,2344),complex(*record['a']),complex(*record['b_plane']),origin) for p in grids]
        for p in positions[index]:
            assert (p.min(axis=0)>radius).all() and (p.max(axis=0)+radius < np.array(raw.shape[::-1])-1).all()
        assert positions[index][0][:,0].max()+radius < positions[index][1][:,0].min()-radius
        shape[index] = raw.shape
    reference = [reg.sample(guides[ANCHOR],p) for p in positions[ANCHOR]]
    results = []
    for record in receipt['frames']:
        index = record['index']
        result,_ = reg.fit(guides[index],*reference,*positions[index])
        before = result['before']['validation_rmse']; after = result['after']['validation_rmse']
        ratio = after/before if before > 0 else None
        admitted = index == ANCHOR or (result['converged'] and not result['at_translation_bound']
                   and result['after']['gain_positive'] and ratio is not None and ratio < 1.0)
        if index == ANCHOR:
            assert before < 1e-12 and after < 1e-12 and np.max(np.abs(result['delta_source_native'])) < 1e-10
        results.append(dict(index=index, **result, validation_ratio=ratio, admitted=bool(admitted),
            applied_delta_source_native=[0.0,0.0] if index == ANCHOR else result['delta_source_native']))
    admitted = all(r['admitted'] for r in results)
    save(out/'result.json', dict(schema=1,status='ADMITTED_FIXED_NINE' if admitted else 'STOP_ANY_FIT_FAILED',
        full_pair_admitted=admitted, plan=ref(staged/'plan.json'), receipt=ref(staged/'receipt.json'),
        registrar=ref(REGISTRAR), all_frames=results, non_anchor_fit_count=8,
        global_reference=244, local_anchor=ANCHOR, support_native=SUPPORT, taper_native=32,
        support_radius_native=radius, support_includes='guide, bilinear footprint, all optimizer and finite-difference shifts',
        image_quality_claim=False, no_gain_or_bias_applied=True))
    print('ADMITTED_FIXED_NINE' if admitted else 'STOP_ANY_FIT_FAILED', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('plan','stage','fit','stage-child','fit-child'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--staged', type=Path)
    args = parser.parse_args(); out = args.out.resolve()
    if args.phase == 'stage-child': extract(out); return
    if args.phase == 'fit-child': fit(out,args.staged.resolve()); return
    out.mkdir(exist_ok=False)
    if args.phase in ('plan','stage'):
        save(out/'plan.json', plan())
        if args.phase == 'plan': return
    else:
        assert args.staged is not None and read(args.staged/'process.json')['exit_code'] == 0
    band = load('marigold_existing_bounds',ROOT/'experiments/band-source-agreement/run.py')
    bindings = [ref(p) for p in (Path(__file__),HERE/'design.md',REGISTRAR,RECIPE,DECODER)]
    save(out/'bindings.json',bindings)
    command = [sys.executable,'-I','-B','-X','faulthandler',str(Path(__file__)),args.phase+'-child','--out',str(out)]
    if args.staged: command += ['--staged',str(args.staged.resolve())]
    band.job(command,dict(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',RAYON_NUM_THREADS='1'),out,
             wall=120,cpu=90,gib=2)
    assert all(ref(Path(row['path'])) == row for row in bindings)
    save(out/'completion.json',dict(instrument_completed=True,phase=args.phase,sources_unchanged=True,
        result=ref(out/('receipt.json' if args.phase == 'stage' else 'result.json'))))


if __name__ == '__main__':
    main()
