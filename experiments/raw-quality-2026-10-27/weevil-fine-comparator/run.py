"""Root-only fixed Helicon B4/S4 full299 replay; no RAW or development path."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import time

import numpy as np
import psutil
import tifffile
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / "outputs/raw-quality-2026-10-26"
EXPORT = OLD / "weevil-107-tiff-export"
PRIOR = OLD / "weevil-107-comparator"
EXE = Path("C:/dev/blog/death-of-software/projects/strehl/experiments/helicon-current/program/HeliconFocus.exe")
APP_LOG = Path("C:/Users/chris/AppData/Local/HeliconFocus/HeliconFocus.log")
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
HARNESS = ROOT / "experiments/m12-scorecard/m12-harness.py"
DEFAULT_OUT = ROOT / "outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-1"
ICC_SHA = "238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b"
PINS = {
    EXE: "29ca62df122163c1295e1e2a416a42acfdf52f20c83d0beed99c4af154d42089",
    EXPORT / "receipt.json": "461ecb3a8e44a82005ed6883718aa85276a74a2ebfca31fb0628809c4ba315a0",
    PRIOR / "b/invocation.json": "1503d1054b1b126bc76aca84d1bb576d220e2cedecb8dda9583fcf741eea6eff",
    PRIOR / "b/inputs-before.json": "ee7a3ad62c89380c207bf2b18f86fc0d155c5588e14d7ba9fd282972ca0bd7af",
    PRIOR / "b/completion.json": "c21f3af01d81ac24cb64c8ffec6b1eb93ab20053c712f4a98755a1bcf31ae510",
    PRIOR / "c/completion.json": "26d9b1125d8604fd2ec4afe16255ba3605257bd5b85fd267562a108662a933d7",
    HELPER: "47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b",
    HARNESS: "6cfb408992f37b225f102da4d62ba836f9c5b67c92bdd418ff460987866a1bb9",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def ref(path):
    path = Path(path).resolve()
    initial = path.stat()
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 << 20):
            h.update(block)
    final = path.stat()
    assert (initial.st_size, initial.st_mtime_ns) == (final.st_size, final.st_mtime_ns), "input changed during hashing"
    return dict(path=str(path), bytes=final.st_size, mtime_ns=final.st_mtime_ns, sha256=h.hexdigest())


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def no_existing_helicon():
    found = []
    for process in psutil.process_iter(["pid", "name"]):
        if (process.info["name"] or "").lower() == "heliconfocus.exe":
            found.append(process.info["pid"])
    assert not found, f"Existing Helicon processes require root scheduling; nothing terminated: {found}"


def command_settings(command):
    assert len(command) == 13 and command[3] == "-i" and command[11] == "-o"
    normalized = command.copy()
    normalized[4] = "<input-manifest>"
    normalized[10] = "-save:<output-master>"
    normalized[12] = "<saved-output-list>"
    return normalized


def audit_application_log(path, command, inputs, launched_ns, stopped_ns):
    log = path.read_text(encoding="utf-8-sig", errors="strict")
    commands = re.findall(r"^\s*QList\((.*)\)\s*$", log, flags=re.MULTILINE)
    assert len(commands) == 1, "need one current command, not an accumulated/stale log"
    actual = json.loads("[" + commands[0] + "]")
    assert actual == command, "application command does not name this fresh output and fixed settings"
    stamp = re.search(r'^0:\s*"(\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC"', log)
    assert stamp, "current application start timestamp absent"
    app_ns = int(datetime.strptime(stamp[1], "%d-%m-%y %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1e9)
    assert launched_ns - 2_000_000_000 <= app_ns <= stopped_ns + 2_000_000_000, "application log timestamp outside this run"
    rows = []
    for ordinal, count, quoted_path in re.findall(r'Processing source (\d+) out of (\d+) ("[^"\r\n]*")', log):
        rows.append((int(ordinal), int(count), json.loads(quoted_path)))
    expected = [(i, 299, str(p)) for i, p in enumerate(inputs)]
    expected += [(i, 299, str(p)) for i, p in enumerate(reversed(inputs))]
    assert rows == expected, "B must account for both complete ordered299 passes"
    assert '"Helicon Focus 8.3.11 x64"' in log
    assert "FocusTask::compile Rendering finished." in log and "Exiting gracefully." in log
    return dict(exact_command=True, method="B", radius=4, smoothing=4, source_count=299,
                processing_rows=len(rows), passes=["ascending0..298", "descending298..0"],
                application_start_utc=stamp[1]+" UTC", complete_ordered_sources=True,
                license_observations=[line for line in log.splitlines() if "license" in line.lower()],
                gpu_observations=[line for line in log.splitlines() if "OpenCL device not selected" in line],
                scope="Command and complete processing-row verification; not proof of visual quality or GPU use.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="Fresh workspace output only; all processing settings and inputs remain fixed")
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to((ROOT / "outputs/raw-quality-2026-10-27").resolve()) and not out.exists()
    out.mkdir(parents=True)
    started = time.monotonic()
    pinned = [ref(path) for path in PINS]
    assert all(row["sha256"] == PINS[Path(row["path"])] for row in pinned), "held executable/development/provenance/helper changed"
    source = read(EXPORT / "receipt.json")
    assert source["status"] == "299_UNALIGNED_NATIVE_RGB16_DEVELOPED" and len(source["frames"]) == 299
    assert source["worker_count"] == 4 and source["golden"]["status"] == "EXACT" and source["input_content_and_metadata_unchanged"]
    assert source["active_wh"] == [7032, 4688]
    prior_inputs = read(PRIOR / "b/inputs-before.json")
    assert len(prior_inputs) == 299
    inputs = [Path(row["output"]).resolve() for row in source["frames"]]
    assert len(set(inputs)) == 299
    before = []
    for i, (path, row, old) in enumerate(zip(inputs, source["frames"], prior_inputs)):
        assert row["ordinal"] == i and path.parent == (EXPORT / "frames").resolve()
        assert path.name == f"DSC{i+1:05d}.tiff" and row["output_wh"] == [7032, 4688]
        bound = ref(path)
        assert bound["sha256"] == row["output_sha256"] == old["sha256"]
        assert bound["bytes"] == row["output_bytes"] == old["bytes"] and Path(old["path"]).samefile(path)
        before.append(bound)
    save(out / "inputs-before.json", before)
    manifest = out / "inputs.txt"
    with manifest.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(str(path) for path in inputs) + "\n")
    output = out / "stack-master.tiff"
    command = [str(EXE), "-silent", "-noprogress", "-i", str(manifest), "-mp:1", "-rp:4", "-sp:4",
               "-sort:asc", "-tif:u", "-save:"+str(output), "-o", str(out / "saved-outputs.txt")]
    prior_command = read(PRIOR / "b/invocation.json")["command"]
    expected_prior = command.copy()
    expected_prior[6] = "-rp:8"
    assert command_settings(prior_command) == command_settings(expected_prior), "more than radius changed from prior B command"
    spec = importlib.util.spec_from_file_location("weevil_fine_bounded", HELPER)
    b = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = b
    spec.loader.exec_module(b)
    env, removed = b.clean_environment()
    resources = dict(free_disk_bytes=shutil.disk_usage(out).free, available_physical_bytes=psutil.virtual_memory().available,
                     host_cpu_percent=psutil.cpu_percent(interval=1), physical_cores=psutil.cpu_count(logical=False),
                     logical_cores=psutil.cpu_count(), scope="Operational host preflight, not an isolated speed measurement")
    save(out / "resources.json", resources)
    assert resources["available_physical_bytes"] > (49 << 30), "Need45GiB job plus4GiB host reserve; root must finish heavy native work first"
    assert resources["free_disk_bytes"] > (4 << 30), "Need room for full TIFF/JPEG and bounded logs"
    no_existing_helicon()
    log_before = ref(APP_LOG) if APP_LOG.exists() else None
    limits = dict(wall_seconds=180, cpu_seconds=5760, committed_bytes=45 << 30, log_bytes=32 << 20)
    invocation = dict(command=command, executable=ref(EXE), pinned=pinned, runner=ref(Path(__file__)),
                      input_manifest=ref(manifest), development_receipt=ref(EXPORT / "receipt.json"),
                      inputs_before=ref(out / "inputs-before.json"), removed_environment=removed, limits=limits,
                      application_log_before=log_before, method="B", radius=4, smoothing=4,
                      semantic_change_from_prior_B="radius8 to4 only; new manifest/output paths",
                      desktop_context="Root must launch with the same authorized OS desktop access as successful flat desktop runs",
                      scope="Whole existing TIFF stack, vendor alignment and merge; no new RAW decode/development, no native default change",
                      original_export_timing_receipt=str(PRIOR / "develop/completion.json"))
    save(out / "invocation.json", invocation)
    launched_ns = time.time_ns()
    result = b.run(command, env, ROOT, out / "process.log", api=b.load_job_api(b.binding(HARNESS)), **limits)
    stopped_ns = time.time_ns()
    save(out / "process.json", result)
    log_after = ref(APP_LOG) if APP_LOG.exists() else None
    if log_after:
        shutil.copyfile(APP_LOG, out / "application.log")
        assert ref(out / "application.log")["sha256"] == log_after["sha256"]
        assert ref(APP_LOG) == log_after, "application log changed during capture"
    save(out / "application-log-binding.json", dict(before=log_before, after=log_after,
         launch_unix_ns=launched_ns, stopped_unix_ns=stopped_ns))
    # Record preservation even when the owned vendor process failed or timed out.
    after = [ref(path) for path in inputs]
    save(out / "inputs-after.json", after)
    pins_after = [ref(path) for path in PINS]
    preservation = dict(inputs_unchanged=before == after, pins_unchanged=pinned == pins_after,
                        inputs_after=ref(out / "inputs-after.json"), pinned_after=pins_after)
    save(out / "preservation.json", preservation)
    assert preservation["inputs_unchanged"] and preservation["pins_unchanged"]
    assert result["exit_code"] == 0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"], result
    assert log_after and (not log_before or log_after["sha256"] != log_before["sha256"]), "fresh application log required"
    log_audit = audit_application_log(out / "application.log", command, inputs, launched_ns, stopped_ns)
    save(out / "application-audit.json", log_audit)
    assert output.is_file()
    with tifffile.TiffFile(output) as tf:
        assert len(tf.pages) == 1
        page = tf.pages[0]
        assert page.dtype == np.uint16 and len(page.shape) == 3 and page.shape[2] == 3
        assert 0.9*7032 <= page.shape[1] <= 1.1*7032 and 0.9*4688 <= page.shape[0] <= 1.1*4688
        icc = bytes(page.tags[34675].value)
        assert hashlib.sha256(icc).hexdigest() == ICC_SHA, "original common ICC required"
        rgb = page.asarray()
    image = Image.fromarray(((rgb.astype(np.uint32)+128)//257).astype(np.uint8))
    image.save(out / "stack-full.jpg", quality=98, subsampling=0, icc_profile=icc)
    with Image.open(out / "stack-full.jpg") as check:
        assert check.size == (rgb.shape[1], rgb.shape[0]) and check.info["icc_profile"] == icc
    image.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
    image.save(out / "overview.jpg", quality=98, icc_profile=icc)
    saved_list = out / "saved-outputs.txt"
    summary = dict(status="COMPLETE299_B4_READY_FOR_INDEPENDENT_REVIEW", source_count=299, method="B", radius=4, smoothing=4,
                   master=ref(output), full_jpeg=ref(out / "stack-full.jpg"), overview=ref(out / "overview.jpg"),
                   shape=list(rgb.shape), dtype="uint16", icc_sha256=ICC_SHA,
                   application_log=ref(out / "application.log"), application_audit=ref(out / "application-audit.json"),
                   inputs_unchanged=True, pinned_executable_and_receipts_unchanged=True,
                   saved_outputs_list=ref(saved_list) if saved_list.exists() else None,
                   saved_outputs_note="Absence is disclosed, as in prior B/C; exact fresh command/log and complete master are checked independently.",
                   vendor_child_seconds=result["wall_seconds"], whole_wrapper_seconds=time.monotonic()-started,
                   original_export_timing_receipt=str(PRIOR / "develop/completion.json"),
                   timing_scope="Child180s/45GiB limits exclude serial hashing and image export; no clean competitive speed claim.",
                   visual_review="Pending complete photograph then same ten mapped native witnesses; no quality claim")
    save(out / "completion.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
