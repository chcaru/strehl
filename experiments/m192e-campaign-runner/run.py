"""Prospective M192e persistence rehearsal. Only --worker launches product work.

No build, RAW read or process starts on import. The closed three-run schedule is
not the 133-invocation certificate and cannot be extended by a plan parameter.
"""
from __future__ import annotations
import time
START = time.monotonic()
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone
from uuid import UUID
import durable as d

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SAMPLER = ROOT/"experiments/m192c-sampler/sampler.py"
BINDINGS = ROOT/"experiments/m192b-verifier/verify.py"
PUBLICATION = ROOT/"experiments/m193c-output-grid/saved-completion-publication.py"
LAUNCHER = ROOT/"experiments/m193c-output-grid/bounded-process.py"
HARNESS = ROOT/"experiments/m12-scorecard/m12-harness.py"
PROTOCOL = ROOT/"experiments/M192-m12-certify/protocol.json"
LEGACY = ROOT/"experiments/M192-m12-certify/verify.py"
SCHEDULE = ("off", "on", "placebo")
CPU_LIMIT = 600
WALL_LIMIT = 240
CHILD_WALL = 210
CLEANUP_WALL = 12
PUBLICATION_WALL = 6
MAX_LOG = 2*d.MIB
BASE_KEYS = {"summary", "independent_review", "source_freeze", "inputs", "record", "preserved"}
PLAN_KEYS = {"schema", "campaign_id", "source_bindings", "baseline",
             "python", "binary", "sidecar", "output_directory"}

def utc(): return datetime.now(timezone.utc).isoformat()

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def save(budget, path, value, cap=d.RECORD_BYTES, family="metadata"):
    return budget.write(path, d.encode(value), family, cap)

def plan_read(path, expected_sha256):
    plan, _ = d.json_binding(path, expected_sha256=expected_sha256)
    d.need(set(plan) == PLAN_KEYS and plan["schema"] == "m192e-rehearsal-plan-v1",
           "closed rehearsal plan")
    d.need(str(UUID(plan["campaign_id"])) == plan["campaign_id"], "canonical campaign ID")
    output = d.lexical_path(plan["output_directory"],missing=True)
    d.need(output.parent == HERE.resolve() and output.name.startswith("rehearsal-")
           and not output.is_symlink(), "fresh owned output root")
    d.need(set(plan["baseline"]) == BASE_KEYS, "six baseline bindings")
    refs = [*plan["source_bindings"], *plan["baseline"].values(),
            plan["python"], plan["binary"], plan["sidecar"]]
    for ref in refs: d.check_ref(ref)
    sources = {str(Path(r["path"]).resolve()): r for r in plan["source_bindings"]}
    required = {Path(__file__).resolve(), HERE/"durable.py", HERE/"verify.py",
                HERE/"launch.py", ROOT/"experiments/m193c-output-grid/sift-lightglue-saved-completion-run.py",
                HERE/"preregistration.md", HERE/".gitattributes", SAMPLER, BINDINGS, PUBLICATION,
                LAUNCHER, HARNESS, PROTOCOL, LEGACY,
                ROOT/"scripts/check-defaults.py",
                ROOT/"experiments/m192d-production-rehearsal/run.py",
                ROOT/"experiments/m192d-production-rehearsal/independent-verify.py"}
    d.need(len(sources) == len(plan["source_bindings"])
           and {str(p.resolve()) for p in required} <= set(sources), "source closure")
    d.need(Path(plan["python"]["path"]).resolve() == Path(sys.executable).resolve(),
           "actual Python executable")
    summary = d.read_ref(plan["baseline"]["summary"])
    independent = d.read_ref(plan["baseline"]["independent_review"])
    freeze = d.read_ref(plan["baseline"]["source_freeze"])
    cached = d.read_ref(plan["baseline"]["record"])
    inputs = d.read_ref(plan["baseline"]["inputs"])
    original = d.read_ref(sources[str(PROTOCOL.resolve())])
    d.need(summary["schema"] == "m192d-rehearsal-v1"
           and summary["status"] == "NONPERTURBATION_VERIFIED"
           and summary["completed"] == 7 and summary["identity_and_execution"] is True,
           "completed original sampler rehearsal")
    d.need(independent["schema"] == "m192d-independent-artifact-review-v1"
           and independent["status"] == "PASS", "independent original rehearsal")
    d.need(Path(independent["author_output_directory"]).resolve() ==
           Path(plan["baseline"]["summary"]["path"]).resolve().parent,
           "independent review package association")
    d.need(cached["identity_matches"] is True and cached["terminal_matches"] is True
           and cached["returncode"] == 0 and cached["mode"] == "on",
           "cached observed positive record")
    d.need(cached["binary_sha256"].upper() == plan["binary"]["sha256"].upper()
           and cached["sidecar_sha256"].upper() == plan["sidecar"]["sha256"].upper()
           == original["sidecars"]["33"]["sha256"], "binary/sidecar association")
    d.need(cached["tiff"]["output_sha256"] == freeze["reference_output_sha256"]
           and cached["tiff"]["pixel_sha256"] == freeze["reference_pixel_sha256"],
           "cached file/pixel baseline")
    d.need(type(inputs) is list and len(inputs) == 33
           and len({str(Path(r["path"]).resolve()) for r in inputs}) == 33
           and all(Path(r["path"]).parent.resolve() ==
                   Path(original["inputs"]["33"]).resolve() for r in inputs),
           "exact previously selected 33 inputs")
    # The existing independent report binds the entire original seven-record set.
    source_refs = freeze["sources"]
    d.need(any(Path(r["path"]).resolve() == SAMPLER and
               r["sha256"].upper() == sources[str(SAMPLER)]["sha256"].upper()
               for r in source_refs), "same commissioned sampler source")
    return plan, output, original, cached, inputs

