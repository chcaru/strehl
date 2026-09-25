"""Independent existing-delivery readback; no RAW decoding or source-content reread."""
from pathlib import Path
import hashlib,json,re
import numpy as np
import tifffile
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def bound(v):
    p=Path(v['path']);assert p.stat().st_size==v['bytes'] and sha(p)==v['sha256'];return p
def digest(items):
    h=0xcbf29ce484222325
    for x in items:
        for b in Path(x['path']).name.encode()+b'\0'+x['bytes'].to_bytes(8,'little')+b'\0':h=((h^b)*0x100000001b3)&((1<<64)-1)
    return f'{h:016x}'
manifest=load(ROOT/'scripts/native-build.json')
exe=ROOT/manifest['executable']['path'];assert sha(exe)==manifest['executable']['sha256']
built=load(exe.parent/'executables.json')['strehl'];bound(built)
assert Path(built['path'])==exe and built['sha256']==manifest['executable']['sha256']
assert (ROOT/manifest['source_bindings']).is_file()
corelog=(ROOT/'experiments/garnet-spatial-trace/core-suite-fixed-2/process.log').read_text()
assert '569 passed; 0 failed; 2 ignored' in corelog
rows=[];orders={};pixels={}
for name in ['garnet-104','chip-before','chip-fixed']:
    d=ROOT/'outputs/quality-september25'/name
    done=load(d/'completion.json');inv=load(d/'invocation.json');proc=load(d/'render-process.json');order=load(d/'input-order.json')
    for key in ['master','full_jpeg','overview','warp_map','executable']:bound(done[key])
    for key in ['runner','helper','harness','existing_map','executable']:bound(inv[key])
    assert proc['command']==inv['commands'][0][1] and len(inv['commands'])==1
    assert proc['exit_code']==0 and proc['error'] is None and proc['terminal_job_accounting'] and not proc['cleanup_errors']
    assert done['warp_map']==inv['existing_map'] and done['executable']==inv['executable']
    assert done['frames']==inv['frames']==len(order)
    lines=Path(done['warp_map']['path']).read_text().splitlines()
    headers=dict(x.split(' ',1) for x in lines if x.startswith(('stack-digest ','frames ','reference ','resampler ')))
    entries=[s.split() for s in lines if re.match(r'^\d+ ',s)]
    assert headers['resampler']=='catmull-rom' and headers['stack-digest']==digest(order)
    assert int(headers['frames'])==len(order) and int(headers['reference'])==len(order)//2
    assert [int(x[0]) for x in entries]==list(range(len(order))) and all(x[1]=='placed' for x in entries)
    swapped=order.copy();swapped[0],swapped[1]=swapped[1],swapped[0];assert digest(swapped)!=headers['stack-digest']
    paths=[Path(x['path']) for x in order];assert paths==sorted(paths) and len(set(paths))==len(paths)
    for p,x in zip(paths,order):assert p.is_file() and p.stat().st_size==x['bytes'] and p.stat().st_mtime_ns==x['mtime_ns']
    with tifffile.TiffFile(done['master']['path']) as tf:
        arr=tf.asarray();icc=bytes(tf.pages[0].tags[34675].value);assert len(tf.pages)==1 and icc
    assert arr.dtype==np.uint16 and list(arr.shape[:2][::-1])==done['native_dimensions']
    assert done['native_dimensions']==[2*done['crop_quad_xywh'][2],2*done['crop_quad_xywh'][3]]
    with Image.open(done['full_jpeg']['path']) as jpg:assert list(jpg.size)==done['native_dimensions'] and jpg.info['icc_profile']==icc
    ph=hashlib.sha256(arr.astype('<u2',copy=False).tobytes()).hexdigest()
    if name=='garnet-104':
        equivalence=load(ROOT/'experiments/garnet-spatial-trace/production-equivalence.json')
        with tifffile.TiffFile(equivalence['corrected_test_adapter']) as tf:
            other=tf.asarray();other_icc=bytes(tf.pages[0].tags[34675].value)
        assert np.array_equal(arr,other) and icc==other_icc and ph==equivalence['pixels_sha256'];del other
    del arr
    rows.append(dict(name=name,frames=len(order),native_dimensions=done['native_dimensions'],map_digest=headers['stack-digest'],pixel_sha256=ph,executable_sha256=done['executable']['sha256'],file_bindings_match=True,source_metadata_match=True,original_contents_reread=False,swapped_order_rejected=True))
    orders[name]=order
before=load(ROOT/'outputs/quality-september25/chip-before/invocation.json')
after=load(ROOT/'outputs/quality-september25/chip-fixed/invocation.json')
assert orders['chip-before']==orders['chip-fixed'] and before['environment']==after['environment']
def normalized_argv(inv):
    a=inv['commands'][0][1].copy();a[0]='EXE';a[a.index('--out')+1]='OUT';return a
assert normalized_argv(before)==normalized_argv(after)
result=dict(status='DELIVERY_BINDINGS_VERIFIED',rows=rows,chip_pair_same_inputs_map_flags_environment=True,garnet_production_adapter_rgb16_icc_exact=True,manifest_executable_verified=True,source_protection_scope='RAW content hashes at both endpoints are established by executed wrapper receipts; this independent readback compares order and current size/mtime, without rereading all RAW contents.')
(HERE/'delivery-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
