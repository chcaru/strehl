"""Collect retained command receipts and full output hashes; no image transformations."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[2];base=root/"outputs/multi-stack";out=Path(__file__).parent/"results";out.mkdir(exist_ok=True)
labels="single-route-6 insect-repeat-4 insect-pooled-4 insect-only-106-4 insect-only-107-4 insect-primary-6 slide-hdr-5 slide-hdr-pair-6 hdr-short-7 hdr-long-7 fabric-aperture-layers-6 insect-repeat-7 prefetch-a1 prefetch-b1 prefetch-b2 prefetch-a2 packaged-pilot".split()
result={"base":"c149e52834fc1c86c2af0fe022713c39fa25f33c","runs":{},"verification":{}}
sha=lambda p:hashlib.file_digest(p.open("rb"),"sha256").hexdigest()
for label in labels:
 folder=base/label;r=json.loads((base/(label+"-run")/"receipt.json").read_text(encoding="utf-8-sig"))
 expected=("failed",1) if label=="slide-hdr-5" else ("complete",0)
 assert (r["state"],r["exit_code"])==expected,(label,r)
 entry={"receipt":r,"artifacts":{}}
 names="source-identities.json alignment.json calibration.json photometry.json render-report.json completed.json photograph.tiff master.tiff".split()
 for p in [folder/name for name in names]+list(folder.glob("layer-*/*.tiff")):
  if p.exists():entry["artifacts"][p.relative_to(folder).as_posix()]={"bytes":p.stat().st_size,"sha256":sha(p)}
 result["runs"][label]=entry
for name in ["prefetch-equality.json","final-full-equality.json","package-equality.json","package-verification.json","single-route-6/regression.json","docs-link-check.json"]:
 result["verification"][name]=json.loads((base/name).read_text(encoding="utf-8-sig"))
for name in ["candidate-7/build.json","desktop-package/desktop-package.json"]:
 data=json.loads((base/name).read_text(encoding="utf-8-sig"));result["verification"][name]={k:v for k,v in data.items() if k!="owned_source_sha256"}
(out/"evidence.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print("saved",out/"evidence.json",(out/"evidence.json").stat().st_size)