def verify_inputs(expected):
    rows = []
    for row in expected:
        actual = d.binding(row["path"])
        d.need(actual["bytes"] == row["bytes"] and
               actual["sha256"] == row["sha256"].upper()
               and Path(row["path"]).stat().st_mtime_ns == row["mtime_ns"],
               "selected input changed")
        rows.append(dict(actual, mtime_ns=Path(row["path"]).stat().st_mtime_ns))
    return rows

def preserve_outputs(plan):
    """Exactly seven existing M192d outputs; no new render or old record mutation."""
    manifest=d.read_ref(plan["baseline"]["preserved"])
    d.need(set(manifest)=={"schema","rows"} and manifest["schema"]=="m192e-prior-output-preservation-v1",
           "closed old-output preservation manifest")
    rows=manifest["rows"];d.need(type(rows) is list and len(rows)==7,"seven old outputs")
    review=d.read_ref(plan["baseline"]["independent_review"])
    original=Path(plan["baseline"]["summary"]["path"]).parent
    answer=[]
    for i,row in enumerate(rows):
        d.need(set(row)=={"index","record","output"} and type(row["index"]) is int and row["index"]==i,"literal old output index")
        d.need(Path(row["record"]["path"]).resolve()==original/f"{i:02d}-record.json","exact old record path")
        record=d.read_ref(row["record"]);actual=d.check_ref(row["output"])
        expected=review["rows"][i]
        d.need(record["index"]==i and Path(record["output_path"]).resolve()==Path(actual["path"]) and
               actual["sha256"]==record["tiff"]["output_sha256"]==expected["output_sha256"] and
               record["tiff"]["pixel_sha256"]==expected["pixel_sha256"],"same independently reviewed seven outputs")
        answer.append(dict(index=i,record=row["record"],output=actual))
    return dict(schema="m192e-old-output-preservation-v1",rows=answer)


def binding_domain(v, plan):
    refs = {str(Path(row["path"]).resolve()):row for row in plan["source_bindings"]}
    return d.environment_domain(refs[str((ROOT/"scripts/check-defaults.py").resolve())], v)

def environment(v, domain, output, rid, sidecar):
    env = os.environ.copy()
    prefixes = ("STREHL_", "RAYON_", "OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_")
    removed = sorted(k for k in env if k.upper().startswith(prefixes))
    for key in removed: del env[key]
    folder = output/"work"/"monitor"/rid
    active = dict(STREHL_PYRAMID_WORKERS="8", STREHL_WARPMAP=str(sidecar),
                  STREHL_CACHE_DIR=str(output/"work"/"cache"/"native"/"n33"),
                  TEMP=str(folder/"temp"), TMP=str(folder/"temp"))
    env.update(active)
    recorded = {key: env.get(key) for key in sorted(set(domain) | set(active) | set(removed))}
    d.need(all(value is None for key,value in recorded.items() if key not in active),
           "complete cleared environment domain")
    return env, recorded, removed, folder

