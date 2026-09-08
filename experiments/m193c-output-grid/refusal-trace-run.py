"""Saved-correspondence replay. Source-only until exact review/release; no images or matching."""
import time
START = time.monotonic()
import argparse
import ast
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import traceback
import types
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SELF = Path(__file__).resolve()
SPEC = HERE / "work/real-precise-refusal-diagnostic-preregister.md"
REFERENCE = ROOT / "experiments/M193-cover-overlap/reference.py"
MIB = 1 << 20
CAPS = dict(cpu_seconds=300, wall_seconds=480, file_bytes=8*MIB, metadata_bytes=8*MIB)
ALLOWANCE = dict(cpu_seconds=20, wall_seconds=30, file_bytes=MIB, metadata_bytes=MIB)
COMPLETE = "COMPLETE_SAVED_REFUSAL_TRACE_ONLY"
CODE = "UNMEASURED_INPUT_REGISTRATION_INADEQUATE"
PINS = {
 "native-derivative-run.py":"94fe31fbd80854fac80114e0b16b150d9d70ed8899ced727dd8c052b74d0244a",
 "coverage-sensor-white-run.py":"16f9e944673aa58b81727fabddadc7192a082cef149e950cd7dda24f217e51cf",
 "bounded-process.py":"47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b",
 "reference.py":"c08340f6f0658fae048dda92629a543b5a539462a93db196aaae29e1862ba790"}
PURE = ("ContractError", "require", "round_fraction_ties_even", "ceil_sqrt_ratio", "Match",
        "SimilarityQ32", "quantize_similarity", "pair_hypothesis", "exact_similarity_fit",
        "residual_squared_q40", "inlier_threshold_squared", "choose_similarity", "register_to_reference")
CONSTANTS = ("Q32", "XY_Q", "MAX_MATCHES", "MIN_FIT_MATCHES", "MIN_HOLDOUT_MATCHES",
             "INLIER_RADIUS_PX", "MAX_HELDOUT_RMS_PX")
CDF = (Fraction(1,4), Fraction(1,2), Fraction(1), Fraction(2), Fraction(4), Fraction(8), Fraction(16), Fraction(32))
IDS = ("private-false-counterexample", "private-true-known-map", "within-split-association-destroyer", "restored-private-true")
QUALIFICATION = dict(status="NONADMISSIBLE_DIAGNOSTIC_CANDIDATES", coordinate_gauge="native pixel centres; source to reference",
    coordinate_lattice_step_q8=8, inherited_quantization_guard_q8=1, guard_status="UNQUALIFIED_FOR_COARSE_LATTICE",
    consumer="saved registrar rejection path; no support, overlap, graph solve, placement, merge or quality admission",
    limitation="Residual severity does not identify bad correspondence versus localization or model error without real truth; lattice quantum does not bound detector localization.")


def need(ok, message):
    if not ok: raise ValueError(message)


def digest(raw): return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def raw(path, cap=4*MIB):
    with Path(path).open("rb") as stream: data = stream.read(cap+1)
    need(0 < len(data) <= cap, "bounded source/metadata read")
    return data


def load_bytes(path, expected, name):
    data = raw(path); need(digest(data) == expected, "executed source pin")
    module = types.ModuleType(name); module.__file__ = str(path); sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def pure_module(path, expected, definitions, constants=()):
    """Select original AST nodes by a closed name list; transform no body or expression."""
    data = raw(path); need(digest(data) == expected, "pure helper source pin")
    tree = ast.parse(data, filename=str(path)); wanted = set(definitions) | set(constants)
    selected = []; seen = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__": selected.append(node)
        name = node.name if isinstance(node, (ast.FunctionDef, ast.ClassDef)) else None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name): name = node.targets[0].id
        if name in wanted:
            need(name not in seen, "unique pure helper declaration")
            seen.add(name); selected.append(node)
    need(seen == wanted, "closed pure helper selection")
    module = types.ModuleType("m193c_trace_pure_" + path.stem.replace("-", "_"))
    module.__file__ = str(path); sys.modules[module.__name__] = module
    module.__dict__.update(dict(math=math, Fraction=Fraction, dataclass=dataclass, Any=Any,
                                Sequence=Sequence, json=json, sys=sys, traceback=traceback, need=need))
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), module.__dict__)
    return module


def replace(command, sha, request=None):
    return [sha if x == "ACTUAL_PLAN_SHA256" else request if x == "ACTUAL_REQUEST_SHA256" else x for x in command]


