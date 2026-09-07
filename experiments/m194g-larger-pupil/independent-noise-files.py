"""Independent post-generation reader of all ninety actual native CFA files.

No author sampler import, draws, optical calls or author encoder use.
"""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.perf_counter()
import argparse
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUPPORT = HERE / "independent-noise-verifier-support.py"
spec = importlib.util.spec_from_file_location("m194g_noise_files_support", SUPPORT)
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
SHAPE = (240,320)
SEEDS = (None,701,709,719,727,733,739,743,751)
FOCI = [0.5,0.625,0.75,0.875,1.0]
IDENTITY = dict(scale=1.0,rotation=0.0,centre=[0.0,0.0],translation=[0.0,0.0])
GEOMETRY = dict(width=320,height=240,cfa_origin=[0,0],reference_index=2,
                frame_indices=[0,1,2,3,4],inverse_foci=FOCI,forward_similarity=IDENTITY)
SENSOR = dict(cfa="RGGB",factors_f64=[.75,1.0,1.0,.6],gain_dn_per_e=[.25]*4,
              read_noise_e=[4]*4,black=[512]*4,white=[15360]*4,
              quantization="ties-even-then-clip-[0,15360]",
              wb_rgb_f32=[1.3333333730697632,1.0,1.6666666269302368])
MANIFEST_KEYS = {"schema","status","ref_root","upstream_ref_root","contract","float_commission",
                 "noise_commission","runtime","source_bindings","geometry","sensor","bundles"}
RUN_KEYS = {"schema","mode","status","invocation","execution_release","runtime","sources_before",
            "sources_after","inputs_before","inputs_after","index","manifest","independent_reader",
            "work","error","finalization_errors"}
CONTROL_IDS = (
    "actual-full-ninety-entry", "private-layout-entry", "missing-bundle", "duplicate-bundle",
    "wrong-scene", "bool-seed", "bool-frame-index", "missing-frame", "wrong-focus", "wrong-origin",
    "wrong-reference", "wrong-factors", "extra-manifest-field", "incomplete-manifest", "restored-layout-entry",
    "incomplete-generation", "generation-source-change", "generation-input-change", "generation-error",
    "generation-manifest-association", "actual-full-entry-incomplete-generation", "private-below-black-valid", "old-black-floor-destroyer",
    "actual-cfa-hardlink-identity", "private-range-restored", "cfa-short", "cfa-appended", "cfa-above-white", "cfa-bool-extent",
    "audit-q-hash", "audit-seed", "audit-key", "audit-rail", "audit-noise-off-stream",
    "noise-off-one-code", "restored-noise-off", "restored-noisy-audit",
)


def layout(manifest, law):
    law.keys(manifest, MANIFEST_KEYS, "intended manifest")
    law.need(manifest["schema"] == "m194g-software-noise-manifest-v1"
             and manifest["status"] == "COMPLETE_NOISE_FILES_UNCOMMISSIONED"
             and manifest["ref_root"] == "manifest-parent" and manifest["upstream_ref_root"] == "repository",
             "intended manifest status/root")
    law.need(law.same(manifest["geometry"],GEOMETRY), "fixed native geometry")
    law.need(law.same(manifest["sensor"],SENSOR), "fixed sensor law")
    law.need(type(manifest["bundles"]) is list and len(manifest["bundles"]) == 18, "eighteen ordered bundles")
    rows = []
    for bundle, (scene, seed) in zip(manifest["bundles"], [(s,r) for s in ("textured","flat") for r in SEEDS]):
        law.keys(bundle,{"scene","seed","noise_enabled","frames"},"bundle")
        law.need(law.same({k:bundle[k] for k in ("scene","seed","noise_enabled")},
                          dict(scene=scene,seed=seed,noise_enabled=seed is not None)), "ordered bundle identity")
        law.need(type(bundle["frames"]) is list and len(bundle["frames"]) == 5, "five original frames")
        for index,frame in enumerate(bundle["frames"]):
            law.keys(frame,{"index","inverse_focus","cfa","audit"},"frame")
            law.need(type(frame["index"]) is int and frame["index"] == index
                     and type(frame["inverse_focus"]) is float and frame["inverse_focus"] == FOCI[index],
                     "original index/focus/type")
            rows.append((scene,seed,index,frame))
    return rows


