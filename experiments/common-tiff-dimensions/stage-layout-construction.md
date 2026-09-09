# Parent stage metadata layout construction

2026-09-08. DERIVED, metadata only. The following exact stdlib constructor ran
once during source authoring through Python -I -S -B reading this source on stdin.
It imported no controller, helper, core or numerical module; no image/process
or product/control operation ran. This document retains the construction and
observed result for independent source review, not a new operational test.

The normal fixed schedule has70 success artifact roles,26 early-refusal roles
and12 late-refusal roles. The proxy deliberately also includes three prior
bundles (render itself only needs two).512 ASCII backslashes bound escaped
FileRef width in the stated release-path domain; root must inspect actual
release paths. Remaining-fields allowance is64KiB, environment8KiB, argv4KiB.
This is not an arbitrary failure-record or arbitrary Unicode-path guarantee.

```python
import json
def raw(v):return (json.dumps(v,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
def ref():return dict(path='\\'*512,bytes=1638400,sha256='f'*64)
folds=(2,5,8,5,5,5,5,5,3)+(0,)*13+(4,4)
cases=[]
for i,n in enumerate(folds):
    names=['report.json','report.incomplete.json']+[f'report.frame-{j}.json' for j in range(n)]
    if i<9:names.append('output.tiff')
    cases.append(dict(ordinal=i,id='x'*48,expected_exit_code=int(i>=9),expected_folded_frames=n,
                      artifacts={name:ref() for name in names}))
value=dict(schema='common-tiff-dimensions-owned-stage-v1',status='COMPLETE_STAGE_UNVERIFIED',
           stage='render',release=ref(),invocation=['x'*4090],children=[ref() for _ in range(24)],
           artifacts=dict(cases=cases),prerequisites={p:{role:ref() for role in
           ('result','tail','outer','stdout','stderr','exit')} for p in ('build','prepare','render')},
           operations=[dict(ordinal=i,expected_exit_code=int(i>=9),status='EXPECTED_PROCESS_DISPOSITION') for i in range(24)],
           environment='x'*8192,remaining_fields_allowance='x'*65536)
size=len(raw(value))
M=1<<20;K=1024
reserve=3*256*K
case=2*1638400+8*16*K+2*192*K+4*K
physical={
'build':64*M+16*M+32*K+2*256*K+8*K,
'prepare':32*M+256*K+32*K+2*256*K+8*K,
'render':24*case+24*256*K+24*32*K+2*256*K+8*K,
'verify':16*M+M+32*K+2*256*K+8*K}
caps={'build':128*M,'prepare':34*M,'render':128*M,'verify':19*M}
assert size<256*K
assert all(physical[k]+reserve<caps[k] for k in physical)
print(json.dumps(dict(normal_complete_parent_proxy_bytes=size,parent_cap=256*K,artifacts=sum(len(c['artifacts']) for c in cases),
                     widest_FileRef_bytes=len(raw(ref())),physical_bytes=physical,scan_reserved_bytes=reserve,
                     remaining={k:caps[k]-physical[k]-reserve for k in physical}),indent=2))
```

Observed stdout JSON:

```json
{
  "normal_complete_parent_proxy_bytes": 255854,
  "parent_cap": 262144,
  "artifacts": 108,
  "widest_FileRef_bytes": 1128,
  "physical_bytes": {
    "build": 84451328,
    "prepare": 34381824,
    "render": 98934784,
    "verify": 18391040
  },
  "scan_reserved_bytes": 786432,
  "remaining": {
    "build": 48979968,
    "prepare": 483328,
    "render": 34496512,
    "verify": 745472
  }
}
```

Source/read review still owns field coverage. Atomic encoding enforces the
actual262144-byte cap; this proxy cannot authorize dropping rows or recovery
links. The separate product N8 report needs its own independent size check.
