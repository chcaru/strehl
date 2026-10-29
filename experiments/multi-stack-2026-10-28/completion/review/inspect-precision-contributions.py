import os
for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):os.environ[key]="1"
from pathlib import Path
import json,hashlib,numpy as np,tifffile
R=Path(__file__).resolve().parents[4];D=R/"outputs/multi-stack/completion/hdr-precision-01";P=R/"experiments/multi-stack-2026-10-28/completion/review"
rois=json.loads((R/"experiments/multi-stack-2026-10-28/review/hdr-roi-mapped-frozen.json").read_text())["rois"]
index=json.loads((D/"contributions/index.json").read_text());report=json.loads((D/"render-report.json").read_text())
result={"schema":"strehl.frozen-witness-contributions.v1","scope":index["scope"],"report_sha256":hashlib.sha256((D/"render-report.json").read_bytes()).hexdigest(),"argv":[__file__],"bands":[]}
for b in [0,2,5]:
 band=index["bands"][b];step=band["step_quad"]*2;d={"band":b,"step_sensor":step,"witnesses":{r["name"]:{} for r in rois}}
 for name in ["effective-sources","contributing-sources","dominant-source-fraction","accepted-repeat-fraction","fixed-guide-fraction","kind"]:
  p=D/"contributions"/f"band-{b:02}"/(name+".tiff");a=tifffile.memmap(p,mode="r")
  assert list(a.shape[::-1])==band["dimensions"]
  for roi in rois:
   x,y=roi["origins"]["shared-hdr-gauge"];s=roi["size"]
   # Conservative interior samples whose centers lie inside the frozen witness.
   x0=(x+step-1)//step;y0=(y+step-1)//step;x1=(x+s)//step;y1=(y+s)//step
   v=np.asarray(a[y0:y1,x0:x1]).reshape(-1);valid=v[np.isfinite(v)]
   stats={"samples":int(v.size),"finite":int(valid.size),"min":float(valid.min()) if valid.size else None,"median":float(np.median(valid)) if valid.size else None,"max":float(valid.max()) if valid.size else None}
   if name=="kind":stats["counts"]={str(int(k)):int(n) for k,n in zip(*np.unique(valid,return_counts=True))}
   d["witnesses"][roi["name"]][name]=stats
  del a
 result["bands"].append(d)
with (P/"precision-witness-contributions.json").open("x",encoding="utf-8") as f:json.dump(result,f,indent=2,allow_nan=False);f.write("\n")
for d in result["bands"]:
 print("band",d["band"],{n:{k:round(v[k]["median"],5) if v[k]["median"] is not None else None for k in ["effective-sources","accepted-repeat-fraction","fixed-guide-fraction"]} for n,v in d["witnesses"].items()})
