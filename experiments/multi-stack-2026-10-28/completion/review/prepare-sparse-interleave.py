"""Stage predeclared pitch8/offset4 controls from verified existing copies only."""
from pathlib import Path
import hashlib,json,shutil,sys,time
R=Path(__file__).resolve().parents[4];B=R/"outputs/multi-stack/completion/interleave-inputs";O=R/"outputs/multi-stack/completion/interleave-pitch8-inputs"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
preparation=B/"preparation.json";records=json.loads(preparation.read_text())["copies"]
assert len(records)==182 and [v["ordinal"] for v in records]==list(range(182))
O.mkdir(exist_ok=False)
for name in ["even8","offset4"]:(O/name).mkdir()
selected=[]
for v in records:
 i=v["ordinal"]
 if i%8 not in [0,4]:continue
 arm="even8" if i%8==0 else "offset4";src=Path(v["copy"]);assert src.resolve().is_relative_to(B.resolve())
 assert src.stat().st_size==v["bytes"] and src.stat().st_mtime_ns==v["mtime_ns"] and sha(src)==v["sha256"]
 target=O/arm/src.name
 with src.open("rb") as f,target.open("xb") as out:shutil.copyfileobj(f,out,1024*1024)
 shutil.copystat(src,target)
 assert target.stat().st_size==v["bytes"] and sha(target)==v["sha256"]
 selected.append({**v,"parent_copy":v["copy"],"copy":str(target),"arm":arm})
assert len(selected)==46 and len({v["sha256"] for v in selected})==46
manifest={"version":1,"mode":"interleave","primary_pass":None,"passes":[{"name":"Pitch8 positions 0,8,16...","directories":[str(O/"even8")]},{"name":"Pitch8 offset4 positions 4,12,20...","directories":[str(O/"offset4")]}]}
for name,value in [("interleave.json",manifest),("preparation.json",{"schema":"strehl.sparse-interleave-inputs.v1","source_preparation":str(preparation),"source_preparation_sha256":sha(preparation),"argv":sys.argv,"workers":1,"original_raw_opened":False,"scope":"46 original photons from one measured tilted sweep; complementary depth sampling, not independent repeated capture or new information beyond dense182.","witness_policy":"Freeze display/witnesses from the first completed single-half control before viewing combined pixels. Dense182 remains a separate-gauge union ceiling.","copies":selected})]:
 with (O/name).open("x",encoding="utf-8") as f:json.dump(value,f,indent=2);f.write("\n")
print(json.dumps({"manifest":str(O/"interleave.json"),"counts":{"even8":23,"offset4":23},"copied_bytes":sum(v["bytes"] for v in selected),"preparation_sha256":sha(O/"preparation.json")}))