def setup(args):
    utility = HERE/"native-derivative-run.py"; data = raw(utility)
    need(digest(data)["sha256"] == PINS[utility.name], "immutable reader/budget")
    n = load_bytes(utility, digest(data), "m193c_trace_utility")
    data = raw(args.plan); need(digest(data)["sha256"] == args.sha256, "external plan SHA")
    plan = n.strict(data)
    n.closed(plan, "schema source_bindings real_baseline prior_work preparation_allowance python_executable commands".split(), "trace plan")
    need(plan["schema"] == "m193c-refusal-trace-plan-v1" and plan["preparation_allowance"] == ALLOWANCE, "closed trace version/allowance")
    for path in (SELF, SPEC, REFERENCE, *(HERE/name for name in PINS if name != "reference.py"), n.HARNESS):
        expected = plan["source_bindings"][n.relative(path)]
        need(digest(raw(path)) == expected and (path.name not in PINS or expected["sha256"] == PINS[path.name]), "source closure pin")
    output = Path(args.output).resolve()
    need(Path.cwd().resolve() == ROOT and output.is_relative_to(HERE) and not output.exists(), "fresh owned output/cwd")
    need(sys.dont_write_bytecode and set(sys._xoptions) == {"faulthandler","pycache_prefix"} and sys._xoptions["faulthandler"] is True
         and not Path(sys._xoptions["pycache_prefix"]).exists()
         and Path(sys._xoptions["pycache_prefix"]).resolve().is_relative_to(output.parent if args.worker else output), "exact fresh cache/options")
    n.closed(plan["commands"], ("parent","worker"), "commands")
    need(replace(plan["commands"]["worker" if args.worker else "parent"], args.sha256, args.request_sha256) == sys.orig_argv, "exact argv")
    return n, plan, output, dict(path=str(Path(args.plan).resolve()), **digest(data))


def budget_for(n, output, prior):
    class Budget(n.Budget):
        complete = True
        def check(self, force=False):
            super().check(force)
            need(all(self.work()[k]-self.prior[k] <= v for k,v in CAPS.items()), "trace local cap")
        def limits(self, metadata_cap=MIB):
            value = super().limits(metadata_cap); work = self.work()
            for key in ("cpu_seconds", "wall_seconds"): value[key] = min(value[key], CAPS[key]-(work[key]-self.prior[key]))
            value["log_bytes"] = min(value["log_bytes"], CAPS["file_bytes"]-(work["file_bytes"]-self.prior["file_bytes"]))
            need(all(x > 0 for x in value.values()), "remaining trace child budget")
            return value
        def save(self, path, value, cap=4*MIB):
            need(sum(self.extents.values())+len(n.json_bytes(value)) <= 8*MIB, "trace metadata preallocation")
            super().save(path, value, cap)
    return Budget(output, prior, START, 0.0)


def read(files, ref): return files.read(ref, absolute=Path(ref["path"]).is_absolute())


def same(files, a, b):
    return files.path(a, Path(a["path"]).is_absolute()) == files.path(b, Path(b["path"]).is_absolute()) and all(a[k] == b[k] for k in ("sha256","bytes"))


def checked_raw(files, ref, cap=4*MIB):
    path = files.verify(ref, cap, Path(ref["path"]).is_absolute()); data = raw(path, cap)
    need(digest(data) == {k:ref[k] for k in ("sha256","bytes")}, "same-byte metadata read")
    return data