def persistence_controls(budget, output, cached, publication):
    """New storage integration only; no old observer/Job/pixel controls replay."""
    directory = output/"controls"; directory.mkdir()
    rows = []
    pubdir = directory/"terminal"; pubdir.mkdir()
    pub = publication.Publisher(publication.Writer(budget, pubdir, "terminal"),
            dict(schema="m192e-storage-control-terminal-v1"), 4096)
    checkpoint = d.Checkpoint(budget, directory/"trace", dict(campaign_id="STORAGE-CONTROL",run_id="STORAGE-CONTROL"), 16384)
    fixture = dict(actual_cached_trace_counts=cached["trace"]["phase_counts"],
                   actual_cached_trace_drops=cached["trace"]["dropped"],
                   actual_cached_argv=cached["argv"])
    def record(name, action):
        row = dict(id=name, passed=False); rows.append(row)
        try: action(row); row["passed"] = True
        except BaseException as e: row["error"] = repr(e); raise
        finally:
            raw = d.encode(rows)
            budget.write(directory/"progress.json", raw, cap=128*1024,
                         replace=(directory/"progress.json").exists())
    def positive(row):
        first = checkpoint.save(fixture)
        row.update(first=first, recovered=checkpoint.recover())
        d.need(row["recovered"]["sequence"] == 0, "first checkpoint recoverable")
    record("actual-metadata-roundtrip", positive)
    def partial(row):
        before = checkpoint.recover()
        try: checkpoint.save(fixture, fault="partial-stage")
        except OSError as e: row["expected_error"] = str(e)
        else: raise ValueError("partial-stage did not fail")
        after = checkpoint.recover()
        d.need(before == after, "partial staging cannot replace committed generation")
        row.update(before=before, after=after)
    record("partial-stage-recovery", partial)
    def overflow(row):
        before = checkpoint.recover()
        try: checkpoint.save(dict(padding="x"*checkpoint.size))
        except ValueError as e:
            d.need(str(e) == "trace checkpoint capacity", "actual trace overflow seam")
            row["expected_error"] = str(e)
        else: raise ValueError("trace overflow did not fail")
        after = checkpoint.recover()
        d.need(before == after, "overflow retains committed trace")
        result = pub.publish(dict(schema="m192e-storage-control-terminal-v1",
                                  status="REFUSED", reason="TRACE_OVERFLOW"))
        d.need(result["canonical_refusal_verified"] is True and not result["passed"],
               "terminal refusal survives trace overflow")
        row.update(before=before, after=after, publication=result,
                   retained_refusal=budget.write(directory/"overflow-refusal.json",
                       pub.paths["result.json"].read_bytes(),cap=4096))
    record("trace-overflow-terminal-refusal", overflow)
    def no_commit(row):
        before = checkpoint.recover()
        try: checkpoint.save(fixture, fault="before-replace")
        except OSError as e: row["expected_error"] = str(e)
        else: raise ValueError("replacement fault not exercised")
        d.need(checkpoint.recover() == before, "complete staging is not commitment")
        row["recovered"] = before
    record("before-replace-recovery", no_commit)
    def restore(row):
        unchanged = d.sha(d.encode(fixture))
        final = checkpoint.save(fixture)
        restored = d.read_ref(final, checkpoint.size)
        d.need(d.sha(d.encode(restored["payload"])) == unchanged,
               "restored whole intrinsic payload")
        result = pub.publish(dict(schema="m192e-storage-control-terminal-v1",
                                  status="COMPLETE_STORAGE_CONTROL_ONLY",
                                  checkpoint=final), late=lambda: None)
        d.need(result["passed"], "same publisher restored after capacity refusal")
        row.update(final=final, intrinsic_sha256=unchanged, publication=result,
                   recovered=checkpoint.recover())
    record("same-instance-restored-placebo", restore)
    def resealed(row,kind):
        originals={p:p.read_bytes() for p in checkpoint.paths}
        try:
            retained=[]
            targets=checkpoint.paths if kind!="generation" else [checkpoint.paths[(checkpoint.sequence-1)%2]]
            for path in targets:
                value=d.read_json(path,checkpoint.size)
                if kind=="generation":value["previous_sha256"]="F"*64
                else:value["identity"][kind]="WRONG-RESEALED-IDENTITY"
                value["payload_sha256"]=d.sha(d.encode(value["payload"]))
                checkpoint._write(path,checkpoint.pack(value))
                retained.append(dict(value=value,mutated=d.binding(path),fixed_extent=checkpoint.size,
                                     scope="injected generation before exact same-path restoration"))
            error=None
            try:checkpoint.recover()
            except ValueError as exc:error=str(exc)
            d.need(error is not None,"resealed association fault must reject recovery")
            row.update(expected_error=error,injected_generation_witnesses=retained)
        finally:
            for path,raw in originals.items():checkpoint._write(path,raw)
            d.need(all(p.read_bytes()==raw for p,raw in originals.items()),"exact original control generations restored")
            row["restored_recovery"]=checkpoint.recover()
    record("resealed-campaign-identity",lambda row:resealed(row,"campaign_id"))
    record("resealed-run-identity",lambda row:resealed(row,"run_id"))
    record("resealed-generation-chain",lambda row:resealed(row,"generation"))
    return save(budget, directory/"controls.json", rows, 128*1024)

