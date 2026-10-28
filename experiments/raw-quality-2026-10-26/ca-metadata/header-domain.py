"""Current header-only replay of BUILD-CHROMA's 24-frame selection, not its fit.

Root runs this file. Standard library only; no image decoder or pixel arithmetic.
Full source bytes are streamed for SHA256 before/after metadata inspection.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


EXPECTED = {
    "tweezers-cpl": 100,
    "bee-3-cpl": 299,
    "coffee-bean": 105,
    "lavendar-cpl": 299,
    "couch-fibers-cpl": 299,
    "bee-2-cpl": 299,
}
EXE_SHA = "89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388"
REFERENCE_SHA = "d9fb0f7a3f08620786c26577b50f08d881063b7353891857a958f3ec75327006"
RETAINED_SHA = "9a56c71a36527016328189e964614b21c541e5a5f57032898d6708b09033af38"
RETAINED = Path("C:/Users/chris/AppData/Local/Temp/strehl-core-main-0d466788/") / (
    "experiments/rea-a7c2-2026-10-24/metadata-results.json"
)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def stat(path):
    value = path.stat()
    return {"bytes": value.st_size, "mtime_ns": value.st_mtime_ns}


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def selected_indices(count):
    # Nearest integer to k*(count-1)/23. Denominator 23 is odd, so no ties.
    # Equivalent to np.unique(np.linspace(0,count-1,24).round().astype(int))
    # for the three fixed counts, without importing numerical packages.
    return sorted({(2 * k * (count - 1) + 23) // 46 for k in range(24)})


def inventory(directory):
    files = sorted(directory.glob("*.ARW"), key=lambda p: str(p))
    return [{"name": p.name, **stat(p)} for p in files if p.is_file()]


def checked_facts(code, samples, setting, identity):
    if not isinstance(code, int) or isinstance(code, bool) or not 0 <= code <= 255:
        raise ValueError("missing or invalid coarse focus code")
    if not isinstance(samples, list) or len(samples) != 32:
        raise ValueError("missing or non-32-element CA table")
    if any(not isinstance(x, int) or isinstance(x, bool) or not -32768 <= x <= 32767 for x in samples):
        raise ValueError("invalid signed CA table element")
    return {"coarse_focus_code": code, "ca_table_raw": samples,
            "ca_setting_raw": setting, "identity": identity}


def retained_facts(row):
    raw = row["raw"]
    table = raw["ca_params"]
    if len(table) != 33 or table[0] != 32:
        raise ValueError("retained CA prefix/count mismatch")
    return checked_facts(row["focus"]["focus_position_2"], table[1:],
                         raw.get("ca_opcode"), row["identity"])


def native_facts(report, source):
    if report.get("schema") != "strehl-sony-focus-audit-v1" or report.get("file_count") != 1:
        raise ValueError("unexpected native inspect schema/count")
    frames = report["frames"]
    if len(frames) != 1 or Path(frames[0]["path"]).resolve() != source.resolve():
        raise ValueError("native inspect returned a different source")
    frame = frames[0]
    if frame["status"] != "present" or frame["optical"]["status"] != "present":
        raise ValueError("native focus/optical header is not present")
    ca = frame["optical"]["facts"]["chromatic_aberration"]
    iso = frame["optical"]["facts"]["iso"]
    if ca["table"]["prefix"] != 32:
        raise ValueError("native CA prefix mismatch")
    return checked_facts(frame["metadata"]["coarse_focus_position"],
                         ca["table"]["samples"],
                         None if ca["setting"] is None else ca["setting"]["value"],
                         {"model": frame["metadata"]["model"],
                          "software": frame["metadata"]["software"],
                          "iso": None if iso is None else iso["value"],
                          "optical_identity": frame["metadata"]["optical_identity"]})


def summarize(rows, references):
    result = {}
    for stack in EXPECTED:
        items = [r for r in rows if r["stack"] == stack]
        codes = sorted({r["facts"]["coarse_focus_code"] for r in items})
        tuples = sorted({tuple(r["facts"]["ca_table_raw"]) for r in items})
        comparisons = {}
        for reference in references:
            code, table = reference["coarse_focus_code"], reference["ca_table_raw"]
            matched = [r for r in items
                       if r["facts"]["identity"]["model"] == reference["camera"]
                       and r["facts"]["identity"]["software"] == reference["firmware"]
                       and r["facts"]["identity"]["iso"] == reference["iso"]
                       and r["facts"]["identity"]["optical_identity"] == reference["optical_identity"]
                       and r["facts"]["ca_setting_raw"] == reference["ca_setting_raw"]]
            comparisons[reference["stack"]] = {
                "exact_focus_code_seen": code in codes,
                "focus_code_within_sampled_numeric_range": min(codes) <= code <= max(codes),
                "exact_32_table_seen": tuple(table) in tuples,
                "exact_joint_code_table_seen": any(r["facts"]["coarse_focus_code"] == code
                    and r["facts"]["ca_table_raw"] == table for r in items),
                "same_camera_firmware_lens_focal_aperture_iso_setting_count": len(matched),
                "same_identity_focus_codes": sorted({r["facts"]["coarse_focus_code"] for r in matched}),
                "same_identity_exact_table_seen": any(r["facts"]["ca_table_raw"] == table for r in matched),
                "same_identity_exact_joint_code_table_seen": any(r["facts"]["coarse_focus_code"] == code
                    and r["facts"]["ca_table_raw"] == table for r in matched),
            }
        result[stack] = {"selected_count": len(items), "coarse_focus_codes": codes,
                         "distinct_ca_tables": [list(t) for t in tuples],
                         "reference_comparisons": comparisons}
    return result


def run(args, receipt):
    out = args.out.resolve()
    macro = args.macro_root.resolve()
    if out == macro or macro in out.parents:
        raise ValueError("output must be outside the capture corpus")
    out.mkdir(parents=True, exist_ok=False)
    receipt["output"] = str(out)
    exe = args.exe.resolve()
    if digest(exe) != EXE_SHA:
        raise ValueError("frozen executable hash mismatch")
    reference_path = Path(__file__).with_name("header-observation.json")
    reference_bytes = reference_path.read_bytes()
    if hashlib.sha256(reference_bytes).hexdigest() != REFERENCE_SHA:
        raise ValueError("reference header observations hash mismatch")
    references = json.loads(reference_bytes)["records"]
    if [r["stack"] for r in references] != ["weevil", "bug2"]:
        raise ValueError("unexpected reference records")
    for r in references:
        checked_facts(r["coarse_focus_code"], r["ca_table_raw"], r["ca_setting_raw"], r["optical_identity"])
    write_json(out / "references.json", json.loads(reference_bytes))
    receipt.update(executable=str(exe), executable_sha256=EXE_SHA,
                   reference_path=str(reference_path),
                   reference_sha256=hashlib.sha256(reference_bytes).hexdigest(),
                   inventories={}, selected_sources=[], retained_equalities=0,
                   native_inspections=0, planned_selected_denominator=144)
    # Snapshot every complete filename list and count before opening any source.
    for stack, count in EXPECTED.items():
        rows = inventory(macro / stack)
        receipt["inventories"][stack] = {"expected_count": count, "observed_count": len(rows),
                                         "files": rows, "selected_indices": selected_indices(count)}
    write_json(out / "input-inventory.json", receipt["inventories"])
    for stack, inv in receipt["inventories"].items():
        names = [r["name"].casefold() for r in inv["files"]]
        if inv["observed_count"] != inv["expected_count"] or len(names) != len(set(names)):
            raise ValueError(f"source count or duplicate filename mismatch: {stack}")
        if any(r["bytes"] <= 0 for r in inv["files"]):
            raise ValueError(f"empty source: {stack}")
        if len(inv["selected_indices"]) != 24:
            raise ValueError("selection does not have exactly 24 sources")
    retained = {}
    if args.retained.is_file():
        if digest(args.retained) != RETAINED_SHA:
            raise ValueError("retained header manifest hash mismatch")
        saved = json.loads(args.retained.read_text(encoding="utf-8"))
        retained = {r["relative_path"]: r for r in saved["files"]}
        if len(retained) != len(saved["files"]):
            raise ValueError("duplicate retained source paths")
        receipt["retained"] = {"path": str(args.retained), "sha256": RETAINED_SHA}
    else:
        receipt["retained"] = {"path": str(args.retained), "status": "absent"}
    env = dict(os.environ, RAYON_NUM_THREADS="1")
    headers = out / "headers"
    headers.mkdir()
    for stack, inv in receipt["inventories"].items():
        for index in inv["selected_indices"]:
            source = macro / stack / inv["files"][index]["name"]
            before_stat, before_sha = stat(source), digest(source)
            if before_stat != {k: inv["files"][index][k] for k in ("bytes", "mtime_ns")}:
                raise ValueError("source stat changed after inventory")
            row = {"stack": stack, "original_index": index, "source": str(source),
                   "before_stat": before_stat, "before_sha256": before_sha}
            receipt["selected_sources"].append(row)
            target = headers / f"{stack}-{index:03d}.json"
            cached = retained.get(f"{stack}/{source.name}")
            command = [str(exe), "focus", "inspect", str(source), "--optical", "--out", str(target)]
            row["command"] = command
            row["retained_match"] = "absent" if cached is None else "source_hash_differs"
            started = time.monotonic()
            process = subprocess.run(command, capture_output=True, env=env, timeout=20, check=False)
            row.update(exit_code=process.returncode, seconds=time.monotonic() - started)
            (headers / f"{stack}-{index:03d}.stdout.txt").write_bytes(process.stdout)
            (headers / f"{stack}-{index:03d}.stderr.txt").write_bytes(process.stderr)
            row.update(after_sha256=digest(source), after_stat=stat(source))
            if row["after_sha256"] != before_sha or row["after_stat"] != before_stat:
                raise ValueError(f"source changed: {source}")
            if process.returncode != 0:
                raise ValueError(f"native inspect exit {process.returncode}: {source}")
            row.update(header=str(target), header_sha256=digest(target))
            report = json.loads(target.read_text(encoding="utf-8"))
            row.update(mode="frozen_native_header_inspect", facts=native_facts(report, source))
            receipt["native_inspections"] += 1
            if cached is not None and cached.get("sha256") == before_sha:
                retained_path = headers / f"{stack}-{index:03d}.retained.json"
                write_json(retained_path, cached)
                expected = retained_facts(cached)
                row.update(retained_match="exact_source_sha256", retained_header=str(retained_path),
                           retained_header_sha256=digest(retained_path),
                           retained_equal={key: row["facts"][key] == expected[key]
                                           for key in ("coarse_focus_code", "ca_table_raw", "ca_setting_raw")})
                if not all(row["retained_equal"].values()):
                    raise ValueError("independent retained header comparison failed")
                receipt["retained_equalities"] += 1
            print(f"{stack} index={index} {row['mode']} focus={row['facts']['coarse_focus_code']}", flush=True)
    for stack, inv in receipt["inventories"].items():
        if inventory(macro / stack) != inv["files"]:
            raise ValueError(f"directory inventory changed: {stack}")
    if digest(exe) != EXE_SHA or reference_path.read_bytes() != reference_bytes:
        raise ValueError("executable or reference facts changed during run")
    if len(receipt["selected_sources"]) != 144:
        raise ValueError("incomplete selected source set")
    receipt.update(status="COMPLETE_CURRENT_SELECTION_HEADER_REPLAY", summary=summarize(receipt["selected_sources"], references))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--exe", type=Path, default=Path("outputs/raw-quality-2026-10-26/baseline-strehl.exe"))
    parser.add_argument("--macro-root", type=Path, default=Path("D:/personal/macro"))
    parser.add_argument("--retained", type=Path, default=RETAINED)
    args = parser.parse_args()
    receipt = {"schema": 1, "status": "INCOMPLETE", "command": sys.argv,
               "script_sha256": digest(Path(__file__)), "python": sys.version,
               "platform": platform.platform(), "workers": 1, "child_threads": 1,
               "scope": "Current selection replay, NOT exact historical coefficient identity. No pixel decoding or fit. Full-file bytes read only for hashes.",
               "limits": ["Sampled metadata domain only; not all source headers in each stack.",
                          "Codes and tables have no inferred physical units, freshness, or optical calibration.",
                          "A metadata envelope does not establish profile applicability or photographic quality."]}
    started = time.monotonic()
    exit_code = 0
    try:
        run(args, receipt)
    except Exception as error:
        receipt.update(status="REFUSED_OR_INCOMPLETE", error=f"{type(error).__name__}: {error}")
        print(receipt["error"], file=sys.stderr, flush=True)
        exit_code = 2
    receipt["seconds"] = time.monotonic() - started
    if "output" in receipt:
        write_json(Path(receipt["output"]) / "receipt.json", receipt)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