def authority(n, plan, files):
    refs = plan["real_baseline"]; n.closed(refs, "plan result outer console exit audit".split(), "actual real baseline")
    previous, parent, outer, audit = (read(files, refs[k]) for k in ("plan","result","outer","audit"))
    need(previous["schema"] == "m193c-real-precise-plan-v1" and parent["implementation_version"] == "m193c-real-precise-v1"
         and parent["status"] == "COMPLETE_FACTOR_EIGHT_SUPPORT_ONLY" and parent["error"] is None and parent["finalization_errors"] == []
         and parent["sources_unchanged"] is True and same(files, parent["plan"], refs["plan"]), "actual completed real diagnostic")
    need(outer["exit_code"] == 0 and outer["admissible_parent_exit"] is True and outer["command"] == parent["command"]
         and outer["plan_sha256"] == refs["plan"]["sha256"] and checked_raw(files,refs["exit"],64).strip() == b"0", "actual outer/exit")
    console = n.strict(checked_raw(files,refs["console"]).splitlines()[-1])
    need(console["status"] == parent["status"] and console["error"] is None and console["finalization_errors"] == []
         and console["cpu_accounting_complete"] is True and Path(console["result"]).resolve() == files.path(refs["result"], Path(refs["result"]["path"]).is_absolute()), "actual final console")
    need(audit["schema"] == "m193c-saved-real-precise-audit-v1" and audit["status"] == "PASS_SAVED_REAL_PRECISE_OUTCOME_AUDIT"
         and audit["subject_complete"] is True and audit["cpu_accounting_complete"] is True and audit["refused_control"] is None
         and audit["worker_status"] == parent["status"], "actual independent complete-population audit")
    for key in ("plan","result","outer","console","exit"): need(same(files, audit["external"][key], refs[key]), "actual audit association")
    need(audit["actual_final_work"] == console["work_through_final_checks"] and same(files, audit["worker_result"], parent["worker_result"]), "actual audit work/worker")
    need(Decimal(audit["next_wall_seconds"]) == Decimal(str(parent["prior_work"]["wall_seconds"]))+Decimal(str(outer["elapsed_wall_seconds"])), "conservative actual outer carry")
    prior = read(files,plan["prior_work"]); base = dict(audit["actual_final_work"], wall_seconds=audit["next_wall_seconds"])
    need(all(Decimal(str(prior[k])) == Decimal(str(base[k]))+v for k,v in ALLOWANCE.items()), "all actual work plus nonrefundable preparation")
    need(parent["source_bindings"] == previous["source_bindings"] and all(plan["source_bindings"].get(k)==v for k,v in previous["source_bindings"].items()), "preserved baseline source closure")
    n.binding_map(previous["source_bindings"], files)
    worker = read(files,parent["worker_result"])
    need(worker["status"] == parent["status"] and worker["error"] is None and worker["finalization_errors"] == [] and worker["sources_unchanged"] is True
         and same(files,worker["plan"],refs["plan"]) and worker["source_bindings"] == previous["source_bindings"]
         and worker["real_decode_attempts"] == worker["real_decodes_completed"] == 9 and worker["unvisited"] == []
         and len(worker["controls"]) == 14 and all(row["passed"] is True for row in worker["controls"]), "actual complete 14 controls/9 images")
    expected = sorted({(i,i+d) for d in (1,2,4) for i in range(9-d)} | {tuple(sorted((5,j))) for j in range(9) if j != 5})
    need(len(worker["pairs"]) == 23 and [row["pair"]["id"] for row in worker["pairs"]] == [f"pair-{i}-{j}" for i,j in expected]
         and all(row["status"] == "REGISTRATION_REFUSED" for row in worker["pairs"]), "exact refused 23 pair population")
    pairs=[]
    for row in worker["pairs"]:
        record = read(files,row["record"])
        need(record["pair"] == row["pair"] and record["outcome"]["status"] == "REGISTRATION_REFUSED", "actual saved pair association")
        pairs.append(dict(ref=row["record"], record=record))
    private_parent = read(files,previous["private_baseline"]["result"]); private_worker = read(files,private_parent["worker_result"])
    need(private_parent["status"] == private_worker["status"] == "COMPLETE_PRIVATE_PRECISE_UPSCALE_CONTROL_ONLY"
         and len(private_worker["arms"]) == 3, "actual canonical private baseline")
    arms = [dict(ref=ref, record=read(files,ref)) for ref in private_worker["arms"][:2]]
    need([arm["record"]["name"] for arm in arms] == ["explicit-false","precise-true"], "fixed saved false/true controls")
    return pairs, arms, prior


def signature(outcome):
    error = outcome["error"]
    return dict(status=outcome["status"], transform=outcome["transform"], metrics=outcome["metrics"], guard=outcome["guard"],
                error=None if error is None else dict(code=error["code"], message=error["message"]))


def compare(n, label, left, right):
    a,b = n.json_bytes(left), n.json_bytes(right)
    return dict(label=label, equal=a == b, left=digest(a), right=digest(b), method="entire registrar return/refusal or trace; exact canonical bytes")