def generation_header(run, manifest_ref, manifest, run_path, law):
    law.keys(run,RUN_KEYS,"generation run")
    law.need(run["schema"] == "m194g-software-noise-run-v1" and run["mode"] == "intended"
             and run["status"] == "COMPLETE_NOISE_FILES_UNCOMMISSIONED" and run["error"] is None
             and run["finalization_errors"] == [] and run["index"] is None and run["independent_reader"] is None,
             "complete intended generation required")
    law.need(type(run["sources_before"]) is dict and bool(run["sources_before"])
             and law.same(run["sources_before"],run["sources_after"])
             and law.same(run["sources_before"],manifest["source_bindings"]), "generation source closure")
    law.need(type(run["inputs_before"]) is dict and bool(run["inputs_before"])
             and law.same(run["inputs_before"],run["inputs_after"]), "generation input closure")
    ref = run["manifest"]
    law.keys(ref,law.FILE_KEYS,"generation manifest reference")
    actual = {**ref,"path":S.relative(run_path.parent,ref["path"]).relative_to(ROOT).as_posix()}
    law.need(law.same(actual,manifest_ref), "generation manifest association")
    work=run["work"]
    law.keys(work,{"stage","limits","cpu_seconds","wall_seconds","requested_variates","live_array_bytes",
                   "output_bytes","requested_by_component","generator_constructions","started_frames","completed_frames",
                   "peak_live_array_bytes","tracked_scope"},"generation work")
    limits=dict(cpu_seconds=120.0,wall_seconds=240.0,requested_variates=12288000,
                live_array_bytes=33554432,output_bytes=33554432)
    law.need(work["stage"] == "intended" and law.same(work["limits"],limits),"generation budget limits")
    for key,ceiling in limits.items():
        value=law.number(work[key],key) if key.endswith("seconds") else law.integer(work[key],key)
        law.need(0 <= value <= ceiling,"generation bounded work")
    law.integer(work["peak_live_array_bytes"],"generation peak arrays",0,33554432)
    law.need(law.same({k:work[k] for k in ("requested_variates","generator_constructions","started_frames","completed_frames")},
                      dict(requested_variates=12288000,generator_constructions=160,started_frames=90,completed_frames=90))
             and law.same(work["requested_by_component"],dict(photo=6144000,read=6144000)),"generation actual draw/population counts")
    law.need(type(work["tracked_scope"]) is str and "not RSS" in work["tracked_scope"],"generation allocation scope")


def cfa_file(ref,base,session,law,*,identities=None):
    law.keys(ref,law.ARRAY_KEYS,"CFA ArrayRef")
    law.need(type(ref["bytes"]) is int and ref["bytes"] == 153600
             and ref["dtype"] == "<u2" and law.same(ref["shape"],[240,320]), "CFA shape/dtype/extent")
    raw,path = session.reads.raw(ref,base,maximum=153600,array=True)
    if identities is not None:
        st = path.stat()
        identity = (st.st_dev,st.st_ino)
        law.need(st.st_ino != 0 and identity not in identities,"distinct actual CFA file identity")
        identities.add(identity)
    session.budget.check_allocation(SHAPE,"<u2")
    q = session.budget.watch(law.np.frombuffer(raw,dtype="<u2").reshape(SHAPE),"actual emitted CFA")
    law.need(int(q.max()) <= 15360,"actual CFA exceeds white rail")
    return q,{"path":path.relative_to(ROOT).as_posix(),"sha256":ref["sha256"],"bytes":ref["bytes"]}


