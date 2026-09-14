"""One reference RAW, two independent decoders, native diagnostic crops only."""
from pathlib import Path
import json
import struct
import subprocess
import hashlib
import numpy as np
import rawpy
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "source-review-1"
OUT.mkdir(exist_ok=False)
SOURCE = Path("D:/personal/macro/requests/misc-diagnostic/3d-printer-piece-cpl/DSC00053.ARW")
SECONDARY = ROOT / "experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe"
regions = json.loads((HERE / "baseline-1/views/crops.json").read_text())["regions"]
original = (SOURCE.stat().st_size, SOURCE.stat().st_mtime_ns)
# Native sensor-visible coordinates: render crop starts at plane (48,32).
for r in regions:
    r["sensor_x"] = r["x"] + 96
    r["sensor_y"] = r["y"] + 64
x0 = min(r["sensor_x"] for r in regions)
y0 = min(r["sensor_y"] for r in regions)
x1 = max(r["sensor_x"] + r["width"] for r in regions)
y1 = max(r["sensor_y"] + r["height"] for r in regions)
w, h = x1-x0, y1-y0
with rawpy.imread(str(SOURCE)) as raw:
    patch = raw.raw_image_visible[y0:y1, x0:x1].copy()
    pattern = raw.raw_pattern.copy()
    black = np.asarray(raw.black_level_per_channel, dtype=np.float32)
    white = raw.white_level
    meta = dict(visible_shape=list(raw.raw_image_visible.shape), pattern=pattern.tolist(),
                black=black.tolist(), white=white, camera_whitebalance=raw.camera_whitebalance,
                rawpy=rawpy.__version__, libraw=list(rawpy.libraw_version))
    # Supplementary independent development, same decoder context, no second RAW load.
    developed = raw.postprocess(use_camera_wb=True, no_auto_bright=True, output_bps=16,
        gamma=(1, 1), output_color=rawpy.ColorSpace.sRGB,
        demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD)
    rgb_patches = {r["name"]: developed[r["sensor_y"]:r["sensor_y"]+r["height"],
        r["sensor_x"]:r["sensor_x"]+r["width"]].copy() for r in regions}
    del developed
np.save(OUT / "source-visible-union.npy", patch, allow_pickle=False)
assert pattern.tolist() == [[0,1],[3,2]], "unexpected CFA phase"
result = subprocess.run([str(SECONDARY), str(SOURCE), str(OUT), "reference52", str(y0),
    str(x0), str(h), str(w)], capture_output=True, text=True, timeout=45, check=True)
(OUT / "secondary.log").write_text(result.stdout + result.stderr, encoding="utf-8")
blob = (OUT / "rawler-reference52.bin").read_bytes()
assert struct.unpack("<4I", blob[:16]) == (y0,x0,h,w)
other = np.frombuffer(blob, dtype="<u2", offset=16).reshape(h,w)
different = int(np.count_nonzero(patch != other))
assert different == 0, "independent decode mismatch"
def fixed_display(v):
    # Identical fixed display for every raw green and developed colour patch.
    return np.rint(255 * np.clip(v * 2.809, 0, 1)**(1/2.2)).astype(np.uint8)
for r in regions:
    x, y = r["sensor_x"]-x0, r["sensor_y"]-y0
    a = patch[y:y+r["height"], x:x+r["width"]]
    for label,dx,dy,channel in [("g1",1,0,1),("g2",0,1,3)]:
        signal = (a[dy::2,dx::2].astype(np.float32)-black[channel])/(white-black[channel])
        Image.fromarray(fixed_display(signal)).save(OUT/f"{r['name']}-{label}.png")
    Image.fromarray(fixed_display(rgb_patches[r["name"]].astype(np.float32)/65535)).save(
        OUT/f"{r['name']}-libraw.png")
assert (SOURCE.stat().st_size, SOURCE.stat().st_mtime_ns) == original
receipt = dict(source=str(SOURCE), original_bytes=original[0], original_mtime_ns=original[1],
    output_crop_origin_native=[96,64], reference_index=52, reference_warp="identity",
    decoder=meta, raw_union_xywh=[x0,y0,w,h], regions=regions,
    independent_decode_different_sensels=different,
    raw_u16_sha256=hashlib.sha256(patch.tobytes()).hexdigest(),
    display="fixed exposure gain 2.809 then power 1/2.2, clipped [0,1], round to8; no spatial resampling",
    green_sampling="one displayed pixel per original same-colour green sensel; pitch two native pixels",
    colour_display="LibRaw AHD, camera WB, linear sRGB16, no_auto_bright; supplementary developer, not matched pipeline",
    interpretation="No focus winner selection or sharpness metric; single middle source cannot establish best-focus loss.",
    command="python -X faulthandler experiments/quality-september14/source-review.py")
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
assert sum(p.stat().st_size for p in OUT.iterdir() if p.is_file()) < 64<<20
print(json.dumps(dict(status="SOURCE_PATCHES_READY", different_sensels=different, out=str(OUT))))
