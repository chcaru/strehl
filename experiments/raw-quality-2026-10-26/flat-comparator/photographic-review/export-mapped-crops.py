"""Small root-authorized cached-output crop export; no RAW access or image fit."""
from pathlib import Path
import hashlib
import json
import sys
import time

import numpy as np
from PIL import Image
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FROZEN = HERE / "mapped-witnesses.json"
BASE = ROOT / "outputs/raw-quality-2026-10-26"
NATIVE = ROOT / "experiments/raw-quality-2026-10-26/flat-baseline"
ICC_SHA = "238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b"


def ref(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(8 << 20):
            h.update(block)
    s = path.stat()
    return {"path": str(path), "sha256": h.hexdigest(), "bytes": s.st_size, "mtime_ns": s.st_mtime_ns}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    started = time.monotonic()
    frozen = json.loads(FROZEN.read_text())
    native_manifest = NATIVE / "frozen-witnesses.json"
    require(ref(native_manifest)["sha256"] == frozen["native_manifest_sha256"], "native nomination changed")
    native_rows = json.loads(native_manifest.read_text())["witnesses"]
    require([(r["name"], r["native_xywh"]) for r in native_rows]
            == [(r["name"], r["native_xywh"]) for r in frozen["witnesses"]], "original8 changed")
    require(frozen["all_three_complete_outputs_viewed"] is True, "whole views required")
    sources = {arm: BASE / "flat-1s-comparator" / f"{arm}-desktop" for arm in ("b", "c")}
    inputs = [FROZEN, native_manifest, Path(__file__).resolve(), BASE / "flat-1s-baseline/stack-master.tiff"]
    for source in sources.values():
        inputs.extend([source / "completion.json", source / "stack-master.tiff"])
    before = [ref(p) for p in inputs]
    require(before[3]["sha256"] == frozen["master_sha256"]["native"], "native master changed")
    records = {}
    for arm, source in sources.items():
        out = HERE / arm
        require(not out.exists(), "fresh vendor crop directory required")
        receipt = json.loads((source / "completion.json").read_text())
        path = source / "stack-master.tiff"
        require(ref(path)["sha256"] == receipt["master"]["sha256"] == frozen["master_sha256"][arm], "vendor master changed")
        require(receipt["inputs_unchanged"] is True and receipt["shape"] == [4688,7032,3]
                and receipt["dtype"] == "uint16", "complete vendor receipt differs")
        with tifffile.TiffFile(path) as f:
            require(len(f.pages) == 1 and f.pages[0].shape == (4688,7032,3)
                    and f.pages[0].dtype == np.uint16, "RGB16 dimensions/type differ")
            icc = bytes(f.pages[0].tags[34675].value)
        require(hashlib.sha256(icc).hexdigest() == ICC_SHA, "ICC differs")
        rgb = tifffile.memmap(path, mode="r")
        out.mkdir()
        rows = []
        for row in frozen["witnesses"]:
            name = row["name"]
            x,y,w,h = row[f"{arm}_xywh"]
            require(w == h == 384 and 0 <= x <= 7032-w and 0 <= y <= 4688-h, "invalid native rectangle")
            crop = rgb[y:y+h, x:x+w].copy()
            small = ((crop.astype(np.uint32)+128)//257).astype(np.uint8)
            png, tiff = out / f"{name}.png", out / f"{name}.tiff"
            Image.fromarray(small).save(png, icc_profile=icc)
            tifffile.imwrite(tiff, crop, photometric="rgb", metadata=None,
                             extratags=[(34675,"B",len(icc),icc,False)])
            with Image.open(png) as check:
                require(check.size == (384,384) and check.info.get("icc_profile") == icc
                        and np.array_equal(np.asarray(check), small), "PNG changed")
            with tifffile.TiffFile(tiff) as check:
                require(bytes(check.pages[0].tags[34675].value) == icc
                        and np.array_equal(check.asarray(), rgb[y:y+h,x:x+w]), "RGB16 crop changed")
            rows.append({"name":name,"native_xywh":[x,y,w,h],"resized":False,
                         "rgb16":ref(tiff),"png":ref(png),
                         "native_baseline_png":ref(NATIVE / "baseline-native" / f"{name}.png")})
        del rgb
        records[arm] = {"master":ref(path),"witnesses":rows}
    require([ref(p) for p in inputs] == before, "bound input changed during export")
    result = {"status":"ALL16_VENDOR_NATIVE_CROPS_READY_NO_VERDICT","quality_claim":False,
              "command":[sys.executable,*sys.orig_argv[1:]],"inputs":before,"input_files_unchanged":True,
              "original_raw_reads":0,"display":frozen["display"],"mapping":ref(FROZEN),
              "icc_sha256":ICC_SHA,"arms":records,"operational_seconds":time.monotonic()-started}
    with (HERE / "crop-export-receipt.json").open("x",encoding="utf-8",newline="\n") as f:
        f.write(json.dumps(result,indent=2)+"\n")
    print(f"All16 fixed vendor crops exact and ICC-preserved; {result['operational_seconds']:.3f}s.")


if __name__ == "__main__":
    main()
