"""Replay a prevalidated focused-window placement using the held full-star baseline."""
from pathlib import Path
import argparse, importlib.util, json, sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=HERE/'star-full-context-placement/baseline-1'
spec=importlib.util.spec_from_file_location('focused_replay_bounds', ROOT/'experiments/full-context-placement/run.py')
common=importlib.util.module_from_spec(spec);sys.modules[spec.name]=common;spec.loader.exec_module(common)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('placement',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    placement=args.placement.resolve();out=args.out.resolve()
    assert out.is_relative_to(ROOT) and placement.is_relative_to(ROOT)
    document=json.loads(placement.read_text())
    assert document['schema_version']==1 and document['expected_frame_count']==259
    assert document['support_native']==[594,1424,392,392] and document['taper_native']==32
    assert document['native_geometry']==[7032,4688]
    assert 2 <= len(document['frames']) <= 9
    out.mkdir()
    inv=json.loads((BASE/'invocation.json').read_text())
    inputs=json.loads((BASE/'inputs.json').read_text())
    done=json.loads((BASE/'completion.json').read_text())
    cfg=json.loads((BASE/'config.json').read_text())
    assert Path(document['source_dir']).resolve()==Path(cfg['dir']).resolve()
    assert common.ref(Path(inputs['executable']['path']))==inputs['executable']
    assert common.ref(Path(done['image']['path']))==done['image']
    assert common.ref(Path(cfg['map']))==inputs['warp']
    sources=json.loads((BASE/'sources.json').read_text())
    assert all(common.ref(Path(r['path']))==r for r in sources)
    cfg.update(out=str(out/'output'),observe=False)
    common.save(out/'config.json',cfg)
    common.save(out/'provenance.json',dict(placement=common.ref(placement),baseline=done['image'],
        sources=sources,runner=common.ref(Path(__file__)),interpretation='Focused neighbourhood only; fixed original global map and all259 inputs; photographic benefit requires native review'))
    fields=dict(inv['environment'])
    fields.update(STREHL_MATCHED_SOURCE_CONFIG=str(out/'config.json'),STREHL_LOCAL_PLACEMENT_FILE=str(placement))
    for row in inputs['inputs']:
        st=Path(row['path']).stat();assert (st.st_size,st.st_mtime_ns)==(row['bytes'],row['mtime_ns'])
    common.job(inv['command'],fields,out)
    for row in inputs['inputs']:
        st=Path(row['path']).stat();assert (st.st_size,st.st_mtime_ns)==(row['bytes'],row['mtime_ns'])
    assert all(common.ref(Path(r['path']))==r for r in sources)
    receipt=json.loads((out/'output/receipt.json').read_text())
    assert receipt['source_frame_count']==259 and receipt['crop_quad_xywh']==[77,52,3362,2240]
    assert receipt['raw_count']==receipt['gathered_count']==receipt['merged_count']==0
    common.save(out/'completion.json',dict(status='FOCUSED_WINDOW_FULL_STAR_REPLAYED',image=common.ref(out/'output/replay.tiff'),original_metadata_unchanged=True))

if __name__=='__main__': main()
