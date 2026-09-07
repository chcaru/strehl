"""Short preregistered sampler controls. Retains every arm and timing repetition."""
from __future__ import annotations
import os
for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
import sampler

HERE, ROOT = sampler.HERE, sampler.ROOT
CHILD = HERE / "child.py"
MODES = ("original", "off", "on", "placebo")
PACKAGE = ROOT / "experiments/M192-m12-certify/recovery-20260906-163253/results"


def sha(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def inventory():
    paths = [sampler.INHERITED, ROOT / "experiments/M192-m12-certify/campaign.py",
        ROOT / "experiments/M192-m12-certify/protocol.json", ROOT / "experiments/M192-m12-certify/verify.py"]
    paths += sorted(p for p in PACKAGE.rglob("*") if p.is_file())
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")


def run_arm(out, name, workload, mode, injection=None):
    folder = out / name
    output, receipt = folder / "output.bin", folder / "child-receipt.json"
    argv = [sys.executable, "-B", str(CHILD), "--mode", workload,
            "--output", str(output), "--receipt", str(receipt)]
    env = os.environ.copy()
    env["TEMP"] = env["TMP"] = str(folder / "temp")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if mode == "original":
        folder.mkdir()
        (folder / "temp").mkdir()
        (folder / "temp/fixture.bin").write_bytes(bytes(4096))
        observer_start = time.process_time()
        row = sampler.h.monitor_command(argv=argv, env=env, stdout_path=folder/"stdout.log",
            stderr_path=folder/"stderr.log", temp=folder/"temp", measured_commit="synthetic-m192c")
        row["observer_cpu_seconds"] = time.process_time()-observer_start
        row["product_cpu_seconds"] = row["host_load_during_run"]["process_tree_cpu_seconds"]
        row["host_busy_cpu_seconds"] = row["host_load_during_run"]["system_busy_cpu_seconds"]
        row["coverage"] = row["memory"]["sample_count"]/(row["memory"]["sample_count"]+row["memory"]["missed_intervals"])
        row["max_interval_ms_including_final"] = None
        row["sampling_pass"] = row["memory"]["max_gap_ms"] <= 100 and row["coverage"] >= .9
        row["argv"] = argv
        row["mode"] = mode
    else:
        row = sampler.monitor(argv=argv, env=env, folder=folder, mode=mode, injection=injection)
    row["name"], row["workload"] = name, workload
    row["environment"] = {k: env.get(k) for k in ("TEMP", "TMP", "PYTHONDONTWRITEBYTECODE",
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
    row["output"] = sha(output)
    row["child_receipt"] = json.loads(receipt.read_text())
    child_receipt = receipt.with_suffix(".child.json")
    if child_receipt.exists():
        row["spawned_child_receipt"] = json.loads(child_receipt.read_text())
        row["spawned_child_output"] = sha(output.with_suffix(".child.bin"))
    begin, end = row["child_receipt"][0], row["child_receipt"][-1]
    row["child_wall_seconds"] = (end["qpc_ns"]-begin["qpc_ns"])/1e9
    row["child_cpu_seconds"] = end["cpu_s"]-begin["cpu_s"]
    write(folder / "record.json", row)
    print(f"{name}: rc={row['returncode']} coverage={row['coverage']:.3f} max-ms={row.get('max_interval_ms_including_final')} wall={row['wall_seconds']:.3f}", flush=True)
    return row


def pulse_checks(row):
    events = {e["event"]: e for e in row["child_receipt"]}
    observations = row["trace"]["observations"]
    intervals = {
        "before": (events["start"]["qpc_ns"], events["allocate-begin"]["qpc_ns"]),
        "plateau": (events["allocated-touched"]["qpc_ns"], events["release-begin"]["qpc_ns"]),
        "after": (events["released"]["qpc_ns"], events["end"]["qpc_ns"])}
    values = {name: [o["private_bytes"] for o in observations if lo <= o["observed_ns"] <= hi]
              for name, (lo, hi) in intervals.items()}
    if not all(values.values()):
        return {"intervals_observed": False, "counts": {k:len(v) for k,v in values.items()}}
    levels = {name: statistics.median(v) for name,v in values.items()}
    return {"intervals_observed": True, "levels": levels, "counts": {k:len(v) for k,v in values.items()},
        "rise_bytes": levels["plateau"]-levels["before"], "fall_bytes": levels["plateau"]-levels["after"],
        "rise_pass": levels["plateau"]-levels["before"] >= 48*1024**2,
        "fall_pass": levels["plateau"]-levels["after"] >= 48*1024**2,
        "kernel_peak_pass": row["job_peak_bytes"] >= row["peak_private_bytes"]-1024**2}


def spawn_checks(row):
    child = row["spawned_child_receipt"]
    pid = child[0]["pid"]
    found = [p for p in row["processes"] if p["pid"] == pid]
    return {"child_pid": pid, "child_lifetime_ms": (child[-1]["qpc_ns"]-child[0]["qpc_ns"])/1e6,
        "observed": len(found) == 1 and found[0]["created"] > 0,
        "job_count": row["job_accounting"]["total_processes"],
        "job_count_pass": row["job_accounting"]["total_processes"] == 2,
        "allocation_pass": bool(found) and found[0]["peak_private_bytes"] >= 24*1024**2}


def stall_checks(row, phase):
    trace = row["trace"]
    longest = max(trace["phase_max_ms"], key=trace["phase_max_ms"].get)
    injected_events = [e for e in trace["events"] if e["injection_label"]]
    return {"longest_phase": longest, "localized": longest == phase,
        "phase_duration_ms": trace["phase_max_ms"].get(phase),
        "injection_measured": len(injected_events) == 1 and injected_events[0]["wall_ms"] >= 140,
        "interval_red": row["max_interval_ms_including_final"] > 100,
        "criterion_red": not row["sampling_pass"],
        "incident_retained": any(i["trigger"].get("phase") == phase for i in trace["incidents"])}


def main():
    out = HERE / ("out-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
    out.mkdir()
    frozen = inventory()
    sources = {p.name:sha(p) for p in (HERE/"preregistration.md", HERE/"sampler.py", CHILD, Path(__file__))}
    write(out/"source-freeze.json", {"argv":sys.argv, "cwd":str(Path.cwd()), "sources":sources,
        "preserved_inputs":frozen, "python":platform.python_version(), "psutil":sampler.psutil.__version__,
        "head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT).decode().strip(),
        "utc":datetime.now(timezone.utc).isoformat()})
    records, gates, detail = [], {}, {}
    for workload in ("null", "pulse", "spawn"):
        arms=[]
        for mode in ("off", "on", "placebo"):
            row=run_arm(out, f"control-{workload}-{mode}", workload, mode,
                        injection="job-memory" if mode == "placebo" else None)
            records.append(row); arms.append(row)
            gates[row["name"]+"-sampling"] = row["sampling_pass"]
            if workload == "pulse":
                checks=pulse_checks(row); detail[row["name"]]=checks
                gates[row["name"]+"-pulse"] = all(checks.get(k,False) for k in
                    ("intervals_observed","rise_pass","fall_pass","kernel_peak_pass"))
            if workload == "spawn":
                checks=spawn_checks(row); detail[row["name"]]=checks
                gates[row["name"]+"-spawn"] = all(checks[k] for k in ("observed","job_count_pass","allocation_pass"))
        gates[workload+"-identical"] = len({r["output"]["sha256"] for r in arms}) == 1
    for phase in sampler.PHASES:
        row=run_arm(out, "stall-"+phase, "null", "on", injection=phase)
        records.append(row)
        checks=stall_checks(row,phase); detail[row["name"]]=checks
        gates[row["name"]]=all(checks[k] for k in
            ("localized","injection_measured","interval_red","criterion_red","incident_retained"))
        # A phase-specific label-only placebo cannot depend on another phase's success.
        placebo=run_arm(out, "placebo-"+phase, "null", "placebo", injection=phase)
        records.append(placebo)
        gates[placebo["name"]]=placebo["sampling_pass"] and placebo["trace"]["injected"]
        gates[row["name"]+"-identity"] = row["output"] == placebo["output"]
    timing=[]
    for workload in ("null","fixed"):
        for sweep in range(4):
            order=MODES if sweep%2==0 else tuple(reversed(MODES))
            for mode in order:
                row=run_arm(out, f"overhead-{workload}-s{sweep}-{mode}",workload,mode,
                    injection="job-memory" if mode=="placebo" else None)
                row["sweep"]=sweep
                records.append(row); timing.append(row)
    minima={}
    paired_deltas={}
    for workload in ("null","fixed"):
        selected=[r for r in timing if r["workload"]==workload]
        gates["overhead-"+workload+"-identity"] = len({r["output"]["sha256"] for r in selected})==1
        minima[workload]={mode:{field:min(r[field] for r in selected if r["mode"]==mode)
            for field in ("wall_seconds","observer_cpu_seconds","product_cpu_seconds","host_busy_cpu_seconds")}
            for mode in MODES}
        paired_deltas[workload]=[{"sweep":s, **{mode:
            next(r["wall_seconds"] for r in selected if r["sweep"]==s and r["mode"]==mode)-
            next(r["wall_seconds"] for r in selected if r["sweep"]==s and r["mode"]=="original")
            for mode in ("off","on","placebo")}} for s in range(4)]
    slow=run_arm(out,"slow-control","fixed-slow","on"); records.append(slow)
    ordinary=[r for r in timing if r["workload"]=="fixed" and r["mode"]=="on"]
    gates["slow-control"] = slow["child_wall_seconds"]-min(r["child_wall_seconds"] for r in ordinary) > .15
    gates["slow-output-identity"] = slow["output"]==ordinary[0]["output"]
    payload=(out/"slow-control/output.bin").read_bytes()
    corrupt=bytes([payload[0]^1])+payload[1:]
    gates["one-byte-output-mutation"] = hashlib.sha256(payload).hexdigest()!=hashlib.sha256(corrupt).hexdigest()
    gates["all-exit-zero"] = all(r["returncode"]==0 for r in records)
    gates["trace-complete"] = all(not any(r["trace"]["dropped"].values()) for r in records if "trace" in r)
    gates["inputs-preserved"] = frozen==inventory()
    gates["sources-preserved"] = sources=={p.name:sha(p) for p in (HERE/"preregistration.md", HERE/"sampler.py", CHILD, Path(__file__))}
    result={"schema":"m192c-sampler-v1", "status":"COMMISSIONED" if all(gates.values()) else "COMMISSIONING_FAILED",
        "gates":gates,"checks":detail,"arm_count":len(records),"records":[r["name"] for r in records],
        "overhead_minima":minima,"paired_wall_deltas_seconds":paired_deltas,
        "slow_added_child_wall_seconds":slow["child_wall_seconds"]-min(r["child_wall_seconds"] for r in ordinary),
        "preserved_inputs_after":inventory(),"source_freeze":sha(out/"source-freeze.json")}
    write(out/"summary.json",result)
    print("RESULT",result["status"],"failed:",[k for k,v in gates.items() if not v],flush=True)
    print("OUTPUT",out,flush=True)
    return 0 if all(gates.values()) else 1


if __name__=="__main__":
    raise SystemExit(main())