def matches_from(v, rows):
    need(24 <= len(rows) <= 256, "fixed saved landmark count")
    values=[]
    for ordinal,row in enumerate(rows):
        need(row["split"] == ("holdout" if ordinal%2 else "calibration"), "saved alternating split/order")
        xy = row["reference_q8"]+row["source_q8"]
        need(len(xy) == 4 and all(type(x) is int and -(1<<31) <= x < (1<<31) for x in xy), "saved integral Q8 endpoints")
        need(len(row["digest"]) == 64 and all(c in "0123456789abcdef" for c in row["digest"]), "saved digest format")
        values.append(v.Match(*xy, bytes.fromhex(row["digest"])))
    need(values == sorted(values, key=lambda m:(m.digest,m.reference_y_q8,m.reference_x_q8,m.source_y_q8,m.source_x_q8)), "unchanged frozen digest order")
    return values


def census(matches, ordinals):
    selected = [matches[i] for i in ordinals]
    groups = Counter((m.reference_x_q8,m.reference_y_q8,m.source_x_q8,m.source_y_q8) for m in selected)
    sides = {}
    for side in ("reference","source"):
        xy=[(getattr(m,side+"_x_q8"),getattr(m,side+"_y_q8")) for m in selected]
        sides[side] = dict(unique_sites=len(set(xy)), bbox_q8=None if not xy else [min(p[0] for p in xy),min(p[1] for p in xy),max(p[0] for p in xy),max(p[1] for p in xy)])
    return dict(rows=len(selected), unique_joint_groups=len(groups), joint_multiplicity_histogram=sorted(Counter(groups.values()).items()), endpoints=sides)


def candidate(v, matches, transform, label, calibration_input=None):
    denominator = v.XY_Q*v.Q32; rows=[]
    for ordinal,m in enumerate(matches):
        dx=transform.a*m.source_x_q8-transform.b*m.source_y_q8+transform.tx*v.XY_Q-m.reference_x_q8*v.Q32
        dy=transform.b*m.source_x_q8+transform.a*m.source_y_q8+transform.ty*v.XY_Q-m.reference_y_q8*v.Q32
        squared=dx*dx+dy*dy
        need(squared == v.residual_squared_q40(m,transform), "signed/exact residual association")
        rows.append([ordinal,dx,dy,squared,squared <= v.inlier_threshold_squared()])
    summaries={}
    for split,indices in (("all",range(len(matches))),("calibration",range(0,len(matches),2)),("holdout",range(1,len(matches),2))):
        indices=list(indices); residuals=sorted(rows[i][3] for i in indices); count=len(indices)
        summaries[split] = dict(count=count, within_two_native=sum(rows[i][4] for i in indices),
            cdf=[dict(radius_native=str(radius),count=sum(Fraction(s,denominator**2) <= radius*radius for s in residuals)) for radius in CDF],
            quantiles_nearest_rank=[dict(fraction=str(q), squared_residual_numerator=residuals[max(0,math.ceil(q*count)-1)],
                native_px=math.sqrt(residuals[max(0,math.ceil(q*count)-1)])/denominator) for q in (Fraction(0),Fraction(1,2),Fraction(9,10),Fraction(19,20),Fraction(1))],
            all_rows=census(matches,indices), within_two_rows=census(matches,[i for i in indices if rows[i][4]]))
    return dict(label=label, transform_q32=transform.as_dict(), qualification=dict(QUALIFICATION), calibration_input_ordinals=calibration_input,
        calibration_update_ordinals=[i for i in range(0,len(matches),2) if rows[i][4]],
        residual_columns=["ordinal","predicted_minus_reference_x_numerator","predicted_minus_reference_y_numerator","squared_numerator","within_two_native"],
        residual_coordinate_denominator=denominator, residual_squared_denominator=denominator**2, residuals=rows, summaries=summaries)