def audit_record(audit,scene,seed,index,q,scalar,mu,session,law):
    law.keys(audit,{"input","phase","fault_id","observer_mode","streams","derived_hashes",
                    "rail_counts","witness","q_sha256"},"CFA audit")
    expected = dict(scene=scene,seed=seed,frame_index=index,width=320,height=240,
                    scalar_level=12000 if scene == "flat" else None,expected_scalar_sha256=law.raw_hash(scalar))
    law.need(law.same(audit["input"],expected),"audit original input identity/hash")
    law.need(audit["phase"] == "baseline" and audit["fault_id"] is None and audit["observer_mode"] == "off",
             "intended audit phase/observer")
    law.need(audit["q_sha256"] == law.raw_hash(q),"audit actual Q hash")
    law.witness(audit["witness"],"off",seed is not None)
    law.keys(audit["rail_counts"],{"pre_encoder_x","x_used"},"audit rail stages")
    zeros = {k:0 for k in law.RAIL_KEYS}
    law.need(all(law.same(value,zeros) for value in audit["rail_counts"].values()),"audit preclipping rail counts")
    law.keys(audit["derived_hashes"],{"photo_used","read_draw","electron_sum","pre_encoder_x"},"audit derived hashes")
    law.need(all(law.hash_value(audit["derived_hashes"][k]) for k in ("photo_used","electron_sum","pre_encoder_x"))
             and (audit["derived_hashes"]["read_draw"] is None if seed is None
                  else law.hash_value(audit["derived_hashes"]["read_draw"])),"audit derived hash types")
    if seed is None:
        law.need(audit["streams"] is None,"noise-off must have null streams")
        x = session.budget.empty(SHAPE,"<f8","independent noise-off DN")
        law.np.multiply(mu,.25,out=x)
        law.np.add(x,512.,out=x)
        expected_q,rails = law.rounded_codes(x,session.budget)
        law.need(law.np.array_equal(q,expected_q),"noise-off exact independent Q")
        law.need(law.same(rails,zeros),"independent noise-off preclipping rails")
        law.need(audit["derived_hashes"]["photo_used"] == law.raw_hash(mu)
                 and audit["derived_hashes"]["electron_sum"] == law.raw_hash(mu)
                 and audit["derived_hashes"]["pre_encoder_x"] == law.raw_hash(x),"noise-off actual intermediate hashes")
        return True
    law.keys(audit["streams"],{"photo","read"},"intended RNG stream pair")
    for component in ("photo","read"):
        stream = audit["streams"][component]
        law.keys(stream,law.STREAM_KEYS,"intended stream")
        key,words = law.independent_key(expected,component)
        law.need(type(stream["key"]) is str and stream["key"].encode("ascii") == key
                 and stream["key_sha256"] == law.sha(key) and law.same(stream["entropy_words"],words),
                 "intended stream key/entropy")
        law.state_record(stream["initial_state"])
        law.state_record(stream["final_state"])
        law.need(stream["initial_state"]["state"]["inc"] == stream["final_state"]["state"]["inc"],
                 "intended stream increment")
        call = (dict(method="poisson",size=None,dtype="<i8",lambda_sha256=law.raw_hash(mu)) if component == "photo"
                else dict(method="standard_normal",size=76800,dtype="<f8",lambda_sha256=None))
        law.need(law.same(stream["call"],call) and law.hash_value(stream["draw_sha256"]),"intended actual draw call")
    law.need(audit["streams"]["read"]["draw_sha256"] == audit["derived_hashes"]["read_draw"],
             "intended raw read hash association")
    return None


def source_and_command(run,run_path,session,law):
    release, _ = session.reads.json(run["execution_release"])
    law.keys(release,{"schema","scope","source_bindings","inputs","commands"},"generation release")
    law.need(release["schema"] == "m194g-numerical-execution-release-v1"
             and release["scope"] == "noise-emission", "generation release scope")
    law.need(law.same(release["source_bindings"],run["sources_before"]),"generation release source mapping")
    command = run["invocation"]
    choices = [[run["execution_release"]["sha256"] if x == "ACTUAL_EXECUTION_RELEASE_SHA256" else x for x in c]
               for c in release["commands"]]
    law.need(type(command) is list and command in choices,"released actual generation invocation")
    law.need("--output" in command and Path(command[command.index("--output")+1]).resolve() == run_path.parent,
             "generation output command association")
    for name,wanted in run["sources_before"].items():
        session.reads.raw({"path":name,**wanted})
    for name,wanted in run["inputs_before"].items():
        session.reads.raw({"path":name,**wanted})
    for ref in release["inputs"]:
        law.need(law.same(run["inputs_before"].get(ref["path"]),{k:ref[k] for k in ("sha256","bytes")}),
                 "released generation input binding")


