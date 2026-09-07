"""Commission existing maximum/RMS/error-domain bars with sparse and dense faults."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("comparison",HERE/"independent-comparison-math.py")
cm=importlib.util.module_from_spec(spec);spec.loader.exec_module(cm)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,required=True);args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    result=dict(schema="m194e-independent-comparison-controls-v1",status="RUNNING",argv=sys.argv,sources={},checks=[])
    for name in ("independent-comparison-math.py","independent-comparison-controls.py"):
        shutil.copyfile(HERE/name,args.output/name)
        result["sources"][name]=hashlib.sha256((HERE/name).read_bytes()).hexdigest()
    try:
        reference=np.zeros((48,64),dtype="<f8")
        same=cm.compare(reference.copy(),reference)
        assert same["pass"] and same["whole"]["maximum_e"]==0
        result["checks"].append(dict(name="unchanged-null",statistics=same,passed=True))
        sparse=reference.copy();sparse[24,32]=.005
        s=cm.compare(sparse,reference)
        assert not s["pass"] and not s["whole"]["maximum_pass"] and s["whole"]["rms_pass"]
        assert s["edge"]["maximum_e"]==.005
        result["checks"].append(dict(name="sparse-maximum-only-fault",statistics=s,passed=True))
        dense=reference.copy();dense[:]=.0009
        d=cm.compare(dense,reference)
        assert not d["pass"] and d["whole"]["maximum_pass"] and not d["whole"]["rms_pass"]
        result["checks"].append(dict(name="dense-rms-only-fault",statistics=d,passed=True))
        outside=reference.copy();outside[2,2]=.005
        o=cm.compare(outside,reference)
        assert not o["pass"] and o["edge"]["maximum_e"]==0
        result["checks"].append(dict(name="outside-edge-still-in-whole-domain",statistics=o,passed=True))
        for name,mutant in (("wrong-shape",np.zeros((47,64),dtype="<f8")),("wrong-dtype",np.zeros((48,64),dtype="<f4")),("nonfinite",np.full((48,64),np.nan,dtype="<f8"))):
            try: cm.compare(mutant,reference)
            except ValueError: result["checks"].append(dict(name=name,passed=True))
            else: raise AssertionError(name)
        result["status"]="PASS_MATH_READER_ONLY"
    except Exception as exc:
        result["status"]="INSTRUMENT_INVALID";result["exception"]=repr(exc)
    result["source_unchanged"]=all(hashlib.sha256((HERE/name).read_bytes()).hexdigest()==value for name,value in result["sources"].items())
    (args.output/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf8")
    print(json.dumps(dict(status=result["status"],checks=len(result["checks"]))))
    return 0 if result["status"]=="PASS_MATH_READER_ONLY" else 1


if __name__=="__main__":
    raise SystemExit(main())
