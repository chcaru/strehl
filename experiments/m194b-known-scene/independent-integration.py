"""Coherently reseal geometry/configuration mutations of a completed real run."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
import numpy as np

HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
    return sha(path)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--index",type=Path,required=True);ap.add_argument("--sha256",required=True);ap.add_argument("--reader-binding",type=Path,required=True);ap.add_argument("--reader-binding-sha",required=True);args=ap.parse_args()
    index_path=args.index.resolve();assert sha(index_path)==args.sha256
    original=load(index_path);assert original["status"]=="complete"
    assert sha(args.reader_binding)==args.reader_binding_sha
    original_revision=load(args.reader_binding)
    reader_binding=(args.reader_binding,args.reader_binding_sha)
    root=index_path.parent
    spec=importlib.util.spec_from_file_location("independent_integration_subject",HERE/"score-benchmark.py")
    subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
    work=HERE/"work"/("independent-integration-"+uuid.uuid4().hex[:10]);work.mkdir(parents=True)
    def absolute(path):
        p=Path(path);return str(p.resolve() if p.is_absolute() else (root/p).resolve())
    base=copy.deepcopy(original)
    for key in ["build_record","producer_result","producer_commission"]:base[key]["path"]=absolute(base[key]["path"])
    for row in base["source_snapshots"]:row["path"]=absolute(row["path"])
    for row in base["commands"]:
        row["log"]=absolute(row["log"]);row["consumer_evidence"]["path"]=absolute(row["consumer_evidence"]["path"])
    for case in base["cases"]:
        for key in ["plan_path","manifest_path"]:case[key]=absolute(case[key])
        for arm in case["arms"]:arm["receipt_path"]=absolute(arm["receipt_path"])
    results=[]
    def run_case(name,mutate=None,receipt_mutate=None):
        directory=work/name;directory.mkdir();index=copy.deepcopy(base)
        # Re-seal the actual complete chain, not just one stale checksum.
        # Actual source files and TIFF pixels are read at their original paths.
        for case in index["cases"]:
            plan=load(case["plan_path"])
            if mutate:mutate(plan)
            plan_path=directory/"plans"/(case["label"]+".json")
            case["plan_path"]=str(plan_path);case["plan_sha256"]=write(plan_path,plan)
            for arm in case["arms"]:
                receipt=load(arm["receipt_path"]);receipt["plan"]=plan;receipt["plan_sha256"]=case["plan_sha256"]
                if receipt_mutate:receipt_mutate(receipt)
                p=directory/"receipts"/(case["label"]+"-"+arm["name"]+".json")
                arm["receipt_path"]=str(p);arm["receipt_sha256"]=write(p,receipt)
        pairs=[(case,None) for case in index["cases"]]+[(case,arm) for case in index["cases"] for arm in case["arms"]]
        for i,(command,(case,arm)) in enumerate(zip(index["commands"],pairs)):
            evidence=load(command["consumer_evidence"]["path"])
            env=evidence["environment"];env["STREHL_M194B_PLAN"]=case["plan_path"]
            evidence["result"]=case["plan_path"] if arm is None else arm["receipt_path"]
            evidence["result_sha256"]=case["plan_sha256"] if arm is None else arm["receipt_sha256"]
            argv=command["command"]
            argv[argv.index("--plan")+1]=case["plan_path"]
            if arm is not None:
                env["STREHL_M194B_PLAN_SHA256"]=case["plan_sha256"]
                env["STREHL_M194B_RECEIPT"]=arm["receipt_path"]
                argv[argv.index("--plan-sha256")+1]=case["plan_sha256"]
                argv[argv.index("--receipt")+1]=arm["receipt_path"]
            p=directory/"evidence"/(str(i)+".json")
            command["consumer_evidence"]={"path":str(p),"sha256":write(p,evidence)}
        path=directory/"run-index.json";digest=write(path,index)
        revision=copy.deepcopy(original_revision);revision["render_index_sha256"]=digest
        revision["reason"] += "; independent fixture control: " + name
        revision_path=directory/"reader-revision.json";revision_sha=write(revision_path,revision)
        try:
            got=subject.score_run(path,digest,(revision_path,revision_sha))
            results.append(dict(name=name,accepted=True,index_sha256=digest,result_output_count=got["output_count"]))
            if name=="no-op":write(directory/"score.json",got)
            return got
        except Exception as exc:
            results.append(dict(name=name,accepted=False,index_sha256=digest,error=f"{type(exc).__name__}: {exc}"))
            return None
    baseline=subject.score_run(index_path,args.sha256,reader_binding)
    write(work/"original-score.json",baseline)
    noop=run_case("no-op")
    def changed_crop(p):p["crop_quad"]["x"]+=1;p["canonical_native_offset"][0]+=2
    def changed_normalization(p):p["normalization"]["tiff_u16_to_dn"]*=1.01
    def changed_wb(p):p["wb_f32"][0]=float(np.float32(1.5))
    def changed_interior(p):p["placements"][3]["quad_similarity"]["b_re"]+=.25
    def changed_floor(p):p["config"]["gate_floor_enabled"]=False
    def changed_exponent(p):p["config"]["exponent"]=3.
    def changed_diagnostic(p):p["diagnostic"]="white-floor-isolation"
    def changed_unknown(p):p["unrecognized_field"]=1
    for name,f in [("translated-all-case-crop",changed_crop),("changed-DN-normalization",changed_normalization),
                   ("changed-consumed-WB",changed_wb),("changed-interior-map",changed_interior),
                   ("disabled-measured-floor",changed_floor),("changed-soft-exponent",changed_exponent),
                   ("diagnostic-marked-as-baseline",changed_diagnostic),("unknown-plan-field",changed_unknown)]:run_case(name,f)
    run_case("wrong-sample-type",receipt_mutate=lambda r:r["output"].update(sample_type="f32"))
    run_case("wrong-observer-read-count",receipt_mutate=lambda r:r.update(decode_counts=[2]*len(r["decode_counts"])))
    final=subject.score_run(index_path,args.sha256,reader_binding)
    checks={"original-40-actual-TIFFs":baseline["output_count"]==40,
            "coherent-relocated-noop-accepted":noop is not None,
            "coherent-relocated-noop-numeric-equality":noop is not None and noop["summary"]==baseline["summary"],
            "all-ten-resealed-mutations-refused":all(not r["accepted"] for r in results if r["name"]!="no-op"),
            "final-original-reread-unchanged":baseline==final and sha(index_path)==args.sha256}
    # Actual final-binary TIFF comparison with the earlier independently read
    # build1/build2 production path fixture, no additional native rendering.
    case=next(c for c in base["cases"] if c["scene"]=="plane" and c["repeat"] is None)
    arm=next(a for a in case["arms"] if a["name"]=="full9")
    receipt=load(arm["receipt_path"])
    checks["final-compiled-baseline-preserves-independent-plane-bytes"]=sha(receipt["output"]["path"])==sha(HERE/"work/independent-consumer-8240dcbdf7/full/output.tiff")
    result=dict(schema="m194b-independent-integration-v1",pass_=all(checks.values()),checks=checks,
                index_path=str(index_path),index_sha256=args.sha256,work=str(work),reader_revision_sha256=args.reader_binding_sha,
                sources={"score.py":sha(HERE/"score.py"),"score-benchmark.py":sha(HERE/"score-benchmark.py")},cases=results,
                scope="recorded artifact consistency and fixed benchmark readout, not authenticity of fully fabricated replacement telemetry")
    write(HERE/"independent-integration.json",result)
    print(json.dumps(result))
    if not result["pass_"]:raise SystemExit(1)


if __name__=="__main__":main()