def upstream(manifest,run,base,session,law):
    gate,_ = session.reads.json(manifest["float_commission"])
    law.keys(gate,{"schema","status","ref_root","fixture","component_verification","comparison","width","height",
                   "cell","units","reference_index","primary_frames"},"float admission")
    law.need(gate["schema"] == "m194g-float-commission-v1" and gate["status"] == "PASS_COMPLETE_FLOAT_MODEL"
             and gate["ref_root"] == "repository" and type(gate["reference_index"]) is int
             and gate["reference_index"] == 2 and gate["width"] == 320 and gate["height"] == 240,
             "complete registered float admission")
    projection = {k:v for k,v in gate.items() if k not in ("schema","status","comparison")}
    comparison,_ = session.reads.json(gate["comparison"])
    law.need(comparison["status"] == "PASS_COMPLETE_FLOAT_MODEL" and comparison["error"] is None
             and comparison["finalization_errors"] == [] and law.same(comparison["admitted_inputs"],projection),
             "float comparison admission projection")
    component,_ = session.reads.json(gate["component_verification"])
    law.need(component["status"] == "PASS_COMPONENTS_AND_OBSERVER_ONLY" and component["exception"] is None
             and component["inputs_unchanged"] is True,"float component authority")
    fixture,_ = session.reads.json(gate["fixture"])
    law.need(law.same(fixture["frame_indices"],[0,1,2,3,4]) and law.same(fixture["inverse_foci"],FOCI)
             and law.same(fixture["forward_similarity"],IDENTITY),"float original gauge")
    law.need(type(gate["primary_frames"]) is list and len(gate["primary_frames"]) == 5,"five float originals")
    for index,frame in enumerate(gate["primary_frames"]):
        law.need(type(frame["index"]) is int and frame["index"] == index
                 and frame["inverse_focus"] == FOCI[index],"float original frame order")
        receipt,path = session.reads.json(frame["author_receipt"])
        ref = receipt["arrays"]["scalar"]
        actual = {**ref,"path":S.relative(path.parent,ref["path"]).relative_to(ROOT).as_posix()}
        law.need(law.same(actual,frame["scalar"]),"float primary scalar association")
    noise,noise_path = session.reads.json(manifest["noise_commission"])
    law.keys(noise,RUN_KEYS,"noise commission")
    law.need(noise["mode"] == "commission" and noise["status"] == "PASS_SOFTWARE_NOISE_COMMISSION"
             and noise["error"] is None and noise["finalization_errors"] == []
             and law.same(noise["sources_before"],noise["sources_after"])
             and law.same(noise["sources_before"],run["sources_before"])
             and law.same(noise["inputs_before"],noise["inputs_after"]),"successful same-source noise commission")
    child,_ = session.reads.json(noise["independent_reader"],noise_path.parent)
    law.keys(child,{"schema","status","read","controls"},"private read wrapper")
    law.need(child["status"] == "PASS_SOFTWARE_NOISE_PRIVATE_TRACES","private reader wrapper")
    read,_ = session.reads.json(child["read"],noise_path.parent)
    controls,_ = session.reads.json(child["controls"],noise_path.parent)
    index,index_path = session.reads.json(noise["index"],noise_path.parent)
    law.need(read["schema"] == "m194g-independent-software-noise-reader-v1"
             and read["status"] == "PASS_SOFTWARE_NOISE_PRIVATE_TRACES" and read["record_count"] == 1186
             and controls["status"] == "PASS_INDEPENDENT_NOISE_READER_CONTROLS"
             and controls["actual_full_entry_companion_sha256"] == law.sha(law.canonical(read))
             and law.same(read["index"],{**noise["index"],"path":str(index_path)})
             and law.same(index["source_bindings"],run["sources_before"]),"actual private read/index/control association")
    law.need(controls["schema"] == "m194g-independent-noise-reader-controls-v1"
             and type(controls["check_count"]) is int and controls["check_count"] == 36
             and type(controls["checks"]) is list and len(controls["checks"]) == 36
             and all(row.get("pass") is True for row in controls["checks"]),"complete private reader controls")
    runtime,_ = session.reads.json(manifest["runtime"],base)
    previous,_ = session.reads.json(noise["runtime"],noise_path.parent)
    actual,_ = session.reads.json(run["runtime"],base)
    law.need(law.same(runtime,previous) and law.same(runtime,actual),"commissioned runtime equality")
    # Held strict runtime reader verifies actual dependency bytes without RNG construction.
    law.validate_runtime(manifest["runtime"],base,session.budget)
    for ref in (manifest["float_commission"],manifest["noise_commission"]):
        law.need(law.same(run["inputs_before"].get(ref["path"]),{k:ref[k] for k in ("sha256","bytes")}),
                 "generation upstream input binding")
    return gate


