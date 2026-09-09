# Independent product metadata layout construction

This preserves the exact metadata-only Python body already executed once in
this source-authoring turn (tool output chunk0bf1e2, exit0,0.1007351 seconds
outer command wait). It is a record of that construction, not another run.
Invocation: the displayed body was supplied on stdin to the pinned local
Python312 with `-I -S -B -`. No candidate import or candidate function call,
TIFF payload, fixture generation, numerical operator, build or product ran.

The source read at that moment was independent-controls.py64,924 bytes,
SHA256 b090ab30cd6fe0405841f72c6d3bbc47f40a3281e1c09f548d9267165a4854e2.
Only the literal MERGE assignment was extracted with ast.literal_eval. All
other constructor fields below were independently selected after reading the
actual mod.rs/writer.rs report construction, including serde(skip) image bytes.
The later held checker has the identical MERGE literal. Paths/scalars include
impossible simultaneous maxima deliberately: this is a dominating encoded
shape for this fixed recipe, not a valid admission record or general arbitrary
path-depth guarantee. No hypothetical field is represented as observed data.

## Exact executed constructor

```python
# Metadata-only upper-shape constructor. No candidate import or function execution.
import ast,json
from pathlib import Path
source=Path('experiments/common-tiff-dimensions/independent-controls.py').read_text(encoding='utf-8')
tree=ast.parse(source)
merge=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MERGE' for t in n.targets))
def size(v):return len(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode())+1
pin={'path':'\\'*1024,'bytes':999999999,'sha256':'a'*64}
prov=dict(schema='common-tiff-stack-input-v1',id='i'*48,fixture_sha256='a'*64,color_space='linear-prophoto-d50',noise_model='synthetic-independent-rademacher8-v1',geometry='identity-common-rgb-pixels')
gate=dict(called=True,mode='on',visited_levels=4,allocated_rows=4,scope='s'*256,frames=8,levels=[dict(level=k,kind='Laplacian' if k<3 else 'mean-base',width=512,height=512,sites=262144,averaged_fraction=0.12345678901234567,zero_denominator=262144,positive_denominator=262144) for k in range(4)])
beta=[1.2345678901234567e-30]*4
fold=dict(ordinal=7,id='i'*48,file=pin,width=512,height=512,strip_count=262144,pixel_sha256='a'*64,icc_sha256='a'*64,provenance=prov,merge_sha256_before='a'*64,merge_sha256_after='a'*64,proxy_f32_sha256_before='a'*64,proxy_f32_sha256_after='a'*64,variance_f32_sha256_before='a'*64,variance_f32_sha256_after='a'*64,variance_value_before=24.0,variance_value_after=24.0,variance_sites=262144,passed_frame_beta=beta[:3],merge_frames=8,gate=gate)
plan=dict(schema='common-tiff-stack-v2',grid=dict(width=512,height=512,channels='RGB',coordinates='identity-common-rgb-pixels'),color=dict(space='linear-prophoto-d50',icc=pin),noise=dict(model='synthetic-independent-rademacher8-v1',units='rgb16-code-squared',rgb_covariance=[[64.0]*3]*3,proxy_variance=24.0,band_transfer='core-white-bandgain-v1'),merge=merge,inputs=[dict(id='i'*48,tiff=pin,pixel_sha256='a'*64,provenance=prov)]*8,output=dict(path='\\'*1024,space='linear-prophoto-d50',sample_format='RGB16',quantization='finite-clamp-round-half-away-v1'))
report=dict(schema='common-tiff-stack-result-v2',status='REFUSED',subject_complete=False,stage='publish-output',command=['\\'*512]*9,observer_mode='placebo',incomplete=pin,manifest=pin,binary=pin,consumed=[fold]*8,frame_receipts=[pin]*8,output=None,scope='s'*256,plan=plan,profile=pin,runtime=dict(rayon_threads=2,actual_core_white_band_gain=beta,passed_frame_beta=beta[:3],band_gain_scope='s'*256,proxy='(R+2G+B)/4 in RGB16 code values',variance_units='RGB16-code squared'),observer=dict(observation=dict(called=True,mode='placebo',visited_samples=786432,allocated_samples=786432,plane_major_f32_sha256='a'*64,placebo_f32_sha256='a'*64),output_f32_sha256_before='a'*64,output_f32_sha256_after='a'*64,scope='s'*256),final_gate=gate,encoding=dict(width=512,height=512,sample_format='RGB16',color_space='linear-prophoto-d50',icc_sha256='a'*64,pixel_sha256='a'*64,prequantization_f32_sha256='a'*64,clipped_low=[262144]*3,clipped_high=[262144]*3,quantization='finite-clamp-round-half-away-v1'),inputs_rechecked=True)
pre=size(report);report.update(output=pin,stage='complete',status='COMPLETE',subject_complete=True);final=size(report)
report.update(error='\x01'*2048,status='REFUSED',subject_complete=False);refusal=size(report)
frame=size(dict(schema='common-tiff-stack-frame-v2',manifest=pin,fold=fold))
assert pre<=176*1024 and final<=192*1024 and refusal<=192*1024 and frame<=16*1024
print(json.dumps(dict(prepublish=pre,final=final,full_error_refusal=refusal,frame=frame,plan=size(plan),path_characters=1024,command_fields=9,command_width=512,scope_width=256,claim='metadata envelope only; no valid payload or numerical execution')))
```

## Exact observed stdout

```json
{"prepublish": 100763, "final": 102906, "full_error_refusal": 115205, "frame": 6745, "plan": 26009, "path_characters": 1024, "command_fields": 9, "command_width": 512, "scope_width": 256, "claim": "metadata envelope only; no valid payload or numerical execution"}
```

The per-frame16KiB, prepublication176KiB and final192KiB producer guards
remain authoritative on actual execution. This constructor proves the normal
fixed population has prospective encoding room. It does not admit absent,
oversized, incomplete, malformed or process-failed future output.
