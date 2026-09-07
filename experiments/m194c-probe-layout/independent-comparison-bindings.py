"""Resealed controller contradictions alongside an unchanged complete package."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import uuid

HERE=Path(__file__).resolve().parent


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--controller",type=Path,required=True);ap.add_argument("--sha256",required=True);args=ap.parse_args()
    path=args.controller.resolve();directory=path.parent
    spec=importlib.util.spec_from_file_location("independent_controller_subject",HERE/"compare-candidate.py")
    subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
    original=subject.validate_controller(path,args.sha256)
    cases=[]
    def trial(name,change=None):
        record=copy.deepcopy(original)
        if change:change(record)
        p=directory/("independent-comparison-"+name+".json")
        if p.exists():p=directory/("independent-comparison-"+uuid.uuid4().hex[:10]+"-"+name+".json")
        with p.open("x",encoding="utf-8",newline="\n") as f:json.dump(record,f,indent=2);f.write("\n")
        digest=subject.S.sha256(p)
        try:subject.validate_controller(p,digest)
        except Exception as exc:cases.append(dict(name=name,accepted=False,error=f"{type(exc).__name__}: {exc}",sha256=digest))
        else:cases.append(dict(name=name,accepted=True,sha256=digest))
    trial("unchanged-copy")
    def remove_extra(r):
        key=next(k for k in r["supplemental_before"] if k.endswith("legacy-fill-noise.rs"))
        del r["supplemental_before"][key];del r["supplemental_after"][key]
    def wrong_extra(r):
        key=next(k for k in r["supplemental_before"] if k.endswith("independent-tests.rs"))
        r["supplemental_before"][key]="0"*64;r["supplemental_after"][key]="0"*64
    def extra_member(r):
        r["supplemental_before"]["experiments/m194c-probe-layout/missing.rs"]="1"*64
        r["supplemental_after"]["experiments/m194c-probe-layout/missing.rs"]="1"*64
    def wrong_command(r):r["commands"][1]["command"][-1]+="-different-input-run"
    def failed_command(r):r["commands"][2]["exit_code"]=1
    def missing_command(r):r["commands"].pop()
    def fake_source_diff(r):r["changed_compiler_inputs"].append("crates/strehl-cli/src/merge_cmd.rs")
    def missing_frozen(r):del r["frozen_m194b_files"]["producer-output-1/producer-result.json"]
    def wrong_frozen(r):r["frozen_m194b_files"]["score.py"]="0"*64
    def changed_after(r):r["supplemental_after"][next(iter(r["supplemental_after"]))]="1"*64
    for name,change in [("missing-nested-source",remove_extra),("changed-independent-source",wrong_extra),
                        ("added-source-member",extra_member),("false-render-argv",wrong_command),
                        ("failed-scoring-command",failed_command),("missing-scoring-command",missing_command),
                        ("false-compiler-delta",fake_source_diff),("missing-original-input-binding",missing_frozen),
                        ("changed-scorer-binding",wrong_frozen),("changed-final-source",changed_after),
                        ("different-baseline-index",lambda r:r.update(baseline_index_sha256=r["index_sha256"])),
                        ("different-scored-run-index",lambda r:r.update(index_sha256=r["baseline_index_sha256"]))]:trial(name,change)
    again=subject.validate_controller(path,args.sha256)
    result=dict(schema="m194c-independent-comparison-bindings-v1",pass_=cases[0]["accepted"] and all(not c["accepted"] for c in cases[1:]) and again==original,
                controller_sha256=args.sha256,source_sha256={name:subject.S.sha256(HERE/name) for name in ["run-candidate.py","compare-candidate.py"]},
                cases=cases,original_unchanged=subject.S.sha256(path)==args.sha256,
                scope="new controller JSON copies only; original build/index/score/source snapshots and TIFFs unchanged")
    (HERE/"independent-comparison-bindings.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result));assert result["pass_"]


if __name__=="__main__":main()