def install_trace(s, checkpoint, mode):
    original_trace, original_telemetry = s.Trace, s.telemetry
    witness = dict(mode=mode, checkpoint_every_observations=100,
                   calls=0, telemetry_calls=0, checkpoint_count=0,
                   latest_telemetry=None, restored=False)
    class PersistentTrace(original_trace):
        def observe(self, row):
            super().observe(row)
            witness["calls"] += 1
            if witness["calls"] % 100 == 0:
                payload = dict(trace=self.result(),
                               latest_telemetry=witness["latest_telemetry"],
                               telemetry_calls=witness["telemetry_calls"],
                               last_observation=row["observed_ns"],
                               retained_scope="bounded tails + aggregate counts/maxima; INCOMPLETE",
                               placebo_label=mode == "placebo")
                checkpoint.save(payload)
                witness["checkpoint_count"] += 1
    def telemetry():
        row = original_telemetry()
        witness["telemetry_calls"] += 1
        witness["latest_telemetry"] = row
        return row
    if mode != "off": s.Trace, s.telemetry = PersistentTrace, telemetry
    def restore():
        s.Trace, s.telemetry = original_trace, original_telemetry
        witness["restored"] = s.Trace is original_trace and s.telemetry is original_telemetry
    return witness, restore

def terminal_markers(text, count, workers, stack, output):
    markers = [f"frames          : {count} from {stack}",
               "coverage mode   : scale -- as asked, --cover",
               "alignment       : ON (sidecar-override)", f"{count} placed / 0 refused",
               f"folded          : {count} / {count} frames", f"{workers} execution threads",
               "memory plan     : 4 canonical chunks, 1 reusable frame worker, 1 retained + 1 scratch accumulator",
               "camera RGB -> LINEAR sRGB", "Malvar-He-Cutler demosaic",
               "wrote           : "+str(output), "total           :"]
    return {marker: marker in text for marker in markers}

def terminal_evidence(budget, path, value):
    raw = d.encode(value)
    d.need(len(raw) <= 128*1024, "child terminal evidence capacity")
    raw += b" "*(128*1024-len(raw))
    budget.reserve(path, len(raw), "terminal", terminal=True)
    with Path(path).open("wb") as stream:
        d.need(stream.write(raw) == len(raw), "child terminal evidence write")
        stream.flush(); os.fsync(stream.fileno())
    return d.binding(path)