def replay(v, matches, mode, check):
    """Call unchanged register/choose bodies with a saved-match callback and temporary observers."""
    names=("match_features","require","pair_hypothesis","exact_similarity_fit","choose_similarity")
    missing=object(); original={name:getattr(v,name,missing) for name in names}
    trace=dict(seed_counts=dict(total=0,separation_rejected=0,scale_rejected=0,eligible=0), seed=None,
               calibration_gate=None, refinement=[], final=None, gates=[], qualification=dict(QUALIFICATION))
    ordinals={id(m):i for i,m in enumerate(matches)}; callback_calls=0
    def saved(a,b):
        nonlocal callback_calls
        need(a is None and b is None, "metadata-only callback operands")
        callback_calls+=1; return list(matches)
    def observed_require(condition, code, message):
        if mode == "on":
            frame=sys._getframe(1)
            if frame.f_code is original["choose_similarity"].__code__ and message == "no majority landmark consensus":
                local=frame.f_locals; transform=local["best_transform"]; chosen=local["best_inliers"]
                trace["calibration_gate"] = dict(candidate_exists=transform is not None, minimum_12=len(chosen)>=v.MIN_FIT_MATCHES,
                    at_least_half=2*len(chosen)>=len(local["matches"]), selected_count=len(chosen), calibration_count=len(local["matches"]))
                if transform is not None:
                    first,second=local["best_key"][2:]; left,right=local["matches"][first],local["matches"][second]
                    item=candidate(v,matches,transform,"selected-calibration-seed")
                    item.update(selection_key=list(local["best_key"]), seed_calibration_ordinals=[first,second],
                        seed_full_ordinals=[ordinals[id(left)],ordinals[id(right)]],
                        seed_baseline_squared_q8={side:sum((getattr(right,side+axis)-getattr(left,side+axis))**2 for axis in ("_x_q8","_y_q8")) for side in ("source","reference")})
                    trace["seed"]=item
            if frame.f_code in (original["choose_similarity"].__code__, v.register_to_reference.__code__):
                gate=dict(message=message,code=code,passed=bool(condition))
                if frame.f_code is v.register_to_reference.__code__ and message == "held-out landmarks lack a majority consensus":
                    local=frame.f_locals; count=len(local["holdout_inliers"])
                    gate.update(minimum_12=count>=v.MIN_HOLDOUT_MATCHES,at_least_half=2*count>=len(local["holdout"]),selected_count=count,holdout_count=len(local["holdout"]))
                trace["gates"].append(gate)
            del frame
        return original["require"](condition,code,message)
    def observed_pair(a,b):
        value=original["pair_hypothesis"](a,b)
        if mode == "on":
            counts=trace["seed_counts"]; counts["total"]+=1
            separation=any(sum((getattr(a,side+axis)-getattr(b,side+axis))**2 for axis in ("_x_q8","_y_q8")) < (32*v.XY_Q)**2 for side in ("source","reference"))
            counts["separation_rejected" if separation else "scale_rejected" if value is None else "eligible"]+=1
            if counts["total"]%256 == 0: check()
        return value
    def observed_fit(items):
        evidence=None
        if mode == "on":
            frame=sys._getframe(1); local=frame.f_locals
            evidence=dict(callsite_line=frame.f_lineno,loop_index=local.get("_"),seen_signature_count=len(local.get("seen",())),
                current_coordinate_signature=[list(s) for s in local.get("signature",())])
            del frame
        attempt=None
        if mode == "on":
            attempt=dict(status="ATTEMPTED",calibration_input_ordinals=[ordinals[id(m)] for m in items],original_caller_state=evidence,candidate=None,error=None)
            trace["refinement"].append(attempt)
        try:
            value=original["exact_similarity_fit"](items)
        except BaseException as exc:
            if attempt is not None:
                attempt.update(status="FAILED",error=dict(type=type(exc).__name__,code=getattr(exc,"code",None),message=str(exc)))
            raise
        if attempt is not None:
            attempt.update(status="RETURNED",candidate=candidate(v,matches,value,"visited-refinement-"+str(len(trace["refinement"])-1),attempt["calibration_input_ordinals"]))
        return value
    def observed_choose(items):
        value,inliers=original["choose_similarity"](items)
        if mode == "on": trace["final"]=candidate(v,matches,value,"actually-returned-by-choose",[ordinals[id(m)] for m in inliers])
        return value,inliers
    result=dict(status="REGISTRATION_REFUSED",transform=None,metrics=None,guard=None,error=None)
    try:
        v.match_features=saved
        if mode != "off":
            v.require=observed_require; v.pair_hypothesis=observed_pair; v.exact_similarity_fit=observed_fit; v.choose_similarity=observed_choose
        try:
            transform,metrics,guard=v.register_to_reference(None,None)
            result.update(status="RETURNED",transform=transform.as_dict(),metrics=metrics,guard=guard)
        except v.ContractError as exc:
            need(exc.code == CODE, "only declared registrar refusal")
            result["error"]=dict(code=exc.code,message=str(exc))
    finally:
        for name,value in original.items():
            if value is missing:
                if hasattr(v,name): delattr(v,name)
            else: setattr(v,name,value)
        trace["helpers_restored"]=all(not hasattr(v,name) if value is missing else getattr(v,name) is value for name,value in original.items())
    need(callback_calls == 1 and trace["helpers_restored"], "single saved callback and exact finally restoration")
    trace.update(signature=result,callback_calls=callback_calls)
    if mode == "on":
        counts=trace["seed_counts"]; need(counts["total"] == sum(counts[k] for k in ("separation_rejected","scale_rejected","eligible")), "seed census partition")
        if trace["calibration_gate"] is not None and not all(trace["calibration_gate"][k] for k in ("candidate_exists","minimum_12","at_least_half")):
            need(trace["refinement"] == [] and trace["final"] is None, "no fit after failed seed gate")
        need(len(trace["refinement"]) <= 9, "unchanged maximum refinement path")
    check(); return result,trace


