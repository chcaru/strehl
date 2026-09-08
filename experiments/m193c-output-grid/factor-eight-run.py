"""Fixed AREA8 diagnostic; imports immutable direct-pair helpers, never edits them.
SOURCE ONLY until a complete externally hashed plan and exact commands are released.
"""
import time
START = time.monotonic()
import argparse
from collections import defaultdict
from decimal import Decimal
import hashlib
from pathlib import Path
import sys
import traceback
import types

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "experiments/m193c-output-grid"
SELF = Path(__file__).resolve()
MIB = 1 << 20
DIRECT_SHA = "fbf89076ae3e8069ab717796818a6c0a2417637cd29973d533ceefdd1fd82782"
PROTOTYPE_SHA = "86111beb318f270c4532d4a5299d8b6a14413845c5eb384790f3e8d21d959d6f"
COMPLETE = "COMPLETE_FACTOR_EIGHT_SUPPORT_ONLY"
ALLOWANCE = dict(cpu_seconds=30, wall_seconds=60, file_bytes=2*MIB, metadata_bytes=2*MIB)
QUALIFIER = dict(coordinate_gauge="native pixel centres; q_native=8*q_coarse+896",
                 coordinate_lattice_step_q8=8, inherited_quantization_guard_q8=1,
                 guard_status="UNQUALIFIED_FOR_COARSE_LATTICE",
                 scope="Diagnostic direct fit only; no support, overlap, placement or quality admission")


def need(ok, message):
    if not ok: raise ValueError(message)


def setup(args):
    path = HERE / "direct-pair-run.py"
    raw = path.read_bytes()
    need(len(raw) == 24373 and hashlib.sha256(raw).hexdigest() == DIRECT_SHA, "immutable direct-pair source")
    d = types.ModuleType("m193c_factor_direct"); d.__file__ = str(path); sys.modules[d.__name__] = d
    exec(compile(raw, str(path), "exec"), d.__dict__)
    cp = HERE / "coverage-sensor-white-run.py"; raw = cp.read_bytes()
    need(d.digest(raw)["sha256"] == d.PINS[cp.name], "immutable coverage source")
    c = d.load(cp, d.digest(raw), "m193c_factor_coverage")
    raw = c.raw_read(args.plan, 4*MIB)
    need(d.digest(raw)["sha256"] == args.sha256, "external factor-eight plan SHA")
    plan = c.strict(raw)
    need(set(plan) == set("schema source_bindings native_baseline prior_work preparation_allowance python_executable commands".split())
         and plan["schema"] == "m193c-factor-eight-plan-v1", "closed factor-eight plan")
    pins = dict(d.PINS, **{"direct-pair-run.py": DIRECT_SHA, "factor-eight-prototype.py": PROTOTYPE_SHA})
    for p in (SELF, HERE/"factor-eight-preregister.md", *(HERE/x for x in pins)):
        ref = plan["source_bindings"][p.relative_to(ROOT).as_posix()]
        need(d.digest(c.raw_read(p, 4*MIB)) == ref and (p.name not in pins or ref["sha256"] == pins[p.name]), "executed source closure")
    need(all(plan["source_bindings"][p.relative_to(ROOT).as_posix()]["sha256"] == sha for p,sha in c.PINS.items()), "frozen numerical pins")
    n = d.load(HERE/"native-derivative-run.py", plan["source_bindings"]["experiments/m193c-output-grid/native-derivative-run.py"], "m193c_factor_util")
    f = d.load(HERE/"factor-eight-prototype.py", plan["source_bindings"]["experiments/m193c-output-grid/factor-eight-prototype.py"], "m193c_factor_representation")
    output = Path(args.output).resolve()
    need(Path.cwd().resolve() == ROOT and output.is_relative_to(HERE) and not output.exists(), "fresh owned output/cwd")
    need(sys.dont_write_bytecode and set(sys._xoptions) == {"faulthandler", "pycache_prefix"}
         and sys._xoptions["faulthandler"] is True and not Path(sys._xoptions["pycache_prefix"]).exists()
         and Path(sys._xoptions["pycache_prefix"]).resolve().is_relative_to(output.parent if args.worker else output), "exact fresh cache/options")
    need(set(plan["commands"]) == {"parent", "worker"} and
         d.replace(plan["commands"]["worker" if args.worker else "parent"], args.sha256, args.request_sha256) == sys.orig_argv, "exact original argv")
    return d,c,n,f,plan,output,dict(path=str(Path(args.plan).resolve()), **d.digest(raw))


