"""Fixed real AREA8+precise-SIFT diagnostic, reusing the immutable factor controller.
Source-only until an exact reviewed plan/commands release; no support admission.
"""
import time
START=time.monotonic()
from decimal import Decimal
import hashlib
from pathlib import Path
import sys
import traceback
import types

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/"experiments/m193c-output-grid"
SELF=Path(__file__).resolve()
MIB=1<<20
DIRECT_SHA="fbf89076ae3e8069ab717796818a6c0a2417637cd29973d533ceefdd1fd82782"
PROTOTYPE_SHA="86111beb318f270c4532d4a5299d8b6a14413845c5eb384790f3e8d21d959d6f"
FACTOR_SHA="3699b85aceed462edb8a5641a3847e5a3676a0166cff7a03f630fa670dff6082"
PINS={"direct-pair-run.py":DIRECT_SHA,"factor-eight-run.py":FACTOR_SHA,"factor-eight-prototype.py":PROTOTYPE_SHA,
      "precise-upscale-run.py":"bdb52e2a87992709d2479237ed2f275ce6a0e223667b55c3fc6a2c316d0f0547",
      "precise-upscale-canonical-run.py":"ae38588792af5128c7f7ad51707eeb8ba72b94b95b73a88e827fee545e087919"}
VERSION="m193c-real-precise-v1"
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
KWARGS=dict(nfeatures=2048,nOctaveLayers=3,contrastThreshold=0.01,edgeThreshold=12,sigma=1.6)
CANONICAL=None
HISTORY_FACTOR=None
PRIVATE_CACHE=None
FACTORY_ACTIVE=False
OBSERVATIONS={"private":[],"real":[]}


def need(ok,message):
    if not ok: raise ValueError(message)


def new_witness(scope,ordinal):
    need(scope in OBSERVATIONS and ordinal==len(OBSERVATIONS[scope]),"ordered scoped extraction")
    need(ordinal<(2 if scope=="private" else 9),"fixed true extraction maximum")
    value=dict(scope=scope,ordinal=ordinal,requested_true=True,calls=[],restored=False,error=None)
    if scope=="real": value["original_index"]=(0,13,26,39,52,65,78,91,104)[ordinal]
    OBSERVATIONS[scope].append(value)
    return value


def precise_call(v1,witness,operation):
    global FACTORY_ACTIVE
    need(not FACTORY_ACTIVE,"no nested or legacy-control precision wrapper")
    original=v1.cv2.SIFT_create
    def factory(*args,**kwargs):
        need(args==() and kwargs==KWARGS and all(type(kwargs[k]) is type(v) for k,v in KWARGS.items()),"exact frozen SIFT constructor arguments")
        actual=dict(kwargs,enable_precise_upscale=True); witness["calls"].append(actual)
        need(len(witness["calls"])==1,"one SIFT factory per extraction")
        return original(**actual)
    FACTORY_ACTIVE=True
    try:
        v1.cv2.SIFT_create=factory
        value=operation()
        need(len(witness["calls"])==1,"successful extraction used the explicit-true factory")
        return value
    except BaseException:
        witness["error"]=traceback.format_exc(); raise
    finally:
        v1.cv2.SIFT_create=original
        witness["restored"]=v1.cv2.SIFT_create is original
        FACTORY_ACTIVE=False

