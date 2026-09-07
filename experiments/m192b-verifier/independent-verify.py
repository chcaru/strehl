"""Independent whole-package mutations; no RAW access or artifact commands run.

Keep the original reductions fixed. Re-seal all mutated journal/file bindings so
only inconsistent semantics can reject. A fully fabricated consistent telemetry
package is outside this check's claim.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "experiments/M192-m12-certify/recovery-20260906-163253/results"


def sha(data): return hashlib.sha256(data).hexdigest().upper()
def read(path): return json.loads(path.read_bytes())
def write(path,obj): path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
def digest_record(row):
    return sha(json.dumps({k:v for k,v in row.items() if k!="record_sha256"},sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode())


def seal_package(root):
    rows = [json.loads(line) for line in (root/"records.jsonl").read_bytes().splitlines()]
    previous = "0"*64
    for row in rows:
        row["previous_record_sha256"] = previous
        row["record_sha256"] = digest_record(row)
        previous = row["record_sha256"]
    (root/"records.jsonl").write_text("".join(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n" for r in rows),encoding="utf-8")
    certificate = read(root/"certificate.json")
    certificate["records"]["sha256"] = sha((root/"records.jsonl").read_bytes())
    certificate["records"]["last_record_sha256"] = previous
    write(root/"certificate.json",certificate)
    complete = read(root/"campaign-complete.json")
    complete["last_record_sha256"] = previous
    for name in complete["artifact_sha256"]:
        complete["artifact_sha256"][name] = sha((root/name).read_bytes())
    write(root/"campaign-complete.json",complete)


def mutate_records(root,fn):
    rows=[json.loads(line) for line in (root/"records.jsonl").read_bytes().splitlines()]
    fn(rows)
    (root/"records.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows),encoding="utf-8")


def mutate_json(root,name,fn):
    obj=read(root/name)
    fn(obj)
    write(root/name,obj)


def cases():
    return {
        "inert_reseal": lambda p: None,
        "omitted_cleared_environment_key": lambda p: mutate_records(p,lambda rows:rows[5]["environment"].pop("STREHL_GATE_FLOOR")),
        "commission_failed_w1_exit": lambda p: mutate_json(p,"commission.json",lambda c:c["unrepaired"]["n33_w1"].update(returncode=17)),
        "commission_wrong_gate": lambda p: mutate_json(p,"commission.json",lambda c:c["unrepaired"]["n33_w1"]["argv"].__setitem__(10,"999")),
        "commission_log_binding_disagrees": lambda p: mutate_json(p,"commission.json",lambda c:c["unrepaired"]["n33_w1"]["log_artifacts"]["stderr"].update(sha256="0"*64)),
        "commission_wrong_executable": lambda p: mutate_json(p,"commission.json",lambda c:c["unrepaired"]["n33_w1"]["argv"].__setitem__(0,"C:\\synthetic\\unrelated.exe")),
        "commission_uncleared_gate_environment": lambda p: mutate_json(p,"commission.json",lambda c:c["unrepaired"]["n33_w1"]["environment"].update(STREHL_GATE_FLOOR="999")),
        "commission_false_terminal_witness": lambda p: mutate_json(p,"commission.json",lambda c:c["unrepaired"]["n33_w1"]["terminal_witness"].update(all=False,folded_all=False)),
        "cpu_boolean_repetition": lambda p: mutate_json(p,"sweeps.json",lambda s:s[1].update(repetition=True)),
        "cpu_trace_schema_unknown": lambda p: mutate_json(p,"sweeps.json",lambda s:s[1].update(schema="UNRECOGNIZED")),
        "cpu_zero_boundary_mean_with_busy_trace": lambda p: mutate_json(p,"sweeps.json",lambda s:s[1].update(whole_host_cpu_mean_percent=0)),
        "extra_archive_file": lambda p:(p/"unregistered.txt").write_text("not in any manifest",encoding="utf-8"),
        "empty_cpu_trace": lambda p: mutate_json(p,"sweeps.json",lambda s:s[1].update(trace=[])),
    }


def main():
    source_before={p.relative_to(SOURCE).as_posix():sha(p.read_bytes()) for p in SOURCE.rglob("*") if p.is_file()}
    spec=importlib.util.spec_from_file_location("m192b_independent_subject",HERE/"verify.py")
    subject=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(subject)
    source_hash=sha((HERE/"verify.py").read_bytes())
    baseline=subject.verify_artifact(SOURCE)
    assert baseline["partition"] == {"pass":1,"fail":0,"unmeasured":3,"total":4}
    results=[]
    for name,mutate in cases().items():
        path=HERE/("independent-fixture-"+uuid.uuid4().hex)
        shutil.copytree(SOURCE,path)
        try:
            mutate(path)
            seal_package(path)
            try:
                observed=subject.verify_artifact(path)
                results.append({"name":name,"accepted":True,"partition":observed["partition"]})
            except Exception as error:
                results.append({"name":name,"accepted":False,"error":str(error),"exception":type(error).__name__})
        finally:
            assert path.resolve().parent==HERE.resolve() and path.name.startswith("independent-fixture-")
            shutil.rmtree(path)
    assert sha((HERE/"verify.py").read_bytes())==source_hash,"subject changed during review"
    assert source_before=={p.relative_to(SOURCE).as_posix():sha(p.read_bytes()) for p in SOURCE.rglob("*") if p.is_file()}
    passed=all(row["accepted"] == (row["name"]=="inert_reseal") for row in results)
    outcome={"status":"INDEPENDENT_REFUSAL_CHECKS_PASS" if passed else "INDEPENDENT_REFUSAL_CHECKS_FAIL","verifier_sha256":source_hash,"baseline":baseline,"cases":results,"original_300_files_unchanged":True}
    write(HERE/"independent-verification.json",outcome)
    print(json.dumps(outcome,indent=2))
    assert passed,"a bad package was accepted or the inert control rejected"


if __name__=="__main__": main()
