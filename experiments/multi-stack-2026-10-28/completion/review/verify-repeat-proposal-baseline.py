"""Verify copied fixture / EqualObservation did not change original equal arms."""
from pathlib import Path
import json,hashlib,argparse,sys
ap=argparse.ArgumentParser();ap.add_argument("new",type=Path);ap.add_argument("output",type=Path);ap.add_argument("old",type=Path,nargs="+");a=ap.parse_args();assert not a.output.exists()
r=json.loads(a.new.read_text());current={(x["case"],x["arm"],x["seed"]):x for x in r["rows"]}
arm_map={"proposal":"equal-proposed","legacy-partial":"legacy-partial","all-single":"all-single","proposal-primary-a":"equal-primary-a","pass-a":"pass-a","pass-b":"pass-b"}
checks=[]
for path in a.old:
 old=json.loads(path.read_text());count=0
 for row in old["rows"]:
  name=arm_map[row["arm"]];key=(row["case"],name,row["seed"])
  if key not in current:continue
  new=current[key]
  for k in ["against_clean_all_single","against_clean_passes"]:assert row[k]==new[k],(path,key,k)
  for x,y in zip(row["diagnostics"],new["diagnostics"]):assert all(y[k]==v for k,v in x.items()),(path,key,"diagnostics")
  count+=1
 checks.append({"file":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"rows_exact":count})
result={"command":sys.argv,"analyzer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"new_sha256":hashlib.sha256(a.new.read_bytes()).hexdigest(),"checks":checks,"scope":"All shared saved clean/noisy per-color and per-target numerical summaries and original diagnostic counters exact; full arrays were not retained by old fixture."}
a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8");print(json.dumps(result,indent=2))
