"""Summarize saved candidate/native evidence without reading or rendering RAW."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument("run",type=Path)
parser.add_argument("--out",type=Path,required=True)
args=parser.parse_args()
raw=(args.run/"mosaic-native-measurements.json").read_bytes()
receipts=json.loads(raw)
session=json.loads((args.run/"session.json").read_text())
rows=[]
for receipt in receipts:
    c=receipt["candidate"]
    source_ids=[c["source_a"],c["source_b"]]
    passes=[c["pass_a"],c["pass_b"]]
    distances=[]
    for source,pass_id,focus in zip(source_ids,passes,[c["focus_a"],c["focus_b"]]):
        frame=session["frames"][source]
        assert frame["global_index"]==source and frame["pass_index"]==pass_id
        distances.append(None if focus is None else abs(frame["pass_frame_index"]-focus[0])/max(focus[1],1.0))
    measurements=receipt.get("measurements",[])
    observed={m["direction"]:{k:m[k] for k in ("rms_quad","used_tiles","support_reserved","support_unclipped","sample_step_quad")} for m in measurements}
    rows.append({"id":c["id"],"role":c["role"],"grid":c["grid_nomination"],"sources":source_ids,"passes":passes,"accepted":receipt["accepted"],"refusal":receipt["refusal"],"focus_distance_in_widths":distances,"measured_stages":observed,"reciprocal_quad":receipt["reciprocal_error_quad"]})
counts=Counter("accepted" if r["accepted"] else (r["refusal"] or "unspecified").split(":")[0] for r in rows)
groups={}
for role in ("fit","heldout"):
    for kind in ("descriptor","grid"):
        selected=[r for r in rows if r["role"]==role and r["grid"]==(kind=="grid")]
        groups[role+"_"+kind]={"candidates":len(selected),"accepted":sum(r["accepted"] for r in selected),"both_focus_shapes_usable":sum(all(d is not None for d in r["focus_distance_in_widths"]) for r in selected),"witness_beyond_local_focus_width":sum(any(d is not None and d>1.0 for d in r["focus_distance_in_widths"]) for r in selected)}
result={"schema":"strehl.mosaic-native-author-summary.v1","input_sha256":hashlib.sha256(raw).hexdigest(),"census":dict(counts),"groups":groups,"details":rows,"limits":"Normalized focus distances use only usable exported focus shape at the candidate point. Missing/ambiguous focus is unknown, not zero distance. These associations cannot establish a depth metric or prove that blur caused a native rejection. Admission bars are unchanged."}
with args.out.open("x") as stream:json.dump(result,stream,indent=2);stream.write("\n")
print(json.dumps({"census":dict(counts),"groups":groups},indent=2))
