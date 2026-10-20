"""Two frozen full-stack comparisons. Source RAW files are only read.

Run from repository root after compiling the current CLI:
  python experiments/quality-october20/run-slide-pair.py <slide-bracket>

No settings sweep, no alignment re-fit, no promotion of an automatic correction.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OLD_MAP = ROOT.parent / "strehl-1792309957142-43564-3/cache/very-tilted-all-axis-sw10-cpl-d27e0aab43ba1ae7.warpmap.txt"
OUT = ROOT / "outputs/quality-october20-slide"
EXE = ROOT / "outputs/quality-october20-target/release/strehl.exe"

def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def inventory(source):
    return [{"name": p.name, "bytes": p.stat().st_size, "mtime_ns": p.stat().st_mtime_ns}
            for p in sorted(source.iterdir()) if p.is_file()]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Read-only 197-frame calibration-slide bracket")
    source = parser.parse_args().source.resolve(strict=True)
    OUT.mkdir(parents=True, exist_ok=False)
    files = sorted(source.glob("*.ARW"))
    assert len(files) == 197, len(files)
    before = inventory(source)
    recipe = {"version": 1, "regions": [{
        "id": "qr-edge-source-49", "name": "QR edge: source 50",
        "note": "Frozen manual repair control, chosen from original whole photograph and source index49; not automatic artifact detection.",
        "shape": {"kind": "rectangle", "min": [4650/7032, 400/4688], "max": [5290/7032, 1040/4688]},
        "feather": 0.2, "enabled": True, "source_range": {"first": 49, "last": 49}
    }]}
    recipe_path = OUT / "region-recipe.json"
    recipe_path.write_text(json.dumps(recipe, indent=2)+"\n", encoding="utf8")
    cache = OUT / "cache"
    cache.mkdir()
    base_env = {k: v for k,v in os.environ.items() if not k.startswith("STREHL_")}
    env_settings = {"STREHL_PYRAMID_WORKERS": "4", "RAYON_NUM_THREADS": "4",
                    "STREHL_CACHE_DIR": str(cache), "STREHL_UI_PROGRESS": "1"}
    receipt = {"source": str(source), "source_count": len(files),
        "source49": {"name": files[49].name, "sha256": sha(files[49])},
        "source_inventory_before": before,
        "exe": str(EXE), "exe_sha256": sha(EXE),
        "original_map": str(OLD_MAP), "map_sha256": sha(OLD_MAP),
        "recipe": recipe, "recipe_sha256": sha(recipe_path),
        "runs": []}
    for label in ["baseline", "repair"]:
        directory=OUT/label
        directory.mkdir()
        warp=directory/"fixed.warpmap.txt"
        warp.write_bytes(OLD_MAP.read_bytes())
        env=base_env|env_settings|{"STREHL_WARPMAP": str(warp)}
        args=[str(EXE), "stack", str(source), "--merge", "pyramid", "--srgb",
              "--out", str(directory/"result.tiff")]
        if label=="repair":
            args += ["--region-recipe", str(recipe_path), "--linear-master", str(directory/"linear-master.tiff")]
        run={"label":label,"argv":args,"environment":env_settings|{"STREHL_WARPMAP":str(warp)},
             "started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
        receipt["runs"].append(run)
        (OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf8")
        start=time.monotonic()
        with (directory/"run.log").open("wb") as log:
            result=subprocess.run(args,env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        run.update(exit_code=result.returncode,wall_seconds=time.monotonic()-start,
                   ended_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                   consumed_map_sha256=sha(warp))
        assert run["consumed_map_sha256"]==receipt["map_sha256"], "fixed placement sidecar changed"
        if result.returncode==0:
            run["output_sha256"]=sha(directory/"result.tiff")
        (OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf8")
        if result.returncode:
            raise SystemExit(f"{label} failed: {directory/'run.log'}")
    receipt["source_inventory_after"]=inventory(source)
    receipt["source49"]["after_sha256"]=sha(files[49])
    assert receipt["source_inventory_after"]==before, "source inventory changed"
    assert receipt["source49"]["sha256"]==receipt["source49"]["after_sha256"],"source49 changed"
    (OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"directory":str(OUT),"runs":receipt["runs"]},indent=2))

if __name__=="__main__":
    main()
