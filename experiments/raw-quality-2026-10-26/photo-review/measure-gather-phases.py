"""Exact u16 phase differences in the frozen hair site; no quality score."""
from pathlib import Path
import hashlib
import json
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
receipt=json.loads((ROOT/"outputs/raw-quality-2026-10-26/weevil-anchor149-gather/capture.json").read_text())
arrays={}
for arm in ("original","gathered"):
    path=Path(receipt[arm]["path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest()==receipt[arm]["sha256"]
    arrays[arm]=np.memmap(path,mode="r",dtype="<u2",shape=(4596,6896))
result={}
for name,dy,dx in (("R",0,0),("G1",0,1),("G2",1,0),("B",1,1)):
    before=arrays["original"][640+dy:1024:2,1820+dx:2204:2]
    after=arrays["gathered"][640+dy:1024:2,1820+dx:2204:2]
    delta=after.astype(np.int32)-before.astype(np.int32)
    result[name]={"changed":int(np.count_nonzero(delta)),"total":int(delta.size),
                  "mean_abs_DN":float(np.mean(np.abs(delta))),"max_abs_DN":int(np.max(np.abs(delta)))}
(HERE/"source149-gather-1/cfa-phase-differences.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
