"""Read only frozen u16 caches at unchanged coordinates; no fit or RAW decode."""
from pathlib import Path
import hashlib
import importlib.util
import json
import time

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CACHE = ROOT/"outputs/raw-quality-2026-10-26/insect-placement-cache"
OUT = HERE/"phase-inspection-1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    start = time.monotonic()
    manifest = json.loads((CACHE/"cache.json").read_text())
    assert digest(HERE/"run.py") == manifest["script_sha256"]
    spec = importlib.util.spec_from_file_location("frozen_insect_profile", HERE/"run.py")
    model = importlib.util.module_from_spec(spec); spec.loader.exec_module(model)
    transforms = model.transforms()
    phases = {"R": (0,0), "G1": (1,0), "G2": (0,1), "B": (1,1)}
    OUT.mkdir(exist_ok=False)
    sources = {}; rows = []
    for record in manifest["records"]:
        path = Path(record["cache"])
        assert digest(path) == record["cache_sha256"]
        data = np.load(path, allow_pickle=False)
        index = record["index"]
        t = dict(transforms); t["index"] = t[index]
        for name, center in model.CENTERS.items():
            for phase, parity in phases.items():
                for axis in ("x", "y"):
                    plan = model.query(center, axis, t, parity)
                    values = model.profile(data, plan)
                    offsets = model.OFFSETS
                    mid = float(np.median(values[np.abs(offsets) <= 1]))
                    lo = float(np.median(values[(offsets >= -16) & (offsets <= -12)]))
                    hi = float(np.median(values[(offsets >= 12) & (offsets <= 16)]))
                    key = f"{index}/{name}/{phase}/{axis}"
                    rows.append({"key":key, "index":index, "feature":name, "phase":phase, "axis":axis,
                        "central_median_above_black_dn":mid-512,
                        "left_shoulder_minus_center_dn":lo-mid, "right_shoulder_minus_center_dn":hi-mid,
                        "profile_min_max_above_black_dn":[float(np.min(values))-512,float(np.max(values))-512],
                        "raw_dn_values":values.tolist()})
        if index == 105:
            icc = Image.open(ROOT/"experiments/raw-quality-2026-10-26/photo-review/source-locator-1/thorax-texture-source-105.png").info["icc_profile"]
            for phase, (dx, dy) in phases.items():
                plane = data[dy::2, dx::2]
                f = np.maximum((plane.astype(np.float32)-512)/(15360-512)*3.434, 0)
                f = np.where(f <= .0031308,12.92*f,1.055*f**(1/2.4)-.055)
                p8 = np.rint(np.clip(f,0,1)*255).astype(np.uint8)
                rgb = np.repeat(p8[..., None],3,axis=2)
                Image.fromarray(rgb).save(OUT/f"source105-{phase}-physical-sensels.png",icc_profile=icc)
                np.save(OUT/f"source105-{phase}-u16.npy",plane,allow_pickle=False)
        sources[index] = {"path":str(path), "sha256":record["cache_sha256"]}
    # Source105 profiles: all four channels share axes and a DN scale. Neighbor
    # values are retained in JSON; no shifts or maxima are fitted to them.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"R":"#b73030","G1":"#147d32","G2":"#46a684","B":"#295acb"}
    source105 = [r for r in rows if r["index"] == 105]
    ymax = max(r["profile_min_max_above_black_dn"][1] for r in source105)
    ymin = min(0., min(r["profile_min_max_above_black_dn"][0] for r in source105))
    for feature in model.CENTERS:
        fig, axes = plt.subplots(2,1,figsize=(7,6),sharex=True,sharey=True)
        for ax, axis in zip(axes,("x","y")):
            for r in source105:
                if r["feature"] != feature or r["axis"] != axis: continue
                ax.plot(model.OFFSETS,np.array(r["raw_dn_values"])-512,color=colors[r["phase"]],label=r["phase"])
            ax.axvspan(-1,1,color="gray",alpha=.15)
            for value in (-16,-12,-10,-1,1,10,12,16): ax.axvline(value,color="gray",alpha=.25,lw=.5)
            ax.set(title=f"Frozen feature{feature}, {axis} profile",ylabel="Original DN minus512",ylim=(ymin,ymax*1.05))
            ax.legend(ncol=4,fontsize=8)
        axes[-1].set_xlabel("Offset in source105 native pixels; center and windows unchanged")
        fig.tight_layout(); fig.savefig(OUT/f"feature-{feature}-all-phases.png",dpi=120); plt.close(fig)
    for record in manifest["records"]:
        assert digest(record["cache"]) == record["cache_sha256"]
    result = {"status":"FIXED_ALL_PHASE_DESCRIPTION_NO_FIT", "sources":sources,
        "cache_manifest_sha256":digest(CACHE/"cache.json"), "script_sha256":digest(__file__),
        "frozen_observation_sha256":digest(HERE/"run.py"), "rows":rows,
        "elapsed_seconds":time.monotonic()-start,
        "display":"Four256-square direct phase arrays, pitch2native pixels, same black512/white15360/gain3.434/sRGB grayscale; no white balance or per-phase normalization; ICC retained. Plots share DN scale.",
        "limits":"No moving windows, edge estimates, motion fits, private noise estimate, RAW reads or photographic quality score."}
    (OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    assert result["elapsed_seconds"] < 10, "scheduled postflight exceeded10seconds"
    print(json.dumps({"elapsed_seconds":result["elapsed_seconds"], "source105_contrasts":[{k:r[k] for k in ("feature","phase","axis","central_median_above_black_dn","left_shoulder_minus_center_dn","right_shoulder_minus_center_dn")} for r in source105]}),flush=True)


if __name__ == "__main__":
    main()
