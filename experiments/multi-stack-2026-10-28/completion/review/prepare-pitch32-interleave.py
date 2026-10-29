"""Stage predeclared pitch32/offset16 controls from verified existing copies only."""
from pathlib import Path
import hashlib,json,shutil,sys,time
R=Path(__file__).resolve().parents[4];B=R/"outputs/multi-stack/completion/interleave-inputs";O=R/"outputs/multi-stack/completion/interleave-pitch32-inputs"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
preparation=B/"preparation.json";records=json.loads(preparation.read_text())["copies"]
assert len(records)==182 and [v["ordinal"] for v in records]==list(range(182))
O.mkdir(exist_ok=False)
for name in ["even32","offset16"]:(O/name).mkdir()
selected=[]
for v in records:
 i=v["ordinal"]
 if i%32 not in [0,16]:continue
 arm="even32" if i%32==0 else "offset16";src=Path(v["copy"]);assert src.resolve().is_relative_to(B.resolve())
 assert src.stat().st_size==v["bytes"] and src.stat().st_mtime_ns==v["mtime_ns"] and sha(src)==v["sha256"]
 target=O/arm/src.name
 with src.open("rb") as f,target.open("xb") as out:shutil.copyfileobj(f,out,1024*1024)
 shutil.copystat(src,target)
 assert target.stat().st_size==v["bytes"] and sha(target)==v["sha256"]
 selected.append({**v,"parent_copy":v["copy"],"copy":str(target),"arm":arm})
assert len(selected)==12 and len({v["sha256"] for v in selected})==12
manifest={"version":1,"mode":"interleave","primary_pass":None,"passes":[{"name":"Pitch32 positions 0,32,64...","directories":[str(O/"even32")]},{"name":"Pitch32 offset16 positions 16,48,80...","directories":[str(O/"offset16")]}]}
for name,value in [("interleave.json",manifest),("preparation.json",{"schema":"strehl.sparse-interleave-inputs.v1","source_preparation":str(preparation),"source_preparation_sha256":sha(preparation),"argv":sys.argv,"workers":1,"original_raw_opened":False,"scope":"12 original photons from one measured tilted sweep; complementary depth sampling, not independent repeated capture or new information beyond dense182.","selection_basis":"Dense-half shape widths measured in original ordinals: median about5.6, p10 about3.2,p90 about9.2; pitch32 creates a stronger predictable focus gap than pitch8. Width is shape, not uncertainty.","witness_policy":"Freeze display/witnesses from the first completed single-half control before viewing combined pixels. Dense182 remains a separate-gauge union ceiling.","copies":selected})]:
 with (O/name).open("x",encoding="utf-8") as f:json.dump(value,f,indent=2);f.write("\n")
print(json.dumps({"manifest":str(O/"interleave.json"),"counts":{"even32":6,"offset16":6},"copied_bytes":sum(v["bytes"] for v in selected),"preparation_sha256":sha(O/"preparation.json")}))