class FinalTail:
    """Bounded post-publication sample; complete CPU requires actual outer exit."""
    SIZE=8192
    def __init__(self,pub,budget,role,plan_ref):
        self.pub=pub;self.budget=budget;self.role=role;self.plan=plan_ref
        self.path=pub.writer.root/"terminal-tail.json";self.stage=pub.writer.root/"terminal-tail-stage.json"
        self.default=dict(schema="m192e-publication-tail-v1",role=role,plan=plan_ref,
            process_id=os.getpid(),status="REFUSED",phase="INITIAL_INCOMPLETE",
            complete_cpu_accounting=False,outer_exit_required=True)
        raw=self.pack(self.default)
        for path in (self.path,self.stage):pub.writer.write(path,raw,terminal=True)
    def pack(self,value):
        raw=d.encode(value);d.need(len(raw)<=self.SIZE,"fixed final-tail capacity")
        return raw+b" "*(self.SIZE-len(raw))
    def write(self,value):
        raw=self.pack(value)
        self.pub.writer.write(self.stage,raw,replace=True,terminal=True)
        self.pub.writer.replace(self.stage,self.path)
        actual,ref=d.json_binding(self.path,self.SIZE)
        d.need(actual==value and ref["bytes"]==self.SIZE,"exact final-tail readback")
        return ref
    def sample(self):
        own=time.process_time()
        return dict(process_cpu_seconds=own,latest_owned_job_cpu_seconds=self.budget.child_cpu,
            combined_cpu_seconds=own+self.budget.child_cpu,wall_seconds=time.monotonic()-START,
            observed_job_queries=self.budget.job_queries,accounting_error=self.budget.accounting_error)
    def finish(self,result):
        started_cpu=time.process_time();started_wall=time.monotonic()
        result["terminal_tail_path"]=str(self.path)
        result["complete_cpu_accounting"]=False
        result["outer_exit_required"]=True
        result["command"]=sys.orig_argv
        published=None;tailref=None;error=None
        def admission():
            self.budget.check(True,terminal=True)
            sample=self.sample()
            d.need(sample["accounting_error"] is None,"final valid Job accounting")
            d.need(sample["wall_seconds"]<=(WALL_LIMIT if self.role=="parent" else CHILD_WALL),"whole process wall through publication")
            if self.role=="parent":d.need(sample["combined_cpu_seconds"]<=CPU_LIMIT,"whole combined CPU through publication")
            d.need(time.process_time()-started_cpu<=2 and time.monotonic()-started_wall<=3,"fixed final-publication allowance")
        try:
            # No success line is emitted before the durable post-publication tail.
            published=self.pub.publish(result,late=admission,after=admission)
            d.need(published["passed"] or published.get("canonical_refusal_verified") is True,"canonical disposition verified")
            status=result["status"] if published["passed"] else "REFUSED"
            value=dict(self.default,status=status,phase="AFTER_CANONICAL_PUBLICATION",
                canonical=published["canonical"],first_positive=published.get("first_positive"),
                child=result.get("child"),worker=result.get("worker"),
                sample=self.sample(),publication=dict(cpu_seconds=time.process_time()-started_cpu,
                    wall_seconds=time.monotonic()-started_wall),
                sampling_scope="through completed canonical publication; excludes this tail write and process exit")
            tailref=self.write(value)
            if published["passed"]:admission()
            advert=dict(schema="m192e-terminal-advertisement-v1",role=self.role,status=status,
                process_id=os.getpid(),plan=self.plan,canonical=published["canonical"],tail=tailref,
                sample_after_tail=self.sample(),complete_cpu_accounting=False,outer_exit_required=True)
            raw=d.encode(advert);d.need(len(raw)<=4096,"bounded final advertisement")
            sys.stdout.write(raw.decode()+"\n");sys.stdout.flush()
            if published["passed"]:admission()
            return 0 if published["passed"] else 1
        except BaseException as exc:
            text=str(exc);error=dict(type=type(exc).__name__,message_suffix=text[-1024:],
                full_message_characters=len(text),full_message_sha256=d.sha(text.encode()),truncated=len(text)>1024)
            # One bounded revocation attempt. No observer/product work resumes.
            refused=dict(result,status="REFUSED",publication_error=error)
            prior_positive=None if published is None else published.get("first_positive")
            try:
                published=self.pub.publish(refused)
                value=dict(self.default,status="REFUSED",phase="FINAL_PUBLICATION_REFUSED",
                    canonical=published.get("canonical"),canonical_refusal_verified=published.get("canonical_refusal_verified") is True,
                    first_positive=prior_positive,child=result.get("child"),worker=result.get("worker"),
                    error=error,sample=self.sample(),
                    sampling_scope="refused recovery sample; actual outer exit is authoritative")
                self.write(value)
            except BaseException:
                # The initialized tail remains conservative if even bounded
                # replacement fails. Outer nonzero exit still denies admission.
                pass
            return 1


