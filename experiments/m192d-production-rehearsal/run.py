"""Bounded native rehearsal; preserves every registered invocation and outcome."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import statistics
import sys
import time
import traceback
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("m192d_sampler", ROOT / "experiments/m192c-sampler/sampler.py")
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
PACKAGE = ROOT / "experiments/M192-m12-certify/recovery-20260906-163253/results"
BINARY = PACKAGE.parent / "work/builds/measured/bin/strehl.exe"
SENSOR = Path(r"D:\personal\macro\bee-1-cpl")
SHA = "89482ACD60C4E39A22F763B2E722754804430E955546EA96F7AE7CA4C7EA1032"
SIDE_SHA = "A4B99B954EF98C0065FC35A36203545AEEF9A50997BC6B53F68BF859D9CE79DF"
SUFFIX = ["--merge", "pyramid", "--pyramid-gate", "2.0", "--resampler", "catmull-rom", "--cover", "scale", "--linear-srgb", "--demosaic"]

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(2**20):
            h.update(block)
    return h.hexdigest().upper()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")

def manifest(paths):
    return [{"path":str(p),"bytes":p.stat().st_size,"mtime_ns":p.stat().st_mtime_ns,"sha256":digest(p)} for p in paths]

def main():
    out = HERE / ("out-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
    out.mkdir()
    work = HERE / "work" / out.name
    work.mkdir(parents=True)
    (work / "cache").mkdir()
    originals = sorted(p for p in PACKAGE.rglob("*") if p.is_file())
    sources = [HERE / "preregistration.md", Path(__file__), Path(s.__file__), s.INHERITED, BINARY]
    freeze = manifest(sources)
    assert digest(BINARY) == SHA
    sidecar = work / "n33.warpmap.txt"
    shutil.copyfile(PACKAGE / "sidecars/n33.warpmap.txt", sidecar)
    assert digest(sidecar) == SIDE_SHA
    paths = sorted(p for p in SENSOR.iterdir() if p.suffix.lower() == ".arw")[:33]
    assert len(paths) == 33
    prior = [json.loads(line) for line in (PACKAGE / "records.jsonl").read_bytes().splitlines()]
    reference = next(r for r in prior if r["phase"] == "native" and r["limit"] == 33 and r["workers"] == 8 and r["kind"] == "scored")
    inputs_before = manifest(paths)
    originals_before = manifest(originals)
    write(out / "source-freeze.json", {"sources":freeze,"originals":originals_before,"sidecar":manifest([sidecar])[0],
          "reference_run_id":reference["run_id"],"reference_output_sha256":reference["output_sha256"],"reference_pixel_sha256":reference["pixel_sha256"]})
    write(out / "inputs-before.json",inputs_before)
    rows = []
    schedule = [("warmup", "off"), ("forward", "off"), ("forward", "on"), ("forward", "placebo"),
                ("reverse", "placebo"), ("reverse", "on"), ("reverse", "off")]
    try:
        for index, (sweep,mode) in enumerate(schedule):
            folder = work / f"{index:02d}-{sweep}-{mode}"
            output = folder / "output.tiff"
            env = os.environ.copy()
            prefixes = ("STREHL_", "RAYON_", "OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_")
            cleared = sorted(k for k in env if k.startswith(prefixes))
            for key in cleared:
                del env[key]
            env.update(STREHL_PYRAMID_WORKERS="8",STREHL_WARPMAP=str(sidecar),STREHL_CACHE_DIR=str(work / "cache"),
                       TEMP=str(folder / "temp"),TMP=str(folder / "temp"))
            argv = [str(BINARY),"stack",str(SENSOR),"--limit","33","--out",str(output),*SUFFIX]
            write(out / "progress.json",{"active":index,"sweep":sweep,"mode":mode,"completed":len(rows),"argv":argv,
                                          "started_utc":datetime.now(timezone.utc).isoformat()})
            row = s.monitor(argv=argv,env=env,folder=folder,mode=mode,
                            injection="process-table" if mode == "placebo" else None)
            row.update(index=index,sweep=sweep,environment=s.h.relevant_environment(env),cleared_present_variables=cleared,
                       binary_sha256=SHA,sidecar_sha256=SIDE_SHA,output_path=str(output))
            for stream in ("stdout","stderr"):
                archived = out / f"{index:02d}-{stream}.log"
                shutil.copyfile(folder / (stream+".log"),archived)
                row[stream+"_artifact"] = {"path":archived.name,"bytes":archived.stat().st_size,"sha256":digest(archived)}
            if output.is_file():
                row["tiff"] = s.h.tiff_witness(output)
            text = (folder / "stderr.log").read_text(encoding="utf-8")
            row["terminal_matches"] = all(marker in text for marker in
                ("frames          : 33 from "+str(SENSOR),"alignment       : ON (sidecar-override)","33 placed / 0 refused",
                 "folded          : 33 / 33 frames","8 execution threads","4 canonical chunks",
                 "camera RGB -> LINEAR sRGB","Malvar-He-Cutler demosaic","wrote           : "+str(output),"total           :"))
            row["identity_matches"] = row.get("tiff",{}).get("output_sha256") == reference["output_sha256"] and row.get("tiff",{}).get("pixel_sha256") == reference["pixel_sha256"]
            row["cpu_raw_matches"] = row["host_busy_cpu_seconds"] == (row["host_end"]["busy_100ns"]-row["host_start"]["busy_100ns"])/1e7 and row["product_cpu_seconds"] == row["job_accounting"]["total_cpu_100ns"]/1e7
            write(out / f"{index:02d}-record.json",row)
            rows.append(row)
            print(f"{index} {sweep} {mode}: exit={row['returncode']} identity={row['identity_matches']} sampling={row['sampling_pass']} gap_ms={row['max_interval_ms_including_final']:.3f} wall_s={row['wall_seconds']:.3f}",flush=True)
        after = manifest(paths)
        write(out / "inputs-after.json",after)
        assert inputs_before == after
        assert originals_before == manifest(originals)
        assert freeze == manifest(sources)
        assert digest(sidecar) == SIDE_SHA
        # Mutate real output bytes/pixels in memory; original output untouched.
        output = Path(rows[-1]["output_path"])
        mutated = hashlib.sha256()
        with output.open("rb") as stream:
            first = bytearray(stream.read(2**20))
            first[65557] ^= 0x04
            mutated.update(first)
            while block := stream.read(2**20):
                mutated.update(block)
        file_mutation = mutated.hexdigest().upper() != rows[-1]["tiff"]["output_sha256"]
        import tifffile
        pixels = tifffile.memmap(output,mode="r")
        view = memoryview(pixels).cast("B")
        mutated = hashlib.sha256()
        first = bytearray(view[:2**20])
        first[23344] ^= 0x40
        mutated.update(first)
        mutated.update(view[2**20:])
        pixel_mutation = mutated.hexdigest().upper() != rows[-1]["tiff"]["pixel_sha256"]
        del view,pixels
        timings = {}
        for mode in ("off","on","placebo"):
            selected = [r for r in rows[1:] if r["mode"]==mode]
            deltas = [r["wall_seconds"]-next(b["wall_seconds"] for b in rows[1:] if b["sweep"]==r["sweep"] and b["mode"]=="off") for r in selected]
            timings[mode] = {"minimum_wall_seconds":min(r["wall_seconds"] for r in selected),"paired_delta_seconds":deltas,
                             "paired_mean_seconds":statistics.mean(deltas),"paired_sem_seconds":statistics.stdev(deltas)/2**.5}
        all_identity = all(r["returncode"]==0 and r["terminal_matches"] and r["identity_matches"] and r["cpu_raw_matches"] for r in rows)
        summary = {"schema":"m192d-rehearsal-v1","status":"NONPERTURBATION_VERIFIED" if all_identity and file_mutation and pixel_mutation else "REHEARSAL_FAILED",
                   "completed":len(rows),"identity_and_execution":all_identity,"sampling_passes":sum(r["sampling_pass"] for r in rows),
                   "max_interval_ms":max(r["max_interval_ms_including_final"] for r in rows),"file_mutation_rejected":file_mutation,"pixel_mutation_rejected":pixel_mutation,
                   "timing_descriptive_only":timings,"inputs_unchanged":len(paths),"original_artifacts_unchanged":len(originals),
                   "source_freeze_unchanged":True,"completed_utc":datetime.now(timezone.utc).isoformat()}
        write(out / "summary.json",summary)
        write(HERE / "latest.json",{"output_directory":str(out),"summary":summary})
        print(json.dumps(summary,indent=2),flush=True)
        return 0 if summary["status"]=="NONPERTURBATION_VERIFIED" else 1
    except BaseException as error:
        write(out / "aborted.json",{"type":type(error).__name__,"error":str(error),"traceback":traceback.format_exc(),"completed":len(rows)})
        raise

if __name__ == "__main__":
    raise SystemExit(main())
