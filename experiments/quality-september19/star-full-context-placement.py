"""Prepared paired full-star RAW consumer replay; root executes after Rust gates."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / 'star-full-context-placement'
COMMON_PATH = ROOT / 'experiments/full-context-placement/run.py'
spec = importlib.util.spec_from_file_location('star_common_runner', COMMON_PATH)
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
MAP = HERE / 'star-baseline-1/star.warpmap.txt'
MAP_HASH = '6594d98255383218a3114fd783bfd0e2215b39b202777f1ee2e493f4b287a6a1'
FIT = HERE / 'star-porous-translation-1/fit/result.json'
SAMPLES = HERE / 'star-porous-translation-1/porous-grain/receipt.json'
RAW = Path('D:/personal/macro/requests/misc-diagnostic/star-sand-cpl')
REGIONS = {
    'core': [472,1352,328,328],
    'left-transition': [394,1352,128,328],
    'right-transition': [750,1352,128,328],
    'top-transition': [472,1276,328,128],
    'bottom-transition': [472,1630,328,128],
    'far-control': [1392,1168,328,328],
}


def configure():
    OUT.mkdir(exist_ok=False)
    assert hashlib.sha256(MAP.read_bytes()).hexdigest() == MAP_HASH
    fit = json.loads(FIT.read_text())
    assert len(fit['rois']) == 1 and fit['rois'][0]['roi'] == 'porous-grain'
    data = fit['rois'][0]
    assert data['target_origin_native'] == [594,1424]
    samples = json.loads(SAMPLES.read_text())
    assert samples['reference_index'] == 129 and samples['map_sha256'] == MAP_HASH
    originals = {row['index']:row for row in samples['frames']}
    bits = {int(p[0]):p[2:6] for line in MAP.read_text().splitlines()
            if len(p:=line.split())>5 and p[0].isdigit() and p[1]=='placed'}
    rows = []
    assert [r['frame'] for r in data['frames']] == list(range(125,134))
    for row in data['frames']:
        index = row['frame']
        assert row['converged'] and not row['at_translation_bound']
        assert row['after']['gain_positive']
        if index != 129:
            assert row['validation_ratio'] < 1
        original = originals[index]
        # Bind published fit geometry to the exact bits consumed by Rust.
        decoded = [struct.unpack('>d', bytes.fromhex(v))[0] for v in bits[index]]
        assert decoded == original['a']+original['b_plane']
        delta = [0.0,0.0] if index==129 else row['delta_source_native']
        rows.append(dict(file_name=Path(original['source']).name,transform_bits=bits[index],delta_source_native=delta))
    config = dict(schema_version=1,source_dir=str(RAW),expected_frame_count=259,
                  native_geometry=[7032,4688],support_native=[594,1424,392,392],taper_native=32,frames=rows)
    common.save(OUT / 'star-config.json',config)
    common.save(OUT / 'frozen-comparison.json',dict(output_native_regions=REGIONS,
        output_shape=[4480,6724,3],sensor_crop_origin=[154,104],support_sensor_xywh=[594,1424,392,392],
        interpretation='Native core, taper boundaries and distant ridged-shell control frozen before paired renders; no sharpness score'))
    common.save(OUT / 'provenance.json',dict(config=common.ref(OUT/'star-config.json'),fit=common.ref(FIT),
        samples=common.ref(SAMPLES),map=common.ref(MAP),runner=common.ref(Path(__file__)),
        reference_delta='Frame129 forced to exact [0,0]; fitting a frame to itself is not motion',
        mutation_scope='Only neighbours125..133, inside 392 native support with taper32; all other frames/locations retain zero correction',
        comparison='All259 original RAWs; seven Laplacian bands + base; same pinned tone; observer disabled',
        tone=dict(black=.01566,white=.51099,contrast=.55),status='PREPARED_NOT_EXECUTED'))


def replay(args):
    output = (args.out or OUT/(args.phase+'-1')).resolve()
    output.mkdir(exist_ok=False)
    provenance = json.loads((OUT/'provenance.json').read_text())
    for key,path in (('config',OUT/'star-config.json'),('fit',FIT),('samples',SAMPLES),('map',MAP),('runner',Path(__file__))):
        assert common.ref(path) == provenance[key], f'Frozen input changed: {key}'
    build = args.build.resolve()
    exe = build/'cli-tests.exe'
    artifacts = json.loads((build/'executables.json').read_text())
    assert common.ref(exe) == artifacts['cli-tests']
    sources = json.loads((build/'sources.json').read_text())
    assert all(common.ref(Path(r['path'])) == r for r in sources)
    common.save(output/'sources.json',sources)
    files = sorted(p for p in RAW.iterdir() if p.is_file() and p.suffix.upper()=='.ARW')
    assert [p.name for p in files] == [f'DSC{i:05d}.ARW' for i in range(16,275)]
    inputs = [dict(path=str(p),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns) for p in files]
    cfg = dict(dir=str(RAW),map=str(MAP),out=str(output/'output'),frames=259,
               tone=dict(black=.01566,white=.51099,contrast=.55),observe=False,
               regions=[dict(name='porous-grain',frame=129,x=472,y=1352,width=328,height=328)])
    common.save(output/'config.json',cfg)
    fields = dict(RAYON_NUM_THREADS='8',STREHL_PYRAMID_WORKERS='8',STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1',STREHL_DIRECT_PLANES='rounded',STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel',STREHL_GPU_GATHER='on',STREHL_GPU_SCHEDULE='device',
        STREHL_GPU_GATHER_LOG='off',STREHL_DEFECT='off',STREHL_WARPMAP=str(MAP),
        STREHL_MATCHED_SOURCE_CONFIG=str(output/'config.json'))
    if args.phase == 'candidate':
        fields['STREHL_LOCAL_PLACEMENT_FILE'] = str(OUT/'star-config.json')
        common.save(output/'placement-binding.json',common.ref(OUT/'star-config.json'))
    common.save(output/'inputs.json',dict(inputs=inputs,warp=common.ref(MAP),executable=common.ref(exe),runner=common.ref(Path(__file__))))
    command = [str(exe),'merge_cmd::matched_source_tests::matched_source_actual_consumer','--exact','--ignored','--nocapture','--test-threads=1']
    common.job(command,fields,output)
    for record in inputs:
        st = Path(record['path']).stat()
        assert (st.st_size,st.st_mtime_ns)==(record['bytes'],record['mtime_ns'])
    assert all(common.ref(Path(r['path']))==r for r in sources)
    log = (output/'process.log').read_text(encoding='utf-8',errors='replace')
    assert '7 Laplacian levels + 1 base' in log and 'reference frame 129, 259 placed' in log
    receipt = json.loads((output/'output/receipt.json').read_text())
    assert receipt['source_frame_count']==259 and receipt['crop_quad_xywh']==[77,52,3362,2240]
    assert receipt['raw_count']==receipt['gathered_count']==receipt['merged_count']==0
    common.save(output/'completion.json',dict(status='FULL_STAR_STACK_REPLAYED',input_frames=259,
        image=common.ref(output/'output/replay.tiff'),original_metadata_unchanged=True,pinned_tone=True,observer=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('configure','baseline','candidate'))
    parser.add_argument('--build',type=Path,default=ROOT/'experiments/full-context-placement/build-2')
    parser.add_argument('--out',type=Path)
    args = parser.parse_args()
    if args.phase=='configure': configure()
    else: replay(args)