def worker(args):
    plan, output, original, cached, inputs = plan_read(args.plan,args.plan_sha256)
    budget = d.Budget(output, CHILD_WALL-PUBLICATION_WALL, started=START)
    publication = load(PUBLICATION, "m192e_publication")
    terminal_dir = output/"worker"; terminal_dir.mkdir()
    pub = publication.Publisher(publication.Writer(budget, terminal_dir, "terminal"),
            dict(schema="m192e-worker-v1", campaign_id=plan["campaign_id"]))
    tail=FinalTail(pub,budget,"worker",d.binding(args.plan))
    result = dict(schema="m192e-worker-v1", campaign_id=plan["campaign_id"],
                  status="REFUSED", completed=[], unvisited=list(SCHEDULE),
                  active=None, error=None, full_campaign_certificate=False)
    try:
        result["controls"] = persistence_controls(budget, output, cached, publication)
        s = load(SAMPLER, "m192e_sampler")
        v = load(BINDINGS, "m192e_bindings")
        domain = binding_domain(v, plan)
        result["inputs_before"] = save(budget, output/"inputs-before.json", verify_inputs(inputs))
        result["preserved_before"] = save(budget,output/"preserved-before.json",preserve_outputs(plan))
        sidecar = output/"work"/"sidecars"/"n33.warpmap.txt"
        sidecar.parent.mkdir(parents=True); sidecar.write_bytes(Path(plan["sidecar"]["path"]).read_bytes())
        d.need(d.binding(sidecar)["sha256"] == plan["sidecar"]["sha256"].upper(), "sidecar copy")
        (output/"work"/"outputs").mkdir()
        (output/"work"/"cache"/"native"/"n33").mkdir(parents=True)
        (output/"records").mkdir()
        (output/"logs").mkdir()
        for index, mode in enumerate(SCHEDULE):
            result["active"] = mode
            rid = f"native-n33-w8-{mode}"
            trace = d.Checkpoint(budget, output/"records"/rid/"trace",
                                 dict(campaign_id=plan["campaign_id"], run_id=rid))
            env, recorded, removed, folder = environment(v, domain, output, rid, sidecar)
            destination = output/"work"/"outputs"/(rid+".tiff")
            argv = [plan["binary"]["path"], "stack", original["inputs"]["33"],
                    "--limit", "33", "--out", str(destination),
                    *original["configuration"]["arguments_after_output"]]
            invocation = dict(schema="m192e-invocation-v1", campaign_id=plan["campaign_id"],
                run_id=rid, sequence=index, mode=mode, sampler_mode="on", limit=33, workers=8,
                argv=argv, environment=recorded, cleared_present_variables=removed,
                environment_domain=sorted(domain), actual_monitor_folder=str(folder),
                binary=plan["binary"], sidecar=d.binding(sidecar), source_plan=d.binding(args.plan),
                input_binding=result["inputs_before"], started_utc=utc())
            invref = save(budget, output/"records"/rid/"invocation.json", invocation, 64*1024)
            progress = dict(active=rid, completed=result["completed"], unvisited=result["unvisited"],
                            invocation=invref, checkpoint_slots=[str(p) for p in trace.paths],
                            status="INCOMPLETE", may_resume=False)
            budget.write(output/"progress.json", d.encode(progress), cap=64*1024,
                         replace=(output/"progress.json").exists())
            observation, restore = install_trace(s, trace, mode)
            raw = None
            try:
                raw = s.monitor(argv=argv, env=env, folder=folder, mode="on")
            finally:
                restore()
                observation["latest_telemetry"] = None  # Full final telemetry lives once in raw monitor.
                save(budget, output/"records"/rid/"adapter.json", observation, 4096)
            rawref = save(budget, output/"records"/rid/"monitor.json", raw,
                          d.RECORD_BYTES, "trace")
            logs = {}
            origins = {}
            for stream in ("stdout", "stderr"):
                origin = folder/(stream+".log")
                origins[stream] = d.binding(origin)
                d.need(origins[stream]["bytes"] <= MAX_LOG, "product log capacity")
                dest = output/"logs"/(rid+"."+stream+".log")
                with origin.open("rb") as source: payload = source.read(MAX_LOG+1)
                if payload:
                    logs[stream] = budget.write(dest, payload, "logs", MAX_LOG)
                else:
                    dest.write_bytes(b""); logs[stream] = d.binding(dest)
                d.need(logs[stream]["sha256"] == origins[stream]["sha256"],
                       "archive log exact origin")
            stderr = Path(origins["stderr"]["path"]).read_text(encoding="utf-8")
            markers = terminal_markers(stderr, 33, 8, original["inputs"]["33"], destination)
            identity = s.h.tiff_witness(destination) if destination.is_file() else None
            good_identity = identity is not None and all(identity[k] == cached["tiff"][k]
                                  for k in ("output_sha256", "pixel_sha256"))
            no_termination = raw["job_accounting"]["total_terminated_processes"] == 0
            natural = raw["returncode"] == 0 and raw["job_accounting"]["active_processes"] == 0 and no_termination
            record = dict(schema="m192e-record-v1", campaign_id=plan["campaign_id"],
                          run_id=rid, sequence=index, mode=mode, invocation=invref,
                          monitor=rawref, adapter=d.binding(output/"records"/rid/"adapter.json"),
                          logs=logs, log_origins=origins, terminal_markers=markers,
                          tiff=identity, output=d.binding(destination) if destination.is_file() else None,
                          identity_matches=good_identity, natural_complete=natural,
                          sampling_pass=raw["sampling_pass"],
                          max_interval_ms_including_final=raw["max_interval_ms_including_final"],
                          coverage=raw["coverage"],checkpoint_exercised=(mode=="off" or observation["checkpoint_count"]>0),
                          checkpoint_count=observation["checkpoint_count"],completed_utc=utc(),
                          trace_recovery=trace.recover(),
                          full_trace_retained=all(n == 0 for n in raw["trace"]["dropped"].values()),
                          dropped=raw["trace"]["dropped"])
            rec = save(budget, output/"records"/rid/"record.json", record, 64*1024)
            result["completed"].append(rec); result["unvisited"].remove(mode)
            # A sampling refusal is recorded and the fixed schedule continues.
            d.need(natural and all(markers.values()) and observation["restored"] and record["checkpoint_exercised"],
                   "invalid native execution/terminal/adapter")
            budget.check(True)
        result["inputs_after"] = save(budget, output/"inputs-after.json", verify_inputs(inputs))
        result["preserved_after"] = save(budget,output/"preserved-after.json",preserve_outputs(plan))
        d.need(d.read_ref(result["preserved_before"])==d.read_ref(result["preserved_after"]),"all seven old outputs unchanged")
        d.need(d.read_ref(result["inputs_before"]) ==
               d.read_ref(result["inputs_after"]), "input preservation")
        for ref in plan["source_bindings"]: d.check_ref(ref)
        d.check_ref(plan["binary"]); d.check_ref(plan["sidecar"])
        records = [d.read_ref(r) for r in result["completed"]]
        identities = all(r["identity_matches"] for r in records)
        sampling = all(r["sampling_pass"] for r in records)
        result.update(active=None, status="COMPLETE_REHEARSAL_EVIDENCE_ONLY",
                      output_nonperturbation=identities, sampling_all_pass=sampling,
                      integration_pass=identities and sampling,
                      timing_bar="NOT_EVALUATED_THREE_RUN_DURABILITY_REHEARSAL",
                      trace_policy="BOUNDED_TAILS_WITH_DECLARED_EVICTIONS",
                      bytes_written_by_durable_adapter=budget.bytes_written)
    except BaseException as e:
        result["error"] = dict(type=type(e).__name__, message=str(e))
    return tail.finish(result)