def scalar_for(scene,index,gate,session,law):
    if scene == "flat":
        scalar = session.budget.empty(SHAPE,"<f8","independent flat scalar")
        scalar.fill(12000.)
    else:
        ref = gate["primary_frames"][index]["scalar"]
        # Register the exact bytes for final recheck; held reader loads same-buffer bounded NPY.
        session.reads.raw(ref,array=True,maximum=700000)
        scalar = law.read_array(ref,ROOT,session.budget,"<f8",SHAPE)
        law.need(float(scalar.min()) >= 0,"admitted scalar nonnegative")
    mu = session.budget.empty(SHAPE,"<f8","independent CFA means")
    for (y,x),factor in zip(((0,0),(0,1),(1,0),(1,1)),(.75,1.,1.,.6)):
        law.np.multiply(scalar[y::2,x::2],factor,out=mu[y::2,x::2])
    return scalar,mu


def read_files(manifest_ref,generation_ref,session,law,*,private_layout_only=False):
    """Actual entry; private layout boundary is explicitly ineligible for admission."""
    manifest,base_path = session.reads.json(manifest_ref)
    rows = layout(manifest,law)
    if private_layout_only:
        return dict(status="PASS_PRIVATE_LAYOUT_ONLY",rows=len(rows))
    run,run_path = session.reads.json(generation_ref)
    generation_header(run,manifest_ref,manifest,run_path,law)
    source_and_command(run,run_path,session,law)
    contract,_ = session.reads.raw(manifest["contract"],base_path.parent)
    law.need(law.sha(contract) == law.CONTRACT_SHA,"held noise contract bytes")
    gate = upstream(manifest,run,base_path.parent,session,law)
    identities,outputs,audit_identities = set(),[],set()
    for scene,seed,index,frame in rows:
        scalar,mu = scalar_for(scene,index,gate,session,law)
        q,ref = cfa_file(frame["cfa"],base_path.parent,session,law,identities=identities)
        audit,path = session.reads.json(frame["audit"],base_path.parent)
        stat = path.stat()
        ident = (stat.st_dev,stat.st_ino)
        law.need(stat.st_ino != 0 and ident not in audit_identities,"distinct audit identities")
        audit_identities.add(ident)
        exact = audit_record(audit,scene,seed,index,q,scalar,mu,session,law)
        outputs.append(dict(scene=scene,seed=seed,index=index,cfa=ref,audit=S.file_ref(path),
                            minimum=int(q.min()),maximum=int(q.max()),noise_off_exact=exact))
        del scalar,mu,q
        session.budget.check()
    law.need(len(outputs) == len(identities) == len(audit_identities) == 90,"all ninety actual files")
    return dict(files=outputs,manifest=manifest,run=run,gate=gate,base=base_path.parent,run_path=run_path)