def setup(args):
    path = HERE / "direct-pair-run.py"
    raw = path.read_bytes()
    need(len(raw) == 24373 and hashlib.sha256(raw).hexdigest() == DIRECT_SHA, "immutable direct-pair source")
    d = types.ModuleType("m193c_real_direct"); d.__file__ = str(path); sys.modules[d.__name__] = d
    exec(compile(raw, str(path), "exec"), d.__dict__)
    cp = HERE / "coverage-sensor-white-run.py"; raw = cp.read_bytes()
    need(d.digest(raw)["sha256"] == d.PINS[cp.name], "immutable coverage source")
    c = d.load(cp, d.digest(raw), "m193c_real_coverage")
    raw = c.raw_read(args.plan, 4*MIB)
    need(d.digest(raw)["sha256"] == args.sha256, "external factor-eight plan SHA")
    plan = c.strict(raw)
    need(set(plan) == set("schema source_bindings private_baseline prior_work preparation_allowance python_executable commands".split())
         and plan["schema"] == "m193c-real-precise-plan-v1", "closed factor-eight plan")
    pins = dict(d.PINS, **PINS)
    for p in (SELF, HERE/"real-precise-preregister.md", *(HERE/x for x in pins)):
        ref = plan["source_bindings"][p.relative_to(ROOT).as_posix()]
        need(d.digest(c.raw_read(p, 4*MIB)) == ref and (p.name not in pins or ref["sha256"] == pins[p.name]), "executed source closure")
    need(all(plan["source_bindings"][p.relative_to(ROOT).as_posix()]["sha256"] == sha for p,sha in c.PINS.items()), "frozen numerical pins")
    n = d.load(HERE/"native-derivative-run.py", plan["source_bindings"]["experiments/m193c-output-grid/native-derivative-run.py"], "m193c_real_util")
    f = d.load(HERE/"factor-eight-prototype.py", plan["source_bindings"]["experiments/m193c-output-grid/factor-eight-prototype.py"], "m193c_real_representation")
    output = Path(args.output).resolve()
    need(Path.cwd().resolve() == ROOT and output.is_relative_to(HERE) and not output.exists(), "fresh owned output/cwd")
    need(sys.dont_write_bytecode and set(sys._xoptions) == {"faulthandler", "pycache_prefix"}
         and sys._xoptions["faulthandler"] is True and not Path(sys._xoptions["pycache_prefix"]).exists()
         and Path(sys._xoptions["pycache_prefix"]).resolve().is_relative_to(output.parent if args.worker else output), "exact fresh cache/options")
    need(set(plan["commands"]) == {"parent", "worker"} and
         d.replace(plan["commands"]["worker" if args.worker else "parent"], args.sha256, args.request_sha256) == sys.orig_argv, "exact original argv")
    global CANONICAL, HISTORY_FACTOR
    def history(name,module):
        return d.load(HERE/name,plan["source_bindings"][(HERE/name).relative_to(ROOT).as_posix()],module)
    old_precise=history("precise-upscale-run.py","m193c_real_private_history")
    CANONICAL=history("precise-upscale-canonical-run.py","m193c_real_canonical_history")
    CANONICAL.BASE_AUTHORITY=old_precise.authority
    HISTORY_FACTOR=history("factor-eight-run.py","m193c_real_factor_history")
    original_extract=f.extract_coarse
    def real_extract(np,reference,coarse,receipt):
        ordinal=len(OBSERVATIONS["real"])
        witness=new_witness("real",ordinal)
        # Attach before extraction: inadequate SIFT still retains its actual call.
        receipt["precise_factory"]=witness
        return precise_call(reference,witness,lambda:original_extract(np,reference,coarse,receipt))
    f.extract_coarse=real_extract
    original_publish=c.publish
    def tagged_publish(n,path,result,save,final,summary,after_stdout):
        result["implementation_version"]=VERSION
        result["precise_factory_observations"]=OBSERVATIONS
        result["private_precision_baseline"]={k:PRIVATE_CACHE[k] for k in ("arm_ref","features_ref")} if PRIVATE_CACHE else None
        def checked_final():
            final()
            need(not FACTORY_ACTIVE,"no factory wrapper survives publication")
            if args.worker and result["status"]=="COMPLETE_FACTOR_EIGHT_SUPPORT_ONLY":
                need(len(OBSERVATIONS["private"])==2 and len(OBSERVATIONS["real"])==9,"exact true extraction population")
                need(all(x["restored"] and len(x["calls"])==1 and x["error"] is None for x in OBSERVATIONS["private"]),"two completed private true factories")
                need(all(x["restored"] and len(x["calls"])<=1 for x in OBSERVATIONS["real"]),"bounded restored real factories")
        return original_publish(n,path,result,save,checked_final,summary,after_stdout)
    c.publish=tagged_publish
    return d,c,n,f,plan,output,dict(path=str(Path(args.plan).resolve()), **d.digest(raw))