def literal_control(v, matches, returned):
    truth=v.SimilarityQ32(0,v.Q32,3071*v.Q32,0)
    result=candidate(v,matches,truth,"independent-literal-rotation-truth")
    transform=v.SimilarityQ32(**returned["transform"]); corners=[]
    for x,y in ((0,0),(2303,0),(0,3071),(2303,3071)):
        dx=transform.a*x-transform.b*y+transform.tx-(3071-y)*v.Q32
        dy=transform.b*x+transform.a*y+transform.ty-x*v.Q32
        corners.append(dict(source_native=[x,y],squared_numerator=dx*dx+dy*dy,squared_denominator=v.Q32**2,within_one_native=dx*dx+dy*dy<=v.Q32**2))
    result["returned_map_known_corners"]=corners
    return result


def worker(n, plan, args, output, plan_ref, b, files, result, pairs, arms):
    request_ref=dict(path=str(Path(args.request).resolve()), **digest(raw(args.request)))
    need(request_ref["sha256"] == args.request_sha256, "external request SHA")
    request=read(files,request_ref)
    n.closed(request,"schema plan prior_work pair_refs private_refs".split(),"trace request")
    need(request["schema"] == "m193c-refusal-trace-request-v1" and request["plan"] == plan_ref
         and request["pair_refs"] == [item["ref"] for item in pairs] and request["private_refs"] == [item["ref"] for item in arms],"actual request inputs")
    n.closed(request["prior_work"], ("cpu_seconds","wall_seconds","file_bytes","metadata_bytes"), "request carried work")
    need(all((n.number(request["prior_work"][k]) if k.endswith("seconds") else n.integer(request["prior_work"][k]))
             and request["prior_work"][k] >= result["prior_work"][k] for k in result["prior_work"]), "request carries at least the complete plan work")
    result["request"]=request_ref
    v=pure_module(REFERENCE,plan["source_bindings"][n.relative(REFERENCE)],PURE,CONSTANTS)
    need((v.Q32,v.XY_Q,v.MIN_FIT_MATCHES,v.MIN_HOLDOUT_MATCHES,v.INLIER_RADIUS_PX,v.MAX_HELDOUT_RMS_PX)==(1<<32,256,12,12,2,1.0),"immutable native acceptance constants")
    def run(matches,mode):
        result["registrar_replay_attempts"]+=1; need(result["registrar_replay_attempts"] <= 77,"fixed 77 replay maximum")
        return replay(v,matches,mode,b.check)
    def save(name,value):
        path=output/(name+".json"); b.save(path,value); return files.bind(path,4*MIB,True)
    def triplet(matches,cached):
        signatures={}; trace=None
        for mode in ("off","on","placebo"):
            value,observed=run(matches,mode); signatures[mode]=value
            if mode == "on": trace=observed
        checks=[compare(n,"on-vs-"+mode,signatures["on"],signatures[mode]) for mode in ("off","placebo")]
        checks.append(compare(n,"on-vs-actual-cache",signatures["on"],signature(cached)))
        return trace,checks
    true_matches=true_trace=None
    for index,arm in enumerate(arms):
        result["active"]=IDS[index]; outcome=arm["record"]["outcome"]; matches=matches_from(v,outcome["landmarks"])
        trace,checks=triplet(matches,outcome)
        returned=trace["signature"]["status"] == "RETURNED"
        truth=literal_control(v,matches,trace["signature"]) if returned else None
        corners_ok=returned and all(row["within_one_native"] for row in truth["returned_map_known_corners"])
        within=truth["summaries"]["all"]["within_two_native"] if returned else None
        passed=all(row["equal"] for row in checks) and returned and (corners_ok if index else not corners_ok)
        passed=passed and (within*2 >= len(matches) if index else within == 0)
        value=dict(id=IDS[index],passed=bool(passed),cached=arm["ref"],comparisons=checks,trace=trace,literal_truth=truth)
        ref=save(IDS[index],value); result["controls"].append(dict(id=IDS[index],passed=bool(passed),record=ref))
        need(passed,"private truth/observer control failed")
        if index: true_matches,true_trace=matches,trace
    result["active"]=IDS[2]
    mutated=list(true_matches); permutation=[]
    for parity in (0,1):
        slots=list(range(parity,len(mutated),2))
        order=sorted(slots,key=lambda i:hashlib.sha256(b"M193C-REFUSAL-TRACE-PERMUTE-V1\x00"+bytes([parity])+struct.pack(">I",i)+true_matches[i].digest).digest())
        for target,source in zip(slots,order,strict=True):
            a,z=true_matches[target],true_matches[source]
            mutated[target]=v.Match(a.reference_x_q8,a.reference_y_q8,z.source_x_q8,z.source_y_q8,a.digest)
            permutation.append([target,source])
    marginal_checks=[]
    for parity in (0,1):
        a=true_matches[parity::2]; z=mutated[parity::2]
        marginal_checks.append(sorted((m.source_x_q8,m.source_y_q8) for m in a)==sorted((m.source_x_q8,m.source_y_q8) for m in z))
    changed=sum(a != z for a,z in zip(true_matches,mutated,strict=True))
    outcome,trace=run(mutated,"on")
    truth=candidate(v,mutated,v.SimilarityQ32(0,v.Q32,3071*v.Q32,0),"literal-truth-on-permuted-pairings")
    passed=changed>0 and all(marginal_checks) and outcome["status"] == "REGISTRATION_REFUSED" and truth["summaries"]["all"]["within_two_native"]*2 < len(mutated)
    ref=save(IDS[2],dict(id=IDS[2],passed=passed,changed_pairings=changed,permutation=permutation,marginals_preserved=marginal_checks,
        digest_semantics="Original row-order/split labels retained under explicit metadata fault; these are not rematched/rehashed landmark digests",trace=trace,literal_truth=truth))
    result["controls"].append(dict(id=IDS[2],passed=passed,record=ref)); need(passed,"permutation lacks actual rejection power")
    result["active"]=IDS[3]; _,restored=run(true_matches,"on")
    checks=[compare(n,"entire-restored-vs-true-trace",restored,true_trace)]
    ref=save(IDS[3],dict(id=IDS[3],passed=all(x["equal"] for x in checks),comparisons=checks,trace=restored))
    result["controls"].append(dict(id=IDS[3],passed=all(x["equal"] for x in checks),record=ref)); need(all(x["equal"] for x in checks),"restored trace differs")
    for ordinal,item in enumerate(pairs):
        record=item["record"]; result["active"]=record["pair"]["id"]
        matches=matches_from(v,record["outcome"]["landmarks"]); trace,checks=triplet(matches,record["outcome"])
        passed=all(row["equal"] for row in checks) and trace["signature"]["status"] == "REGISTRATION_REFUSED"
        value=dict(schema="m193c-saved-refusal-trace-record-v1",pair=record["pair"],input=item["ref"],passed=passed,comparisons=checks,trace=trace,
            qualification=dict(QUALIFICATION),saved_landmark_digest_semantics="Producer witness; descriptors absent, no digest recomputation, rematching or split change")
        ref=save(record["pair"]["id"],value)
        result["pairs"].append(dict(pair=record["pair"],record=ref,passed=passed)); result["unvisited"]=list(range(ordinal+1,23))
        need(passed,"saved refusal or observer reproduction failed")
    need(result["registrar_replay_attempts"] == 77,"complete fixed replay population")
    result["active"]=None