def controls(actual,manifest_ref,generation_ref,session,law,record):
    checks=record["checks"]
    def add(name,passed,evidence):
        checks.append(dict(name=name,**{"pass":bool(passed)},evidence=evidence))
        record["check_count"]=len(checks)
        law.need(passed,"intended reader control failed: "+name)
    def reject(name,fn,message):
        try:
            fn()
        except (ValueError,law.Rejection) as exc:
            add(name,message in str(exc),dict(exception=type(exc).__name__,message=str(exc),expected=message))
        else:
            add(name,False,dict(accepted=True,expected=message))
    add("actual-full-ninety-entry",len(actual["files"]) == 90,dict(file_count=90))
    def private(value,name):
        ref=session.json("controls/"+name+"-manifest.json",value)
        return read_files(ref,generation_ref,session,law,private_layout_only=True)
    add("private-layout-entry",private(actual["manifest"],"valid")["status"] == "PASS_PRIVATE_LAYOUT_ONLY",{})
    edits=[
        ("missing-bundle",lambda v:v["bundles"].pop(),"eighteen"),
        ("duplicate-bundle",lambda v:v["bundles"].__setitem__(1,v["bundles"][0]),"bundle identity"),
        ("wrong-scene",lambda v:v["bundles"][0].update(scene="flat"),"bundle identity"),
        ("bool-seed",lambda v:v["bundles"][1].update(seed=True),"bundle identity"),
        ("bool-frame-index",lambda v:v["bundles"][0]["frames"][0].update(index=False),"index/focus/type"),
        ("missing-frame",lambda v:v["bundles"][0]["frames"].pop(),"five original"),
        ("wrong-focus",lambda v:v["bundles"][0]["frames"][0].update(inverse_focus=.625),"index/focus/type"),
        ("wrong-origin",lambda v:v["geometry"].update(cfa_origin=[1,0]),"fixed native geometry"),
        ("wrong-reference",lambda v:v["geometry"].update(reference_index=0),"fixed native geometry"),
        ("wrong-factors",lambda v:v["sensor"].update(factors_f64=[.6,1.,1.,.75]),"fixed sensor law"),
        ("extra-manifest-field",lambda v:v.update(extra=1),"intended manifest keys"),
        ("incomplete-manifest",lambda v:v.update(status="PARTIAL"),"manifest status/root"),
    ]
    for name,edit,message in edits:
        value=copy.deepcopy(actual["manifest"])
        edit(value)
        reject(name,lambda v=value,n=name:private(v,n),message)
    add("restored-layout-entry",private(actual["manifest"],"restored")["rows"] == 90,{})
    for name,edit,message in [
        ("incomplete-generation",lambda v:v.update(status="PARTIAL"),"complete intended generation"),
        ("generation-source-change",lambda v:v.update(sources_after={}),"generation source closure"),
        ("generation-input-change",lambda v:v.update(inputs_after={}),"generation input closure"),
        ("generation-error",lambda v:v.update(error="planted"),"complete intended generation"),
        ("generation-manifest-association",lambda v:v["manifest"].update(sha256="0"*64),"manifest association"),
    ]:
        value=copy.deepcopy(actual["run"])
        edit(value)
        reject(name,lambda v=value:generation_header(v,manifest_ref,actual["manifest"],actual["run_path"],law),message)
    value=copy.deepcopy(actual["run"])
    value["status"]="PARTIAL"
    incomplete=session.json("controls/incomplete-actual-entry-generation.json",value)
    reject("actual-full-entry-incomplete-generation",
           lambda:read_files(manifest_ref,incomplete,session,law,private_layout_only=False),
           "complete intended generation required")
    q=session.budget.empty(SHAPE,"<u2","private CFA boundary")
    q.fill(511)
    ref={**session.write("controls/below-black.cfa",q.tobytes()),"dtype":"<u2","shape":[240,320]}
    arr,_=cfa_file(ref,ROOT,session,law)
    add("private-below-black-valid",int(arr.min()) == 511,{"minimum":int(arr.min())})
    add("old-black-floor-destroyer",not bool(law.np.all(arr >= 512)),{"old_minimum512_predicate":False})
    del arr
    alias=session.output/"controls/below-black-alias.cfa"
    original=ROOT/ref["path"]
    S.need(session.budget.output_bytes+153600 <= 16<<20,"CFA hardlink logical output reservation")
    os.link(original,alias)
    session.budget.output_bytes += 153600
    session.budget.check()
    alias_ref={**S.file_ref(alias),"dtype":"<u2","shape":[240,320]}
    session.written[alias_ref["path"]]={k:alias_ref[k] for k in ("sha256","bytes")}
    first,second=original.stat(),alias.stat()
    S.need(original != alias and first.st_ino != 0 and (first.st_dev,first.st_ino) == (second.st_dev,second.st_ino),
           "distinct CFA paths did not share actual identity")
    identities=set()
    arr,_=cfa_file(ref,ROOT,session,law,identities=identities)
    del arr
    reject("actual-cfa-hardlink-identity",lambda:cfa_file(alias_ref,ROOT,session,law,identities=identities),
           "distinct actual CFA file identity")
    arr,_=cfa_file(ref,ROOT,session,law,identities=set())
    add("private-range-restored",int(arr.max()) == 511,{})
    del arr
    q.flat[0]=15361
    for name,raw,message in (("cfa-short",q.tobytes()[:-2],"input bytes/hash changed"),
                             ("cfa-appended",q.tobytes()+b"xx","input bytes/hash changed"),
                             ("cfa-above-white",q.tobytes(),"exceeds white")):
        private_ref={**session.write("controls/"+name+".cfa",raw),"dtype":"<u2","shape":[240,320]}
        private_ref["bytes"]=153600
        reject(name,lambda r=private_ref:cfa_file(r,ROOT,session,law),message)
    reject("cfa-bool-extent",lambda:cfa_file({**ref,"bytes":True},ROOT,session,law),"CFA shape/dtype/extent")
    del q
    scene,seed,index,frame=layout(actual["manifest"],law)[5]
    scalar,mu=scalar_for(scene,index,actual["gate"],session,law)
    q,_=cfa_file(frame["cfa"],actual["base"],session,law)
    audit,_=session.reads.json(frame["audit"],actual["base"])
    for name,edit,message in (
        ("audit-q-hash",lambda a:a.update(q_sha256="0"*64),"actual Q hash"),
        ("audit-seed",lambda a:a["input"].update(seed=709),"input identity/hash"),
        ("audit-key",lambda a:a["streams"]["read"].update(key="planted"),"stream key/entropy"),
        ("audit-rail",lambda a:a["rail_counts"]["pre_encoder_x"].update(x_below_zero=1),"preclipping rail counts"),
    ):
        value=copy.deepcopy(audit)
        edit(value)
        reject(name,lambda a=value:audit_record(a,scene,seed,index,q,scalar,mu,session,law),message)
    # Hold only this frame while testing its audit; no five-frame volume.
    add("restored-noisy-audit",audit_record(audit,scene,seed,index,q,scalar,mu,session,law) is None,{})
    # Its final list position is fixed below to keep the noisy restored companion last.
    noisy_restored=checks.pop()
    del q,scalar,mu
    scene,seed,index,frame=layout(actual["manifest"],law)[0]
    scalar,mu=scalar_for(scene,index,actual["gate"],session,law)
    q,_=cfa_file(frame["cfa"],actual["base"],session,law)
    audit,_=session.reads.json(frame["audit"],actual["base"])
    value=copy.deepcopy(audit)
    value["streams"]={}
    reject("audit-noise-off-stream",lambda:audit_record(value,scene,seed,index,q,scalar,mu,session,law),"null streams")
    changed=session.budget.empty(SHAPE,"<u2","noise-off known pixel defect")
    law.np.copyto(changed,q)
    changed[17,23] += 1
    value=copy.deepcopy(audit)
    value["q_sha256"]=law.raw_hash(changed)
    reject("noise-off-one-code",lambda:audit_record(value,scene,seed,index,changed,scalar,mu,session,law),"exact independent Q")
    add("restored-noise-off",audit_record(audit,scene,seed,index,q,scalar,mu,session,law) is True,{})
    checks.append(noisy_restored)
    law.need(tuple(row["name"] for row in checks) == CONTROL_IDS,"fixed intended-reader control population")
    return dict(check_count=len(checks),checks=checks)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--release",type=Path,required=True)
    parser.add_argument("--release-sha256",required=True)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--manifest-sha256",required=True)
    parser.add_argument("--generation-result",type=Path,required=True)
    parser.add_argument("--generation-result-sha256",required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    prefix=HERE.relative_to(ROOT).as_posix()+"/"
    required=[prefix+x for x in (Path(__file__).name,SUPPORT.name,"independent-noise-reader.py",
              "next-noise-files-verifier-design.md","next-noise-contract.md","software-noise-interface.md")]
    session=S.Session(args,"noise-files-verification",ENTRY_CPU,ENTRY_WALL,required)
    result=dict(schema="m194g-independent-noise-files-read-v1",status="UNCOMMISSIONED_NOISE_FILES",
                ref_root="repository",method="actual-native-cfa-files-v1",manifest=S.file_ref(args.manifest),
                generation_result=S.file_ref(args.generation_result),float_commission=None,noise_commission=None,
                execution_release=session.release_ref,invocation=list(sys.orig_argv),
                sources_before=session.release["source_bindings"],sources_after=None,inputs_before=None,inputs_after=None,
                file_count=0,noise_off_count=0,noisy_count=0,files=[],controls=dict(check_count=0,checks=[]),
                work=None,error=None,finalization_errors=[])
    try:
        S.need(result["manifest"]["sha256"] == args.manifest_sha256
               and result["generation_result"]["sha256"] == args.generation_result_sha256,"external population pins")
        S.need(result["manifest"] in session.release["inputs"] and result["generation_result"] in session.release["inputs"],
               "actual intended inputs not released")
        for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
            os.environ[key]="2"
        law=session.load("independent-noise-reader.py","m194g_held_independent_noise_law")
        session.budget.np=law.np
        prospective,_=session.reads.json(result["manifest"])
        S.need(prospective.get("float_commission") in session.release["inputs"]
               and prospective.get("noise_commission") in session.release["inputs"],"upstream external pins not released")
        actual=read_files(result["manifest"],result["generation_result"],session,law)
        result["files"]=actual["files"]
        result["float_commission"]=actual["manifest"]["float_commission"]
        result["noise_commission"]=actual["manifest"]["noise_commission"]
        S.need(result["float_commission"] in session.release["inputs"]
               and result["noise_commission"] in session.release["inputs"],"upstream external pins not released")
        result["file_count"]=len(result["files"])
        result["noise_off_count"]=sum(r["seed"] is None for r in result["files"])
        result["noisy_count"]=result["file_count"]-result["noise_off_count"]
        result["controls"]=controls(actual,result["manifest"],result["generation_result"],session,law,result["controls"])
        law.validate_runtime(actual["manifest"]["runtime"],actual["base"],session.budget)
        session.final_checks.append(lambda:law.validate_runtime(actual["manifest"]["runtime"],actual["base"],session.budget))
        S.need((result["file_count"],result["noise_off_count"],result["noisy_count"]) == (90,10,80),"full population counts")
        result["status"]="PASS_SOFTWARE_NOISE_FILES_ONLY"
    except Exception:
        result["error"]=traceback.format_exc()
    result["inputs_before"]=dict(session.reads.observed)
    session.terminal(result,gate=result["status"] == "PASS_SOFTWARE_NOISE_FILES_ONLY")
    print(S.canonical({"status":result["status"],"file_count":result["file_count"],
                       "result":S.file_ref(args.output/"result.json")}).decode(),flush=True)
    return 0 if result["status"] == "PASS_SOFTWARE_NOISE_FILES_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