def authority(d,c,n,plan,files):
    global PRIVATE_CACHE
    refs=plan["private_baseline"]; n.closed(refs,"plan result outer console exit audit".split(),"completed canonical private baseline")
    for ref in refs.values(): files.verify(ref,4*MIB,Path(ref["path"]).is_absolute())
    old,parent,outer,audit=(d.read(files,refs[k]) for k in ("plan","result","outer","audit"))
    need(old["schema"]=="m193c-precise-upscale-canonical-plan-v1" and
         all(plan["source_bindings"].get(k)==v for k,v in old["source_bindings"].items()),"preserved exercised private source closure")
    # Separate immutable historical modules prevent new controller adapters from
    # recursively changing the old canonical/precise/factor authority chain.
    f=sys.modules["m193c_real_representation"]
    _,old_prior=CANONICAL.authority(d,c,n,f,HISTORY_FACTOR,old,files)
    need(parent["schema"]=="m193c-precise-upscale-run-v1" and parent["status"]=="COMPLETE_PRIVATE_PRECISE_UPSCALE_CONTROL_ONLY" and
         parent["implementation_version"]=="m193c-precise-upscale-canonical-v1" and parent["error"] is None and parent["finalization_errors"]==[] and
         parent["sources_unchanged"] is True and parent["prior_work"]==old_prior and parent["source_bindings"]==old["source_bindings"] and
         d.same(files,parent["plan"],refs["plan"]),"actual completed canonical parent")
    need(type(outer["exit_code"]) is int and outer["exit_code"]==0 and outer["admissible_parent_exit"] is True and
         outer["command"]==parent["command"]==d.replace(old["commands"]["parent"],refs["plan"]["sha256"]) and
         outer["plan_sha256"]==refs["plan"]["sha256"] and c.checked_raw(n,files,refs["exit"],64).strip()==b"0","actual private outer/exit")
    final=n.strict(c.checked_raw(n,files,refs["console"],4*MIB).splitlines()[-1])
    need(final["status"]==parent["status"] and final["cpu_accounting_complete"] is True and final["error"] is None and final["finalization_errors"]==[] and
         Path(final["result"]).resolve()==files.path(refs["result"],Path(refs["result"]["path"]).is_absolute()),"actual private final accounting")
    need(audit["schema"]=="m193c-saved-precise-upscale-canonical-audit-v1" and audit["status"]=="PASS_SAVED_PRECISE_UPSCALE_CANONICAL_OUTCOME_AUDIT" and
         audit["subject_complete"] is True and audit["refused_control"] is None and audit["cpu_accounting_complete"] is True and
         audit["actual_final_work"]==final["work_through_final_checks"],"independent completed private audit")
    for k in ("plan","result","outer","console","exit"):
        need(d.same(files,audit["external"][k],refs[k]),"audit actual private association")
    need(d.same(files,audit["worker_result"],parent["worker_result"]),"audited private worker")
    n.successful_process(parent["child"],parent["child"]["command"])
    worker=d.read(files,parent["worker_result"])
    need(worker["schema"]=="m193c-precise-upscale-worker-v1" and worker["status"]==parent["status"] and
         worker["implementation_version"]==parent["implementation_version"] and worker["error"] is None and worker["finalization_errors"]==[] and
         worker["sources_unchanged"] is True and tuple(x["id"] for x in worker["controls"])==CANONICAL.IDS and all(x["passed"] is True for x in worker["controls"]) and
         [(x["id"],x["passed"]) for x in worker["comparison_controls"]]==[("whole-record-comparator",True)] and
         worker["counters"]==dict(private_decode_attempts=1,feature_extraction_attempts=6,factory_calls=6,matcher_calls=5) and len(worker["arms"])==3,"actual complete private population")
    arm_ref=worker["arms"][1]; arm=d.read(files,arm_ref); features=d.read(files,arm["feature_record"])
    need(arm["name"]=="precise-true" and arm["enable_precise_upscale"] is True and arm["factory_restored"] is True and arm["error"] is None and
         arm["constructor_calls"]==[dict(KWARGS,enable_precise_upscale=True)]*2 and arm["outcome"]["status"]=="RETURNED" and
         f.literal_corner_pass(arm["outcome"]["transform"]),"actual precise-true known-map positive")
    PRIVATE_CACHE=dict(arm_ref=arm_ref,features_ref=arm["feature_record"],features=features,outcome=arm["outcome"])
    # Recover the unchanged real9/native23 population from its historical plan;
    # the private comparison itself has no real population to invent or extend.
    old_precise=d.read(files,old["failed_attempt"]["plan"])
    old_factor=d.read(files,old_precise["factor_eight_baseline"]["plan"])
    rows,fixtures,schedule,native_pairs,_=HISTORY_FACTOR.authority(d,c,n,old_factor,files)
    need(any(d.same(files,features["fixture"],x) for x in fixtures),"same private fixture population")
    prior=d.read(files,plan["prior_work"]); need(plan["preparation_allowance"]==ALLOWANCE,"fixed real preparation allowance")
    base=dict(final["work_through_final_checks"])
    base["wall_seconds"]=Decimal(str(parent["prior_work"]["wall_seconds"]))+Decimal(str(outer["elapsed_wall_seconds"]))
    need(base["wall_seconds"]==Decimal(audit["next_wall_seconds"]),"actual private outer wall carry")
    need(all(Decimal(str(prior[k]))==Decimal(str(base[k]))+ALLOWANCE[k] for k in ALLOWANCE),"complete private cost plus preparation; no refund")
    return rows,fixtures,schedule,native_pairs,prior

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
        return HISTORY_FACTOR.qualify(f,d.observe_pair(v1,a,z,mode))
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
        private_ref_witness=new_witness("private",0)
        feature_ref=precise_call(v1,private_ref_witness,lambda:v1.extract_features(coarse_ref))
        private_src_witness=new_witness("private",1)
        feature_src=precise_call(v1,private_src_witness,lambda:v1.extract_features(coarse_src))
        del coarse_ref,coarse_src
        ref = f.lifted(np,v1,feature_ref); src = f.lifted(np,v1,feature_src)
        feature_record = dict(schema="m193c-factor-eight-private-features-v1",fixture=fixture,
                              qualification=dict(HISTORY_FACTOR.QUALIFIER),reference=None,source=None)
        for name,coarse,native,receipt in (("reference",feature_ref,ref,receipt_ref),("source",feature_src,src,receipt_src)):
            feature_record[name] = dict(representation=receipt,count=len(coarse.keys),
                coarse_coordinates_q8=coarse.coordinates_q8.tolist(),native_coordinates_q8=native.coordinates_q8.tolist(),
                descriptors_sha256=hashlib.sha256(coarse.descriptors.astype("<i2").tobytes()).hexdigest(),
                keys_sha256=hashlib.sha256(n.json_bytes([list(k[:-1])+[k[-1].hex()] for k in coarse.keys])).hexdigest())
        feature_path = files.budget.output/"rotation-feature-record.json"
        files.budget.save(feature_path,feature_record)
        feature_record_ref = files.bind(feature_path,4*MIB,True)
        feature_comparison=CANONICAL.compare(n,"entire-private-feature-record-vs-cached-true",feature_record,PRIVATE_CACHE["features"])
        del feature_record
        positive = call(ref,src)
        outcome_comparison=CANONICAL.compare(n,"entire-private-outcome-vs-cached-true",positive,PRIVATE_CACHE["outcome"])
        comparisons=[feature_comparison,outcome_comparison]
        record(active,positive["status"] == "RETURNED" and len(positive["landmarks"]) >= 24
               and f.literal_corner_pass(positive["transform"]) and all(x["equal"] for x in comparisons),
               dict(features=feature_record_ref,outcome=positive,corner_errors=corner(positive),literal_truth_q32=f.rotation_truth(),
                    cached_true_arm=PRIVATE_CACHE["arm_ref"],cached_true_features=PRIVATE_CACHE["features_ref"],
                    canonical_comparisons=comparisons,precise_factories=list(OBSERVATIONS["private"])))
        begin("native-two-pixel-map-destroyer")
        bad_map = dict(positive["transform"]); bad_map["tx"] += 2*f.Q32
        record(active,not f.literal_corner_pass(bad_map),dict(baseline=positive["transform"],mutated=bad_map,
               qualification=dict(HISTORY_FACTOR.QUALIFIER),corner_errors=f.corner_errors(bad_map),added_native_px=2))
        begin("centre-offset-destroyer")
        missing = call(f.lifted(np,v1,feature_ref,omit_centre=True),f.lifted(np,v1,feature_src,omit_centre=True))
        missing["qualification"].update(coordinate_gauge="active faulty coordinates; q_fault=8*q_coarse+0",
            expected_ordinary_coordinate_gauge=HISTORY_FACTOR.QUALIFIER["coordinate_gauge"],active_defect="omitted +896 Q8 on both endpoints")
        record(active,missing["status"] == "RETURNED" and not f.literal_corner_pass(missing["transform"]),
               dict(features=feature_record_ref,outcome=missing,corner_errors=corner(missing),active_omission_q8=896))
        begin("native-rotation-restored")
        restored = call(ref,src)
        comparisons=[CANONICAL.compare(n,"entire-restored-outcome-vs-fresh-positive",restored,positive),
                     CANONICAL.compare(n,"entire-restored-outcome-vs-cached-true",restored,PRIVATE_CACHE["outcome"])]
        record(active,d.signature(restored) == d.signature(positive) and corner(restored) == corner(positive)
               and restored["status"] == "RETURNED" and f.literal_corner_pass(restored["transform"])
               and all(x["equal"] for x in comparisons),dict(outcome=restored,corner_errors=corner(restored),canonical_comparisons=comparisons))
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


def main():
    path=HERE/"factor-eight-run.py"; raw=path.read_bytes()
    need(len(raw)==24036 and hashlib.sha256(raw).hexdigest()==FACTOR_SHA,"immutable factor controller")
    base=types.ModuleType("m193c_real_factor_controller"); base.__file__=str(path); sys.modules[base.__name__]=base
    exec(compile(raw,str(path),"exec"),base.__dict__)
    # Fixed seams; worker/main/graph/budget/legacy controls stay unchanged.
    base.setup=setup; base.authority=authority; base.additive_controls=additive_controls; base.START=START
    return base.main()


if __name__=="__main__": raise SystemExit(main())