def authority(d,c,n,plan,files):
    refs = plan["native_baseline"]
    n.closed(refs, "plan result outer console exit audit".split(), "native baseline evidence")
    for ref in refs.values(): files.verify(ref, 4*MIB, Path(ref["path"]).is_absolute())
    old_plan,parent,outer,audit = (d.read(files, refs[k]) for k in ("plan","result","outer","audit"))
    need(old_plan["schema"] == "m193c-direct-pair-plan-v1" and
         all(plan["source_bindings"].get(k) == v for k,v in old_plan["source_bindings"].items()), "unaltered native source closure")
    # Intentionally pass the complete old plan unchanged. Its old carry and coverage
    # assertions remain historical authority; the new carry is checked separately.
    rows,fixtures,old_refusal,old_prior = d.authority(c,n,old_plan,files)
    need(parent["schema"] == "m193c-direct-pair-run-v1" and parent["status"] == "COMPLETE_DIRECT_PAIR_SUPPORT_ONLY"
         and parent["error"] is None and parent["finalization_errors"] == [] and parent["sources_unchanged"] is True
         and parent["source_bindings"] == old_plan["source_bindings"] and parent["prior_work"] == old_prior
         and d.same(files,parent["plan"],refs["plan"]), "actual complete native parent")
    need(type(outer["exit_code"]) is int and outer["exit_code"] == 0 and outer["admissible_parent_exit"] is True
         and outer["command"] == parent["command"] and outer["plan_sha256"] == refs["plan"]["sha256"]
         and c.checked_raw(n,files,refs["exit"],64).strip() == b"0", "actual native outer/exit")
    final = n.strict(c.checked_raw(n,files,refs["console"],4*MIB).splitlines()[-1])
    need(final["status"] == parent["status"] and final["cpu_accounting_complete"] is True
         and final["error"] is None and final["finalization_errors"] == []
         and Path(final["result"]).resolve() == files.path(refs["result"],Path(refs["result"]["path"]).is_absolute()), "actual native final accounting")
    need(audit["schema"] == "m193c-saved-direct-pair-audit-v1" and audit["status"] == "PASS_SAVED_DIRECT_PAIR_OUTCOME_AUDIT"
         and audit["subject_complete"] is True and audit["cpu_accounting_complete"] is True
         and audit["actual_final_work"] == final["work_through_final_checks"], "independent native audit")
    for k in ("plan","result","outer","console","exit"):
        need(d.same(files,audit["external"][k],refs[k]), "audit native association")
    need(d.same(files,audit["worker_result"],parent["worker_result"]), "audit actual native worker")
    n.successful_process(parent["child"], parent["child"]["command"])
    worker = d.read(files,parent["worker_result"]); schedule = d.pair_plan(rows)
    need(worker["status"] == parent["status"] and worker["error"] is None and worker["finalization_errors"] == []
         and worker["sources_unchanged"] is True and worker["unvisited"] == []
         and [x["id"] for x in worker["controls"]] == list(d.CONTROL_IDS) and all(x["passed"] is True for x in worker["controls"])
         and [x["pair"] for x in worker["pairs"]] == schedule
         and all(x["outcome"]["status"] == "REGISTRATION_REFUSED" for x in worker["pairs"]), "complete cached 23 native refusals")
    native_pairs=[]
    for pair in worker["pairs"]:
        ref = files.bind(files.path(parent["worker_result"],Path(parent["worker_result"]["path"]).is_absolute()).parent/(pair["pair"]["id"]+".json"), 4*MIB, True)
        need(d.read(files,ref) == pair, "exact cached native per-pair file")
        native_pairs.append(ref)
    prior = d.read(files,plan["prior_work"])
    need(plan["preparation_allowance"] == ALLOWANCE, "fixed nonrefundable preparation allowance")
    base = dict(final["work_through_final_checks"])
    base["wall_seconds"] = Decimal(str(parent["prior_work"]["wall_seconds"])) + Decimal(str(outer["elapsed_wall_seconds"]))
    need(base["wall_seconds"] == Decimal(audit["next_wall_seconds"]), "native outer wall carry")
    need(all(Decimal(str(prior[k])) == Decimal(str(base[k])) + ALLOWANCE[k] for k in ALLOWANCE), "exact native carry plus preparation; no refund")
    return rows,fixtures,schedule,native_pairs,prior


