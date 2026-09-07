"""Independent choice tests, including unlabeled and CPU-active sampler stalls."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time
from uuid import uuid4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "experiments/m192c-sampler/sampler.py"
spec = importlib.util.spec_from_file_location("independent_m192c", SOURCE)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    original = ROOT / "experiments/M192-m12-certify/recovery-20260906-163253/results"
    before = {str(p): digest(p) for p in original.rglob("*") if p.is_file()}
    sources = {str(p.relative_to(ROOT)): digest(p) for p in
               (SOURCE, HERE / "child.py", Path(__file__), s.INHERITED)}
    out = HERE / ("out-" + uuid4().hex)
    out.mkdir()
    results = []
    # Reverse the author's mode order, then re-run on for allocation evidence.
    for mode in ("placebo", "on", "off", "on"):
        folder = out / (str(len(results)) + "-" + mode)
        row = s.monitor(argv=[sys.executable, "-B", str(HERE / "child.py"), str(folder)],
                        env=os.environ.copy(), folder=folder, mode=mode,
                        injection="process-table" if mode == "placebo" else None)
        assert row["returncode"] == 0 and row["sampling_pass"], row["max_interval_ms_including_final"]
        assert row["job_accounting"]["total_processes"] == 2
        events = {e["name"]: e for e in json.loads((folder / "events.json").read_text())}
        pid = events["start"]["pid"]
        assert any(p["pid"] == pid and p["created"] > 0 for p in row["processes"])
        levels = {}
        for label, lo, hi in (("before", "start", "allocated"), ("plateau", "allocated", "release"), ("after", "released", "end")):
            values = [p["private"] for observation in row["trace"]["observations"]
                      if events[lo]["time_ns"] <= observation["observed_ns"] <= events[hi]["time_ns"]
                      for p in observation["processes"] if p["pid"] == pid]
            assert values, (mode, label)
            levels[label] = statistics.median(values)
        assert levels["plateau"] - max(levels["before"], levels["after"]) >= 32 * 2**20, levels
        row["independent_levels"] = levels
        row["output_sha256"] = digest(folder / "output.bin")
        (folder / "record.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
        results.append({"mode": mode, "max_gap_ms": row["max_interval_ms_including_final"],
                        "levels": levels, "sha256": row["output_sha256"]})
    assert len({r["sha256"] for r in results}) == 1
    mutated = bytearray((out / "0-placebo/output.bin").read_bytes())
    mutated[2309] ^= 0x80
    assert hashlib.sha256(mutated).hexdigest() != results[0]["sha256"]

    stalls = []
    for target, active in (("process_table", False), ("process_table", True), ("job_memory", False)):
        old = getattr(s.h, target)
        fired = False
        empty_memory_calls = 0
        def delayed(*args, **kwargs):
            nonlocal fired, empty_memory_calls
            # Final Job memory has no live processes; table stall occurs at
            # first PID discovery. No Trace injection metadata is used.
            if target == "job_memory" and s.h.job_accounting(args[0])["active_processes"] == 0:
                empty_memory_calls += 1
            # Two empty polling observations precede final memory accounting.
            eligible = target != "job_memory" or empty_memory_calls == 3
            if eligible and not fired:
                fired = True
                until = time.perf_counter() + .125
                if active:
                    while time.perf_counter() < until:
                        pass
                else:
                    time.sleep(.125)
            return old(*args, **kwargs)
        setattr(s.h, target, delayed)
        folder = out / ("stall-" + str(len(stalls)))
        try:
            row = s.monitor(argv=[sys.executable, "-B", str(HERE / "child.py"), str(folder)],
                            env=os.environ.copy(), folder=folder)
        finally:
            setattr(s.h, target, old)
        assert fired and not row["trace"]["injected"] and not row["sampling_pass"]
        phase = "process-table" if target == "process_table" else "final-memory"
        events = [e for e in row["trace"]["events"] if e["phase"] == phase and e["wall_ms"] >= 120]
        assert events and any(i["trigger"].get("phase") == phase for i in row["trace"]["incidents"])
        event = max(events, key=lambda e:e["wall_ms"])
        fraction = event["observer_thread_cpu_ms"] / event["wall_ms"]
        assert fraction >= .5 if active else fraction < .2, fraction
        assert digest(folder / "output.bin") == results[0]["sha256"]
        (folder / "record.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
        stalls.append({"phase": phase, "active_cpu": active, "cpu_fraction": fraction,
                       "max_gap_ms": row["max_interval_ms_including_final"], "unlabeled_stall_caught": True})

    trace = s.Trace(True)
    for index in range(5000):
        trace.event({"phase": "overflow", "start_ns": index, "end_ns": index+1, "wall_ms": 51 if index % 100 == 0 else 1})
        trace.observe({"index": index})
    bounded = trace.result()
    assert len(bounded["events"]) == 4096 and len(bounded["observations"]) == 1000 and len(bounded["incidents"]) == 32
    assert bounded["dropped"] == {"events":904,"observations":4000,"incidents":18,"telemetry":0}
    assert all(len(i["context"]) <= 16 and len(i["following"]) <= 16 for i in bounded["incidents"])
    assert before == {str(p):digest(p) for p in original.rglob("*") if p.is_file()}
    assert sources == {name:digest(ROOT/name) for name in sources}
    summary = {"status":"VERIFIED", "sources":sources, "output_directory":str(out.relative_to(ROOT)),
               "controls":results,"unlabeled_stalls":stalls,"bounded_overflow":bounded["dropped"],
               "output_mutation_rejected":True,"original_files_unchanged":len(before)}
    (HERE / "verification.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__ == "__main__":
    main()