def main():
    parser=argparse.ArgumentParser()
    for name in ("plan","sha256","output"): parser.add_argument("--"+name,required=True)
    parser.add_argument("--worker",action="store_true"); parser.add_argument("--request"); parser.add_argument("--request-sha256")
    args=parser.parse_args(); need(args.worker == (args.request is not None and args.request_sha256 is not None),"worker-only request")
    n,plan,output,plan_ref=setup(args)
    prior_ref=plan["prior_work"]; prior=n.strict(raw(n.repo_path(prior_ref["path"])))
    need(digest(raw(n.repo_path(prior_ref["path"]))) == {k:prior_ref[k] for k in ("sha256","bytes")},"prior pin")
    b=budget_for(n,output,prior); files=n.Files(b); output.mkdir()
    result=dict(schema="m193c-refusal-trace-worker-v1" if args.worker else "m193c-refusal-trace-run-v1",status="REFUSED",command=sys.orig_argv,
        plan=plan_ref,request=None,prior_work=prior,source_bindings=plan["source_bindings"],sources_unchanged=False,qualification=dict(QUALIFICATION),
        controls=[],pairs=[],unvisited=list(range(23)),active=None,registrar_replay_attempts=0,image_decodes=0,feature_extractions=0,descriptor_matcher_calls=0,
        child=None,worker_result=None,error=None,finalization_errors=[],work=None,runtime=dict(python=sys.version,executable=sys.executable,pointer_bits=struct.calcsize("P")*8))
    try:
        files.verify(plan_ref,4*MIB,True); n.binding_map(plan["source_bindings"],files)
        need(files.verify(plan["python_executable"],MIB,True)==Path(sys.executable).resolve(),"actual Python executable")
        pairs,arms,actual_prior=authority(n,plan,files); need(actual_prior==prior,"same carried work")
        if args.worker: worker(n,plan,args,output,plan_ref,b,files,result,pairs,arms)
        else:
            request=dict(schema="m193c-refusal-trace-request-v1",plan=plan_ref,prior_work=b.work(),pair_refs=[x["ref"] for x in pairs],private_refs=[x["ref"] for x in arms])
            b.save(output/"request.json",request); ref=files.bind(output/"request.json",MIB,True); result["request"]=ref
            command=replace(plan["commands"]["worker"],args.sha256,ref["sha256"])
            need(command[command.index("--output")+1]==str(output/"worker") and command[command.index("--request")+1]==str(output/"request.json"),"actual worker paths")
            process,api=n.load_process(plan,files); env,removed=process.clean_environment()
            removed += [key for key in env if key.upper().startswith("PYTHON")]; env={k:v for k,v in env.items() if not k.upper().startswith("PYTHON")}
            result["removed_environment"]=sorted(set(removed)); b.complete=False
            observed=process.run(command,env,ROOT,output/"worker.log",api=api,check=b.check,**b.limits()); result["child"]=observed
            account=observed.get("job_accounting")
            if type(account) is dict and n.integer(account.get("total_cpu_100ns")):
                b.child_cpu=account["total_cpu_100ns"]/1e7
                b.complete=observed.get("terminal_job_accounting") is True and account.get("active_processes")==0
            if (output/"worker/result.json").exists(): result["worker_result"]=files.bind(output/"worker/result.json",4*MIB,True)
            n.successful_process(observed,command); child=read(files,result["worker_result"])
            need(child["schema"]=="m193c-refusal-trace-worker-v1" and child["status"]==COMPLETE and child["error"] is None and child["finalization_errors"]==[]
                 and child["command"]==command and child["request"]==ref and child["plan"]==plan_ref and child["sources_unchanged"] is True
                 and len(child["pairs"])==23 and child["unvisited"]==[] and tuple(x["id"] for x in child["controls"])==IDS
                 and all(x["passed"] is True for x in child["controls"]+child["pairs"]) and child["registrar_replay_attempts"]==77,"complete actual saved replay worker")
            for key in ("controls","pairs","unvisited","registrar_replay_attempts"): result[key]=child[key]
        result["status"]=COMPLETE
    except BaseException: result["error"]=traceback.format_exc()
    def final():
        files.recheck(); b.check(True); result["sources_unchanged"]=True
        need(result["status"]!=COMPLETE or b.complete,"complete terminal CPU required")
    try: final()
    except BaseException: result["finalization_errors"].append(traceback.format_exc()); result["status"]="REFUSED"
    result["work"]=dict(cpu_accounting_complete=b.complete,global_work=b.work(),new_extent_bytes=sum(b.extents.values()),snapshot_bytes=0,
        scope="worker sub-observation; parent Job owns setup/worker work" if args.worker else "authoritative parent plus terminal Job")
    publisher=pure_module(HERE/"coverage-sensor-white-run.py",plan["source_bindings"][n.relative(HERE/"coverage-sensor-white-run.py")],("publish",))
    return 0 if publisher.publish(n,output/"result.json",result,b.save,final,
        lambda:dict(status=result["status"],result=str(output/"result.json"),work_through_final_checks=b.work(),cpu_accounting_complete=b.complete,
                    error=result["error"],finalization_errors=result["finalization_errors"]),lambda:b.check(True)) else 1


if __name__ == "__main__": raise SystemExit(main())