def qualify(f,outcome):
    outcome["qualification"] = dict(QUALIFIER)
    if "landmarks" in outcome:
        evidence = f.site_evidence(outcome["landmarks"])
        endpoint_groups = {}
        for side in ("reference_q8", "source_q8"):
            groups = defaultdict(list)
            for i,row in enumerate(outcome["landmarks"]): groups[tuple(row[side])].append(i)
            endpoint_groups[side] = [[list(k),ids] for k,ids in sorted(groups.items())]
        evidence["exact_endpoint_group_layout"] = "[coordinate_q8, landmark_ordinals]; split comes from saved landmark row"
        evidence["exact_endpoint_groups"] = endpoint_groups
        outcome["site_evidence"] = evidence
    return outcome


def additive_controls(d,c,n,f,files,v1,fixtures,rows,save):
    np = v1.np
    def record(name, ok, evidence):
        row = dict(id=name, passed=bool(ok), evidence=evidence)
        rows.append(row); save(name,row); need(ok,"factor-eight control: "+name)
    active = None
    def begin(name):
        nonlocal active
        active = name
    def call(a,z,mode="count"):
        return qualify(f,d.observe_pair(v1,a,z,mode))
    def corner(got):
        return [] if got["transform"] is None else f.corner_errors(got["transform"])
    try:
        begin("area8-half-ties")
        sums = (31,32,33,95,96,97)
        blocks=[]
        for total in sums:
            block = np.full((64,3),total//64,dtype=np.uint16)
            block[:total%64] += 1
            blocks.append(block.reshape(8,8,3))
        blocks.append(np.full((8,8,3),65535,dtype=np.uint16))
        actual = f.area8(np,np.concatenate(blocks,axis=1))
        expected = [[[x]*3 for x in (0,0,1,1,2,2,65535)]]
        record(active,actual.tolist() == expected,dict(input_channel_sums=list(sums)+[64*65535], actual=actual.tolist(),expected=expected))
        del blocks,block,actual
        begin("repeated-block-null")
        known = c.strict(c.raw_read(c.FIXTURES,MIB))["synthetic_overlap"]["sources"]
        fixture = next(ref for ref in fixtures if ref["sha256"] == known[0]["source_sha256"])
        original = d.decode_blob(c,n,files,fixture,v1)
        need(original.shape == (288,384,3),"literal private rotation fixture shape")
        native = np.repeat(np.repeat(original,8,axis=0),8,axis=1)
        rotated = np.ascontiguousarray(np.rot90(native,k=1))
        coarse_ref,receipt_ref = f.representation(np,native)
        coarse_src,receipt_src = f.representation(np,rotated)
        del native,rotated
        expected_rotation = np.ascontiguousarray(np.rot90(original,k=1))
        hashes = {k:hashlib.sha256(v.astype("<u2",copy=False).tobytes()).hexdigest() for k,v in
                  (("original",original),("coarse_reference",coarse_ref),("expected_rotation",expected_rotation),("coarse_source",coarse_src))}
        record(active,np.array_equal(coarse_ref,original) and np.array_equal(coarse_src,expected_rotation),
               dict(fixture=fixture,reference=receipt_ref,source=receipt_src,actual_sha256=hashes))
        del original,expected_rotation
        begin("native-rotation-positive")
        # Only these two detector extractions feed the five new private calls.
        feature_ref = v1.extract_features(coarse_ref); feature_src = v1.extract_features(coarse_src)
        del coarse_ref,coarse_src
        ref = f.lifted(np,v1,feature_ref); src = f.lifted(np,v1,feature_src)
        feature_record = dict(schema="m193c-factor-eight-private-features-v1",fixture=fixture,
                              qualification=dict(QUALIFIER),reference=None,source=None)
        for name,coarse,native,receipt in (("reference",feature_ref,ref,receipt_ref),("source",feature_src,src,receipt_src)):
            feature_record[name] = dict(representation=receipt,count=len(coarse.keys),
                coarse_coordinates_q8=coarse.coordinates_q8.tolist(),native_coordinates_q8=native.coordinates_q8.tolist(),
                descriptors_sha256=hashlib.sha256(coarse.descriptors.astype("<i2").tobytes()).hexdigest(),
                keys_sha256=hashlib.sha256(n.json_bytes([list(k[:-1])+[k[-1].hex()] for k in coarse.keys])).hexdigest())
        feature_path = files.budget.output/"rotation-feature-record.json"
        files.budget.save(feature_path,feature_record)
        feature_record_ref = files.bind(feature_path,4*MIB,True)
        del feature_record
        positive = call(ref,src)
        record(active,positive["status"] == "RETURNED" and len(positive["landmarks"]) >= 24
               and f.literal_corner_pass(positive["transform"]),dict(features=feature_record_ref,outcome=positive,
               corner_errors=corner(positive),literal_truth_q32=f.rotation_truth()))
        begin("native-two-pixel-map-destroyer")
        bad_map = dict(positive["transform"]); bad_map["tx"] += 2*f.Q32
        record(active,not f.literal_corner_pass(bad_map),dict(baseline=positive["transform"],mutated=bad_map,
               qualification=dict(QUALIFIER),corner_errors=f.corner_errors(bad_map),added_native_px=2))
        begin("centre-offset-destroyer")
        missing = call(f.lifted(np,v1,feature_ref,omit_centre=True),f.lifted(np,v1,feature_src,omit_centre=True))
        missing["qualification"].update(coordinate_gauge="active faulty coordinates; q_fault=8*q_coarse+0",
            expected_ordinary_coordinate_gauge=QUALIFIER["coordinate_gauge"],active_defect="omitted +896 Q8 on both endpoints")
        record(active,missing["status"] == "RETURNED" and not f.literal_corner_pass(missing["transform"]),
               dict(features=feature_record_ref,outcome=missing,corner_errors=corner(missing),active_omission_q8=896))
        begin("native-rotation-restored")
        restored = call(ref,src)
        record(active,d.signature(restored) == d.signature(positive) and corner(restored) == corner(positive)
               and restored["status"] == "RETURNED" and f.literal_corner_pass(restored["transform"]),dict(outcome=restored,corner_errors=corner(restored)))
        begin("rotation-observer-null")
        off = call(ref,src,"off"); placebo = call(ref,src,"placebo")
        hashes = {name:hashlib.sha256(n.json_bytes(d.signature(got))).hexdigest() for name,got in
                  (("off",off),("count",restored),("placebo",placebo))}
        record(active,len(set(hashes.values())) == 1 and d.signature(off) == d.signature(restored) == d.signature(placebo)
               and len(restored["landmarks"]) >= 24,
               dict(canonical_signature_sha256=hashes,off=off,count=restored,placebo=placebo))
    except BaseException:
        if active is not None and (not rows or rows[-1]["id"] != active):
            row = dict(id=active,passed=False,evidence=dict(exception=traceback.format_exc()))
            rows.append(row); save(active,row)
        raise
    need(tuple(row["id"] for row in rows) == d.CONTROL_IDS + f.CONTROL_IDS, "fourteen fixed complete controls")


def worker(d,c,n,f,plan,plan_ref,args,output,b,files,result,rows,fixtures,schedule,native_pairs):
    raw = c.raw_read(args.request,MIB); need(d.digest(raw)["sha256"] == args.request_sha256,"actual worker request")
    request = n.strict(raw); result["request"] = dict(path=str(Path(args.request).resolve()),**d.digest(raw))
    files.verify(result["request"],MIB,True)
    n.closed(request,"schema plan pairs rows fixtures native_pairs prior_work".split(),"factor-eight worker request")
    need(request["schema"] == "m193c-factor-eight-request-v1" and request["plan"] == plan_ref and request["rows"] == rows
         and request["pairs"] == schedule and request["fixtures"] == fixtures and request["native_pairs"] == native_pairs
         and all(request["prior_work"][k] >= result["prior_work"][k] for k in result["prior_work"]), "same requested population and carried setup work")
    b.save(output/"pair-plan.json",dict(rows=rows,pairs=schedule,native_pairs=native_pairs))
    consumer = d.load(c.CONSUMER,plan["source_bindings"][c.CONSUMER.relative_to(ROOT).as_posix()],"m193c_factor_consumer")
    v1 = consumer.v1; result["runtime_before"] = c.runtime(consumer)
    need(result["runtime_before"] == c.strict(c.raw_read(c.CONTRACT,MIB))["reference_environment"],"frozen runtime")
    save = lambda name,row:b.save(output/("control-"+name+".json"),row)
    d.controls(c,n,files,v1,fixtures,result["controls"],save)
    additive_controls(d,c,n,f,files,v1,fixtures,result["controls"],save)
    b.save(output/"controls.json",result["controls"])
    features=[]
    for row in rows:
        record = dict(original_index=row["original_index"],tiff=row["tiff"],status="FEATURE_UNAVAILABLE",error=None,representation=None)
        try:
            result["real_decode_attempts"] += 1
            rgb = d.decode_blob(c,n,files,row["tiff"],v1)
            try:
                need(rgb.shape == (4688,7032,3),"admitted native shape")
                coarse,receipt = f.representation(v1.np,rgb)
                record["representation"] = receipt
            finally: del rgb
            result["real_decodes_completed"] += 1
            try: feature,receipt = f.extract_coarse(v1.np,v1,coarse,receipt)
            finally: del coarse
            record.update(status="RETURNED",count=len(feature.keys),coordinates_q8=feature.coordinates_q8.tolist(),representation=receipt,
                descriptors_sha256=hashlib.sha256(feature.descriptors.astype("<i2").tobytes()).hexdigest(),
                keys_sha256=hashlib.sha256(n.json_bytes([list(k[:-1])+[k[-1].hex()] for k in feature.keys])).hexdigest())
        except v1.ContractError as exc:
            if exc.code != d.CODE: raise
            feature = None; record["error"] = dict(code=exc.code,message=str(exc),traceback=traceback.format_exc())
        features.append(feature)
        path = output/f"feature-{row['ordinal']}.json"; b.save(path,record)
        result["features"].append(files.bind(path,4*MIB,True))
    pair_rows=[]
    for ordinal,pair in enumerate(schedule):
        a,z = features[pair["reference"]],features[pair["source"]]
        outcome = d.observe_pair(v1,a,z) if a is not None and z is not None else dict(status="FEATURE_UNAVAILABLE",
                    unavailable=[i for i in (pair["reference"],pair["source"]) if features[i] is None])
        record = dict(pair=pair,native_baseline=native_pairs[ordinal],outcome=qualify(f,outcome))
        path = output/(pair["id"]+".json"); b.save(path,record)
        result["pairs"].append(dict(pair=pair,record=files.bind(path,4*MIB,True),status=outcome["status"]))
        pair_rows.append(record); result["unvisited"] = list(range(ordinal+1,23))
    result["graph"] = d.graph(pair_rows)
    result["graph"]["qualification"] = dict(QUALIFIER)
    result["runtime_after"] = c.runtime(consumer)
    need(result["runtime_after"] == result["runtime_before"],"stable runtime")


def main():
    p = argparse.ArgumentParser()
    for name in ("plan","sha256","output"): p.add_argument("--"+name,required=True)
    p.add_argument("--worker",action="store_true"); p.add_argument("--request"); p.add_argument("--request-sha256")
    args = p.parse_args()
    need(args.worker == (args.request is not None and args.request_sha256 is not None),"worker-only request")
    d,c,n,f,plan,output,plan_ref = setup(args)
    raw = c.raw_read(n.repo_path(plan["prior_work"]["path"]),MIB)
    need(d.digest(raw) == {k:plan["prior_work"][k] for k in ("sha256","bytes")},"actual prior carry")
    prior = n.strict(raw)
    b = d.budget_for(n,output,prior); b.started = START
    files = n.Files(b); output.mkdir()
    result = dict(schema="m193c-factor-eight-worker-v1" if args.worker else "m193c-factor-eight-run-v1",status="REFUSED",
        command=sys.orig_argv,plan=plan_ref,request=None,prior_work=prior,source_bindings=plan["source_bindings"],sources_unchanged=False,
        controls=[],features=[],pairs=[],unvisited=list(range(23)),graph=None,child=None,worker_result=None,
        real_decode_attempts=0,real_decodes_completed=0,runtime_before=None,runtime_after=None,
        qualification=dict(QUALIFIER),error=None,finalization_errors=[],work=None)
    try:
        files.verify(plan_ref,4*MIB,True); n.binding_map(plan["source_bindings"],files)
        need(files.verify(plan["python_executable"],MIB,True) == Path(sys.executable).resolve(),"actual Python pin")
        rows,fixtures,schedule,native_pairs,actual_prior = authority(d,c,n,plan,files)
        need(actual_prior == prior,"same new prior carry")
        if args.worker:
            worker(d,c,n,f,plan,plan_ref,args,output,b,files,result,rows,fixtures,schedule,native_pairs)
        else:
            b.save(output/"pair-plan.json",dict(rows=rows,pairs=schedule,native_pairs=native_pairs))
            request = dict(schema="m193c-factor-eight-request-v1",plan=plan_ref,pairs=schedule,rows=rows,fixtures=fixtures,
                           native_pairs=native_pairs,prior_work=b.work())
            b.save(output/"request.json",request); ref = files.bind(output/"request.json",MIB,True); result["request"] = ref
            command = d.replace(plan["commands"]["worker"],args.sha256,ref["sha256"])
            need(command[command.index("--output")+1] == str(output/"worker") and command[command.index("--request")+1] == str(output/"request.json"),"actual worker paths")
            process,api = n.load_process(plan,files); env,removed = process.clean_environment()
            removed += [k for k in env if k.upper().startswith("PYTHON")]
            env = {k:v for k,v in env.items() if not k.upper().startswith("PYTHON")}; env.update(dict.fromkeys(c.THREADS,"2"))
            result["environment"] = {k:env[k] for k in c.THREADS}; result["removed_environment"] = sorted(set(removed)); b.complete = False
            observed = process.run(command,env,ROOT,output/"worker.log",api=api,check=b.check,**b.limits())
            result["child"] = observed; account = observed.get("job_accounting")
            if type(account) is dict and n.integer(account.get("total_cpu_100ns")):
                b.child_cpu = account["total_cpu_100ns"]/1e7
                b.complete = observed.get("terminal_job_accounting") is True and account.get("active_processes") == 0
            if (output/"worker/result.json").exists(): result["worker_result"] = files.bind(output/"worker/result.json",4*MIB,True)
            n.successful_process(observed,command); child = d.read(files,result["worker_result"])
            need(child["status"] == COMPLETE and child["error"] is None and child["finalization_errors"] == []
                 and child["command"] == command and child["request"] == ref and child["plan"] == plan_ref
                 and len(child["pairs"]) == 23 and child["unvisited"] == [] and child["real_decode_attempts"] == child["real_decodes_completed"] == 9
                 and tuple(x["id"] for x in child["controls"]) == d.CONTROL_IDS + f.CONTROL_IDS
                 and all(x["passed"] is True for x in child["controls"]),"actual complete factor-eight worker")
            result["unvisited"] = []; result["graph"] = child["graph"]
        result["status"] = COMPLETE
    except BaseException: result["error"] = traceback.format_exc()
    def final():
        files.recheck(); b.check(True); result["sources_unchanged"] = True
        need(result["status"] != COMPLETE or b.complete,"complete terminal CPU required")
    try: final()
    except BaseException: result["finalization_errors"].append(traceback.format_exc()); result["status"] = "REFUSED"
    result["work"] = dict(cpu_accounting_complete=b.complete,global_work=b.work(),new_extent_bytes=sum(b.extents.values()),snapshot_bytes=0,
                         scope="worker sub-observation; parent Job owns setup and child work" if args.worker else "authoritative parent plus terminal Job")
    return 0 if c.publish(n,output/"result.json",result,b.save,final,
        lambda:dict(status=result["status"],result=str(output/"result.json"),work_through_final_checks=b.work(),cpu_accounting_complete=b.complete,
                    error=result["error"],finalization_errors=result["finalization_errors"]),lambda:b.check(True)) else 1


if __name__ == "__main__": raise SystemExit(main())