def parent(args):
    start = START
    plan, output, original, cached, inputs = plan_read(args.plan,args.plan_sha256)
    d.need(not output.exists(), "no resume or overwrite")
    output.mkdir()
    budget = d.Budget(output, WALL_LIMIT-PUBLICATION_WALL,CPU_LIMIT,started=start)
    publication = load(PUBLICATION, "m192e_parent_publication")
    pdir = output/"parent"; pdir.mkdir()
    pub = publication.Publisher(publication.Writer(budget, pdir, "terminal"),
          dict(schema="m192e-parent-v1", campaign_id=plan["campaign_id"]))
    tail=FinalTail(pub,budget,"parent",d.binding(args.plan))
    result = dict(schema="m192e-parent-v1", campaign_id=plan["campaign_id"],
                  status="REFUSED", plan=d.binding(args.plan), child=None,
                  worker=None, error=None, full_campaign_certificate=False)
    try:
        launcher = load(LAUNCHER, "m192e_launcher")
        api = launcher.load_job_api({k: v for k,v in
             {**d.binding(HARNESS), "sha256":d.binding(HARNESS)["sha256"].lower()}.items()
                                     if k != "path"})
        terminal_evidence(budget, output/"child.json",
                          dict(status="UNOBSERVED_CHILD_TERMINAL", terminal_job_accounting=False))
        command = [str(Path(sys.executable).resolve()), "-B", str(Path(__file__).resolve()),
                   "--plan", str(Path(args.plan).resolve()), "--plan-sha256", args.plan_sha256, "--worker"]
        remaining = WALL_LIMIT-(time.monotonic()-start)-CLEANUP_WALL-PUBLICATION_WALL
        d.need(remaining >= CHILD_WALL, "full child envelope before launch")
        child_env, removed = launcher.clean_environment()
        original_query=api.job_accounting
        def live_query(job):
            observed=original_query(job);budget.observe_job(observed);return observed
        api.job_accounting=live_query
        try:
            allowed_cpu=CPU_LIMIT-time.process_time()-4
            d.need(allowed_cpu>0,"combined CPU envelope before launch")
            child = launcher.run(command, child_env, ROOT, output/"worker.log", api=api,
                                 wall_seconds=CHILD_WALL, cpu_seconds=allowed_cpu,
                                 log_bytes=d.MIB, committed_bytes=8*(1<<30), check=budget.check)
        finally:api.job_accounting=original_query
        result["child"] = terminal_evidence(budget, output/"child.json", child)
        result["cleared_child_environment"] = removed
        worker_path = output/"worker"/"result.json"
        if worker_path.exists(): result["worker"] = d.binding(worker_path)
        d.need(child["error"] is None and not child["cleanup_errors"]
               and child["exit_code"] == 0 and child["terminal_job_accounting"] is True
               and child["termination"]["attempted"] is False, "natural complete child tree")
        value = d.read_ref(result["worker"], 64*1024)
        d.need(value["status"] == "COMPLETE_REHEARSAL_EVIDENCE_ONLY"
               and value["campaign_id"] == plan["campaign_id"]
               and len(value["completed"]) == 3 and not value["unvisited"], "complete fixed worker")
        checker = load(HERE/"verify.py", "m192e_checker")
        verification = checker.verify_worker(args.plan, args.plan_sha256, worker_path)
        result["verification"] = save(budget, output/"verification.json", verification, 128*1024)
        d.need(verification["status"] == "PASS_REHEARSAL_BINDINGS_ONLY", "new evidence bindings")
        result.update(status="COMPLETE_REHEARSAL_EVIDENCE_ONLY",
                      integration_pass=value["integration_pass"],
                      sampling_all_pass=value["sampling_all_pass"],
                      output_nonperturbation=value["output_nonperturbation"],
                      timing_bar=value["timing_bar"])
    except BaseException as e:
        result["error"] = dict(type=type(e).__name__, message=str(e))
    result["wall_seconds_before_publication"] = time.monotonic()-start
    result["combined_cpu_seconds_before_publication"]=time.process_time()+budget.child_cpu
    result["observed_job_queries"]=budget.job_queries
    result["accounting_error"]=budget.accounting_error
    return tail.finish(result)

