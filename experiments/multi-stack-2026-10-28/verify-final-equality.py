"""Exact output/diagnostic equality after resource scheduling changes."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
import tifffile
root=Path(__file__).resolve().parents[2];base=root/"outputs/multi-stack"
labels=sys.argv[1:-1];out=Path(sys.argv[-1]);assert len(labels)>=2
excluded={"build","renderer_source_sha256","elapsed_before_output_seconds","accumulate_seconds","gather_seconds","prepare_seconds","probe_seconds","probe_cache_hit","working_memory_reservation_bytes","transfer_prefetch","development_reference_pass","limitations"}
def clean(v):
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if k not in excluded}
 if isinstance(v,list):return [clean(x) for x in v]
 return v
sha=lambda p:hashlib.file_digest(p.open("rb"),"sha256").hexdigest()
reports=[json.loads((base/l/"render-report.json").read_text()) for l in labels]
description_changes=[]
for label,r in zip(labels[1:],reports[1:]):
 if r["limitations"]!=reports[0]["limitations"]:
  old=reports[0]["limitations"];new=r["limitations"]
  assert len(old)==len(new)==5 and old[:4]==new[:4]
  assert old[4]=="HDR currently requires equal ISO and aperture and uses exposure-time normalization; it is not a radiometrically calibrated camera response."
  assert new[4]=="HDR requires equal ISO/aperture and a bounded exposure correction validated on spatial holdouts across proposed focus pairs; this does not calibrate a general camera response."
  description_changes.append({"label":label,"field":"limitations[4]","old":old[4],"new":new[4]})
assert all(clean(r)==clean(reports[0]) for r in reports)
geometry=[json.loads((base/l/"alignment.json").read_text())["warpmap"] for l in labels]
assert all(g==geometry[0] for g in geometry)
identities=[json.loads((base/l/"source-identities.json").read_text()) for l in labels]
assert all(i==identities[0] for i in identities)
result={"status":"VERIFIED_EXACT_MECHANICS_NOT_QUALITY","labels":labels,"excluded_fields":sorted(excluded),"remaining_report_fields_equal":True,"explicitly_validated_description_changes":description_changes,"geometry_equal":True,"source_identities_equal":True,"outputs":{}}
for name in ["master.tiff","photograph.tiff"]:
 a=tifffile.memmap(base/labels[0]/name);bits=np.uint32 if a.dtype==np.float32 else np.uint16
 result["outputs"][name]={"shape":list(a.shape),"dtype":str(a.dtype),"sha256":{labels[0]:sha(base/labels[0]/name)},"differences":{}}
 for label in labels[1:]:
  b=tifffile.memmap(base/label/name);assert a.shape==b.shape and a.dtype==b.dtype
  count=sum(int(np.count_nonzero(a[y:y+128].view(bits)!=b[y:y+128].view(bits))) for y in range(0,a.shape[0],128))
  result["outputs"][name]["differences"][label]=count;assert count==0
  result["outputs"][name]["sha256"][label]=sha(base/label/name)
  del b
 del a
result["runs"]={}
for label,r in zip(labels,reports):
 receipt=base/(label+"-run")/"receipt.json"
 result["runs"][label]={"run":json.loads(receipt.read_text()) if receipt.exists() else None,"probe_cache_hits":sum(f["probe_cache_hit"] for f in r["frames"]),"probe_sum_seconds":sum(f["probe_seconds"] for f in r["frames"]),"transfer_prefetch":r.get("transfer_prefetch")}
result["command"]=[sys.executable,*sys.argv];result["script_sha256"]=sha(Path(__file__))
out.parent.mkdir(parents=True,exist_ok=True)
with out.open("x",encoding="utf-8") as f:json.dump(result,f,indent=2);f.write("\n")
print(json.dumps({"status":result["status"],"labels":labels,"runs":result["runs"]},indent=2))
