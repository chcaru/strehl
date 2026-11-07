import json,numpy as np
from pathlib import Path
root=Path(r'C:\Users\chris\.codex\worktrees\multi-stack\strehl')
p=root/'outputs/multi-stack/hdr-preflight/b12-0032-blocks.npz'
with np.load(p,allow_pickle=False) as a:
 print(json.dumps({k:{'shape':a[k].shape,'dtype':str(a[k].dtype)} for k in a.files},default=list))
 for k in a.files:
  if k.endswith('_clipped'):
   b=a[k]; at=np.unravel_index(int(b.argmax()),b.shape)
   print(k,'sum',int(b.sum()),'maximum',int(b[at]),'maxblock_yx',list(map(int,at)))