def recover(args):
    plan, output, *_ = plan_read(args.plan,args.plan_sha256)
    receipt = dict(schema="m192e-recovery-v1", campaign_id=plan["campaign_id"],
                   status="INCOMPLETE_UNLESS_BOUND_TERMINAL_PROVES_COMPLETE",
                   may_resume=False, may_certify=False, terminals={}, checkpoints=[])
    for name in ("parent", "worker"):
        path = output/name/"result.json"
        if path.exists():
            try:
                value, ref = d.json_binding(path, 64*1024)
                receipt["terminals"][name] = dict(binding=ref, value=value)
            except Exception as e: receipt["terminals"][name] = dict(error=repr(e))
    for mode in SCHEDULE:
        rid = "native-n33-w8-"+mode
        directory = output/"records"/rid/"trace"
        if not directory.exists(): continue
        # Read-only recovery: never construct a writer or repair a stage.
        checkpoint = object.__new__(d.Checkpoint)
        checkpoint.paths = [directory/f"slot-{i}.json" for i in range(2)]
        checkpoint.size = d.SLOT_BYTES
        checkpoint.identity = dict(campaign_id=plan["campaign_id"], run_id=rid)
        try: receipt["checkpoints"].append(dict(run_id=rid, **checkpoint.recover()))
        except Exception as e: receipt["checkpoints"].append(dict(run_id=rid,error=repr(e)))
    print(json.dumps(receipt, sort_keys=True, allow_nan=False))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--plan-sha256", required=True)
    flags = parser.add_mutually_exclusive_group()
    flags.add_argument("--worker", action="store_true")
    flags.add_argument("--recover", action="store_true")
    args = parser.parse_args()
    if args.recover: recover(args); return 0
    return worker(args) if args.worker else parent(args)

if __name__ == "__main__": raise SystemExit(main())


