"""Fixed-display native source and baseline patches; no source alignment/resizing."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

import numpy as np
from PIL import Image
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-baseline"
NAMES = ("upper-leg-hairs", "thorax-texture", "turquoise-scales", "elytron-seam")


def display(rgb):
    v = np.clip(rgb * np.float32(3.434), 0, 1)
    encoded = np.where(v <= .0031308, v * 12.92, 1.055 * np.maximum(v, 0)**(1/2.4) - .055)
    return np.rint(encoded * 255).astype(np.uint8)


def main():
    index = int(sys.argv[1]) if len(sys.argv) > 1 else 149
    assert index in (0, 149, 298)
    source_dir = HERE / f"source-{index}"
    map_path = ROOT / "experiments/M-PHASE0-PHASE/src/clib.py"
    map_spec = importlib.util.spec_from_file_location("source_map", map_path)
    clib = importlib.util.module_from_spec(map_spec)
    map_spec.loader.exec_module(clib)
    warp = clib.parse_warpmap(str(BASE / "alignment.txt"))
    a, b = warp["placements"][index]
    path = ROOT / "experiments/M95-demosaic/src/m95dem.py"
    spec = importlib.util.spec_from_file_location("source_mhc", path)
    mhc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mhc)
    raw = np.load(source_dir / "active-cfa-u16.npy", allow_pickle=False)
    metadata = json.loads((source_dir / "decode-receipt.json").read_text())["metadata"]
    wb4 = np.array(metadata["camera_wb"], dtype=np.float32)
    wb = wb4[[0, 1, 2]] / wb4[1]
    xyz_cam = np.array([[.746, -.2365, -.0588], [-.5687, 1.3442, .2474], [-.0624, .1156, .6584]], dtype=np.float32)
    srgb_xyz = np.array([[.4124564, .3575761, .1804375], [.2126729, .7151522, .0721750], [.0193339, .1191920, .9503041]], dtype=np.float64)
    forward = xyz_cam.astype(np.float64) @ srgb_xyz
    matrix = np.linalg.inv(forward / forward.sum(axis=1)[:, None]).astype(np.float32)
    with tifffile.TiffFile(BASE / "stack-master.tiff") as f:
        icc = bytes(f.pages[0].tags[34675].value)
    baseline = tifffile.memmap(BASE / "linear-master.tiff")
    assert baseline.shape == (4596, 6896, 3) and baseline.dtype == np.float32
    witnesses = json.loads((HERE / "baseline-witnesses.json").read_text())["witnesses"]
    out = source_dir / "native-fixed-display"
    out.mkdir(exist_ok=False)
    rows = []
    for witness in witnesses:
        name = witness["name"]
        if name not in NAMES:
            continue
        x, y, w, h = witness["rect_xywh"]
        center = complex(3516, 2344)
        mapped = center + a * (complex(x+68+w/2, y+46+h/2)-center) + 2*b
        sx, sy = (int(round((mapped.real-w/2)/2))*2,
                  int(round((mapped.imag-h/2)/2))*2)
        # Rounded-even centre preserves native source sampling and Bayer phase.
        halo = 8
        cut = raw[sy-halo:sy+h+halo, sx-halo:sx+w+halo]
        yy, xx = np.indices(cut.shape)
        phase = np.where((xx+yy) % 2, 1, np.where(yy % 2, 2, 0))
        normalized = np.maximum(cut.astype(np.float32)-np.float32(512), 0) * wb[phase] / np.float32(15360-512)
        camera = mhc.demosaic_mhc(normalized)[halo:-halo, halo:-halo]
        source = camera @ matrix.T
        comparison = baseline[y:y+h, x:x+w].copy()
        for arm, rgb in (("source", source), ("baseline", comparison)):
            assert rgb.dtype == np.float32 and np.isfinite(rgb).all()
            np.save(out / f"{name}-{arm}-linear.npy", rgb, allow_pickle=False)
            Image.fromarray(display(rgb)).save(out / f"{name}-{arm}.png", icc_profile=icc)
        crop = raw[sy:sy+h, sx:sx+w]
        for green, dx, dy in (("g1", 1, 0), ("g2", 0, 1)):
            plane = np.maximum(crop[dy::2, dx::2].astype(np.float32)-512, 0) / np.float32(15360-512)
            Image.fromarray(display(plane)).save(out / f"{name}-{green}.png")
        rows.append({"name": name, "baseline_native_xywh": [x,y,w,h], "source_active_xywh": [sx,sy,w,h],
                     "mapped_source_center": [mapped.real, mapped.imag],
                     "resampled": False, "greens_native_pitch": 2, "rgb_native_pitch": 1,
                     "known_cfa_sites_preserved": bool(np.array_equal(mhc.mosaic_rggb(camera), normalized[halo:-halo,halo:-halo]))})
    receipt = {"schema": 1, "source_index": index, "selection": "Reference anchor or endpoint, not chosen using image sharpness.",
               "placement": {"a": [a.real,a.imag], "b_plane": [b.real,b.imag], "scale": abs(a)},
               "source_to_reference": "Crop center mapped reference->source using pinned similarity, rounded even. No source rotation/scale interpolation or CA correction; endpoints have native framing differences.",
               "matched_display": "Both source and baseline LINEAR sRGB: fixed gain3.434 then standard sRGB transfer, clamp0..1, round8; no local fitting, sharpening, resizing or denoising.",
               "source_development": "Baseline levels512/15360, as-shot WB, repository M95 f32 MHC port with8pixel plugin halo, row-neutralized baseline camera matrix; no sensor clipping repair.",
               "scope": "Structure-support witness. Not byte-identical native product development: source lacks baseline CA gather/merge/final-MHC chain; float operation order may differ. Fixed display differs from baseline automatic-tone master equally for both arms.",
               "wb": wb.tolist(), "xyz_to_camera": xyz_cam.tolist(), "camera_to_srgb": matrix.tolist(),
               "mhc_source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rows": rows}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Developed {len(rows)} identity-anchor native witnesses and matched-display baseline patches.")


if __name__ == "__main__":
    main()
