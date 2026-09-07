"""Continue fixed API cases after refusal; never commissions a passing subset."""
import os
for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[key]="2"
import argparse
import dataclasses
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
import traceback
import numpy as np

HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",type=Path,required=True)
    p.add_argument("--snapshot-result-sha256",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    record=dict(schema="m194e-independent-refusal-map-v1",status="RUNNING",argv=sys.argv,cases=[])
    try:
        if sha(args.snapshot/"result.json")!=args.snapshot_result_sha256:
            raise ValueError("frozen failed result hash mismatch")
        original=json.loads((args.snapshot/"result.json").read_text())
        source_map={name:original["sources"][name] for name in ("model.py","render.py","independent-model.py")}
        for name,digest in source_map.items():
            if sha(args.snapshot/name)!=digest:
                raise ValueError("snapshot source mismatch: "+name)
            shutil.copyfile(args.snapshot/name,args.output/name)
        shutil.copyfile(__file__,args.output/Path(__file__).name)
        record["sources"]={**source_map,Path(__file__).name:sha(__file__)}
        record["frozen_failure"]=dict(path=str((args.snapshot/"result.json").resolve()),sha256=args.snapshot_result_sha256)
        spec=importlib.util.spec_from_file_location("independent_model",args.output/"independent-model.py")
        m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
        sys.path.insert(0,str(args.output.resolve()))
        import model as a
        import render as r
        ai=r.integrator_for("primary"); meter=r.Meter(ai); budget=m.Budget()

        def convert(scene,frame):
            def field(rad):
                return a.Field(rad.constant,rad.affine,tuple(a.Wave(am,(fx,fy),p) for am,fx,fy,p in rad.waves))
            s=math.hypot(frame.M[0][0],frame.M[1][0]);theta=math.atan2(frame.M[1][0],frame.M[0][0])
            centre=(37.23,24.61);delta=tuple(centre[i]-frame.b[i] for i in range(2))
            inv=((math.cos(theta)/s,math.sin(theta)/s),(-math.sin(theta)/s,math.cos(theta)/s))
            t=tuple(m.dot(inv[i],delta)-centre[i] for i in range(2))
            return a.Scene(field(scene.foreground),field(scene.background),(scene.foreground_depth,scene.background_depth),scene.normal,scene.offset),a.Frame(0,frame.inverse_focus,frame.K,a.Similarity(1/s,-theta,centre,t))

        cases=[]
        c=(37.23,24.61);n=(12/13,5/13)
        affine=m.alternative_scene("affine"); transformed=m.alternative_frame(True)
        for fr in (transformed,dataclasses.replace(transformed,K=0.)):
            for cell in (False,True):
                cases.append((dict(group="R5",K=fr.K,cell=cell,xy=c),affine,fr,c,cell,.02))
        for shift in (0.,.137):
            scene=m.alternative_scene(shift=shift)
            for trans in (False,True):
                fr=m.alternative_frame(trans)
                points=[]
                for y in (6,15,24,35,46,55):
                    base=(c[0]-5/12*(y-c[1]),float(y))
                    points.extend(tuple(base[j]+d*n[j] for j in range(2)) for d in (-4.1,-1.3,-.17,.29,1.7,4.7))
                    points.append(tuple(float(round(v)) for v in base))
                for xy in points:
                    for cell in (False,True):
                        cases.append((dict(group="texture",shift=shift,transformed=trans,xy=xy,cell=cell),scene,fr,xy,cell,.004))
        record["planned_cases"]=len(cases)
        for ordinal,(label,scene,frame,xy,cell,tolerance) in enumerate(cases):
            budget.check()
            item=dict(ordinal=ordinal,**label)
            try:
                aa,ff=convert(scene,frame)
                value,receipt=(r.render_cell if cell else r.render_point)(aa,ff,xy,ai,meter)
                ref,ref_receipt=m.render(scene,frame,xy,cell=cell,eps=.0000078125,budget=budget)
                item.update(status="PASS" if abs(value-ref)<=tolerance else "FAIL_DISCREPANCY",actual_e=value,reference_e=ref,error_e=value-ref,tolerance_e=tolerance,author_receipt=receipt,reference_receipt=ref_receipt)
            except r.NumericalFailure as exc:
                item.update(status="REFUSAL",exception=str(exc))
            except Exception as exc:
                item.update(status="INSTRUMENT_INVALID",exception=str(exc),traceback=traceback.format_exc())
            record["cases"].append(item)
            if (ordinal+1)%20==0:
                record["budget"]=budget.receipt()
                (args.output/"partial.json").write_text(json.dumps(record,indent=2,allow_nan=False),encoding="utf8")
                print(json.dumps(dict(completed=ordinal+1,refusals=sum(x["status"]=="REFUSAL" for x in record["cases"]),budget=budget.receipt())),flush=True)
        counts={key:sum(x["status"]==key for x in record["cases"]) for key in ("PASS","REFUSAL","FAIL_DISCREPANCY","INSTRUMENT_INVALID")}
        record["counts"]=counts
        record["budget"]=budget.receipt();record["author_meter"]=meter.receipt()
        # A successful subset does not supply a valid aggregate RMS for commission.
        record["status"]="UNCOMMISSIONED_NUMERICS" if counts["REFUSAL"] or counts["FAIL_DISCREPANCY"] else "INSTRUMENT_INVALID" if counts["INSTRUMENT_INVALID"] else "PASS_DIAGNOSTIC_ONLY"
        record["no_authority"]="This map never grants a float/model commission, including if all diagnostic cases pass."
    except Exception as exc:
        record["status"]="UNCOMMISSIONED_INCOMPLETE_DIAGNOSTIC"
        record["exception"]=str(exc);record["traceback"]=traceback.format_exc()
    finally:
        record["snapshot_unchanged"]=all(sha(args.output/k)==v for k,v in record.get("sources",{}).items())
        (args.output/"result.json").write_text(json.dumps(record,indent=2,allow_nan=False),encoding="utf8")
        print(json.dumps(dict(status=record["status"],counts=record.get("counts"),completed=len(record["cases"]))))
    return 0 if record["status"]=="PASS_DIAGNOSTIC_ONLY" else 1


if __name__=="__main__":
    raise SystemExit(main())
