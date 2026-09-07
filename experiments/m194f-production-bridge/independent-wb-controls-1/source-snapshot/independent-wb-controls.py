"""Prospectively chosen amendment1 observed-channel WB reader controls."""
import argparse
import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location("m194f_wb_reader",HERE/"independent-verify.py")
V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
R=V.R


def fixture(offset):
    y,x=np.mgrid[:18,:22]
    baseline=np.stack((3200+43*x+17*y,7100+23*x+31*y,9300+29*x+11*y),-1).astype(np.uint16)
    nx,ny=x+offset[0],y+offset[1]
    masks=dict(R=(nx%2==0)&(ny%2==0),G1=(nx%2==1)&(ny%2==0),G2=(nx%2==0)&(ny%2==1),B=(nx%2==1)&(ny%2==1))
    changed=baseline.astype(np.int32)
    changed[...,0][masks["R"]]=2*changed[...,0][masks["R"]]+np.resize(np.array([-1,0,1]),int(masks["R"].sum()))
    # Deliberately unscored interpolated movement must not become an identity bar.
    changed[...,0][~masks["R"]]+=11
    changed[...,1][~(masks["G1"]|masks["G2"])]+=-7
    changed[...,2][~masks["B"]]+=13
    return baseline,changed.astype(np.uint16),masks


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    snapshot=out/"source-snapshot";snapshot.mkdir()
    sources=[Path(__file__),HERE/"independent-verify.py",HERE/"independent-reader.py",HERE/"amendment-1.md",HERE/"independent-wb-amendment-review.md"]
    before={p.relative_to(ROOT).as_posix():V.sha(p) for p in sources}
    for p in sources:shutil.copyfile(p,snapshot/p.name)
    result=dict(schema="m194f-independent-wb-reader-controls-v1",status="RUNNING",fixture_only=True,
                orig_argv=sys.orig_argv,executable=sys.executable,python=sys.version,xoptions=sys._xoptions,numpy=np.__version__,
                source_before=before,started_utc=datetime.now(timezone.utc).isoformat(),cases=[],
                thread_environment={k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")})
    start,cpu=time.perf_counter(),time.process_time()
    def case(name,a,b,offset,refuse=False):
        # Preserve exact byte fixture for every case, including controls that fail.
        np.savez(out/(name+".npz"),baseline=a,changed=b,native_offset=np.array(offset))
        try:
            detail=V.wb_check(a,b,offset)
            row=dict(name=name,passed=not refuse,expected_refusal=refuse,detail=detail)
        except R.Refusal as error:row=dict(name=name,passed=refuse,expected_refusal=refuse,refusal=str(error))
        except Exception as error:row=dict(name=name,passed=False,expected_refusal=refuse,error=repr(error),traceback=traceback.format_exc())
        result["cases"].append(row);print(json.dumps(row,allow_nan=False),flush=True)
    for offset,label in (([6,10],"unequal-even-origin"),([7,10],"odd-x-origin")):
        a,b,masks=fixture(offset)
        case("valid-"+label,a,b,offset)
    a,b,masks=fixture([6,10])
    case("null-WB",a,a.copy(),[6,10],True)
    wrong=a.copy();wrong[...,1]=(wrong[...,1].astype(np.uint32)*2).astype(np.uint16)
    case("wrong-channel-doubled",a,wrong,[6,10],True)
    wrong=b.copy();wrong[...,0][masks["R"]]=(a[...,0][masks["R"]].astype(np.uint32)*3).astype(np.uint16)
    case("red-triple",a,wrong,[6,10],True)
    for name,channel,change in (("R",0,2),("G1",1,1),("G2",1,1),("B",2,1)):
        wrong=b.copy();locations=np.argwhere(masks[name]);yy,xx=locations[len(locations)//2]
        wrong[yy,xx,channel]=int(a[yy,xx,channel])*(2 if name=="R" else 1)+change
        case("one-observed-"+name+"-outside-bar",a,wrong,[6,10],True)
    red=np.argwhere(masks["R"]);yy,xx=red[len(red)//2]
    for name,which,value in (("zero-baseline","a",0),("clipped-baseline","a",65535),("zero-changed","b",0),("clipped-changed","b",65535)):
        aa,bb=a.copy(),b.copy();target=aa if which=="a" else bb;target[yy,xx,0]=value
        case(name,aa,bb,[6,10],True)
    aa,bb=a.copy(),b.copy();aa[...,0][masks["R"]]=1;bb[...,0][masks["R"]]=2
    case("unit-code-amplitude",aa,bb,[6,10],True)
    # One-code quantization can permit an unchanged code1 unless increase is explicit.
    aa,bb=a.copy(),b.copy();aa[yy,xx,0]=1;bb[yy,xx,0]=1
    case("one-red-not-increasing",aa,bb,[6,10],True)
    case("wrong-x-CFA-origin",a,b,[7,10],True)
    case("wrong-y-CFA-origin",a,b,[6,11],True)
    case("empty-height",a[:0],b[:0],[6,10],True)
    case("empty-parity",a[:1,:1],b[:1,:1],[6,10],True)
    case("different-extents",a,b[:-1],[6,10],True)
    case("wrong-sample-type",a.astype(np.float32),b.astype(np.float32),[6,10],True)
    result.update(source_after={p.relative_to(ROOT).as_posix():V.sha(p) for p in sources},wall_seconds=time.perf_counter()-start,
                  cpu_seconds=time.process_time()-cpu,ended_utc=datetime.now(timezone.utc).isoformat())
    result["source_unchanged"]=result["source_before"]==result["source_after"]
    result["passed"]=sum(c["passed"] for c in result["cases"]);result["count"]=len(result["cases"])
    result["status"]="PASS_WB_READER_INSTRUMENT_ONLY" if result["passed"]==result["count"] and result["source_unchanged"] else "FAIL_WB_READER_INSTRUMENT"
    (out/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=result["status"],passed=result["passed"],count=result["count"],sha256=V.sha(out/"result.json"))))
    return 0 if result["status"].startswith("PASS") else 1


if __name__=="__main__":raise SystemExit(main())
